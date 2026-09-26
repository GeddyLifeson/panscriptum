"""ages_check.py -- the rulers' ages and the fading of the long years (the owner's rule, permanent canon).

    "State rulers' ages, and enforce ages returning to normal by the Holy Age."

    python ages_check.py master      # eras/RULERS.json, legendarium/appendices/houses.json and every era plan
    python ages_check.py IV          # the rulers of Age IV and eras/age_IV/PLAN_people.json

eras/RULERS.json is the source of truth: every ruler of the master record with birth, accession, death and the ages
at each, and the curve of the long years. The rules:

  record    every year agrees with the annals event that fixes it, every age is the difference of its years, and
            birth <= accession <= end of reign <= death
  ordinary  no one born in FE 1,200 or later lives past 95 (rule.ordinary_from, rule.max_ordinary_age), and no one
            outside the king's kin ever does; the coal-blooded of the Age of Strangers (rule.exempt) are the owner's
            one exception, and they are no rulers
  fading    the king's kin: the longest natural life of each generation after Ailean is no longer than the longest
            of the generation before (the Line of Aisling and the rulers together), and no child of the kin outlives
            the span of a long-lived parent; parents are between 14 and 70 at an ordinary child's birth, and alive
            at it
  houses    a ruler whose dates come from houses.json has exactly the years houses.json gives
  plans     every planned person (eras/age_*/PLAN_people.json) keeps the ordinary rule, and a planned ruler has the
            birth and death RULERS.json gives (a death after the plan's age may be left out)

check_rodais.py runs check_master(); eras/check_era.py runs check_age(k).
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ERAS = os.path.dirname(HERE)
ROOT = os.path.dirname(ERAS)
LEG = os.path.join(ROOT, 'legendarium')
sys.path.insert(0, LEG)
import reckoning as RK  # noqa: E402

ABBR = {a[3]: a for a in RK.AGES}
KEYS = RK.AGE_KEYS
PLAN_INT_ERA = {'I': 'VE', 'V': 'AE'}          # the plans of these ages write years as bare numbers of that era
DIRECT = ('son', 'daughter', 'eldest son', 'elder son', 'eldest living son')


def to_y(s, default_era=None):
    """'FE 2,938', 'beyond ... (FE 53)' or a bare number of default_era -> a year of the continuous count."""
    if s is None or s == '':
        return None
    if isinstance(s, int):
        era, n = default_era, s
    else:
        m = re.search(r'\b(VE|GE|FE|LE|AE|SE|DE)\s+(-?[\d,]+)', s)
        if not m:
            return None
        era, n = m.group(1), int(m.group(2).replace(',', ''))
    first = ABBR[era][1]
    y = first + n - 1
    if first < 0 <= y:
        y += 1                                                         # no year 0
    return y


def span(b, d):
    a = d - b
    if b < 0 < d:
        a -= 1
    return a


def load():
    return json.load(open(os.path.join(ERAS, 'RULERS.json'), encoding='utf-8'))


def age_of_year(y):
    """The age whose era holds the year y (by the year alone)."""
    k = KEYS[0]
    for a in RK.AGES:
        if y >= a[1]:
            k = a[0]
    return k


def check_record(doc):
    """-> list of problems in RULERS.json itself: years, anchors and ages."""
    ev = {e['id']: e for e in json.load(open(os.path.join(LEG, 'annals_dated.json'), encoding='utf-8'))}
    bad = []
    ids = [r['id'] for r in doc['rulers']]
    if len(ids) != len(set(ids)):
        bad.append('ruler ids not unique')
    byid = {r['id']: r for r in doc['rulers']}
    for r in doc['rulers']:
        for k in ('born', 'accession', 'in_office', 'reign_end', 'died'):
            if to_y(r[k]) != r[k + '_y']:
                bad.append('%s: %s "%s" is not year %s' % (r['id'], k, r[k], r[k + '_y']))
        for k, ek in (('accession', 'accession_event'), ('reign_end', 'reign_end_event'), ('died', 'died_event'),
                      ('in_office', 'in_office_event')):
            if r[ek] and (r[ek] not in ev or ev[r[ek]]['y'] != r[k + '_y']):
                bad.append('%s: %s %s is not the year of %s' % (r['id'], k, r[k], r[ek]))
        b = r['born_y']
        if b is None:
            bad.append('%s: no birth' % r['id'])
            continue
        for k, a in (('accession', 'age_at_accession'), ('reign_end', 'age_at_reign_end'), ('died', 'age_at_death')):
            want = span(b, r[k + '_y']) if r[k + '_y'] is not None else None
            if r[a] != want:
                bad.append('%s: %s %s, not %s' % (r['id'], a, r[a], want))
        seq = [r[k + '_y'] for k in ('born', 'accession', 'in_office', 'reign_end', 'died') if r[k + '_y'] is not None]
        if seq != sorted(seq):
            bad.append('%s: birth, accession, reign and death out of order' % r['id'])
        if r['parent'] and r['parent'] not in byid:
            bad.append('%s: parent %s is not in the list' % (r['id'], r['parent']))
    return bad


def last_known(r):
    """(year, what): the death, or failing it the last year the ruler is known to be alive."""
    for k in ('died', 'reign_end', 'in_office', 'accession'):
        if r[k + '_y'] is not None:
            return r[k + '_y'], k
    return r['born_y'], 'born'


def check_rule(doc):
    """-> (ordinary problems, fading problems) over the rulers and the curve."""
    rule = doc['rule']
    lim, start = rule['max_ordinary_age'], rule['ordinary_from_y']
    ordinary, fading = [], []
    byid = {r['id']: r for r in doc['rulers']}
    for r in doc['rulers']:
        y, what = last_known(r)
        a = span(r['born_y'], y)
        if (r['born_y'] >= start or not r['kin']) and a > lim:
            ordinary.append('%s (%s, %s at %s %s)' % (r['name'], r['born'], a, 'death' if what == 'died' else what,
                                                    r[what]))
    # the fading: the longest natural life of each generation, rulers and the curve together
    best = {}
    for c in doc['curve']:
        if c['age_at_death'] and not c['note'].startswith('slain'):
            best[c['gen']] = max(best.get(c['gen'], 0), c['age_at_death'])
    for r in doc['rulers']:
        if r['gen'] is not None and r['death'] == 'natural' and r['age_at_death'] is not None:
            best[r['gen']] = max(best.get(r['gen'], 0), r['age_at_death'])
    king = next(c['age_at_death'] for c in doc['curve'] if c['gen'] == 0)
    prev = king
    for g in sorted(k for k in best if k > 0):
        if best[g] > prev:
            fading.append('generation %d lives to %d, longer than generation %d (%d)' % (g, best[g], g - 1, prev))
        prev = best[g]
    for r in doc['rulers']:
        p = byid.get(r['parent']) if r['parent'] and r['relation'] in DIRECT else None
        if not p:
            continue
        at = span(p['born_y'], r['born_y'])
        if p['died_y'] is not None and r['born_y'] > p['died_y'] + 1:
            fading.append('%s born after %s died' % (r['name'], p['name']))
        if at < 14:
            fading.append('%s born when %s was %d' % (r['name'], p['name'], at))
        if at > 70 and (p['age_at_death'] or 0) <= lim and not p['kin']:
            fading.append('%s born when %s was %d' % (r['name'], p['name'], at))
        if (r['kin'] and p['kin'] and r['death'] == 'natural' and p['death'] == 'natural' and
                p['age_at_death'] > lim and r['age_at_death'] > p['age_at_death']):
            fading.append('%s (%d) outlives the span of %s (%d)' % (r['name'], r['age_at_death'], p['name'], p['age_at_death']))
    return ordinary, fading


def check_houses(doc):
    """Rulers whose dates come from houses.json keep its years; every house member keeps the ordinary rule."""
    sys.path.insert(0, LEG)
    import build_book  # noqa: E402
    rec = build_book.Record()
    mem = {m['id']: m for h in rec.houses for m in h.get('members', [])}
    bad = []
    for r in doc['rulers']:
        m = re.search(r'houses\.json (\w+)', r.get('source') or '')
        if not m:
            continue
        h = mem.get(m.group(1))
        if not h:
            bad.append('%s: no member %s in houses.json' % (r['id'], m.group(1)))
            continue
        if h.get('born_y') != r['born_y'] or (r['died_y'] is not None and h.get('died_y') != r['died_y']):
            bad.append('%s: houses.json %s gives %s - %s' % (r['id'], m.group(1), h.get('born'), h.get('died')))
    lim, start = doc['rule']['max_ordinary_age'], doc['rule']['ordinary_from_y']
    for h in mem.values():
        if h.get('born_y') is not None and h.get('died_y') is not None and h['born_y'] >= start \
                and span(h['born_y'], h['died_y']) > lim:
            bad.append('houses.json %s %s lives %d years' % (h['id'], h['name'], span(h['born_y'], h['died_y'])))
    return bad


def plan_people(k):
    p = os.path.join(ERAS, 'age_%s' % k, 'PLAN_people.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


def check_plan(doc, k):
    """-> problems in eras/age_<k>/PLAN_people.json: the ordinary rule, and planned rulers against RULERS.json."""
    rule = doc['rule']
    lim, start = rule['max_ordinary_age'], rule['ordinary_from_y']
    alias = {}
    for r in doc['rulers']:
        for a in r['aliases']:
            alias.setdefault(a, []).append(r)
    end_of_age = RK.ERA[k][2]
    bad = []
    for p in plan_people(k):
        b, d = to_y(p.get('born'), PLAN_INT_ERA.get(k)), to_y(p.get('died'), PLAN_INT_ERA.get(k))
        exempt = any(p['name'].startswith(x) for x in rule['exempt'])
        if b is not None and d is not None and b >= start and span(b, d) > lim and not exempt:
            bad.append('%s lives %d years (%s - %s)' % (p['name'], span(b, d), p['born'], p['died']))
        rs = [r for r in alias.get(p['name'], []) if r['born_y'] <= RK.ERA[k][2] and
              (last_known(r)[0] >= RK.ERA[k][1] or r['age'] == k)]
        if len(rs) != 1:
            continue
        r = rs[0]
        if b != r['born_y']:
            bad.append('%s: planned birth %s, RULERS.json %s' % (p['name'], p.get('born'), r['born']))
        if r['died_y'] is not None and (d != r['died_y'] if (d is not None or r['died_y'] <= end_of_age) else False):
            bad.append('%s: planned death %s, RULERS.json %s' % (p['name'], p.get('died'), r['died']))
    return bad


def check_master():
    """-> [(what, problems)] for check_rodais.py."""
    doc = load()
    ordinary, fading = check_rule(doc)
    plans = []
    for k in KEYS:
        plans += ['Age %s: %s' % (k, x) for x in check_plan(doc, k)]
    return [('record', check_record(doc)), ('ordinary', ordinary), ('fading', fading), ('houses', check_houses(doc)),
            ('plans', plans)], doc


def check_age(k):
    """-> [(what, problems)] for eras/check_era.py: the rulers who lived in age k, and its plan."""
    doc = load()
    first, last = RK.ERA[k][1], RK.ERA[k][2]
    mine = dict(doc, rulers=[r for r in doc['rulers'] if r['born_y'] <= last and last_known(r)[0] >= first])
    ordinary, _ = check_rule(mine)
    _, fading = check_rule(doc)
    return [('ordinary', ordinary), ('fading', fading), ('plan', check_plan(doc, k))], mine


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else 'master'
    res, doc = check_master() if arg == 'master' else check_age(arg)
    n = 0
    for what, probs in res:
        print('%-9s %s' % (what, 'ok' if not probs else '%d problem(s)' % len(probs)))
        for x in probs:
            print('          ' + x)
        n += len(probs)
    print('%d ruler(s) checked' % len(doc['rulers']))
    sys.exit(1 if n else 0)


if __name__ == '__main__':
    main()
