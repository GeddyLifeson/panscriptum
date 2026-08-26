"""CORPUS DB — the library as a queryable table, so a question costs a line instead of a script.

WHY THIS EXISTS, AND WHY IT IS SQLITE.

Every question anyone asks about this corpus currently costs a throwaway Python script that walks
216 JSON files and 109,295 entries. This session alone wrote a dozen of them -- how many entries
are excluded, which sources have no host, which entries are unjudged in closed batches, how many
cache files lack an entity field. Each one was correct and each one was thrown away, so the next
question started from nothing and the answers were never comparable.

WHAT WAS EVALUATED, AND WHAT THE MEASUREMENT SAID. The owner asked whether established tools
would beat home-made ones -- correctly, and the answer is mostly yes but almost none of them
apply here. Measured on this machine:

    model + network wall time, per hour   ~7,070 s (across parallel workers)
    coverage.measure(), the slowest CPU op    21.5 s
    load all 216 records (81 MB of JSON)      0.89 s
    load the 88 MB manifest                   0.63 s

CPU work is roughly 0.3% of this pipeline's wall clock, and the GPU sits at 99% utilisation with
9.6 of 10.2 GB resident. So Cython, Rust/PyO3, SIMD and PGO would optimise a rounding error, and
CUDA/cuBLAS would actively COMPETE with Ollama for the one resource that is actually saturated.
Ray and Dask solve distribution on a single machine that has no distribution problem. asyncio and
Tokio would raise fetch concurrency, which is the opposite of what a deliberately rate-limited
crawler wants. Protobuf and Cap'n Proto would parse faster than JSON -- and make the corpus
unreadable to a person, which for a project whose DATA IS THE PRODUCT is a real cost against a
saving that does not matter.

DuckDB was the one strong candidate: in-process OLAP, no server, ideal for exactly this. It
installs and then FAILS TO LOAD -- `An Application Control policy has blocked this file` -- the
same Norton interference that breaks Python's HTTPS here. So it is not available on this machine,
and pretending otherwise would be recommending a tool that cannot run.

SQLite is what remains and it is genuinely the right size. It is in the standard library, needs
nothing installed or allow-listed, and 200,000 rows insert in 0.22s and aggregate in 0.015s --
against a corpus of 109,295 entries. Columnar analytics would be the correct answer at a hundred
times this scale; here it would be equipment for a problem that does not exist.

WHAT THIS IS NOT. Not a second source of truth. The JSON records remain canonical and are the
only thing written by `pipeline.write_record`; this is a DERIVED INDEX, rebuilt from them, and
anything that disagrees with the records is this file being stale. It is read-only by contract.
"""
import argparse
import glob
import json
import os
import sqlite3
import sys
import threading
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

DB = os.path.join(HERE, "state", "corpus.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS source (
    name TEXT PRIMARY KEY, host TEXT, spine TEXT, entries INTEGER,
    cited INTEGER, read INTEGER, no_page INTEGER, not_attempted INTEGER, no_host INTEGER
);
CREATE TABLE IF NOT EXISTS entry (
    source TEXT, name TEXT, category TEXT, type TEXT,
    catalogued INTEGER, excluded INTEGER, magnitude TEXT,
    has_scale_note INTEGER, description_chars INTEGER
);
CREATE INDEX IF NOT EXISTS entry_source ON entry(source);
CREATE INDEX IF NOT EXISTS entry_name   ON entry(name);
CREATE INDEX IF NOT EXISTS entry_cat    ON entry(category);
CREATE TABLE IF NOT EXISTS evidence (
    entity TEXT, host TEXT, feats INTEGER, pages INTEGER,
    chars INTEGER, refused INTEGER, provenance TEXT
);
CREATE INDEX IF NOT EXISTS evidence_entity ON evidence(entity);
CREATE INDEX IF NOT EXISTS evidence_host   ON evidence(host);
"""


def connect(path=None, readonly=False):
    """Open the index. `path=None` means the CURRENT value of DB, read at call time.

    The default used to be `path=DB`, which Python binds ONCE at import: repointing
    `corpus_db.DB` at a temp database then left `query`, `age_seconds` and `freshness` all
    silently answering from the live one. Nothing in production repoints DB, so this was never
    a wrong answer in a run -- but it is exactly wrong when somebody proves a change against a
    throwaway index and gets the real one's numbers back, believing they proved something.
    """
    path = DB if path is None else path
    if readonly:
        return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return sqlite3.connect(path)


def rebuild(include_evidence=True, evidence_limit=None):
    """Rebuild the index from the canonical JSON. -> counts.

    WHOLE REBUILD, NOT INCREMENTAL, and deliberately: an incremental index has to be told what
    changed, and being wrong about that produces a derived view that quietly disagrees with the
    records -- exactly the class of silent, outliving failure this project keeps paying for. The
    whole rebuild takes seconds; correctness is cheaper than cleverness at this size.

    WHAT WOULD NOT PARSE IS COUNTED AND NAMED, in `unreadable_records` / `unreadable_evidence`,
    and the counts are written into `meta` so a reader of the index can see the caveat without
    having the rebuild's stdout. This used to be `except Exception: continue` -- the record was
    dropped in silence and `n_src`/`n_entry` were then reported as the corpus TOTALS. A partial
    count read as a total is precisely how a run here talks itself into work that is already
    done, or out of work that is not; `drift()` a few functions down already records the same
    failure with `silence.note`, so the module was inconsistent with itself about it.
    """
    t0 = time.time()
    # THE TMP NAME CARRIES PID AND THREAD. A fixed `DB + ".tmp"` plus the unconditional delete
    # below meant two concurrent rebuilds destroyed each other's in-progress database: the
    # second one's first act was to unlink the file the first was still writing into, and
    # whichever finished last landed a half-built index over a whole one. The project states
    # this rule in `silence.write_json`'s docstring (silence.py:358-361) and restates it in
    # `module_index.py:88-90`; this was the site that did not obey it. With a unique name the
    # pre-delete can only ever remove THIS process's own leftovers.
    tmp = "%s.%d.%d.tmp" % (DB, os.getpid(), threading.get_ident())
    for p in (tmp, tmp + "-journal"):
        if os.path.exists(p):
            os.remove(p)
    con = connect(tmp)
    con.executescript(SCHEMA)

    hosts = {}
    try:
        with open(os.path.join(HERE, "data", "WIKI_HOSTS.json"), encoding="utf-8") as f:
            hosts = json.load(f) or {}
    except Exception:
        silence.note("corpus_db.py:hosts")

    cov = {}
    try:
        with open(os.path.join(HERE, "data", "COVERAGE.json"), encoding="utf-8") as f:
            cov = {r.get("source"): r for r in json.load(f)}
    except Exception:
        silence.note("corpus_db.py:coverage")

    # THE RESOLVER, NOT THE RAW TABLE. This module first read CHARTER_SPINE_CODES.json into a
    # dict and looked sources up in it directly, and the derived index promptly reported **36
    # sources with no spine code, 13,417 entries** -- a figure alarming enough that it was taken
    # for a curatorial backlog and nearly acted on as one.
    #
    # It was wrong. `address.spine_code_for()` is the real lookup and it does far more than a
    # dict get: letter-level equality (the index writes "Soulcalibur", the roll writes "Soul
    # Calibur"), whole-word containment, and an order-independent token fallback that resolves
    # "all Black Ops" to "Black Ops (all)". Run through it, **35 of the 36 resolve** and the
    # true number of unshelved sources is ONE -- `Bone (Jeff Smith)`, 86 entries.
    #
    # The lesson is the one this file's own header states and then failed to obey: a derived
    # index must derive through the SAME code the library uses, never by reimplementing the
    # lookup more simply. A second implementation of a rule is a second answer to it. A drill
    # net now compares this column against the resolver on every run.
    try:
        import address as _address
        _spine_for = _address.spine_code_for
    except Exception:
        silence.note("corpus_db.py:spine-resolver")
        _spine_for = None

    n_src = n_entry = 0
    unreadable_records = []
    unreadable_evidence = []
    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception as e:
            # NAMED, NOT SKIPPED. The file is still excluded -- there is nothing to insert --
            # but a source silently missing from the index reads downstream as a source with
            # no entries, which is the opposite of "its record could not be read".
            silence.note("corpus_db.py:record")
            unreadable_records.append("%s (%s)" % (os.path.basename(p), type(e).__name__))
            continue
        src = rec.get("source")
        c = cov.get(src) or {}
        code = None
        if _spine_for and src:
            try:
                code = _spine_for(src)
            except Exception:
                silence.note("corpus_db.py:spine-lookup")
            if code == "UNASSIGNED":
                code = None            # NULL means unshelved, and only the resolver may say so
        con.execute(
            "INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)",
            (src, hosts.get(src), code, len(rec.get("entries") or []),
             c.get("cited"), c.get("read"), c.get("no_page"),
             c.get("not_attempted"), c.get("no_host")))
        n_src += 1
        rows = []
        for e in (rec.get("entries") or []):
            if not isinstance(e, dict):
                continue
            rows.append((src, e.get("name"), (e.get("category") or "").split("(")[0].strip(),
                         e.get("type"), 1 if e.get("catalogued") else 0,
                         1 if e.get("excluded") else 0, e.get("magnitude"),
                         1 if e.get("scale_note") else 0,
                         len(e.get("description") or "")))
        con.executemany("INSERT INTO entry VALUES (?,?,?,?,?,?,?,?,?)", rows)
        n_entry += len(rows)

    n_ev = 0
    if include_evidence:
        files = (glob.glob(os.path.join(HERE, "data", "readfeats", "*", "*.json"))
                 + glob.glob(os.path.join(HERE, "data", "feats", "*", "*.json")))
        if evidence_limit:
            files = files[:evidence_limit]
        batch = []
        for p in files:
            try:
                with open(p, encoding="utf-8") as f:
                    d = json.load(f)
            except Exception as e:
                silence.note("corpus_db.py:evidence")
                unreadable_evidence.append("%s (%s)"
                                           % (os.path.basename(p), type(e).__name__))
                continue
            if not isinstance(d, dict):
                # Parsed, but not an evidence document. Also counted: a JSON list or string
                # where a feats file should be is a corrupt file that happens to parse.
                unreadable_evidence.append("%s (not a dict)" % os.path.basename(p))
                continue
            batch.append((d.get("entity"), d.get("host"),
                          len(d.get("feats") or []),
                          len(d.get("pages_read") or d.get("pages") or []),
                          int(d.get("chars_read") or 0),
                          len(d.get("pages_refused") or {}),
                          (d.get("provenance") or {}).get("roll")))
            if len(batch) >= 5000:
                con.executemany("INSERT INTO evidence VALUES (?,?,?,?,?,?,?)", batch)
                n_ev += len(batch)
                batch = []
        if batch:
            con.executemany("INSERT INTO evidence VALUES (?,?,?,?,?,?,?)", batch)
            n_ev += len(batch)

    con.execute("INSERT OR REPLACE INTO meta VALUES ('built_at', ?)", (str(time.time()),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('sources', ?)", (str(n_src),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('entries', ?)", (str(n_entry),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('evidence', ?)", (str(n_ev),))
    # The caveat travels WITH the index, not only in the rebuild's stdout. A query answered
    # from this database months from now should be able to find out that its totals were taken
    # over a corpus two files of which could not be read.
    con.execute("INSERT OR REPLACE INTO meta VALUES ('unreadable_records', ?)",
                (str(len(unreadable_records)),))
    con.execute("INSERT OR REPLACE INTO meta VALUES ('unreadable_evidence', ?)",
                (str(len(unreadable_evidence)),))
    con.commit()
    con.close()
    # THE VERDICT OF THE FINAL WRITE HAS TO REACH THE CALLER. `replace_retry` returns False
    # rather than raising when a reader holds `corpus.db` open, which is this module's NORMAL
    # situation -- the whole point of the file is that other processes read it. Dropped, the
    # rebuild printed full counts and exited 0 over an unchanged database, `age_seconds()` went
    # on reporting the OLD `built_at`, and every later query answered from stale data. Same
    # shape as BUGS M36.
    landed = silence.replace_retry(tmp, DB)
    if not landed:
        # `replace_retry` records a denial and returns False; it does not unlink the temp file.
        # With the pid/thread name above, every denied rebuild would otherwise leave its own
        # multi-megabyte orphan behind forever. Losing it costs nothing -- a rebuild is a pure
        # function of the records and takes under a minute -- while a directory filling with
        # near-identical temp databases is a real hazard next to the live one.
        try:
            os.remove(tmp)
        except OSError:
            silence.note("corpus_db.py:tmp-orphan")
    return {"sources": n_src, "entries": n_entry, "evidence": n_ev,
            "seconds": round(time.time() - t0, 2), "landed": landed,
            "unreadable_records": unreadable_records,
            "unreadable_evidence": unreadable_evidence}


def age_seconds():
    """How old the index is in seconds, or None. -> float|None.

    None IS AMBIGUOUS AND CALLERS MUST NOT RESOLVE IT THEMSELVES. It means any of: no database
    file, a database that cannot be opened (locked by a writer, or corrupt), or one that does
    not record when it was built. `freshness()` distinguishes all three and supplies the reason
    in words; every reader in this module now asks it instead, because `main()` used to print
    None as "absent -- run --rebuild" and a present-but-locked database is not an absent one --
    --rebuild cannot fix the first and is the whole remedy for the second.
    """
    con = None
    try:
        con = connect(readonly=True)
        v = con.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        return time.time() - float(v[0]) if v else None
    except Exception:
        silence.note("corpus_db.py:age")
        return None
    finally:
        # THE HANDLE IS CLOSED ON THE FAILING PATH TOO. `con.close()` sat after the query, so a
        # corrupt or locked database raised past it and left the connection open for the life
        # of the process -- and on Windows a held handle is a DENIED RENAME, which is the exact
        # way `rebuild()` fails to land. The unreadable-index reader was quietly making the
        # unreadable index harder to replace.
        if con is not None:
            try:
                con.close()
            except Exception:
                silence.note("corpus_db.py:age-close")


def freshness():
    """Is this index still telling the truth about the records? -> dict, always.

    MEASURED WHEN THE FIRST DRILL NET RAN, and it settled the design. The index was rebuilt at
    109,295 entries; twenty-seven minutes later the records held 117,908. **8,613 entries in
    under half an hour** -- the cataloguing crawl is genuinely that fast, and it means no
    staleness TOLERANCE can work. A 2% band expires in seven minutes. A nightly rebuild would
    be wrong by tens of thousands by morning.

    So this index does not promise to be fresh. It promises to SAY how stale it is, every time
    it is read, which is the only claim it can keep. That distinction is the whole lesson of
    this project's inspector nets: a report that has drifted from the thing it describes is
    worse than no report, and the difference between the two is entirely whether the report
    admits its own age.

    Staleness is decided by MTIME, not by counting: any record file written after the index was
    built means the index is behind, and 216 stat calls cost microseconds where a recount costs
    the better part of a second on every query. `drift()` does the expensive exact version for
    when somebody actually needs the number.
    """
    out = {"built_at": None, "age_seconds": None, "stale": True,
           "newer_records": 0, "reason": "no index"}
    if not os.path.exists(DB):
        return out
    try:
        cols, rows = query("SELECT value FROM meta WHERE key='built_at'")
    except Exception:
        out["reason"] = "index unreadable"
        return out
    if not rows:
        out["reason"] = "index does not record when it was built"
        return out
    built = float(rows[0][0])
    out["built_at"] = built
    out["age_seconds"] = time.time() - built
    newer = 0
    for p in glob.glob(os.path.join(HERE, "data", "records", "*.json")):
        try:
            if os.path.getmtime(p) > built:
                newer += 1
        except OSError:
            newer += 1                 # a record we cannot stat is a record we cannot vouch for
    out["newer_records"] = newer
    out["stale"] = newer > 0
    out["reason"] = ("%d record file(s) written since the index was built" % newer
                     if newer else "no record has changed since the index was built")
    return out


def drift():
    """The exact entry-count gap between the index and the records. -> (indexed, real, gap).

    The expensive, precise version of `freshness()`. Costs a full pass over the records, which
    is why it is not on the query path -- but when the answer matters, an approximation of how
    wrong the index is would just be a second thing to be wrong about.
    """
    indexed = None
    try:
        cols, rows = query("SELECT value FROM meta WHERE key='entries'")
        if rows:
            indexed = int(rows[0][0])
    except Exception:
        silence.note("corpus_db.py:drift-index")
    real = 0
    for p in glob.glob(os.path.join(HERE, "data", "records", "*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                real += len(json.load(f).get("entries") or [])
        except Exception:
            silence.note("corpus_db.py:drift-record")
    gap = None if indexed is None else real - indexed
    return indexed, real, gap


def _freshness_banner():
    """The line printed above every result. -> str.

    ABOVE the numbers, not below them and not behind a flag. A staleness warning a reader has
    to go looking for is a staleness warning that will be missed exactly when it matters, and
    this index is stale within minutes of every rebuild.
    """
    f = freshness()
    if f["age_seconds"] is None:
        # THE REASON `freshness()` COMPUTED, not a guess. This line said "NO INDEX -- run
        # --rebuild" for all three of its causes, so an index that was present but LOCKED or
        # CORRUPT was reported as one that had never been built, and the suggested remedy was
        # the one that cannot work.
        #
        # The words NO INDEX stay in the line: `drill.py`'s
        # `stale_index_says_so_where_the_numbers_are` net asserts them for exactly this state,
        # and a net is not a formality to route around.
        if not os.path.exists(DB):
            return "  [ NO INDEX — none on disk. Run --rebuild. These are not results. ]"
        return ("  [ NO INDEX — the file IS on disk and unusable: %s. These are not results, "
                "and --rebuild may not be the remedy. ]" % f["reason"])
    mins = f["age_seconds"] / 60
    if not f["stale"]:
        return "  [ index built %.0f min ago; no record has changed since ]" % mins
    return ("  [ STALE: index built %.0f min ago, %d record(s) written since. "
            "Counts below are a FLOOR, not a total. --rebuild for current. ]"
            % (mins, f["newer_records"]))


def query(sql, args=()):
    """Run a read-only query. -> (columns, rows)."""
    con = connect(readonly=True)
    try:
        cur = con.execute(sql, args)
        cols = [d[0] for d in (cur.description or [])]
        return cols, cur.fetchall()
    finally:
        con.close()


# Questions this session answered with throwaway scripts. Kept so the next reader gets the
# answer rather than the archaeology -- and so two people asking the same question get the
# same number.
#
# NO `LIMIT`. SIX OF THESE NINE CARRIED ONE (LIMIT 15, and types LIMIT 25) while `unaddressed`,
# `hostless` and `categories` deliberately carried none, which is the same file understanding
# the rule in one paragraph and breaking it in the next. Hard Rule 0: ranking is encouraged,
# ranking THEN TRUNCATING is forbidden, because a cap on an ordered listing does not fail -- it
# returns a smaller universe wearing the same shape as the real one. `unjudged` and
# `worst_cited` are WORK LISTS: source #16 in either is a source nobody will ever be told about,
# and the comment above promising "the same number" was promising the same TRUNCATED number.
#
# The other four are distributions over bounded domains -- 216 sources, ~130 evidence hosts, a
# few dozen types -- so the cut was buying nothing even as a display. `datasette_metadata()`
# renders this dict verbatim, so every cap was inherited by the browsable front end too, where
# a truncated table looks exactly like a complete one.
#
# If a listing is genuinely long, the answer is `--sql` with the reader's own LIMIT, chosen by a
# person who can see what they are cutting off. It is never a smaller universe by default.
CANNED = {
    "coverage": "SELECT name, entries, cited, read, no_page, not_attempted "
                "FROM source ORDER BY entries DESC",
    "unaddressed": "SELECT name, entries FROM source WHERE spine IS NULL "
                   "ORDER BY entries DESC",
    "hostless": "SELECT name, entries FROM source WHERE host IS NULL ORDER BY entries DESC",
    "categories": "SELECT category, COUNT(*) n FROM entry GROUP BY category ORDER BY n DESC",
    "types": "SELECT type, COUNT(*) n FROM entry WHERE type IS NOT NULL "
             "GROUP BY type ORDER BY n DESC",
    "unjudged": "SELECT source, COUNT(*) n FROM entry WHERE catalogued=0 AND excluded=0 "
                "GROUP BY source ORDER BY n DESC",
    "evidence": "SELECT host, COUNT(*) files, SUM(feats) feats, SUM(pages) pages "
                "FROM evidence GROUP BY host ORDER BY feats DESC",
    "refused": "SELECT host, COUNT(*) n FROM evidence WHERE refused>0 GROUP BY host "
               "ORDER BY n DESC",
    "worst_cited": "SELECT name, entries, cited, ROUND(100.0*cited/entries,1) pct "
                   "FROM source WHERE entries>=40 ORDER BY pct ASC",
}


def datasette_metadata(path=None):
    """Write Datasette's config from CANNED, so there is ONE list of canned queries. -> path.

    THE APP THE OWNER ASKED FOR, AND WHY IT IS THIS ONE. `--sql` above is a query tool for
    someone who already knows SQL and already knows the schema. Datasette is the browsable
    front end: every table faceted and filterable, every query also available as JSON at the
    same URL with `.json` appended, and the canned queries below as named links a person can
    click without writing anything. It is free, MIT, pure Python, installs from PyPI, and --
    the thing that actually settled it on this machine -- it RUNS here, which DuckDB does not.

    GENERATED, NEVER HAND-EDITED. The queries live in `CANNED` and this function renders them.
    A second hand-maintained copy of the same list is how the web UI and the CLI start
    answering the same question differently, which is the failure this whole module exists to
    end. If you add a query, add it to `CANNED`.

    Served read-only and bound to localhost. This is a derived index of a public-facing corpus,
    but the halt file, the ledgers and the owner's rulings are not in it and must not become
    reachable by pointing a web server at `state/`.
    """
    path = path or os.path.join(HERE, "state", "datasette.json")
    doc = {
        "title": "The Panscriptum — corpus index",
        "description": ("A DERIVED index, rebuilt from data/records/*.json by "
                        "src/corpus_db.py. The JSON records remain canonical; anything here "
                        "that disagrees with them is this database being stale."),
        "databases": {
            "corpus": {
                "queries": {
                    k: {"sql": v, "title": k.replace("_", " ")}
                    for k, v in sorted(CANNED.items())
                }
            }
        },
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return path


def serve_command():
    """-> the exact command line that serves the index, with the config this module wrote."""
    return ('datasette "%s" --metadata "%s" --setting sql_time_limit_ms 8000 '
            '--host 127.0.0.1 --port 8801'
            % (DB, os.path.join(HERE, "state", "datasette.json")))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--drift", action="store_true",
                    help="the exact entry-count gap between this index and the records")
    ap.add_argument("--serve", action="store_true",
                    help="write Datasette's config and print the command that serves it")
    ap.add_argument("--no-evidence", action="store_true",
                    help="skip the 109k evidence files (much faster)")
    ap.add_argument("--sql", help="a read-only query")
    ap.add_argument("--canned", help="one of: " + ", ".join(sorted(CANNED)))
    a = ap.parse_args()

    if a.drift:
        indexed, real, gap = drift()
        print("  indexed %s | records %s | gap %s" % (indexed, real, gap))
        print(_freshness_banner())
        return 0

    if a.rebuild:
        # The gap BEFORE, so the rebuild says what it closed rather than only what it wrote.
        # A rebuild that reports 117,908 entries tells you its own size; one that reports
        # "closed a gap of 8,613" tells you how wrong the answers were until you ran it, which
        # is the number that decides how often this needs running.
        _, _, before = drift()
        got = rebuild(include_evidence=not a.no_evidence)
        if not got["landed"]:
            # A rebuild that could not land is not a rebuild. Say so and fail, rather than
            # print counts that describe a database still sitting in a temp file.
            print("REBUILD DID NOT LAND: a reader holds %s open; the old index is unchanged "
                  "and every query still answers from it. Close the readers and re-run." % DB)
            return 1
        print("rebuilt: %(sources)d sources, %(entries)d entries, %(evidence)d evidence rows "
              "in %(seconds)ss" % got)
        # WHAT DID NOT PARSE, BEFORE THE TOTALS ARE BELIEVED. Named in full, never counted and
        # cut: the file that would not read is the one somebody has to go look at.
        for label, bad in (("record", got["unreadable_records"]),
                           ("evidence", got["unreadable_evidence"])):
            if bad:
                print("  WARNING: %d %s file(s) COULD NOT BE PARSED and are missing from the "
                      "counts above -- those counts are a FLOOR, not a total:" % (len(bad), label))
                for name in bad:
                    print("      " + name)
        if before:
            print("  closed a gap of %d entries the index was missing" % before)
        print("  -> %s (%.1f MB)" % (DB, os.path.getsize(DB) / 1e6))
        return 0

    if a.serve:
        p = datasette_metadata()
        print("wrote %s (%d canned queries, generated from CANNED)" % (p, len(CANNED)))
        print("\n  " + serve_command())
        print("\n  then open http://127.0.0.1:8801/ — every page is also JSON with .json")
        return 0

    sql = a.sql or CANNED.get(a.canned or "")
    if not sql:
        # ABSENT AND UNREADABLE ARE DIFFERENT DATABASES. `age_seconds()` answers None for three
        # unrelated reasons and this line rendered all of them as "absent -- run --rebuild",
        # which is the wrong instruction for two of the three: a locked database wants the
        # readers closed and a corrupt one wants deleting first. `freshness()` already knew
        # which; the reader was throwing that away.
        f = freshness()
        if f["age_seconds"] is None:
            print("corpus.db NOT USABLE -- %s (%s)"
                  % (f["reason"], "the file is not on disk" if not os.path.exists(DB)
                     else "the file IS on disk at " + DB))
        else:
            print("corpus.db built %.1f min ago" % (f["age_seconds"] / 60))
        print("\ncanned queries: " + ", ".join(sorted(CANNED)))
        return 0
    cols, rows = query(sql)
    print(_freshness_banner())
    print("  " + " | ".join(str(c) for c in cols))
    print("  " + "-" * 74)
    for r in rows:
        print("  " + " | ".join("" if v is None else str(v)[:40] for v in r))
    print("\n%d row(s)" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
