# Proposed drill nets — run #36, RUN rung, batch 3

`src/drill.py` is owned by another agent this shift, so these are written out rather than added.
Each names the guard, the attack that must be REFUSED, and what a BREACHED verdict means.

Two of the four batch-3 fixes are already pinned inside `verify_math.py` and do not need a net
(`backfill_source`'s ranking, orders ff470a877ac5 + d673aa4d609a; the zero-worlds `main()` calls,
order 96c4be60fb92). The two below are lost-update guards, which is the class `drill.py` already
attacks with a live second writer — the shape `d3313adbf641` established for `scout._mutate` —
and a code-shape check would not tell whether they actually refuse.

---

## NET 1 — `endpoint.register` must REFUSE a stale write, not merely land atomically

**Guard.** `endpoint.register()` (order 6dc3b3682fc8) now takes `silence.digest_of(PAGES_FILE)`
before it reads, writes its merged copy to a pid-stamped temp, and lands it through
`silence.replace_if_unchanged`. On a refusal it RE-READS and re-merges, up to 8 attempts, then
raises rather than reporting success.

**The attack.** Land a second writer's key inside the window between this writer's digest and its
write, then assert BOTH keys survive.

```python
# in a temp dir, with EP.PAGES_FILE pointed at it
EP.register("SrcA", ["https://a.example/1"])
real = silence.digest_of
fired = []

def racing_digest(path):
    d = real(path)
    if path == EP.PAGES_FILE and not fired:
        fired.append(1)
        cur = json.load(open(path, encoding="utf-8"))
        cur["SrcC"] = ["https://c.example/1"]        # the OTHER process, landing in the window
        silence.write_json(path, cur, indent=1, sort_keys=True)
    return d

silence.digest_of = racing_digest
try:
    EP.register("SrcD", ["https://d.example/1"])
finally:
    silence.digest_of = real
reg = json.load(open(EP.PAGES_FILE, encoding="utf-8"))
HELD = sorted(reg) == ["SrcA", "SrcC", "SrcD"] and reg["SrcD"] == ["https://d.example/1"]
```

**BREACHED means** `SrcC` is absent: the write landed over a file it had not read, and a source
that had just been registered from another process is now uncitable — `source_pages()` answers
`[]` for it ever after, with no error anywhere. Verified HELD against the current code.

**What defeats this net.** Anyone replacing the CAS with a bare `silence.write_json(PAGES_FILE,
d, ...)` on the grounds that write_json is "already atomic". It is — atomicity is about TORN
files and says nothing about STALENESS. The net must attack the second-writer window
specifically, not merely assert the file parses after a write; a net that only checks the result
is valid JSON passes on the exact defect. Equally: a net that patches `replace_if_unchanged` to
count calls rather than watching the CONTENT would pass a `register()` that calls it and ignores
the verdict, which is the `d3313adbf641` lesson.

---

## NET 2 — `pipeline.write_record` must merge on a SAME-COUNT drift

**Guard.** `write_record` (order 1c2ea97cdc36) now decides merge-vs-overwrite from two
independent signals: entry count, and `_entry_digest` over the entry names. It used to consult
count alone.

**The attack.** Rewrite the disk copy with the SAME NUMBER of entries under DIFFERENT names,
then write a stale in-memory copy over it and assert the disk names survive.

```python
json.dump({"source": "S", "entries": [{"name": "Alpha"}, {"name": "Beta"}]}, open(p, "w"))
stale = {"source": "S", "entries": [{"name": "Alpha"}, {"name": "OldBeta", "catalogued": True}]}
PL.write_record(p, stale)
after = json.load(open(p, encoding="utf-8"))
HELD = sorted(e["name"] for e in after["entries"]) == ["Alpha", "Beta"]
```

**BREACHED means** the file holds `OldBeta`: a rename, a dedup-then-add, or any same-size cast
correction made by `write_record_catalogue` / `ingest_doc` / `catalogue_web` was silently
reverted by the pipeline's hours-old copy. This is the marvel.json 30,207→1,051 shape at a
granularity the count test cannot see. Verified HELD; the log line reads
`write_record: rec.json drifted on disk by content (2 -> 2 entries); merged`, and the `2 -> 2` is
the whole point — it is exactly what the old signal read as "no drift".

**What defeats this net.** A fixture whose two versions differ in COUNT as well as names: that
passes on the old count-only code too, so the net would report HELD against the very defect it
was written for. The counts must be equal and the names must differ — nothing else attacks the
right signal. Also keep the companion assertion that an IDENTICAL-name write still takes the
fast path (`after["entries"][0]["catalogued"] is True`), or a "fix" that merges unconditionally
would pass this net while silently discarding every judgment field the pipeline computes.
