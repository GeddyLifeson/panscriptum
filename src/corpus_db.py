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


def connect(path=DB, readonly=False):
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
    """
    t0 = time.time()
    tmp = DB + ".tmp"
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

    spine = {}
    try:
        with open(os.path.join(HERE, "data", "CHARTER_SPINE_CODES.json"), encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            spine = {k: str(v) for k, v in raw.items()}
    except Exception:
        silence.note("corpus_db.py:spine")

    n_src = n_entry = 0
    for p in sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue
        src = rec.get("source")
        c = cov.get(src) or {}
        con.execute(
            "INSERT OR REPLACE INTO source VALUES (?,?,?,?,?,?,?,?,?)",
            (src, hosts.get(src), spine.get(src), len(rec.get("entries") or []),
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
            except Exception:
                continue
            if not isinstance(d, dict):
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
    con.commit()
    con.close()
    silence.replace_retry(tmp, DB)
    return {"sources": n_src, "entries": n_entry, "evidence": n_ev,
            "seconds": round(time.time() - t0, 2)}


def age_seconds():
    try:
        con = connect(readonly=True)
        v = con.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        con.close()
        return time.time() - float(v[0]) if v else None
    except Exception:
        return None


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
CANNED = {
    "coverage": "SELECT name, entries, cited, read, no_page, not_attempted "
                "FROM source ORDER BY entries DESC LIMIT 15",
    "unaddressed": "SELECT name, entries FROM source WHERE spine IS NULL "
                   "ORDER BY entries DESC",
    "hostless": "SELECT name, entries FROM source WHERE host IS NULL ORDER BY entries DESC",
    "categories": "SELECT category, COUNT(*) n FROM entry GROUP BY category ORDER BY n DESC",
    "types": "SELECT type, COUNT(*) n FROM entry WHERE type IS NOT NULL "
             "GROUP BY type ORDER BY n DESC LIMIT 25",
    "unjudged": "SELECT source, COUNT(*) n FROM entry WHERE catalogued=0 AND excluded=0 "
                "GROUP BY source ORDER BY n DESC LIMIT 15",
    "evidence": "SELECT host, COUNT(*) files, SUM(feats) feats, SUM(pages) pages "
                "FROM evidence GROUP BY host ORDER BY feats DESC LIMIT 15",
    "refused": "SELECT host, COUNT(*) n FROM evidence WHERE refused>0 GROUP BY host "
               "ORDER BY n DESC LIMIT 15",
    "worst_cited": "SELECT name, entries, cited, ROUND(100.0*cited/entries,1) pct "
                   "FROM source WHERE entries>=40 ORDER BY pct ASC LIMIT 15",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--no-evidence", action="store_true",
                    help="skip the 109k evidence files (much faster)")
    ap.add_argument("--sql", help="a read-only query")
    ap.add_argument("--canned", help="one of: " + ", ".join(sorted(CANNED)))
    a = ap.parse_args()

    if a.rebuild:
        got = rebuild(include_evidence=not a.no_evidence)
        print("rebuilt: %(sources)d sources, %(entries)d entries, %(evidence)d evidence rows "
              "in %(seconds)ss" % got)
        print("  -> %s (%.1f MB)" % (DB, os.path.getsize(DB) / 1e6))
        return 0

    sql = a.sql or CANNED.get(a.canned or "")
    if not sql:
        age = age_seconds()
        print("corpus.db %s" % ("absent -- run --rebuild"
                                if age is None else "built %.1f min ago" % (age / 60)))
        print("\ncanned queries: " + ", ".join(sorted(CANNED)))
        return 0
    cols, rows = query(sql)
    print("  " + " | ".join(str(c) for c in cols))
    print("  " + "-" * 74)
    for r in rows:
        print("  " + " | ".join("" if v is None else str(v)[:40] for v in r))
    print("\n%d row(s)" % len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
