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
    vacuous = [r for r in results if r["ok"] and not r["found"]]
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
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        tmp = REPORT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"at": time.time(), "scope": scope, "evaluations": evaluations}, f,
                      indent=1, ensure_ascii=False)
        silence.replace_retry(tmp, REPORT)
    except Exception:
        silence.note("policy.py:report")


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

    # WHAT WAS AND WAS NOT LOOKED AT, first, before any verdict. A window nobody can see the far
    # side of reads exactly like a complete list, so the scope is stated whether or not it is
    # partial -- a run that says "216 of 216" cannot be mistaken for one that says "40 of 216".
    partial = a.limit is not None
    report(evals, scope={
        "limit": a.limit, "partial": partial,
        "records_total": len(all_records), "records_evaluated": len(records),
        "coverage_total": cov_total, "coverage_evaluated": cov_read,
        "records_skipped": [os.path.basename(p) for p in all_records[a.limit:]] if partial else [],
    })
    print("scope: records %d of %d, coverage rows %d of %d%s"
          % (len(records), len(all_records), cov_read, cov_total,
             "   *** PARTIAL RUN (--limit %d) ***" % a.limit if partial else ""))
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
    print("%d document(s) evaluated" % len(evals))
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
