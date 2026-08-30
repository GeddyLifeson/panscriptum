"""POLICY — checks as DATA, with the observed value recorded, not just pass or fail.

THE OPA/REGO IDEA, WITHOUT THE DSL. Open Policy Agent, CUE and Conftest all separate a rule from
the code that evaluates it, so the rules become a diffable, auditable table rather than a hundred
scattered `if` statements nobody re-reads. That separation is worth having here. Their packaging
is not: each needs a binary or a non-Python language, and this project takes no dependency
without owner sign-off. A dict and a ten-line evaluator get the same property.

WHAT THE SEPARATION ACTUALLY BUYS, and it is not tidiness. A rule buried in imperative code can
degrade to a no-op without anyone noticing -- it reads a field that got renamed, the comparison
becomes `None == None`, and the check reports success for ever. This project has hit that shape
repeatedly: a HIGH guard reading a job-dict key nothing sets, so it never appeared on the page at
all -- not red, not green, ABSENT for its whole life.

So the evaluator does the thing Plumber's control reporting does and most check code does not:
**it records the OBSERVED VALUE of every rule, every run**, not merely the verdict. A rule that
passed because it looked at `None` is then visible in the report as a rule that looked at `None`,
which is the only way a vacuous pass can be told from a real one without reading the source.

WHAT BELONGS HERE, AND WHAT DOES NOT. Structural, stateless assertions about a document: a field
exists, a number is in range, a set is non-empty, a string matches. Those are the ones that rot
invisibly and benefit from being data. Genuinely stateful checks -- "was this page actually
fetched", "does this entity's evidence belong to it" -- stay as Python, because expressing them
as data would mean building the DSL this module exists to avoid.
"""
import fnmatch
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

REPORT = os.path.join(HERE, "state", "policy_report.json")

# The operators a rule may use. A closed set on purpose: an open one becomes a language, and a
# language needs its own tests, parser and error messages -- which is the cost that made Rego and
# CUE the wrong answer here.
OPS = {
    "exists":    lambda v, _a: v is not None,
    "absent":    lambda v, _a: v is None,
    "truthy":    lambda v, _a: bool(v),
    "eq":        lambda v, a: v == a,
    "ne":        lambda v, a: v != a,
    "gte":       lambda v, a: v is not None and v >= a,
    "lte":       lambda v, a: v is not None and v <= a,
    "in_range":  lambda v, a: v is not None and a[0] <= v <= a[1],
    "nonempty":  lambda v, _a: bool(v) and len(v) > 0,
    "len_gte":   lambda v, a: v is not None and len(v) >= a,
    "matches":   lambda v, a: v is not None and re.search(a, str(v)) is not None,
    "not_matches": lambda v, a: v is None or re.search(a, str(v)) is None,
    "glob":      lambda v, a: v is not None and fnmatch.fnmatch(str(v), a),
    "is_type":   lambda v, a: isinstance(v, TYPES[a]),
}

# The type names `is_type` accepts, and a CLOSED SET for the same reason `OPS` is one.
#
# This lived inline as `{...}.get(a, object)`, and the default was the whole defect: a rule
# written without `arg`, or with `arg` misspelled, folded to `isinstance(v, object)` -- true of
# every value including `None`, an unconditional pass that would never fail again. Worse, it was
# invisible to this module's own vacuous-pass detector, because `found` is True whenever the path
# resolves and `evaluate()` only flags a pass that looked at an ABSENT field. So the one shape
# this evaluator exists to refuse -- "a check that cannot fail looks exactly like a check that
# passed" -- was reachable through the evaluator itself. Every rule table in this file happens to
# pass a correct `arg`, so nothing was silently passing in production; it was a landmine for the
# next table. Refused at load now, exactly as an unknown `op` already was. Found by the run #33
# sweep (batch 15).
TYPES = {"str": str, "int": int, "float": float, "bool": bool, "list": list, "dict": dict}


class BadRule(ValueError):
    """A rule that cannot be evaluated. Refused at load, never silently skipped."""


def resolve(doc, path):
    """Dotted path into a nested dict/list. -> (value, found).

    `found` is returned separately from the value, and that is the whole point: `None` because a
    field HOLDS null and `None` because the field is ABSENT are different findings, and a
    resolver that returns only the value makes them identical -- which is how a rule comes to
    check a key nobody sets.
    """
    cur = doc
    for part in str(path).split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return None, False
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None, False
        else:
            return None, False
    return cur, True


def check_rule(doc, rule):
    """Evaluate one rule against one document. -> a record, never a bare bool."""
    for req in ("id", "path", "op"):
        if req not in rule:
            raise BadRule("rule is missing %r: %r" % (req, rule))
    op = rule["op"]
    if op not in OPS:
        raise BadRule("rule %s uses unknown op %r (known: %s)"
                      % (rule["id"], op, ", ".join(sorted(OPS))))
    # Checked HERE rather than inside the lambda, because the `except Exception` below would
    # otherwise catch the KeyError and record it as an ordinary rule FAILURE -- a malformed rule
    # reported as a failing document, which sends the reader to the wrong place entirely. An
    # unevaluable rule is refused at load, like an unknown op; a false verdict is never issued
    # for one.
    if op == "is_type" and rule.get("arg") not in TYPES:
        raise BadRule("rule %s uses unknown is_type arg %r (known: %s)"
                      % (rule["id"], rule.get("arg"), ", ".join(sorted(TYPES))))
    value, found = resolve(doc, rule["path"])
    try:
        ok = bool(OPS[op](value, rule.get("arg")))
    except Exception as e:
        ok = False
        return {"id": rule["id"], "ok": False, "observed": repr(value)[:120],
                "found": found, "op": op, "error": "%s: %s" % (type(e).__name__, e),
                "severity": rule.get("severity", "MINOR"), "why": rule.get("why", "")}
    return {"id": rule["id"], "ok": ok,
            # THE OBSERVED VALUE, ALWAYS. A pass with `observed: None, found: False` is a rule
            # that examined a field that does not exist -- visible here, invisible in a boolean.
            "observed": repr(value)[:120], "found": found, "op": op,
            "severity": rule.get("severity", "MINOR"), "why": rule.get("why", "")}


def evaluate(doc, rules, subject=""):
    """Evaluate a rule table against one document. -> {results, failed, vacuous}."""
    results = [check_rule(doc, r) for r in rules]
    failed = [r for r in results if not r["ok"]]
    # A rule that PASSED while looking at a field that does not exist. Not a failure -- but not
    # evidence of anything either, and the only place it is ever visible.
    #
    # `absent` IS EXEMPT, and it is the one honest exemption. `OPS["absent"]` asserts a field is
    # MISSING, so its only truthful passing case is `found=False` -- flagging it would report
    # every correct pass of that operator as a non-result, which is the same failure as flagging
    # none of them: a signal that always fires is furniture. No rule table in this file uses
    # "absent" today, so nothing was misfiring in production; this closes the trap before the
    # first table walks into it. The exemption is narrow ON PURPOSE and does NOT extend to
    # `not_matches`, whose `v is None` clause passes on an absent field as a side effect rather
    # than as its subject -- that is a genuine vacuous pass and stays reported.
    # Order 9ef866225683 (run #36).
    vacuous = [r for r in results if r["ok"] and not r["found"] and r["op"] != "absent"]
    return {"subject": subject, "at": time.time(), "n": len(results),
            "failed": failed, "vacuous": vacuous, "results": results}


def report(evaluations, scope=None):
    """Land a run's evaluations so a vacuous rule is discoverable later, not just now.

    `scope` (optional, added 2026-08-25) records WHAT WAS LOOKED AT: how many records and
    coverage rows existed, how many were evaluated, and whether a `--limit` was in force. A
    stored report that says only "these N passed" cannot be told apart from a full-corpus run,
    which is precisely how a default `--limit 40` sat unnoticed over 216 records.
    """
    try:
        # silence.write_json, not a fixed `REPORT + ".tmp"` name (order 53dcfb2bd48b):
        # write_json builds its temp name from pid and thread precisely so two writers of the
        # same report cannot collide on the temp file itself -- the m100 shape retired
        # repo-wide, per silence.py's own docstring.
        #
        # GATED. This function's entire purpose is the word "later" in its own first line: the
        # console output is this run's, and `state/policy_report.json` is the only copy that
        # outlives it. `write_json` returns whether the rename LANDED and this dropped it, so a
        # denied replace (a reader holding the file -- the ordinary Windows case here) left the
        # PREVIOUS run's evaluations, its `at` stamp and, worst of all, its `scope` block on
        # disk. The scope block exists to keep a `--limit 40` run from reading like a
        # full-corpus one; a stale one does exactly that, which is the failure it was added
        # after. Said out loud, since this module reports through print.
        ok = silence.write_json(REPORT, {"at": time.time(), "scope": scope,
                                         "evaluations": evaluations},
                                indent=1, ensure_ascii=False)
        if not ok:
            silence.note("policy.py:report-denied")
            print("policy: %s was NOT rewritten (replace refused) -- it still holds an EARLIER "
                  "run's evaluations and scope. This run exists only in the output above."
                  % os.path.basename(REPORT), file=sys.stderr)
        return ok
    except Exception:
        silence.note("policy.py:report")
        return False


# ---------------------------------------------------------------- the rule tables themselves
#
# Structural invariants that were previously asserted in scattered code, or not at all. Each
# carries its severity and the reason it exists, so the table reads as documentation of what a
# well-formed document IS.

RECORD_RULES = [
    {"id": "record.source", "path": "source", "op": "nonempty", "severity": "BLOCKING",
     "why": "a record with no source cannot be addressed, shelved or cited"},
    {"id": "record.entries", "path": "entries", "op": "is_type", "arg": "list",
     "severity": "BLOCKING", "why": "entries must be a list even when empty"},
    # MIGRATION STATE, NOT A DEFECT -- and named as such so it is not chased as one. Stamping
    # was added 2026-08-25 and applies only to records written since; the whole corpus predates
    # it. The rule's value is the TREND: this count should fall to zero as records are rewritten,
    # and if it stops falling, the stamping is not reaching a writer that should be using it.
    {"id": "record.writer.migration", "path": "_writer.by", "op": "nonempty",
     "severity": "INFO",
     "why": "unstamped means written before 2026-08-25, not written wrongly; watch the trend"},
]

# EVALUATED BY `main()` OVER `data/feats` SINCE ORDER ab820740fb85. It had ZERO consumers before
# that -- `grep -rn EVIDENCE_RULES src/*.py` returned only this definition -- so its three
# invariants were not red and not green, they were ABSENT, which is word for word the failure
# this module's own opening thesis describes ("a HIGH guard reading a job-dict key nothing sets,
# so it never appeared on the page at all"). A rule table nothing runs is documentation wearing
# the shape of a check. The corpus was NOT in breach when the order was filed (5,000 of the
# 255,855 files sampled by hand: 0 unreadable, 0 failures, 0 vacuous passes) -- the defect was
# the absent evaluation, and the remedy is the sweep in `main()`, not a change to these rules.
EVIDENCE_RULES = [
    {"id": "evidence.entity", "path": "entity", "op": "nonempty", "severity": "BLOCKING",
     "why": "M23: a cache file that does not name its entity cannot be proved to be its own"},
    {"id": "evidence.host", "path": "host", "op": "nonempty", "severity": "MINOR",
     "why": "provenance: which wiki this came from"},
    {"id": "evidence.feats", "path": "feats", "op": "is_type", "arg": "list",
     "severity": "MAJOR", "why": "feats must be a list; a dict here silently mines to zero"},
]

COVERAGE_RULES = [
    {"id": "coverage.entries", "path": "entries", "op": "gte", "arg": 0,
     "severity": "MAJOR", "why": "a negative entry count is a counting bug"},
    # NAMED "cited_le_entries" until this fix, which promised cited <= entries. `OPS` has no
    # operator that compares two fields of the same document, so the rule could never have
    # checked that -- it only ever checked cited >= 0, which is what its "why" honestly says.
    # The id is what the report prints on a FAIL line, so a green run under the old name read
    # as evidence for an invariant nothing here evaluates. Renamed to match what actually runs;
    # cited<=entries stays unchecked. Order 4f68f9f9f591.
    {"id": "coverage.cited_nonneg", "path": "cited", "op": "gte", "arg": 0,
     "severity": "MAJOR", "why": "cited cannot be negative"},
    {"id": "coverage.source", "path": "source", "op": "nonempty", "severity": "MAJOR",
     "why": "a coverage row with no source cannot be acted on"},
]


def main():
    import argparse
    import glob
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true")
    # [HARD RULE 0] This DEFAULTED TO 40 (corrected 2026-08-25, order c9150ac67099). A default
    # cap is the worst kind, because nobody chose it and nothing said it was there: a plain
    # `--run` read `sorted(glob(records/*.json))[:40]` -- 40 of 216 records -- and
    # `COVERAGE.json[:40]` -- 40 of 210 rows -- then printed "N document(s) evaluated, 0 rule
    # failure(s)" and exited 0. That is a clean structural pass over the alphabetical first
    # fifth of the corpus, reported in language that describes the corpus. The remaining 176
    # records were not passing; they were not looked at.
    #
    # Default is now the WHOLE corpus. `--limit` stays for a deliberate human spot check, and
    # when it is set the run says so, in the summary and in the report file, by count and by
    # what was skipped -- see the banner below.
    ap.add_argument("--limit", type=int, default=None,
                    help="evaluate only the first N of each set (alphabetical for records, "
                         "stored order for coverage). Default: no limit, the whole corpus. "
                         "A spot check, never a default -- the run is labelled PARTIAL when "
                         "this is set.")
    # THE EVIDENCE SWEEP IS ON BY DEFAULT, because a table nothing evaluates is the defect that
    # put it here (order ab820740fb85). It is the slow part -- a quarter of a million cache
    # files -- so there is a way to say "structure only" out loud, and the summary says so when
    # it was used. There is no way to say it quietly.
    ap.add_argument("--skip-evidence", action="store_true",
                    help="do not sweep data/feats against EVIDENCE_RULES. The run is labelled "
                         "EVIDENCE NOT SWEPT; those files are then unchecked, not passing.")
    ap.add_argument("--evidence-workers", type=int, default=min(16, (os.cpu_count() or 4)),
                    help="threads for the evidence sweep (it is file-I/O bound)")
    a = ap.parse_args()
    if not a.run:
        ap.print_help()
        return 0

    evals = []
    # A RECORD THAT COULD NOT BE READ IS A FINDING, NOT A GAP IN THE SAMPLE. This loop used a
    # bare `except Exception: continue`, so a corrupt or truncated record was dropped from the
    # evaluated set with no note, no counter and no line in the summary below -- and the run then
    # reported a clean structural pass over whatever remained. That is this module's own reason
    # for existing turned on itself: "a check that cannot fail looks exactly like a check that
    # passed", and a check that was never attempted looks exactly like one that passed too.
    # Counted and printed by name now. Found by the run #33 sweep (batch 15).
    unreadable = []
    all_records = sorted(glob.glob(os.path.join(HERE, "data", "records", "*.json")))
    records = all_records if a.limit is None else all_records[:a.limit]
    for p in records:
        try:
            with open(p, encoding="utf-8") as f:
                evals.append(evaluate(json.load(f), RECORD_RULES, os.path.basename(p)))
        except Exception as e:
            silence.note("policy.py:record-unreadable")
            unreadable.append((os.path.basename(p), "%s: %s" % (type(e).__name__, str(e)[:70])))
            continue
    cov = os.path.join(HERE, "data", "COVERAGE.json")
    cov_total = cov_read = 0
    if os.path.exists(cov):
        with open(cov, encoding="utf-8") as f:
            rows = json.load(f)
        cov_total = len(rows)
        if a.limit is not None:
            rows = rows[:a.limit]
        cov_read = len(rows)
        for row in rows:
            evals.append(evaluate(row, COVERAGE_RULES, str(row.get("source"))[:40]))

    # THE EVIDENCE CACHE (order ab820740fb85). `EVIDENCE_RULES` declared three invariants and
    # nothing evaluated them; this is the sweep that makes them real, and it is the only
    # structural pass over `data/feats` the project has. `evidence.entity` in particular is the
    # M23 invariant the whole of `cachekey.py` enforces at READ time, one file at a time, with
    # no corpus-wide answer anywhere until now.
    #
    # AGGREGATED, NOT STORED PER FILE, AND THAT IS NOT A CAP. Every failure, every vacuous pass
    # and every unreadable file is named in full, here and in the report. What is not stored is
    # the 261,000 individual PASS records -- those are counted, because a report holding one
    # dict per passing cache file is a ~130 MB artefact that says the same thing as an integer.
    # Nothing is decided by the omission and nothing that failed is left out of it.
    ev_total = ev_read = ev_passed = 0
    ev_unreadable = []
    ev_interesting = []
    if not a.skip_evidence:
        import concurrent.futures as _cf
        feats_root = os.path.join(HERE, "data", "feats")
        all_feats = sorted(glob.glob(os.path.join(feats_root, "*", "*.json")))
        ev_total = len(all_feats)
        feats = all_feats if a.limit is None else all_feats[:a.limit]
        ev_read = len(feats)

        def _sweep_one(p):
            subject = os.path.relpath(p, feats_root).replace(os.sep, "/")
            try:
                with open(p, encoding="utf-8") as fh:
                    return evaluate(json.load(fh), EVIDENCE_RULES, subject)
            except Exception as exc:
                # SAME DISCIPLINE AS THE RECORD LOOP ABOVE: an unreadable file is a finding, not
                # a gap in the sample. A cache file that cannot be parsed is one whose evidence
                # nothing downstream can read either.
                silence.note("policy.py:evidence-unreadable")
                return (subject, "%s: %s" % (type(exc).__name__, str(exc)[:70]))

        if feats:
            with _cf.ThreadPoolExecutor(max_workers=max(1, a.evidence_workers)) as pool:
                for out in pool.map(_sweep_one, feats):
                    if isinstance(out, tuple):
                        ev_unreadable.append(out)
                    elif out["failed"] or out["vacuous"]:
                        ev_interesting.append(out)
                    else:
                        ev_passed += 1
        evals.extend(ev_interesting)

    # WHAT WAS AND WAS NOT LOOKED AT, first, before any verdict. A window nobody can see the far
    # side of reads exactly like a complete list, so the scope is stated whether or not it is
    # partial -- a run that says "216 of 216" cannot be mistaken for one that says "40 of 216".
    partial = a.limit is not None
    report(evals, scope={
        "limit": a.limit, "partial": partial,
        "records_total": len(all_records), "records_evaluated": len(records),
        "coverage_total": cov_total, "coverage_evaluated": cov_read,
        "evidence_swept": not a.skip_evidence,
        "evidence_total": ev_total, "evidence_evaluated": ev_read,
        "evidence_passed": ev_passed, "evidence_unreadable": len(ev_unreadable),
        "evidence_stored": len(ev_interesting),
        "evidence_note": ("only failing/vacuous evidence files are stored individually; "
                          "passes are counted" if not a.skip_evidence else
                          "--skip-evidence: data/feats was NOT swept this run"),
        "records_skipped": [os.path.basename(p) for p in all_records[a.limit:]] if partial else [],
    })
    print("scope: records %d of %d, coverage rows %d of %d%s"
          % (len(records), len(all_records), cov_read, cov_total,
             "   *** PARTIAL RUN (--limit %d) ***" % a.limit if partial else ""))
    if a.skip_evidence:
        print("  *** EVIDENCE NOT SWEPT (--skip-evidence): data/feats was not looked at. Those "
              "files are unchecked, not passing. ***")
    else:
        print("  evidence cache: %d of %d file(s) swept against EVIDENCE_RULES, %d clean, "
              "%d with a finding, %d unreadable"
              % (ev_read, ev_total, ev_passed, len(ev_interesting), len(ev_unreadable)))
        for subj, why in ev_unreadable:
            print("  UNREAD %-40s %s" % (subj[:40], why))
    if partial:
        skipped_rec = all_records[a.limit:]
        print("  PARTIAL: %d record(s) and %d coverage row(s) were NOT evaluated. They are not "
              "passing -- they were not looked at." % (len(skipped_rec), cov_total - cov_read))
        for fname in skipped_rec:
            print("  SKIPPED %s" % os.path.basename(fname))

    # INFO-severity rules are reported separately and never gate. A migration counter reported
    # as a failure is how a real failure ends up buried among 60 expected ones.
    failed = [(e["subject"], r) for e in evals for r in e["failed"]
              if r.get("severity") != "INFO"]
    info = [(e["subject"], r) for e in evals for r in e["failed"]
            if r.get("severity") == "INFO"]
    vacuous = [(e["subject"], r) for e in evals for r in e["vacuous"]]
    # SAY WHICH DOCUMENTS. `len(evals)` counts records, coverage rows and the evidence files
    # that had something to report -- the clean evidence files are counted on the scope line
    # above rather than stored, so a bare total here would understate what was looked at by a
    # quarter of a million and read like the whole corpus.
    print("%d document(s) evaluated in detail (records, coverage rows, and the %d evidence "
          "file(s) with a finding); %d further evidence file(s) passed clean"
          % (len(evals), len(ev_interesting), ev_passed))
    if unreadable:
        print("%d record(s) COULD NOT BE READ and were never evaluated -- not a pass"
              % len(unreadable))
        for fname, why in unreadable:
            print("  UNREAD %-26s %s" % (fname[:26], why))
    if info:
        by_rule = {}
        for _s, r in info:
            by_rule[r["id"]] = by_rule.get(r["id"], 0) + 1
        for rid, n in sorted(by_rule.items()):
            print("  info  %-30s %d document(s)" % (rid, n))
    # Every failure and every vacuous pass is named. These printed 12 and stopped, which on a
    # 216-record corpus meant the 13th failure onward existed only in state/policy_report.json
    # -- and the line above it announced a count that looked like the whole list.
    print("%d rule failure(s)" % len(failed))
    for subj, r in failed:
        print("  FAIL  %-26s %-28s observed=%s" % (subj[:26], r["id"], r["observed"][:34]))
    print("%d VACUOUS pass(es) -- rule looked at a field that does not exist" % len(vacuous))
    for subj, r in vacuous:
        print("  VOID  %-26s %-28s %s" % (subj[:26], r["id"], r["why"][:38]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
