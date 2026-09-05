"""BINDING HEALTH — prove each wiki host still answers the way it did, before trusting it again.

THE PROBLEM THIS SOLVES, and it is one of the oldest here. ~200 sources are bound to wiki hosts,
and a binding can go wrong in four ways that are indistinguishable from each other downstream:

    the host is fine                      -> mine normally
    the host has been redesigned          -> every fetch returns a page that parses to nothing
    the host is throttling us             -> every fetch returns 429, which reads as "empty"
    the binding was always wrong          -> `descent.fandom.com` is the board game Descent

`hostcheck.py` already answers the LAST of those, and answers it well -- it asks whether a wiki
holds this fiction's own names. What nothing has ever asked is the FIRST THREE: *does this host
still behave today the way it behaved when we bound it?* A binding that silently rots is
indistinguishable from a source that genuinely has nothing, which is this project's signature
failure wearing a network costume. Measured precedent: 74 throttled probes came back as 0% and a
repair pass unbound `warhammer40k.fandom.com` from Warhammer 40,000 on the strength of it.

THE PATTERN, borrowed from OSINT enumerators that face exactly this at 3,000-site scale.
`maigret --self-check` and `sherlock`'s `tests/test_validate_targets.py` both keep, per site, a
KNOWN-PRESENT and a KNOWN-ABSENT identity, and assert the detector says found for one and
not-found for the other. Two checks, not one, because they catch opposite failures:

    the PRESENT probe fails   -> the host stopped answering, or we are blocked
    the ABSENT probe passes   -> the host says yes to everything; every "hit" is worthless

A single probe cannot tell "the wiki is down" from "the wiki answers everything". Sherlock's
project history is instructive: it moved from human-reported breakage to automatic quarantine of
sites that start failing, because waiting for someone to notice does not scale past a few dozen.

AND QUARANTINE IS NOT DELETION. Maigret's maintainers are explicit that most disabled entries are
transient -- sites recover. So a failing host is recorded with its REASON, its last-known-good
time, and a retry-after; it is retried on a slower cadence rather than dropped. Silently skipping
a host forever loses coverage permanently and looks exactly like a source with nothing in it.

COST. This is a ~200-page job, not a ~102,000-entity one, and it is deliberately NOT on the
hourly path -- it runs before a sweep or on its own cadence. Two fetches per host against hosts
we are already rate-limited against is the entire expense.
"""
import argparse
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence  # noqa: E402

OUT = os.path.join(HERE, "data", "BINDING_HEALTH.json")
QUARANTINE = os.path.join(HERE, "data", "HOST_QUARANTINE.json")

# How long a quarantined host waits before it is worth another canary. Deliberately long enough
# not to keep spending requests on a dead host, short enough that a wiki that recovers overnight
# is back the next day.
RETRY_AFTER_S = 24 * 3600
# A title no wiki should hold. Long, specific, and nonsense -- if this RESOLVES, the host is
# answering yes to everything and its "hits" prove nothing.
ABSENT_PROBE = "Panscriptum_Canary_NoSuchPage_9f3a2c_DoNotCreate"

# How many known-present titles a host may fail before the canary calls it dead. Bounded because
# the failure branch costs one API call per candidate; generous because the cost of a FALSE
# quarantine is that a healthy host stops being mined. See `_probe_present`.
PRESENT_CANDIDATES = 8

# How many times a compare-and-swap on a read-modify-write may re-read and try again before it
# reports the write as not landed. Bounded because a writer that loops until it wins is a writer
# that never returns; more than one because a single refusal is the ordinary case (another pass
# landed between this one's read and its write) and giving up on it would report a lost
# quarantine that was only ever a lost race.
CAS_ATTEMPTS = 5


class QuarantineUnreadable(RuntimeError):
    """HOST_QUARANTINE.json exists and could not be read as a map of quarantined hosts.

    ITS OWN TYPE BECAUSE THE ANSWER IS NOT `{}`. `_load` spelled "the file is not there" and
    "the file is torn, locked, or not UTF-8" with the same empty default, so a corrupt
    quarantine file read as NOTHING IS QUARANTINED and three things followed, all of them
    measured: `quarantined()` reported an empty map; `is_quarantined()` answered False for every
    rotten host, so mining resumed against it and its empty results were filed as honest
    absences, which is this module's whole subject; and `workorders.sweep` resolved every open
    HOST_QUARANTINED order as "host is no longer quarantined". Two live quarantines were
    destroyed in the demonstration by a single following `quarantine()` call.

    Raised rather than returned for the reason `PushHeld` is: an empty map is a legitimate
    value that every caller already handles, so a third state that arrives wearing it cannot be
    noticed. Every external reader of `quarantined()` -- dashboard, health, feats,
    `workorders.sweep` -- already catches around it, and `health.py` says in its own comment
    what the catch is for: "if the quarantine record cannot be read we do not know that a host
    is excused, so nothing is excused". That is the fail-closed answer; this makes it reachable.
    (order dd3ff361db49)
    """


def _read_json(path):
    """-> (object, 'ok' | 'absent' | 'unreadable'). The distinction `_load` cannot make.

    ABSENT IS A VALUE AND UNREADABLE IS NOT. A file that is not there says, truthfully, that
    nothing has been recorded yet; a file that will not open or will not parse says only that
    this process cannot see what was recorded, which is the one thing a WRITER of that file must
    never treat as an empty starting point.
    """
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), "ok"
    except FileNotFoundError:
        return None, "absent"
    except Exception:
        silence.note("binding_health.py:load")
        return None, "unreadable"


def _read_quarantine():
    """The quarantine map, with the read verdict. -> (map, 'ok'|'absent'|'unreadable').

    A well-formed JSON document that is not a host map is UNREADABLE here, not empty: a list or
    a string in this file is a file that has been overwritten by something else, and the reader
    that treats it as "no host is quarantined" is the reader that then overwrites it for good.
    """
    obj, state = _read_json(QUARANTINE)
    if state != "ok":
        return {}, state
    if not isinstance(obj, dict):
        silence.note("binding_health.py:load")
        return {}, "unreadable"
    return obj, "ok"


def _load(path, default):
    """Read a JSON file, or `default` if it is absent OR unreadable.

    KEPT AS IT WAS, deliberately, for the READ-ONLY callers -- the candidate-title scans, the
    hosts map -- where a default is the right answer and every one of them already treats an
    empty result as "no candidates from here". The callers that WRITE go through `_read_json` /
    `_read_quarantine` instead, because for them the two cases are opposites.
    """
    obj, state = _read_json(path)
    return obj if state == "ok" else default


def _land(path, obj):
    """Write the JSON. -> True if it LANDED on disk, False if the rename was refused.

    GATE ON THE WRITE. `silence.replace_retry` returns whether the rename succeeded and, by its
    own docstring, deliberately never raises on persistent denial ("the caller's write lands next
    round") -- which is right for a metrics file and wrong for this one. This function discarded
    that verdict, so under the WinError 5 collision that helper exists for (a reader holding the
    target open; it took an assay worker down once already, 2026-08-23) `quarantine()` returned a
    record that looked committed, and ESCALATED it, while `HOST_QUARANTINE.json` was untouched.
    `quarantined()` re-reads from disk on every call and has no cache, so the very next check
    would not see it -- and here that failure mode points the wrong way twice: the operator is
    told a rotten host has been closed off when it has not, so mining keeps hitting it and its
    empty results keep being filed as honest absences, which is this module's whole subject.
    `suppressions._land` gates on the identical verdict for the identical reason.

    THE TEMP NAME MUST NOT BE SHARED. This hand-rolled `path + ".tmp"`, which is what
    `silence.write_json` exists to make unavailable to get wrong (and what `runguard._land_claim`
    was rewritten for). Two writers of the same path -- a targeted `--host` investigation racing
    the scheduled whole-estate `--run`, which is the normal situation here, not an exotic one --
    collide on the TEMP FILE ITSELF: both open `BINDING_HEALTH.json.tmp` for writing, the second
    truncates the first, and whichever renames second can land a half-written file over the
    target. `write_json` puts pid and thread in the temp name, so the two writers cannot meet,
    and returns the same `replace_retry` verdict this function has always gated on. It also
    writes UTF-8 explicitly, which this did not: `ensure_ascii=False` plus the platform default
    encoding was one non-ASCII sitename away from a record `_load` (which reads utf-8) could not
    read back -- a silent quarantine loss in the module whose subject is silent losses.
    """
    return silence.write_json(path, obj, indent=1, sort_keys=True, ensure_ascii=False)


def _land_cas(path, obj, expected_digest):
    """`_land`, but ONLY if `path` still holds what this writer read. -> (landed, reason).

    For the one write here that is a READ-MODIFY-WRITE rather than a fresh report: `run()`'s
    partial-pass merge. `_land` is a blind overwrite, which is correct for a whole-estate pass --
    it computed every host and owes nothing to what was there. It is NOT correct for a merge: the
    merge reads the standing report, folds a handful of freshly probed hosts into it, and writes
    the result back, so anything that landed in between is overwritten by a snapshot taken before
    it existed. A whole-estate `--run` finishing inside that window is replaced by ~200 stale
    verdicts plus five fresh ones -- the exact partial-over-complete shape the merge was written
    to prevent, reintroduced through the merge itself.

    `expected_digest` is taken BEFORE the file is read, deliberately: if the file changes between
    the digest and the read, the digest no longer matches at write time and this refuses. The
    other order (read, then digest) would produce a digest that matches disk while the merged
    content is already stale, which is a compare-and-swap that certifies the loss instead of
    catching it. `None` asserts the report did not exist when this pass read for it.
    """
    import threading as _th
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), _th.get_ident())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
    except Exception:
        _unlink(tmp)
        raise
    ok, why = silence.replace_if_unchanged(tmp, path, expected_digest)
    if not ok:
        # `replace_if_unchanged` leaves the temp file where it is on a refusal; a refusal that
        # accumulates litter beside a shared state file is its own small fault.
        _unlink(tmp)
    return ok, why


def _unlink(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        silence.note("binding_health.py:tmp-cleanup")


def _report_not_written(code, what):
    """A write of BINDING_HEALTH.json that did not land, put where the tooling looks.

    THE ASYMMETRY WITH `quarantine()` IS REAL AND IT IS DELIBERATE, and it is written down here
    because an unexplained one is how the next editor copies the wrong half (order 98b6b7f7ad5f
    asked exactly that question). A quarantine that does not land leaves a rotten host BEING
    MINED while the ledger says it was stopped, so it is raised at SUPERVISOR: an action was
    reported that did not happen. A health report that does not land changes nothing about what
    the library does next -- the canary already ran, its results are returned to the caller, and
    the file on disk still holds an earlier pass's verdicts. That is an OBSERVATION going stale,
    not an action being faked, so it is recorded at JANITOR: on the record, in
    `state/escalation.log` and `state/failures.json` where the existing tooling already reads,
    with no authority to stop anything.

    What it must not be is invisible. Until now this printed to stderr and nothing else, so a
    scheduled `--run` whose report never landed left every downstream reader --
    `workorders.sweep`'s binding detector, allsweep's reconcile, `health` -- treating an older
    pass's verdicts as this one's, with the only trace in a log nobody keeps.
    """
    print("binding_health: " + what, file=sys.stderr)
    try:
        import escalation as ESC
        ESC.escalate(ESC.JANITOR, code, what, who="binding_health",
                     evidence={"path": os.path.basename(OUT)})
    except Exception:
        silence.note("binding_health.py:escalate")


def _report_not_released(host, verdict):
    """`release()` said NOT RELEASED. Put that where somebody sees it. -> True if it was a refusal.

    THE OTHER HALF OF THE ASYMMETRY `_report_not_written` DOCUMENTS, and until now the half
    nobody carried. `release()` was rewritten so a lost compare-and-swap returns a string
    beginning "NOT RELEASED" rather than the reason-for-release it could not honour -- but both
    of `run()`'s call sites were BARE STATEMENTS, so the one thing that rewrite produced went
    straight into the bin. A release that loses five CAS rounds was completely invisible:
    `main()` printed `ok` for the host, the sweep reported it recovered, and the host stayed
    closed off with its coverage switched off. A discarded write verdict in the function whose
    whole rewrite was about not discarding it. (order a29c38c9eff3)

    SUPERVISOR, not JANITOR, and the level follows `quarantine()`'s rather than
    `_report_not_written`'s: a health report that does not land is an OBSERVATION going stale,
    but a release that does not land is an ACTION REPORTED THAT DID NOT HAPPEN -- the host is
    excused nowhere, mining stays off for it, and every downstream reader is told it recovered.
    That is the same fault as `HOST_QUARANTINE_NOT_RECORDED` pointing the other way, so it is
    raised at the same rung and closes the same one area of the park.

    The prefix test is the contract: `release()` returns the reason-for-release on success and a
    string starting "NOT RELEASED" on either failure path (an unreadable map, or five refused
    swaps). Tested on the prefix rather than by re-reading the file, because re-reading would
    race the very other writer that caused the refusal.
    """
    if not str(verdict or "").startswith("NOT RELEASED"):
        return False
    print("binding_health: %s" % verdict, file=sys.stderr)
    try:
        import escalation as ESC
        ESC.escalate(ESC.SUPERVISOR, "HOST_RELEASE_NOT_RECORDED", str(verdict),
                     source=host, who="binding_health",
                     evidence={"path": os.path.basename(QUARANTINE)})
    except Exception:
        silence.note("binding_health.py:escalate")
    return True


def quarantined(strict=True):
    """-> {host: record}. Only those whose retry-after has not yet passed.

    RAISES `QuarantineUnreadable` when the file exists and cannot be read. An empty map is the
    answer to "nothing is quarantined", and returning it for "I cannot tell" is what let a torn
    HOST_QUARANTINE.json report an empty quarantine to every reader at once -- the dashboard
    panel, `health`'s excuse list, and worst of all `workorders.sweep`, which closes every open
    HOST_QUARANTINED order whose host is absent from this map. All three already catch around
    this call, and `health.py` states the intended reading in its own comment: "if the quarantine
    record cannot be read we do not know that a host is excused, so nothing is excused."

    `strict=False` is for the one caller that has no useful fail-closed answer -- see
    `is_quarantined`.
    """
    q, state = _read_quarantine()
    if state == "unreadable":
        if strict:
            raise QuarantineUnreadable(
                "%s exists and could not be read as a map of quarantined hosts. This is NOT "
                "'no host is quarantined': the standing quarantines cannot be seen from here, "
                "so nothing may be treated as released and no order about one may be closed."
                % os.path.basename(QUARANTINE))
        silence.note("binding_health.py:quarantine-unreadable")
    now = time.time()
    return {h: r for h, r in (q or {}).items()
            if (r or {}).get("retry_after", 0) > now}


def is_quarantined(host):
    """Is this host already held? -> bool. Answers False when the file cannot be read.

    THE ONE NON-STRICT READER, and the exception is argued rather than inherited. Both callers
    ask this only to decide whether to WRITE -- `feats.note_throttled` skips the hand-off for a
    host already held, and `run()` skips a release for a host that is not -- and both writes
    fail closed on an unreadable file by themselves. Answering True here would SUPPRESS those
    writes, and with them the `HOST_QUARANTINE_NOT_RECORDED` escalation that is the only loud
    thing a broken quarantine file produces; answering False costs one refused write that says
    so. The readers that must not guess -- `quarantined()` itself -- get the exception.
    """
    return host in quarantined(strict=False)


def quarantine(host, reason, last_good=None):
    """Record a host as failing, WITH ITS REASON. Never a silent skip, never a deletion.

    FAILS CLOSED ON AN UNREADABLE FILE. This began `_load(QUARANTINE, {}) or {}` and then blindly
    overwrote the file, so a torn, locked or non-UTF-8 HOST_QUARANTINE.json read as an empty map
    and the next quarantine replaced every standing record with a ONE-KEY map. Demonstrated: a
    file holding two live quarantines plus a torn tail came back as `{}`, and one call left only
    the host just added. Nothing raised, nothing was noted, and the loss is invisible afterwards
    because the file that would have shown it is the file that was overwritten. Reading a file
    you are about to overwrite is the one place where "I could not read it" must never be
    rounded to "there was nothing there". (order dd3ff361db49)

    AND COMPARE-AND-SWAP, which `release()` has had and this has not. This is a READ-MODIFY-WRITE
    and `_land` is a blind overwrite: two writers of HOST_QUARANTINE.json is the normal
    situation here (a scheduled `--run` quarantining a dead host while a targeted `--host` pass
    releases a recovered one), each reads the map, each edits its own key, and whichever renames
    second lands a snapshot taken before the other's edit existed. The write SUCCEEDS, which is
    why nothing ever reported it, and the lost quarantine looks exactly like a host that was
    never quarantined. Re-read and retried rather than refused outright, exactly as `release()`
    does: the other writer's copy is the newer truth, so this pass folds into it and swaps
    again. (order 8ee268ce32cc)

    THE TWO FIXES ARE NOT INTERCHANGEABLE and both are needed: a compare-and-swap over a `{}`
    read still lands `{}`, because the digest of the unreadable file matches nothing and the
    file it certifies is the one whose contents were never seen.
    """
    # THE REASON IS STORED WHOLE. Both branches below wrote `str(reason)[:300]`, a hard slice on
    # a STORED field, which is Hard Rule 0's exact shape -- and the reason is the only record of
    # WHY a host was closed off. Measured for fireemblem.fandom.com, the reason a 429 produces is
    # 330 characters, so the cut landed mid-title with the closing parenthesis gone: the record
    # did not even read as a complete sentence, and nothing said anything had been removed. The
    # two renderers that print it (`main()`'s `--quarantined` table and the report line above it)
    # already truncate at their own call sites, which is where the house puts display cuts.
    # (order d6ca84486153)
    rec, landed, detail = None, False, "not attempted"
    for _ in range(CAS_ATTEMPTS):
        # THE DIGEST IS TAKEN BEFORE THE READ -- see `_land_cas`. Read first and the digest would
        # match disk while the copy in hand is already stale, certifying the loss.
        expected = silence.digest_of(QUARANTINE)
        q, state = _read_quarantine()
        if state == "unreadable":
            rec = {"reason": str(reason), "at": time.time(),
                   "retry_after": time.time() + RETRY_AFTER_S,
                   "last_good": last_good, "times": None}
            landed = False
            detail = ("%s exists and could not be read, so this quarantine cannot be added to "
                      "the records already in it without destroying them"
                      % os.path.basename(QUARANTINE))
            break
        prev = q.get(host) or {}
        rec = {"reason": str(reason), "at": time.time(),
               "retry_after": time.time() + RETRY_AFTER_S,
               "last_good": last_good if last_good is not None else prev.get("last_good"),
               "times": int(prev.get("times", 0)) + 1}
        q[host] = rec
        try:
            landed, detail = _land_cas(QUARANTINE, q, expected)
        except Exception:
            # `_land_cas` re-raises whatever stopped the temp file being written. `quarantine()`
            # is called from inside `run()`'s per-host loop and from `feats.note_throttled`, and
            # neither may lose its sweep to one host's failed write.
            silence.note("binding_health.py:quarantine-write")
            landed, detail = False, "the temp copy could not be written"
        if landed:
            break
    # THE ESCALATION MUST DESCRIBE WHAT IS ON DISK. A refused rename leaves the host UNQUARANTINED
    # -- `quarantined()` reads the file every call -- so raising HOST_QUARANTINED for it would put
    # a lie in the escalation ledger and close a case that was never opened. Raise the failure to
    # write instead, which is the actionable finding, and carry the verdict out in the record so
    # a caller cannot mistake an attempted quarantine for a recorded one.
    rec["landed"] = landed
    try:
        import escalation as ESC
        # SUPERVISOR, not OWNER: one host failing closes that area of the park, never the park.
        if landed:
            ESC.escalate(ESC.SUPERVISOR, "HOST_QUARANTINED",
                         "%s quarantined: %s" % (host, reason), source=host, who="binding_health")
        else:
            ESC.escalate(ESC.SUPERVISOR, "HOST_QUARANTINE_NOT_RECORDED",
                         "%s should be quarantined (%s) but HOST_QUARANTINE.json could not be "
                         "written (%s) -- the host is NOT quarantined and will keep "
                         "being mined" % (host, reason, detail), source=host,
                         who="binding_health")
    except Exception:
        silence.note("binding_health.py:escalate")
    return rec


def release(host, why="canary passed"):
    """Lift a quarantine. -> the reason it was lifted, or a reason saying it was NOT.

    A release that does not reach disk leaves the host quarantined while the caller is told it
    is free, which is the mirror of the `quarantine()` lie and just as expensive: coverage stays
    switched off and the log says it was switched back on.

    COMPARE-AND-SWAP, because this is a READ-MODIFY-WRITE and `_land` is a blind overwrite --
    the same hazard `_land_cas` was written for one file up, arriving in the other state file
    this module owns. Two writers of `HOST_QUARANTINE.json` is the normal situation here, not an
    exotic one (a scheduled `--run` releasing recovered hosts while a targeted `--host` pass
    quarantines a rotten one): each reads the map, each edits its own key, and whichever renames
    second lands a snapshot taken before the other's edit existed. The write SUCCEEDS, which is
    why nothing ever reported it, and the lost update looks exactly like a host that was never
    quarantined -- or, in the other direction, like one nobody ever released. RE-READ AND
    RETRIED rather than refused outright: the other writer's copy is the newer truth, so this
    pass folds into it and swaps again. If the file will not hold still, the caller is told the
    host is STILL QUARANTINED, which is what is on disk. (order 8ee268ce32cc)
    """
    detail = "not attempted"
    for _ in range(CAS_ATTEMPTS):
        # THE DIGEST IS TAKEN BEFORE THE READ, deliberately -- see `_land_cas`. Read first and
        # the digest would match disk while the copy in hand is already stale, which certifies
        # the loss instead of catching it.
        expected = silence.digest_of(QUARANTINE)
        q, state = _read_quarantine()
        if state == "unreadable":
            # THE SAME FAIL-CLOSED READ `quarantine()` GOT, and it matters in the same way: an
            # unreadable file used to come back `{}`, `host not in q` was then trivially true,
            # and this reported the host RELEASED without writing anything -- while whatever the
            # file actually holds may still be holding it. A release nobody can prove is a
            # release that did not happen. (order dd3ff361db49)
            return ("NOT RELEASED: %s exists and could not be read, so it cannot be said "
                    "whether %s is quarantined, and nothing may be written over records that "
                    "cannot be seen. Intended reason: %s"
                    % (os.path.basename(QUARANTINE), host, why))
        if host not in q:
            return why
        q.pop(host, None)
        try:
            landed, detail = _land_cas(QUARANTINE, q, expected)
        except Exception:
            # `_land_cas` re-raises whatever stopped the temp file being written; `release()`
            # has never raised at its callers (`run()` calls it inside the per-host loop, which
            # only guards `canary`), and a sweep must not abort over one release.
            silence.note("binding_health.py:release-write")
            landed, detail = False, "the temp copy could not be written"
        if landed:
            return why
    return ("NOT RELEASED: HOST_QUARANTINE.json could not be written after %d attempts (%s); "
            "%s is still quarantined despite: %s" % (CAS_ATTEMPTS, detail, host, why))


def _fetch_chars(host, title):
    """-> (chars, problem-or-None) for one title. Never raises.

    `problem` is any reason this fetch is not usable evidence that the host is answering: a
    transport error, or a document that came back but is not an article.

    THE PAGE IS JUDGED BY `feats.page_looks_real`, NOT BY ITS LENGTH. This counted characters and
    the caller compared them against a hardcoded 200 -- the first and weakest of the three layers
    `page_looks_real` already applies for exactly this question (length, then an explicit refusal
    phrase, then positive evidence of wiki markup). A Cloudflare interstitial, a login wall, a
    JS challenge or a rate-limit notice is a real document and is comfortably over 200
    characters, so every one of them read here as "the host is serving pages" -- the same
    confusion that filed 1,364 throttled fetches as honest absences (feats.py:204), arriving in
    the one module whose entire job is to notice that a host has stopped answering honestly. For
    a RAW-mode host (every API-closed wiki, D&D Wiki among them) nothing else in the chain
    catches it either: `endpoint.fetch_raw` only rejects bodies literally starting `<!doctype` or
    `<html>`. Judged on the RAW wikitext, before any stripping, because the refusal and markup
    markers live in the page as served.
    """
    try:
        import feats as F
        got = F.fetch(host, [title])
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, str(e)[:120])
    if not got:
        return 0, None
    text = " ".join(str(v) for v in got.values()) if isinstance(got, dict) else str(got)
    # NO TITLE IS PASSED: `page_looks_real` never read the one this handed it, and the check a
    # reader would infer from that argument -- the article must name the title asked for -- is
    # the one thing that must NOT be applied here, because the titles this probe uses carry
    # catalogue disambiguators no article contains. See `feats.page_looks_real`. (9beb0391c8ab)
    real, why = F.page_looks_real(text)
    if not real:
        return len(text.strip()), "not an article: %s" % why
    return len(text.strip()), None


def _candidate_titles(title):
    """One title or many -> the bounded list this probe will actually attempt.

    ONE PLACE, so the RECORD and the PROBE cannot disagree about what was asked. `canary()`
    stores the candidates in its report and `_probe_present` tries them, and while each did its
    own normalisation the report could name a set the probe never used -- most obviously the
    `PRESENT_CANDIDATES` bound, which lived only in the prober. `known_present_titles` already
    returns a list; a bare string is still accepted because `known_present_title` (singular) and
    the drill's stand-ins both hand one over.
    """
    return ([title] if isinstance(title, str) else list(title or []))[:PRESENT_CANDIDATES]


def _probe_present(host, title):
    """Does this host still resolve a title we know it holds? -> (ok, detail).

    NO `timeout` PARAMETER. This declared `timeout=25`, passed it to nothing, and thereby
    offered a bound it did not have: `_fetch_chars` calls `feats.fetch`, which takes no timeout
    and applies `feats.TIMEOUT` inside `feats.api`. A knob that reads as a control and controls
    nothing is worse than no knob, because the caller stops looking for the real one. Dropped
    rather than threaded through, because the RAW path (`endpoint.fetch_raw`, every API-closed
    wiki) does not take one either, so a threaded parameter would still be honoured for some
    hosts and silently ignored for the rest -- the same lie with a smaller blast radius.
    (order 0f8be4893543)

    TAKES A LIST, AND ONE HIT IS ENOUGH. This probed exactly one title until run #33, and that
    single title came from `known_present_title`, which returns a CATALOGUE ENTRY NAME. Entry
    names carry the cataloguer's disambiguators -- `Scout (Jeremy Willis)`, `Sweet Tooth (Marcus
    "Needles" Kane)`, `Cetana (the Synthetic Queen)` -- and no wiki has an article at that
    string. So the probe asked live wikis for pages that could not exist, got nothing, and
    concluded the HOST was dead. Run #33's first full canary sweep quarantined 20 of 134 hosts
    on this alone: teamfortress, stellaris, rocketleague and seventeen more, every one of them
    up and serving. A quarantine stops mining, so a false one is not a cosmetic error.

    Two changes, both needed. The parenthetical is stripped, which recovers `Scout` (12,169
    chars) from `Scout (Jeremy Willis)`. And SEVERAL candidates are tried rather than one,
    because stripping is not sufficient either: `Cetana` is a real entry whose article this wiki
    genuinely does not have, and one absent page must not convict a host. The first title that
    resolves ends the probe -- that is a short-circuit on success, not a truncation, since the
    question is "does this host serve anything we know it holds" and one hit answers it.

    The failure branch IS bounded, at `PRESENT_CANDIDATES`, and that bound is reported in the
    detail rather than left implicit: a host is called dead only after that many known titles
    all came back empty, and the reader can see how many were asked.
    """
    candidates = _candidate_titles(title)
    tried, errors = [], []
    for t in candidates:
        n, err = _fetch_chars(host, t)
        tried.append(t)
        if err:
            errors.append(err)
            continue
        if n <= 0:
            # NOTHING CAME BACK. `_fetch_chars` returns `(0, None)` for an EMPTY fetch -- not an
            # error, but nothing for `page_looks_real` to have judged either -- so this is the one
            # `err is None` case that is not a page. It is kept out of `errors` deliberately: the
            # branch below distinguishes "every probe errored" from "the titles returned nothing",
            # and an empty fetch is the second.
            #
            # THIS WAS `if n >= 200`, A SECOND HARDCODED COPY OF `feats.MIN_REAL_PAGE_CHARS`, and
            # `_fetch_chars`'s own docstring names that comparison as the defect it was written to
            # remove: "THE PAGE IS JUDGED BY `feats.page_looks_real`, NOT BY ITS LENGTH ... the
            # caller compared them against a hardcoded 200". The caller went on doing it. Harmless
            # while the two numbers agreed, and a false-quarantine engine the moment the constant
            # is LOWERED -- short-but-real articles would be refused here and live hosts called
            # dead. The length rule now lives in exactly one place. (order d66e1c8d79cb)
            continue
        # THE SECOND OPERAND WAS `len(tried)` TOO, so this always read "candidate N of N
        # tried" -- the reader could see only that the last candidate tried was the last
        # candidate tried, never how many were AVAILABLE to try. `len(candidates)` is the
        # total this call planned to attempt (bounded at PRESENT_CANDIDATES), which is the
        # number the docstring above actually promises: "the reader can see how many were
        # asked." (order f282ba72f742)
        return True, "%d chars from %r (candidate %d of %d tried)" % (
            n, t, len(tried), len(candidates))
    if not tried:
        return False, "no catalogued title to probe with"
    if errors and len(errors) == len(tried):
        # "errored" covers both shapes `_fetch_chars` reports: the request never completed, and
        # the request completed with something that is not an article (a block page or an
        # interstitial). Both mean the same thing here -- nothing came back that proves this host
        # is still answering -- and the detail says which one it was.
        return False, "every probe failed: %s" % errors[0]
    # EVERY TITLE THAT WAS TRIED, BY NAME. This named `tried[:4]` while the count beside it said
    # 8, so the reader who wants to know WHICH title the probe should have hit -- the first
    # question to ask when a live host fails its canary, per `--titles`' own help text -- could
    # see half of them, and nothing said the rest existed. The docstring above promises "the
    # reader can see how many were asked"; the list is what makes that actionable. The list
    # cannot run away: `_candidate_titles` bounds it at PRESENT_CANDIDATES before the probe
    # starts. (order d6ca84486153)
    return False, ("%d known-present title(s) all returned nothing or too little to be a page "
                   "(tried: %s)" % (len(tried), ", ".join(repr(t) for t in tried)))


# The exact wording `feats.page_looks_real` refuses a BLOCK PAGE with, matched as a substring
# rather than reconstructed -- the same way `feats._SUPERSEDED_GATE_MARK` matches that gate's
# third layer, so the two cannot drift apart silently. It is what separates "we were blocked"
# from "nothing resolved" in `_probe_absent`, and those two have opposite consequences for the
# host: the first is `could not ask`, the second is a clean absence.
_BLOCKED_MARK = "refusal marker"


def _probe_absent(host):
    """Does this host correctly say NO to a title nobody holds? -> (ok, detail).

    No `timeout` parameter either, and for the reason given at `_probe_present`: this one
    declared one and handed `feats.fetch` nothing but the host and the probe title.

    The check nobody thinks to write, and the one that catches a host answering yes to
    everything -- a soft-404, a search page, a login wall dressed as an article. Without it a
    'healthy' verdict means only that something came back.

    JUDGED BY `feats.page_looks_real`, THE SAME GATE `_fetch_chars` PUTS THE PRESENT PROBE
    THROUGH, and until now it was the only fetched body in this module that was not. This read
    `if got: return False, ...` -- ANY returned bytes convicted the host -- while its sibling
    twenty lines up argues the case at length: "A Cloudflare interstitial, a login wall, a JS
    challenge or a rate-limit notice is a real document and is comfortably over 200 characters",
    and for a RAW-mode host (every API-closed wiki, D&D Wiki among them) nothing else in the
    chain catches it because `endpoint.fetch_raw` only rejects bodies literally starting
    `<!doctype` or `<html>`. Every word of that applies here verbatim.

    IT MATTERS MORE HERE THAN ANYWHERE. `verdict()` handles `ok_absent is False` BEFORE it asks
    about reachability -- "That IS a host fault, whether or not it is reachable" -- so this is
    the single probe outcome that can quarantine a demonstrably live wiki with no second
    opinion, and the recorded reason would be actively wrong: it would say the wiki answers yes
    to everything when what happened is that we were blocked.

    Symmetry is the argument for the gate, not leniency. `_probe_present` only counts a hit that
    CLEARS `page_looks_real`, so a body that fails the same gate here cannot have made those
    hits meaningless -- the two probes now judge "is this an article" by one rule. Three
    outcomes, and the detail says which:
      * an article        -> False. The host really did resolve a title nobody holds. Unchanged.
      * a refusal marker  -> None. We were BLOCKED; that is "could not ask", not a host fault,
                             and `verdict()` already handles the third value.
      * too thin / no wiki markup -> True. Nothing resolved into an article, which is absence.
    Judged on the RAW text before any stripping, exactly as `_fetch_chars` does, because the
    refusal and markup markers live in the page as served. (order 27f445b58a76)
    """
    try:
        import feats as F
        got = F.fetch(host, [ABSENT_PROBE])
    except Exception as exc:
        # NOT ASKED IS NOT ANSWERED, and this returned `True, "no answer, which is the correct
        # answer"` for EVERY exception -- a timeout, a 500, a DNS failure, an ImportError, a
        # bug in `feats.fetch`. So the one probe written to catch a host that says yes to
        # everything certified that host as sound whenever the probe itself could not run.
        # The canary's whole value is telling "this host refused a fake title" apart from
        # "something came back", and it could not tell either from "I never got to look".
        #
        # UNKNOWN, not False: returning False would quarantine a perfectly good wiki on a
        # transient network blip, which is the false-quarantine failure `_probe_present`'s own
        # comment warns about at length. `verdict()` decides what to do with a probe that did
        # not run; what this function must not do is invent a pass. Found by the run #34 sweep
        # (orders 9b0e5cf4dfe2 / 2cfc022d8e04, filed twice independently).
        return None, "could not ask (%s) -- NOT a verdict about this host" % type(exc).__name__
    if not got:
        return True, "correctly absent -- nothing came back for a title that cannot exist"
    text = " ".join(str(v) for v in got.values()) if isinstance(got, dict) else str(got)
    # NO TITLE IS PASSED, for the reason `_fetch_chars` gives: `page_looks_real` takes none, and
    # the check a reader would infer from one must not be applied to a probe title by design.
    real, why = F.page_looks_real(text)
    if real:
        return False, ("resolved a title that cannot exist -- this host answers yes to "
                       "everything, so its hits prove nothing (%s)" % why)
    if _BLOCKED_MARK in why:
        return None, ("could not ask -- the impossible title came back as a block page (%s), so "
                      "nothing here is a verdict about this host" % why)
    return True, "correctly absent -- %s" % why


def _probe_reachable(host):
    """Does this host's API answer at all? -> (ok, detail).

    THE THIRD PROBE, and the one that decides whether a failure is the HOST's fault. Without it
    the canary had exactly two outcomes and had to force every failure into one of them, so
    "this wiki is down" and "these entry names are not article titles on this wiki" both came
    out as DEAD. They are not the same fault and they do not have the same remedy: the first
    should stop mining the host, the second must not, because the host is fine and mining it is
    still the right thing to do.

    Run #33 measured the difference. `eberron.fandom.com` answers siteinfo with HTTP 200 and is
    a perfectly live wiki; its bound source is the D&D sourcebook *Rising from the Last War*,
    whose catalogued entries are rules features -- `Alchemical Savant`, `Arcane Firearm`,
    `Eldritch Cannon` -- which that wiki has no articles for. Eight candidates, eight misses,
    and the old canary called the host dead. `www.dandwiki.com` fails this probe outright: 403,
    "restricted to logged in users". Only the second is a host fault.
    """
    try:
        import feats as F
        d = F.api(host, {"action": "query", "meta": "siteinfo"}, retries=0)
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])
    if not isinstance(d, dict) or "query" not in d:
        return False, "siteinfo returned nothing usable -- the API is not answering"
    return True, "siteinfo answered"


# ------------------------------------------------- IS THIS HOST THE WIKI IT IS BOUND TO?
#
# The three probes above answer "is the host up" and "do its titles resolve". Neither can tell
# apart the two entirely different faults that both come out as `healthy is None`:
#
#   * the SOURCE IS BOUND TO THE WRONG WIKI -- prime.fandom.com serves the Prime Hydration
#     drink wiki, starrealms.fandom.com serves 'The Brain World Wikia'. Real, actionable, and a
#     curatorial call: rebind or unbind.
#   * the BINDING IS RIGHT AND THE ENTRY NAMES ARE NOT ARTICLE TITLES -- eberron.fandom.com IS
#     the Eberron Wiki; its bound source's catalogued entries are rules features (`Alchemical
#     Savant`, `Arcane Firearm`) which that wiki has no articles for. Nothing is broken and
#     nothing can repair it.
#
# Until now both filed the same BOTS work order, so three permanently-unfixable ones re-filed
# every sweep for ever -- a queue entry addressed to a bot for a job no bot can do, which is
# how a real signal becomes furniture. The discriminator is MEASURED, not listed by hand: a
# hand-maintained roster of "known-fine" hosts is the same smaller-universe failure this
# project keeps finding, and it would go stale the day a source was rebound.
_IDENTITY_STOPWORDS = {"wiki", "wikia", "fandom", "the", "a", "an", "of", "and",
                       "encyclopedia", "database", "official"}

# Calibrated 2026-08-26 against all five live suspects. The confirmed three scored 100, 100 and
# 100; the two genuine misbindings scored 50 (Prime Hydration Wiki vs 'Prime World Equipment',
# which share only the generic word 'Prime') and 36 (The Brain World Wikia vs 'Star Realms').
# The band between the thresholds is deliberately left UNDECIDED rather than split down the
# middle -- a host this cannot classify is reported as unclassified, because guessing is what
# put an unfixable order in a bot's queue in the first place.
BINDING_CONFIRMED_AT = 85
BINDING_MISBOUND_BELOW = 65


def _normalise_name(s):
    """A wiki name and a source name, reduced to their content words."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    return " ".join(t for t in cleaned.split() if t not in _IDENTITY_STOPWORDS)


def binding_verdict(sitename, source_names):
    """PURE. Does the wiki's own name correspond to the source bound to it?

    -> {"verdict": CONFIRMED | MISBOUND | UNCLASSIFIED | UNKNOWN, "score":.., "sitename":..}

    Separated from the probe, like `verdict()` above and for the same reason: the decision is
    easy to get subtly wrong and must be attackable by the drill without a network, rather than
    inferred from whichever branch today's internet happens to produce.

    THE SCORE OF 100 CAN COME FROM CONTAINMENT ALONE, and the record now says when it did.
    `token_set_ratio` returns 100 whenever one name's words are a subset of the other's, however
    much unrelated material the longer side carries, so a bare containment reaches CONFIRMED on
    its own (order 30854f11f322). `containment` in the returned record marks that case, because
    all three of the live confirmations rest on exactly it -- `Eberron` inside `Eberron: Rising
    from the Last War`, `War Thunder` inside `War Thunder + World of Tanks/...`, `ANEURISM`
    inside `ANEURISM IV` -- and so does the false positive the order names, `Prime` inside
    `Prime World Equipment`.

    AND THAT IS WHY THE THRESHOLD IS NOT TIGHTENED HERE. The obvious remedy -- combine
    `token_set_ratio` with a length- or coverage-aware ratio -- was measured against the
    calibration set and it CANNOT separate the two, because they are the same shape. Take the
    pair that has to be separated: `eberron` vs `eberron rising from last war` must CONFIRM,
    `legends` vs `league legends` must not. Same token counts, same seven characters on the
    short side, and every rapidfuzz metric ranks the false positive HIGHER, not lower
    (`ratio` 40.0 vs 66.7; `token_sort_ratio` the same; `WRatio` 90 vs 90). Any floor that
    refuses `legends` refuses `Eberron Wiki` first. Nor does "is the short name an ordinary
    English word" work, which is the discriminator a person is actually using: `aneurism` is
    one, and `ANEURISM Wiki` is a live confirmed binding. The separating evidence is not in
    these two strings at all -- it is in whether the wiki's CONTENT answers for this source,
    which `hostcheck` measures and this pure function is not given. Recorded, not guessed:
    a caller that wants to distrust a containment-only CONFIRMED can now see which ones they
    are, and the order stays open for the evidence that would actually settle it.
    """
    if not sitename or not source_names:
        return {"verdict": "UNKNOWN", "score": None, "sitename": sitename,
                "sources": list(source_names or []),
                "detail": "no sitename to compare" if not sitename
                          else "no source name bound to this host"}
    from rapidfuzz import fuzz
    site = _normalise_name(sitename)
    # A host can carry more than one source; the binding is right if it matches ANY of them.
    scored = [(fuzz.token_set_ratio(site, _normalise_name(n)), n) for n in source_names]
    # THE TIE IS BROKEN BY MEASUREMENT AND THEN DECLARED, not settled by the alphabet. This was
    # `max(scored)` over (score, name) tuples, so equal scores fell through to a comparison of
    # the SOURCE NAMES -- and for the big shared wikis, which legitimately carry several sources
    # at once, `matched` was then whichever co-bound source happened to sort last. That is a coin
    # toss printed in the field a person reads to decide whether a binding is right. Two changes:
    # among the sources tied at the top score the whole-string `ratio` picks the closest, which
    # is evidence rather than spelling (and `max` keeps the caller's own order when even that
    # ties, so the answer is stable across runs); and every tied source is carried out in
    # `tied_with`, because the honest report of a tie is the tie, not one arbitrary winner.
    # (order 18a2053bc62d)
    score = max(s for s, _ in scored)
    tied = [n for s, n in scored if s == score]
    best = max(tied, key=lambda n: fuzz.ratio(site, _normalise_name(n)))
    # What the score rests on, measured beside it rather than inferred from it: `tight` is the
    # whole-string ratio, which containment does NOT flatter, so a large gap between the two is
    # the signature of a match carried entirely by one name's words sitting inside the other's.
    matched = _normalise_name(best)
    site_words, best_words = set(site.split()), set(matched.split())
    contained = bool(site_words) and bool(best_words) and (
        site_words <= best_words or best_words <= site_words)
    tight = fuzz.ratio(site, matched)
    if score >= BINDING_CONFIRMED_AT:
        v, why = "CONFIRMED", "the wiki names itself after the source bound to it"
    elif score < BINDING_MISBOUND_BELOW:
        v, why = "MISBOUND", "the wiki serves something else entirely"
    else:
        v, why = "UNCLASSIFIED", "too close to call from the names alone -- a person should look"
    return {"verdict": v, "score": score, "sitename": sitename, "matched": best,
            "sources": list(source_names), "detail": why,
            # The strength of the evidence, not a second verdict. `containment` says one name's
            # words sit wholly inside the other's, which is what `token_set_ratio` scores 100
            # whatever else the longer name carries; `tight` is the same pair judged as whole
            # strings, and the distance between them is how one-sided the match is.
            "containment": contained, "tight": tight,
            # Every source that scored the same as `matched`. Empty on the ordinary one-source
            # host; on a shared wiki it is the whole set the score could equally have named, so
            # a reader can see that `matched` was chosen from among these rather than measured
            # alone. Named in full -- ranking is allowed here, truncating a list a person reads
            # to act is not.
            "tied_with": [n for n in tied if n != best]}


def _probe_identity(host):
    """What does this wiki call ITSELF? -> (sitename, detail)."""
    try:
        import feats as F
        d = F.api(host, {"action": "query", "meta": "siteinfo", "siprop": "general"},
                  retries=0)
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, str(e)[:120])
    g = ((d or {}).get("query") or {}).get("general") or {}
    name = g.get("sitename")
    return name, ("sitename %r" % name if name else "siteinfo carried no sitename")


def verdict(ok_present, ok_absent, ok_reachable, det_p="", det_a="", det_r=""):
    """PURE. The three probe outcomes -> (healthy, reason).

    Separated from `canary` so the drill can attack every combination without a network. The
    decision this encodes is the whole point of run #33's change and is easy to get subtly
    wrong, so it is asserted directly rather than inferred from a live probe that can only ever
    exercise whichever branch today's internet happens to produce.
    """
    # THE ABSENT PROBE HAS THREE ANSWERS, NOT TWO. `_probe_absent` returns None when it could
    # not ask at all -- a timeout, a 500, a DNS failure -- and both branches below read a bare
    # falsy value as "the host resolved a title nobody holds", which is a HOST FAULT and
    # quarantines it. So a network blip on our side would have stopped mining a perfectly good
    # wiki, which is precisely the false-quarantine failure this module's own comments warn
    # about. Handled FIRST, before either test can see it.
    #
    # It also must not be able to reach `return True`: a probe that did not run cannot be half
    # of a clean bill of health. Unknown falls through to the reachability question, which is
    # the honest thing left to ask.
    if ok_absent is None:
        if ok_present:
            return None, ("host serves a known title, but the absent-probe could not run (%s) "
                          "-- not proven sound, not proven at fault" % det_a)
        if ok_reachable:
            return None, ("host is UP, no catalogued title resolved (%s), and the absent-probe "
                          "could not run (%s)" % (det_p, det_a))
        return False, "host unreachable: %s (present probe: %s)" % (det_r, det_p)
    if ok_present and ok_absent:
        return True, None
    if not ok_absent:
        # A host that resolves a title nobody holds is answering yes to everything; its hits
        # prove nothing. That IS a host fault, whether or not it is reachable.
        return False, "absent probe resolved: " + det_a
    if ok_reachable:
        return None, ("host is UP but no catalogued title resolved (%s) -- suspect the binding "
                      "or the entry names, not the host" % det_p)
    return False, "host unreachable: %s (present probe: %s)" % (det_r, det_p)


def canary(host, present_title, sources=None):
    """All three probes for one host, plus its identity when the titles failed. -> record.

    The verdict is deliberately THREE-VALUED. `healthy` is True when the host serves what we
    know it holds and correctly refuses what nobody holds; False when the host itself is at
    fault; and None -- neither healthy nor quarantined -- when the host is demonstrably up but
    no catalogued title resolved, which is a fault in the BINDING or the entry names, not in the
    host. `run()` quarantines only on False, because a quarantine stops mining and mining a live
    wiki is still correct even when this particular probe could not find a page.
    """
    ok_p, det_p = _probe_present(host, present_title)
    ok_a, det_a = _probe_absent(host)
    ok_r, det_r = (True, "not probed -- the known-present title resolved") if ok_p \
        else _probe_reachable(host)
    healthy, reason = verdict(ok_p, ok_a, ok_r, det_p, det_a, det_r)
    rec = {"host": host, "at": time.time(), "healthy": healthy,
           # `titles`, PLURAL, AND ALWAYS A LIST. `run()` hands this the list from
           # `known_present_titles`, and it was stored unchanged under the singular key `title`
           # -- a report field whose name promised one string while holding up to
           # PRESENT_CANDIDATES of them. Nothing read it as a string yet, which is exactly the
           # window in which to fix it: stored data whose name lies about its type is how a
           # future consumer inherits a bug nothing announces. (order cdcb11e3d7fa)
           "present": {"titles": _candidate_titles(present_title),
                       "ok": ok_p, "detail": det_p},
           "absent": {"title": ABSENT_PROBE, "ok": ok_a, "detail": det_a},
           "reachable": {"ok": ok_r, "detail": det_r},
           "reason": reason}
    # ASKED ONLY WHERE THE ANSWER CHANGES ANYTHING -- when the titles did not resolve. A host
    # whose titles resolve is bound correctly by demonstration and does not need its name read;
    # asking anyway would spend a network round trip per host per sweep to confirm what the
    # present-probe just proved.
    if healthy is None and sources:
        sitename, det_i = _probe_identity(host)
        rec["binding"] = binding_verdict(sitename, sources)
        rec["binding"]["probe"] = det_i
    return rec


def _title_variants(name):
    """A catalogue entry name -> the article titles a wiki might actually have it under.

    The raw name first (some wikis really do disambiguate in the title), then the name with a
    trailing parenthetical removed. Written with an explicit scan rather than a regex because
    this file has been through the eaten-escape corruption once already.
    """
    name = (name or "").strip()
    out = [name] if name else []
    if name.endswith(")") and "(" in name:
        bare = name[:name.rindex("(")].strip()
        if bare and bare != name and len(bare) > 2:
            out.append(bare)
    return out


def known_present_titles(host, hosts_map=None, records_dir=None, want=None):
    """Ordered candidate titles this host is believed to hold. See `_probe_present` for why a
    single title is not enough to convict a host."""
    import glob
    want = PRESENT_CANDIDATES if want is None else want
    hosts_map = hosts_map if hosts_map is not None else _load(
        os.path.join(HERE, "data", "WIKI_HOSTS.json"), {})
    sources = [s for s, h in (hosts_map or {}).items() if h == host]
    if not sources:
        return []
    want_src = set(sources)
    out, seen = [], set()
    for p in sorted(glob.glob(os.path.join(records_dir or os.path.join(HERE, "data", "records"),
                                           "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            # RECORDED, NOT MERELY SKIPPED. A record this cannot read is one fewer candidate
            # title, and a host with no candidates left is called dead for a fault that is
            # entirely on this side of the network -- the false-quarantine failure `_probe_present`
            # documents, arriving through the file reader instead of the probe.
            silence.note("binding_health.py:candidate-record")
            continue
        if rec.get("source") not in want_src:
            continue
        for e in (rec.get("entries") or []):
            for t in _title_variants((e or {}).get("name")):
                if len(t) > 3 and t not in seen:
                    seen.add(t)
                    out.append(t)
                    if len(out) >= want:
                        return out
    return out


def known_present_title(host, hosts_map=None, records_dir=None):
    """Pick a title this host is believed to hold: the first catalogued entry of a bound source.

    Derived rather than hand-listed, deliberately. A hand-kept table of canary pages is one more
    list to rot, and this project has been bitten by three of those already (m49's job rosters,
    the four spellings of the cache key, the six-vendor secret list).
    """
    import glob
    hosts_map = hosts_map if hosts_map is not None else _load(
        os.path.join(HERE, "data", "WIKI_HOSTS.json"), {})
    sources = [s for s, h in (hosts_map or {}).items() if h == host]
    if not sources:
        return None
    want = set(sources)
    for p in sorted(glob.glob(os.path.join(records_dir or os.path.join(HERE, "data", "records"),
                                           "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            silence.note("binding_health.py:primary-record")
            continue
        if rec.get("source") in want:
            for e in (rec.get("entries") or []):
                n = (e or {}).get("name")
                if n and len(n) > 3:
                    return n
    return None


def run(limit=None, only=None):
    """Canary every bound host. Error-resilient: one bad host never aborts the sweep.

    A WHOLE-ESTATE REPORT IS NEVER BUILT FROM AN EMPTY HOSTS MAP. The partial-pass branch below
    was armed against exactly this shape -- it compare-and-swaps, and it refuses outright when
    the standing report cannot be read, on the reasoning that "Unreadable is NOT empty" -- and
    the whole-estate branch, which is a blind `_land`, reached the same destination through the
    INPUT file instead of the output one. `WIKI_HOSTS.json` unreadable -> `{}` -> no hosts -> no
    records -> `_land(OUT, {"checked": 0, "failed": 0, "hosts": []})` over a 203-host estate
    report, well-formed and describing a library that is mostly not there. `workorders.sweep`'s
    binding detector then reads `hosts: []` and finds no suspect bindings at all.
    (order 9979963c093a)
    """
    hosts_map = _load(os.path.join(HERE, "data", "WIKI_HOSTS.json"), {}) or {}
    if not hosts_map:
        # REFUSED BEFORE ANYTHING IS PROBED. Absent, empty and unreadable are all refused
        # together here, deliberately: the distinction changes what to say and not what to do,
        # because a whole-estate pass with nothing to check has no report to write in any of the
        # three cases, and the file it would land on is the one thing that still knows the
        # estate. Nothing is written and the caller is told why.
        _report_not_written(
            "BINDING_ESTATE_EMPTY",
            "REFUSING to build a whole-estate report: data/WIKI_HOSTS.json is empty or could "
            "not be read, so this pass has no bound hosts to canary. Landing its result would "
            "replace the standing report with a 0-host one and every downstream reader would "
            "see an estate with no suspect bindings in it. %s keeps the verdicts it already "
            "has." % os.path.basename(OUT))
        return [], 0
    hosts = sorted({h for h in hosts_map.values() if h and not str(h).startswith(("pages:", "doc:"))})
    # host -> every source bound to it. A host can carry several, so the binding is right if
    # its own name corresponds to ANY of them.
    bound_to = {}
    for source, h in hosts_map.items():
        if h:
            bound_to.setdefault(h, []).append(source)
    # WAS THIS PASS FILTERED AT ALL? Asked once, here, and used for every downstream decision,
    # because the three sites below each asked it again as `only or limit` and a falsy-but-given
    # `--limit 0` answered "no" to all of them (orders cd7492eec3bc and f1901d2178ba).
    filtered = bool(only) or limit is not None
    bound_hosts = len(hosts)                    # before the filter, so a refusal can say "0 of N"
    if only:
        hosts = [h for h in hosts if h in set(only)]
    # `is not None`, NOT truthiness. `--limit` defaults to None and `argparse` gives it `type=int`,
    # so `--limit 0` arrives as the integer 0 -- which `if limit:` read as "no limit given" and
    # answered by canarying the WHOLE ~200-host estate. The operator asked for nothing and got
    # every host on the roll: the same falsy-zero slip fixed in `burgs.py`, and here it turns a
    # deliberate no-op into the most expensive command this module has.
    if limit is not None:
        hosts = hosts[:limit]
    out, failed = [], 0
    for h in hosts:
        title = known_present_titles(h, hosts_map)
        if not title:
            # THE STANDING QUARANTINE IS NAMED HERE, because this `continue` jumps past the whole
            # quarantine/release cascade below and nothing else in the report ever mentions it.
            # A host that is already held and then loses all its candidate titles -- records
            # deleted, a source unbound, or `known_present_titles`' own `except` swallowing every
            # record file -- is neither released nor re-quarantined by this pass, and the row it
            # leaves behind said only that it could not be probed. (order 5e2aaac58753)
            #
            # NOT RELEASED, deliberately. The order's remedy reads as "release it", and that
            # would be inventing a clean bill of health for the one host this pass has no
            # evidence about at all -- the false-release mirror of the false-quarantine failure
            # `_probe_present` documents. Nor is the hold permanent, which the order believed it
            # was: `quarantined()` filters on `retry_after`, so an un-renewed quarantine ages out
            # by itself after RETRY_AFTER_S. What was genuinely missing was the CONNECTION, and
            # that is what is added: the row now says the host is held and unprobeable, which is
            # the pair of facts a person needs to act on.
            held = is_quarantined(h)
            out.append({"host": h, "healthy": None, "at": time.time(), "quarantined": held,
                        "reason": "no catalogued entry to probe with"
                                  + (" -- and this host is QUARANTINED, so the hold cannot be "
                                     "re-evidenced or lifted until it has a title to probe with"
                                     if held else "")})
            continue
        try:
            rec = canary(h, title, sources=bound_to.get(h))
        except Exception as e:
            # ERROR-RESILIENT BY CONSTRUCTION (maigret's self-check does the same): one host
            # raising must not cost the other 199 their check.
            rec = {"host": h, "healthy": False, "at": time.time(),
                   "reason": "canary raised %s" % type(e).__name__}
        out.append(rec)
        if rec.get("healthy") is False:
            failed += 1
            quarantine(h, rec.get("reason") or "canary failed")
        elif rec.get("healthy") is True and is_quarantined(h):
            # THE VERDICT IS CAPTURED, not dropped. `release()` returns "NOT RELEASED: ..." when
            # the swap never landed, and this was a bare statement, so a host that stayed
            # quarantined was reported as recovered. (order a29c38c9eff3)
            rec["released"] = not _report_not_released(h, release(h))
        elif rec.get("healthy") is None and is_quarantined(h):
            # A HOST HELD ON THE OLD VERDICT GOES FREE. `healthy is None` now means the host
            # answered its API and correctly refused a title nobody holds -- it is up. It was
            # quarantined under the two-valued canary, which had no way to say that, and a
            # quarantine that outlives the reasoning behind it is just an outage nobody
            # remembers starting. The binding is still suspect and is still reported.
            rec["released"] = not _report_not_released(
                h, release(h, "host is reachable; the failure was in the titles, not the host"))
    # A PARTIAL RUN MUST NOT LAND OVER A WHOLE-ESTATE REPORT. Found 2026-08-26 by tripping it:
    # `--host eberron.fandom.com ...` for five hosts wrote BINDING_HEALTH.json with
    # `"checked": 5`, and the other ~200 hosts simply left the file. Everything downstream reads
    # this report AS the estate -- `workorders.sweep`'s binding detector decides which hosts are
    # suspect from it, and allsweep reconciles against it -- so a targeted re-probe, which is
    # exactly what someone runs while INVESTIGATING a binding, silently shrank the estate to the
    # handful of hosts they were looking at. The same smaller-universe shape as a cap: nothing
    # fails, the file is well-formed, and it describes a library that is mostly not there.
    #
    # Merged rather than refused, because a targeted probe IS the useful thing and its results
    # should be kept: each host's record is replaced by the fresh one, every host not probed
    # keeps the verdict it had, and `checked` counts the whole file rather than this pass.
    if not out and not filtered:
        # AND THE SAME REFUSAL ONE STEP LATER. The hosts map was readable and non-empty and this
        # pass still produced no host record -- every binding is a `pages:`/`doc:` pseudo-host,
        # or the map is not the shape this function reads. Whatever the cause, a 0-host
        # whole-estate report is not a description of this estate, and landing one is the
        # destructive act the guard above exists to prevent, reached by a different road.
        _report_not_written(
            "BINDING_ESTATE_EMPTY",
            "REFUSING to land a whole-estate report with 0 hosts in it: %d source binding(s) "
            "were read and none of them yielded a canaryable host. %s keeps the verdicts it "
            "already has." % (len(hosts_map), os.path.basename(OUT)))
        return out, failed
    if not out:
        # A FILTER THAT MATCHED NOTHING MUST NOT RE-STAMP THE REPORT (order f1901d2178ba). The
        # guard above was `not (only or limit) and not out`, so a FILTERED pass that probed zero
        # hosts -- `--host a-name-with-no-binding`, or `--limit 0` once the line above stopped
        # reading it as "no limit" -- fell straight through to the merge path. That path is
        # whole-file: `merged` becomes every PRIOR host, `at` is bumped to now, and the file
        # lands with `partial_pass.probed: []`. Nothing was canaried, no verdict changed, and the
        # report's own freshness stamp now says otherwise -- which is the one field every reader
        # of this file uses to decide whether to trust it. `workorders.sweep`'s binding detector
        # and `allsweep`'s reconciliation both read it as the estate's current state.
        #
        # This is why the two orders had to be taken together and neither alone: fixing the
        # falsy-zero above is what makes `--limit 0` START producing an empty host list, which is
        # precisely the input this branch mishandles. The first fix would have armed the second.
        _report_not_written(
            "BINDING_FILTER_MATCHED_NOTHING",
            "REFUSING to re-stamp %s: this pass was filtered (%s), selected %d of %d bound "
            "host(s) and produced 0 host records, so it canaried nothing. Landing it would bump "
            "the report's `at` to now while every verdict in it came from an earlier run."
            % (os.path.basename(OUT),
               ", ".join(filter(None, ["--host " + "/".join(sorted(only)) if only else "",
                                       "--limit %d" % limit if limit is not None else ""])),
               len(hosts), bound_hosts))
        return out, failed
    merged, prior = list(out), {}
    # READ THE DIGEST BEFORE THE CONTENT, so a file that moves between the two cannot be merged
    # into silently -- see `_land_cas`. Meaningless on the whole-estate path, which reads nothing.
    prior_digest = silence.digest_of(OUT) if filtered else None
    if filtered:
        try:
            with open(OUT, encoding="utf-8") as f:
                prior = {h.get("host"): h for h in (json.load(f).get("hosts") or [])}
        except FileNotFoundError:
            prior = {}
        except Exception:
            # Unreadable is NOT empty. Landing a five-host file over a report that could not be
            # read would destroy the very thing this guard exists to protect, so the partial
            # results are returned to the caller and nothing is written.
            silence.note("binding_health.py:merge-unreadable")
            # THROUGH `_report_not_written` LIKE THE OTHER TWO. This was the THIRD
            # write-not-landed exit in this function and the only one that merely printed, which
            # is exactly the inconsistency that teaches the next reader the unescalated one is
            # deliberate. JANITOR, same as its siblings and for the same reason given there: the
            # probes ran and their results are returned, so what went stale is the OBSERVATION on
            # disk, not an action being faked. (order d19d705925e3)
            _report_not_written(
                "BINDING_HEALTH_PARTIAL_NOT_MERGED",
                "%s could not be read, so this partial run has nothing to merge into and will "
                "NOT land over it; the %d host(s) it probed are not in the report. Run without "
                "--host/--limit to rebuild the whole report."
                % (os.path.basename(OUT), len(out)))
            return out, failed
        for h in out:
            prior[h.get("host")] = h
        merged = [prior[k] for k in sorted(prior)]
    # `checked` AND `failed` NOW COUNT THE SAME POPULATION. `checked` is `len(merged)` -- the
    # whole file, which the merge made deliberately whole-file -- while `failed` was the count
    # from this pass alone, so a `--host` run over five hosts could land "checked: 203,
    # failed: 1" where one of FIVE failed. Nothing in src/ reads `failed`, so the cost was
    # entirely to the person reading the report, who is invited by two numbers side by side to
    # read them as a ratio. Both are now taken over `merged`, and this pass's own count is kept
    # beside them under a name that says which pass it belongs to. (order 6c5faf62b2c6)
    failed_in_report = sum(1 for h in merged if h.get("healthy") is False)
    doc = {"at": time.time(), "checked": len(merged), "failed": failed_in_report,
           "failed_this_pass": failed, "hosts": merged}
    if filtered:
        doc["partial_pass"] = {"probed": sorted(h.get("host") for h in out),
                               "note": "merged into the standing report; hosts not listed "
                                       "here carry the verdict from an earlier pass"}
        # COMPARE-AND-SWAP, because everything above this line is a read-modify-write. A refusal
        # here is the guard working: another writer landed a report after this pass read one, and
        # the merged copy in hand no longer describes what is on disk. Nothing is written and the
        # probe results are still returned, exactly as on the unreadable-report branch above.
        landed, why = _land_cas(OUT, doc, prior_digest)
        if not landed:
            _report_not_written(
                "BINDING_HEALTH_PARTIAL_NOT_MERGED",
                "this partial pass did NOT land -- %s The %d host(s) it probed were not merged; "
                "re-run to fold them into the current report." % (why, len(out)))
    elif not _land(OUT, doc):
        # The canary results are still returned -- the run happened -- but anything reading
        # BINDING_HEALTH.json will be looking at the PREVIOUS round's verdicts, so say so here
        # rather than let a stale report pass for a fresh one.
        _report_not_written(
            "BINDING_HEALTH_NOT_WRITTEN",
            "%s could not be written (rename refused); the file on disk is from an earlier run, "
            "not this one, and %d host(s) checked this pass are not in it"
            % (os.path.basename(OUT), len(out)))
    return out, failed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="canary every bound host")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--host", action="append", help="only these hosts")
    ap.add_argument("--quarantined", action="store_true")
    ap.add_argument("--titles", metavar="HOST",
                    help="show the candidate titles the canary would probe this host with -- "
                         "the first question to ask when a live host fails its canary")
    a = ap.parse_args()
    if a.titles:
        cands = known_present_titles(a.titles)
        print("primary : %r" % (known_present_title(a.titles),))
        if not cands:
            print("no catalogued entry to probe with -- this host cannot be canaried")
            return 1
        for i, t in enumerate(cands, 1):
            print("  %2d. %r" % (i, t))
        return 0
    if a.quarantined:
        try:
            q = quarantined()
        except QuarantineUnreadable as e:
            # NOT "no hosts quarantined". The operator asked what is held and the honest answer
            # is that the file will not open; printing the empty list would be the same lie the
            # readers downstream were told.
            print("binding_health: %s" % e, file=sys.stderr)
            return 1
        if not q:
            print("no hosts quarantined")
            return 0
        for h, r in sorted(q.items()):
            print("  %-34s %s  (x%s, retry after %s)"
                  % (h, r.get("reason", "")[:60], r.get("times"),
                     time.strftime("%Y-%m-%d %H:%M", time.localtime(r.get("retry_after", 0)))))
        return 0
    if a.run:
        out, failed = run(limit=a.limit, only=a.host)
        for r in out:
            state = {True: "ok  ", False: "FAIL", None: "skip"}[r.get("healthy")]
            print("  %s %-34s %s" % (state, r.get("host", "?")[:34], (r.get("reason") or "")[:60]))
        print("\n%d host(s) checked, %d failed and quarantined" % (len(out), failed))
        return 1 if failed else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
