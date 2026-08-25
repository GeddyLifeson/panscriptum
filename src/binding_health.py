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


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception:
        silence.note("binding_health.py:load")
        return default


def _land(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True, ensure_ascii=False)
    silence.replace_retry(tmp, path)


def quarantined():
    """-> {host: record}. Only those whose retry-after has not yet passed."""
    now = time.time()
    return {h: r for h, r in (_load(QUARANTINE, {}) or {}).items()
            if (r or {}).get("retry_after", 0) > now}


def is_quarantined(host):
    return host in quarantined()


def quarantine(host, reason, last_good=None):
    """Record a host as failing, WITH ITS REASON. Never a silent skip, never a deletion."""
    q = _load(QUARANTINE, {}) or {}
    prev = q.get(host) or {}
    q[host] = {"reason": str(reason)[:300], "at": time.time(),
               "retry_after": time.time() + RETRY_AFTER_S,
               "last_good": last_good if last_good is not None else prev.get("last_good"),
               "times": int(prev.get("times", 0)) + 1}
    _land(QUARANTINE, q)
    try:
        import escalation as ESC
        # SUPERVISOR, not OWNER: one host failing closes that area of the park, never the park.
        ESC.escalate(ESC.SUPERVISOR, "HOST_QUARANTINED",
                     "%s quarantined: %s" % (host, reason), source=host, who="binding_health")
    except Exception:
        silence.note("binding_health.py:escalate")
    return q[host]


def release(host, why="canary passed"):
    q = _load(QUARANTINE, {}) or {}
    if host in q:
        q.pop(host, None)
        _land(QUARANTINE, q)
    return why


def _fetch_chars(host, title):
    """-> (chars, error-or-None) for one title. Never raises."""
    try:
        import feats as F
        got = F.fetch(host, [title])
    except Exception as e:
        return 0, "%s: %s" % (type(e).__name__, str(e)[:120])
    if not got:
        return 0, None
    text = " ".join(str(v) for v in got.values()) if isinstance(got, dict) else str(got)
    return len(text.strip()), None


def _probe_present(host, title, timeout=25):
    """Does this host still resolve a title we know it holds? -> (ok, detail).

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
    tried, errors = [], []
    for t in ([title] if isinstance(title, str) else list(title or []))[:PRESENT_CANDIDATES]:
        n, err = _fetch_chars(host, t)
        tried.append(t)
        if err:
            errors.append(err)
            continue
        if n >= 200:
            return True, "%d chars from %r (candidate %d of %d tried)" % (
                n, t, len(tried), len(tried))
    if not tried:
        return False, "no catalogued title to probe with"
    if errors and len(errors) == len(tried):
        return False, "every probe errored: %s" % errors[0]
    return False, ("%d known-present title(s) all returned nothing or too little to be a page "
                   "(tried: %s)" % (len(tried), ", ".join(repr(t) for t in tried[:4])))


def _probe_absent(host, timeout=25):
    """Does this host correctly say NO to a title nobody holds? -> (ok, detail).

    The check nobody thinks to write, and the one that catches a host answering yes to
    everything -- a soft-404, a search page, a login wall dressed as an article. Without it a
    'healthy' verdict means only that something came back.
    """
    try:
        import feats as F
        got = F.fetch(host, [ABSENT_PROBE])
    except Exception:
        return True, "no answer, which is the correct answer"
    if got:
        return False, ("resolved a title that cannot exist -- this host answers yes to "
                       "everything, so its hits prove nothing")
    return True, "correctly absent"


def canary(host, present_title):
    """Both probes for one host. -> record."""
    ok_p, det_p = _probe_present(host, present_title)
    ok_a, det_a = _probe_absent(host)
    healthy = ok_p and ok_a
    return {"host": host, "at": time.time(), "healthy": healthy,
            "present": {"title": present_title, "ok": ok_p, "detail": det_p},
            "absent": {"title": ABSENT_PROBE, "ok": ok_a, "detail": det_a},
            "reason": None if healthy else
            ("known-present probe failed: " + det_p if not ok_p
             else "absent probe resolved: " + det_a)}


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
            continue
        if rec.get("source") in want:
            for e in (rec.get("entries") or []):
                n = (e or {}).get("name")
                if n and len(n) > 3:
                    return n
    return None


def run(limit=None, only=None):
    """Canary every bound host. Error-resilient: one bad host never aborts the sweep."""
    hosts_map = _load(os.path.join(HERE, "data", "WIKI_HOSTS.json"), {}) or {}
    hosts = sorted({h for h in hosts_map.values() if h and not str(h).startswith(("pages:", "doc:"))})
    if only:
        hosts = [h for h in hosts if h in set(only)]
    if limit:
        hosts = hosts[:limit]
    out, failed = [], 0
    for h in hosts:
        title = known_present_titles(h, hosts_map)
        if not title:
            out.append({"host": h, "healthy": None, "reason": "no catalogued entry to probe with"})
            continue
        try:
            rec = canary(h, title)
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
            release(h)
    _land(OUT, {"at": time.time(), "checked": len(out), "failed": failed, "hosts": out})
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
        q = quarantined()
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
