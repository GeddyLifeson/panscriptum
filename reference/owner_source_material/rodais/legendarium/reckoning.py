"""
reckoning.py -- give every event in the annals of Rodos an exact day, month and year.

Every date is assembled from album release dates (albums.json): the DAY from one album, the
MONTH from another, and the YEAR from three more, combined by the reckoning of its age:

    year = first year of the age + (100 x ((yy(A) + yy(C)) mod 100) + yy(B)) mod (length of the age)

where yy is the last two digits of an album's year. (Two albums, A and C, make the hundreds between them: no album
in the pool has a year ending 26-44, and with A alone the reckoning could not reach 1,900 years of the Ancient Age.) Which albums made which date is not
recorded anywhere, by the owner's choice; the reckoning only needs to know that a date CAN be
made from the pool, and it always picks one that can.

Order is the writers' and the chronicle's: events are dated in the order the annals list them,
never going backwards; a canon year from the chronicle is kept exactly; a full canon date
(11 April 2020) is kept whole; an event's "between": [from, to] window is honoured. Within those
limits each event lands as close as the pool allows to an even spread across its stretch of
years, so the annals read as a steady record rather than a crowd at the anchors.

    python reckoning.py        -> annals_dated.json (all ages, every event with y/m/d and a display date)
"""
import calendar
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

AGES = [  # (key, first year, last year); negative = BDE, and there is no year 0
    ('I', -12999, -3001),
    ('II', -3000, -40),
    ('III', -39, 1779),
    ('IV', 1780, 1929),
    ('V', 1930, 2026),
]
MONTHS = ['am Faoilleach', 'an Gearran', 'am Màrt', 'an Giblean', 'an Cèitean', 'an t-Ògmhios', 'an t-Iuchar',
          'an Lùnastal', 'an t-Sultain', 'an Dàmhair', 'an t-Samhain', 'an Dùbhlachd']
ENGLISH_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
                  'October', 'November', 'December']


# ---------------------------------------------------------------- the pool
def load_pool():
    albums = json.load(open(os.path.join(HERE, 'albums.json'), encoding='utf-8'))
    years, months, days = set(), set(), set()
    for a in albums:
        d = a.get('date') or ''
        m = re.match(r'^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$', d)
        if not m:
            continue
        years.add(int(m.group(1)))
        if m.group(2):
            months.add(int(m.group(2)))
        if m.group(3):
            days.add(int(m.group(3)))
    return sorted(years), sorted(months), sorted(days)


def reachable_years(album_years, first, last):
    """Every year of an age the reckoning can make from three album years."""
    span = last - first + 1 - (1 if first < 0 < last else 0)          # no year 0
    yys = sorted({y % 100 for y in album_years})
    hundreds = sorted({(a + c) % 100 for a in yys for c in yys})
    out = set()
    for a in hundreds:
        for b in yys:
            k = (100 * a + b) % span
            year = first + k
            if first < 0 and year >= 0:
                year += 1                                              # skip year 0
            out.add(year)
    return sorted(out)


# ---------------------------------------------------------------- canon dates
FULL = re.compile(r'(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})')


def canon_anchor(ev):
    """(year, month, day) fixed by the chronicle, or (year, None, None), or None."""
    cd = ev.get('canon_date') or ''
    m = FULL.search(cd)
    if m:
        return int(m.group(3)), ENGLISH_MONTHS.index(m.group(1)) + 1, int(m.group(2))
    m = re.search(r'(\d{4})', cd)
    if m:
        return int(m.group(1)), None, None
    return None


def display(y, m, d):
    era = 'DE' if y > 0 else 'BDE'
    return '%d %s %s %s' % (d, MONTHS[m - 1], format(abs(y), ',') if abs(y) >= 10000 else abs(y), era)


def ordinal(y, m, d):
    return (y, m, d)


# ---------------------------------------------------------------- date one age
def nz(y):
    return y if y != 0 else 1


def date_age(events, first, last, years_ok, relaxed, extra=None):
    """Years, in list order: canon years fixed, windows honoured, never backwards, evenly spread."""
    n = len(events)
    fixed = {}
    approx = {}
    for i, e in enumerate(events):
        a = canon_anchor(e) if e.get('canon') else None
        if a:
            fixed[i] = a
            if (e.get('canon_date') or '').strip().startswith('c.'):
                approx[i] = a[0]
    # an approximate canon year ("c. 1915") listed after a later one gives way, by as little as possible
    last_y = None
    for i in range(n):
        if i in fixed:
            y = fixed[i][0]
            if last_y is not None and y < last_y:
                if i in approx and last_y - y <= 2:
                    fixed[i] = (last_y,) + tuple(fixed[i][1:])
                    relaxed.append('%s: c. %d held as %d to keep the chronicle order' % (events[i].get('id'), y, last_y))
                    y = last_y
            last_y = y
    use_window = [True] * n
    while True:
        wlo, whi = [], []
        for i, e in enumerate(events):
            lo, hi = first, last
            if i in fixed:
                lo = hi = fixed[i][0]
            elif e.get('between') and use_window[i]:
                lo, hi = max(lo, e['between'][0]), min(hi, e['between'][1])
            wlo.append(lo); whi.append(hi)
        lb, ub = wlo[:], whi[:]
        for i in range(1, n):
            lb[i] = max(lb[i], lb[i - 1])
        for i in range(n - 2, -1, -1):
            ub[i] = min(ub[i], ub[i + 1])
        bad = [i for i in range(n) if lb[i] > ub[i]]
        if not bad:
            break
        # a writer's window that cannot hold in list order: drop the tightest offending window and retry
        cands = [i for i in range(n) if use_window[i] and events[i].get('between') and i not in fixed
                 and (wlo[i] > ub[i] or whi[i] < lb[i] or i in bad)]
        if not cands:
            sys.exit('canon order cannot hold near %s' % events[bad[0]].get('id'))
        k = min(cands, key=lambda i: whi[i] - wlo[i])
        use_window[k] = False
        relaxed.append(events[k].get('id'))
    # anchors: the chronicle's fixed years, and the middle of every writer's window that still holds,
    # kept in list order; events between two anchors are spread evenly between them
    anchors = [(-1, first)]
    for i in range(n):
        if i in fixed:
            t = fixed[i][0]
        elif extra and i in extra:
            t = extra[i]
        elif events[i].get('between') and use_window[i]:
            t = min(max((wlo[i] + whi[i]) / 2.0, lb[i]), ub[i])
        else:
            continue
        anchors.append((i, max(t, anchors[-1][1])))
    anchors.append((n, max(last, anchors[-1][1])))
    # "within": [ID, N] or [ID, N, M] -- this event falls no more than N (and at least M) years after event ID
    # (one person's life, one reign, "the following year"): once ID has its year, everything from it up to
    # this event is capped at that year + N, and this event is held at least M years after it
    idx = {e.get('id'): i for i, e in enumerate(events)}
    within = {}
    for i, e in enumerate(events):
        w = e.get('within')
        if w and w[0] in idx and idx[w[0]] < i:
            within.setdefault(idx[w[0]], []).append((i, int(w[1]), int(w[2]) if len(w) > 2 else 0))
    cap = [None] * n
    floor_ = [None] * n

    def set_caps(i):
        for j, span, least in within.get(i, []):
            c = years[i] + span
            if c < lb[j]:
                relaxed.append('%s: within %d of %s cannot hold' % (events[j].get('id'), span, events[i].get('id')))
                continue
            for k in range(i + 1, j + 1):
                cap[k] = c if cap[k] is None else min(cap[k], c)
            if least:
                f = years[i] + least
                if f <= ub[j]:
                    floor_[j] = f if floor_[j] is None else max(floor_[j], f)

    years = [None] * n
    prev = first
    a = 0
    for i in range(n):
        while anchors[a + 1][0] < i:
            a += 1
        if anchors[a + 1][0] == i and i in fixed:
            years[i] = fixed[i][0]
            prev = years[i]
            set_caps(i)
            continue
        (i0, y0), (i1, y1) = anchors[a], anchors[a + 1]
        if i1 == i:                                    # a window's own event: aim at its middle
            t = y1
        else:
            t = y0 + (y1 - y0) * (i - i0) / float(i1 - i0)
        lo, hi = max(lb[i], prev), ub[i]
        if floor_[i] is not None:
            lo = max(lo, min(floor_[i], hi))
        if cap[i] is not None and cap[i] >= lo:
            hi = min(hi, cap[i])
        t = min(max(t, lo), hi)
        cands = [y for y in years_ok if lo <= y <= hi]
        if cands:
            y = min(cands, key=lambda c: (abs(c - t), c))
        else:
            y = nz(round(t))
        years[i] = y
        prev = y
        set_caps(i)
    if extra is None and within:
        # second pass: the ends of every "within" stretch become anchors at the years the first pass found,
        # so the events inside a stretch spread across it (not piled on its cap) and those after it
        # carry on evenly from where it ended
        spans = [(i, j) for i, lst in within.items() for j, _, _ in lst]
        inner = lambda k: any(a < k < b for a, b in spans)          # noqa: E731 -- nested stretches spread with their outer one
        ends = {k: years[k] for a, b in spans for k in (a, b) if not inner(k)}
        return date_age(events, first, last, years_ok, relaxed, ends)
    return years


def slot_hash(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xffffffff
    return h


def month_days(years, events, months_ok, days_ok, floor=None):
    """Day and month from the pool: shared years keep list order across the year; every event's own
    slot is chosen by a hash of its id, so dates vary instead of piling on one day."""
    n = len(events)
    out = [None] * n
    groups = {}
    for i, y in enumerate(years):
        groups.setdefault(y, []).append(i)
    for y, idxs in groups.items():
        yl = y if y > 0 else 2001
        slots = [(m, d) for m in months_ok for d in days_ok if d <= calendar.monthrange(yl, m)[1]]
        if floor and y == floor[0]:                    # the age before ended this year: come after it
            slots = [s_ for s_ in slots if s_ > floor[1:]] or slots[-1:]
        pinned = {i: (canon_anchor(events[i])[1], canon_anchor(events[i])[2]) for i in idxs
                  if events[i].get('canon') and canon_anchor(events[i]) and canon_anchor(events[i])[1]}
        k = len(idxs)
        picks = sorted(slots[slot_hash(events[i].get('id', str(i))) % len(slots)] for i in idxs)
        # keep picks distinct and ordered
        for a in range(1, k):
            if picks[a] <= picks[a - 1]:
                later = [s for s in slots if s > picks[a - 1]]
                picks[a] = later[0] if later else picks[a - 1]
        for pos, i in enumerate(idxs):
            out[i] = picks[pos]
        # canon month/day stay put; neighbours around them are pushed to stay in order
        for i, md in pinned.items():
            out[i] = md
        for a in range(1, k):
            i0, i1 = idxs[a - 1], idxs[a]
            if out[i1] < out[i0] and i1 not in pinned:
                later = [s for s in slots if s >= out[i0]]
                out[i1] = later[0] if later else out[i0]
        for a in range(k - 2, -1, -1):
            i0, i1 = idxs[a], idxs[a + 1]
            if out[i0] > out[i1] and i0 not in pinned:
                earlier = [s for s in slots if s <= out[i1]]
                out[i0] = earlier[-1] if earlier else out[i1]
    # "first_of_year": the earliest day the pool gives in its year (an age that closes early in a year)
    for i in range(n):
        if events[i].get('first_of_year'):
            yl = years[i] if years[i] > 0 else 2001
            out[i] = min((m, d) for m in months_ok for d in days_ok if d <= calendar.monthrange(yl, m)[1])
    # "same_day": the writers say this happened on the day of the event before it
    for i in range(1, n):
        if events[i].get('same_day') and years[i] == years[i - 1]:
            out[i] = out[i - 1]
    for i in range(1, n):
        if years[i] == years[i - 1] and out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def main():
    album_years, months_ok, days_ok = load_pool()
    if len(months_ok) < 12 or len(days_ok) < 31:
        print('warning: the pool makes only months %s and days %s' % (months_ok, days_ok))
    all_dated = []
    floor = None
    for key, first, last in AGES:
        path = os.path.join(HERE, 'annals', 'age_%s.json' % key)
        if not os.path.exists(path):
            print('missing', path)
            continue
        events = json.load(open(path, encoding='utf-8'))
        years_ok = reachable_years(album_years, first, last)
        relaxed = []
        years = date_age(events, first, last, years_ok, relaxed)
        mds = month_days(years, events, months_ok, days_ok, floor)
        # "eve": the night before the next event (the day before it, even across the turn of a year);
        # "eve": N puts it N days before. Worked from the end, so a run of eves chains back from its last event
        for i in range(len(events) - 2, -1, -1):
            if events[i].get('eve'):
                import datetime
                ny, (nm, nd) = years[i + 1], mds[i + 1]
                back = 1 if events[i]['eve'] is True else int(events[i]['eve'])
                prev = datetime.date(ny if ny > 0 else 2001, nm, nd) - datetime.timedelta(days=back)
                py = ny if prev.year == (ny if ny > 0 else 2001) else (ny - 1 if ny - 1 != 0 else -1)
                years[i], mds[i] = py, (prev.month, prev.day)
        dated = [dict(e, y=y, m=md[0], d=md[1], date=display(y, md[0], md[1])) for e, y, md in zip(events, years, mds)]
        relaxed = list(dict.fromkeys(relaxed))
        if relaxed:
            print('  Age %s: %d writer windows dropped or held (they contradicted the list order): %s' % (key, len(relaxed), ', '.join(relaxed[:12])))
        for e in dated:
            e['age'] = key
        # never backwards
        for a, b in zip(dated, dated[1:]):
            assert (a['y'], a['m'], a['d']) <= (b['y'], b['m'], b['d']), (a['id'], b['id'])
        all_dated.extend(dated)
        floor = (dated[-1]['y'], dated[-1]['m'], dated[-1]['d'])
        print('Age %-3s %4d events  %s .. %s   (%d years reachable)' % (key, len(dated), dated[0]['date'], dated[-1]['date'], len(years_ok)))
    json.dump(all_dated, open(os.path.join(HERE, 'annals_dated.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('annals_dated.json:', len(all_dated), 'events')


if __name__ == '__main__':
    main()
