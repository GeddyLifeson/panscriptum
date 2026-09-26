"""dates_check.py -- does every era event sit in a year its master ties allow?

    python dates_check.py II            # one age: the counts, then every outlier
    python dates_check.py all --quiet   # every age, counts only

An era event is tied to the master record three ways, and each tie is a promise about its date:

  after     the {"after": M} marker (or the file's span) puts it in the gap after master M: it falls between M and
            the next master. The build enforces this by construction, so it is never an outlier here; but when the
            writer's own year (era_between) lies outside that gap, the build could not honour both and dated it
            inside the gap anyway: that is a "window" outlier (the event sits in the wrong gap, or its year is wrong).
  cause     a link {"to": X, "type": "cause"}: the event comes no later than X.
  sequel    a link of type sequel, legacy, answers or fulfils: the event comes no earlier than X.

Links of type parallel, location and person carry no promise about order. X may be a master event of any age or
an era event of the same age. Dates are compared as days (y, m, d) from the build (build_era.date_era), so this
reads the writer files as they stand, not a stale annals_dated.json. Exit status 1 when any outlier is found.
"""
import argparse
import json
import os
import sys

import qlib as q

B = q.B
AFTER_TYPES = {'sequel', 'legacy', 'answers', 'fulfils'}


def check_age(k):
    """-> (counts, outliers) for age k; outliers are (kind, event id, file, text)."""
    masters = B.master_events(k)
    seed, writers = B.load_sources(k)
    gaps, problems = B.merge(k, masters, writers)
    if problems:
        raise SystemExit('\n'.join(problems))
    out, _ = B.date_era(k)
    when = {e['id']: (e['y'], e['m'], e['d']) for e in out}
    for e in json.load(open(os.path.join(q.LEG, 'annals_dated.json'), encoding='utf-8')):
        when.setdefault(e['id'], (e['y'], e['m'], e['d']))
    counts = {'events': 0, 'tied': 0, 'window': 0, 'cause': 0, 'sequel': 0}
    outl = []
    for g, evs in enumerate(gaps):
        m = masters[g]
        nxt = masters[g + 1] if g + 1 < len(masters) else None
        for e in evs:
            counts['events'] += 1
            me = when[e['id']]
            tied = False
            eb = e.get('era_between')
            if eb:
                tied = True
                lo, hi = B.era_to_y(eb[0], k), B.era_to_y(eb[1], k)
                if not lo <= me[0] <= hi:
                    counts['window'] += 1
                    outl.append(('window', e['id'], e['_file'], 'era_between %s but placed after %s (%s)%s, dated %s'
                                 % (eb, m['id'], m['date'], ' before %s (%s)' % (nxt['id'], nxt['date']) if nxt else '',
                                    B.reckoning.display(*me, age=k))))
            for ln in e.get('links') or []:
                to, t = ln.get('to'), ln.get('type')
                if to not in when or t not in AFTER_TYPES | {'cause'}:
                    continue
                if not to.startswith('E') or to.startswith('E%s-' % k):
                    tied = True
                x = when[to]
                if t == 'cause' and me > x:
                    counts['cause'] += 1
                    outl.append(('cause', e['id'], e['_file'], 'cause of %s (%s) but dated %s'
                                 % (to, _disp(to, x, k), B.reckoning.display(*me, age=k))))
                elif t in AFTER_TYPES and me < x:
                    counts['sequel'] += 1
                    outl.append(('sequel', e['id'], e['_file'], '%s of %s (%s) but dated %s'
                                 % (t, to, _disp(to, x, k), B.reckoning.display(*me, age=k))))
            counts['tied'] += tied
    return counts, outl


def _disp(i, ymd, k):
    try:
        return B.reckoning.display(*ymd, age=B.reckoning.era_of(*ymd))
    except Exception:  # noqa: BLE001
        return '%d-%02d-%02d' % ymd


def main():
    ap = argparse.ArgumentParser(description='Era events against the master dates they are tied to.')
    ap.add_argument('target', help='I..VII or all')
    ap.add_argument('--quiet', action='store_true', help='counts only')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    keys = q.KEYS if a.target == 'all' else [a.target]
    res, bad = {}, 0
    for k in keys:
        c, o = check_age(k)
        res[k] = {'counts': c, 'outliers': o}
        bad += len(o)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for k in keys:
            c = res[k]['counts']
            print('Age %-4s events %4d  tied to a master %4d  outliers: window %d, cause %d, sequel %d'
                  % (k, c['events'], c['tied'], c['window'], c['cause'], c['sequel']))
            if not a.quiet:
                for kind, i, f, txt in res[k]['outliers']:
                    print('   %-6s %s (%s): %s' % (kind, i, f, txt))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
