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
        return "  [ NO INDEX — run --rebuild. These are not results. ]"
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
    ap.add_argument("--serve", action="store_true",
                    help="write Datasette's config and print the command that serves it")
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

    if a.serve:
        p = datasette_metadata()
        print("wrote %s (%d canned queries, generated from CANNED)" % (p, len(CANNED)))
        print("\n  " + serve_command())
        print("\n  then open http://127.0.0.1:8801/ — every page is also JSON with .json")
        return 0

    sql = a.sql or CANNED.get(a.canned or "")
    if not sql:
        age = age_seconds()
        print("corpus.db %s" % ("absent -- run --rebuild"
                                if age is None else "built %.1f min ago" % (age / 60)))
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
