"""
build_era.py -- build one age's own legendarium: its dated annals, LEGENDARIUM.md and its book-length PDF.

    python build_era.py IV              # date the annals, write LEGENDARIUM.md and the PDF of the Age of Sundering
    python build_era.py all             # every age that has eras/age_<K>/annals/
    python build_era.py IV --no-pdf     # dating and LEGENDARIUM.md only (seconds instead of minutes)
    python build_era.py IV --seed       # (re)write annals/age_IV_master.json from legendarium/annals/age_IV.json
    python build_era.py all --seed      # the same for all seven ages

Sources, in eras/age_<K>/ (see WRITERS_GUIDE.md for the rules writers follow):

    annals/age_<K>_master.json   the master events of the age, copied from legendarium/annals/age_<K>.json (a list)
    annals/*.json                the writers' files: {"writer": 1, "span": [FROM, TO], "events": [...]}
    book/*.md                    the era's Books, in file-name order
    gazetteer/*.json             {burg id: entry}, the master gazetteer's entry shape, told as the town stood in the age
    appendices/*.md              the era's appendices, in file-name order
    places.json                  (optional) places the age knew that the master map does not: {"burg:4001": {...}}
    front.json                   (optional) {"epigraph": {"ro": ..., "en": ..., "src": ...}}

Outputs, in eras/age_<K>/:

    annals_dated.json            every event of the age, master and era, with y/m/d, era year and display date
    atlas.json                   for the Atlas timeline: the era header, every event with its category, its links both
                                 ways (each with the target's era, date and title), threads, people and told_in (the
                                 book section that tells it), the threads and people it uses, and the gaps over 100 years
    ../master_links.json         the same for the master (overview) events, links from every era included
    LEGENDARIUM.md               the whole era record as text, in the master LEGENDARIUM.md's shape
    The_Diathir_Legendarium_<Age>.pdf   typeset by legendarium/build_pdf.py's own template and code

The dating rule that matters most: every master event keeps EXACTLY the date legendarium/annals_dated.json gives it.
Master events are never dated here; they are copied, and they cut the age into gaps. Each era event is dated only
inside the gap it stands in, between the two master events around it (see date_gap), and every date it gets is
clamped into that gap. An era event therefore cannot move a master event, and cannot pass one. build() asserts
both after every run, and check_era.py checks them again from the written files.
"""
import argparse
import calendar
import glob
import json
import os
import re
import sys

ERAS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ERAS)
LEG = os.path.join(ROOT, 'legendarium')
sys.path.insert(0, LEG)
import reckoning  # noqa: E402
import build_book  # noqa: E402
import build_pdf  # noqa: E402
import event_links  # noqa: E402

KEYS = reckoning.AGE_KEYS
ORDINALS = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh',
            'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth',
            'Twentieth']
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
# fields that only steer the dating; they are not printed and not kept in annals_dated.json
CONTROL = ('between', 'era_between', 'on', 'within', 'same_day', 'eve', 'first_of_year', 'keep', 'seed')
# what an era event may not carry: the chronicle's own marks belong to the master events alone
FORBIDDEN = ('canon', 'canon_date', 'keep')
ERA_ID = re.compile(r'^E(I|II|III|IV|V|VI|VII)-(\d{4})([a-z]?)$')


class EraError(Exception):
    pass


def age_dir(k):
    return os.path.join(ERAS, 'age_%s' % k)


def english_name(k):
    """'the Age of Sundering' -> 'The Age of Sundering'."""
    en = build_book.AGE_NAMES[k][1]
    return en[0].upper() + en[1:]


def pdf_name(k):
    """The_Diathir_Legendarium_Age_of_Sundering.pdf"""
    en = re.sub(r'^the ', '', build_book.AGE_NAMES[k][1])
    return 'The_Diathir_Legendarium_%s.pdf' % re.sub(r'[^A-Za-z]+', '_', en).strip('_')


def full_title(k):
    return 'The Legendarium of Dia-thìr — %s (%s)' % (english_name(k), build_book.AGE_NAMES[k][0])


# ---------------------------------------------------------------- days
def month_len(y, m):
    return calendar.monthrange(y if y > 0 else 2001, m)[1]     # as reckoning.py: years before 1 have no leap day


def prev_day(y, m, d):
    if d > 1:
        return y, m, d - 1
    if m > 1:
        return y, m - 1, month_len(y, m - 1)
    y = y - 1 if y - 1 != 0 else -1
    return y, 12, 31


def days_before(date, n):
    for _ in range(n):
        date = prev_day(*date)
    return date


def era_to_y(ey, k):
    """Year ey of age k's era -> the continuous count (no year 0)."""
    first = reckoning.ERA[k][1]
    y = first + ey - 1
    if first < 0 <= y:
        y += 1
    return y


# ---------------------------------------------------------------- the master record
def master_events(k):
    """The master events of age k with their master dates, in order (legendarium/annals_dated.json)."""
    return [e for e in json.load(open(os.path.join(LEG, 'annals_dated.json'), encoding='utf-8')) if e['age'] == k]


def master_source(k):
    return json.load(open(os.path.join(LEG, 'annals', 'age_%s.json' % k), encoding='utf-8'))


def write_seed(k):
    d = os.path.join(age_dir(k), 'annals')
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'age_%s_master.json' % k)
    json.dump(master_source(k), open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(p, 'a', encoding='utf-8').write('\n')
    print('wrote', os.path.relpath(p, ROOT), '(%d master events)' % len(master_source(k)))


def bounds(k, masters):
    """The last day an era event of age k may fall on after the age's last master event: the day before the next
    age opens; in the last age, the last master event itself (the present)."""
    i = KEYS.index(k)
    if i + 1 < len(KEYS):
        op = reckoning.openings()[KEYS[i + 1]]
        return prev_day(*op)
    last = masters[-1]
    return last['y'], last['m'], last['d']


# ---------------------------------------------------------------- reading the writers' files
def load_sources(k):
    """-> (seed events, [writer file dicts]) with every event tagged with its file."""
    d = os.path.join(age_dir(k), 'annals')
    files = sorted(glob.glob(os.path.join(d, '*.json')))
    seed_path = os.path.join(d, 'age_%s_master.json' % k)
    if seed_path not in files:
        raise EraError('missing %s (run: python build_era.py %s --seed)' % (os.path.relpath(seed_path, ROOT), k))
    seed = json.load(open(seed_path, encoding='utf-8'))
    writers = []
    for f in files:
        if f == seed_path:
            continue
        data = json.load(open(f, encoding='utf-8'))
        name = os.path.basename(f)
        if not isinstance(data, dict) or not isinstance(data.get('events'), list) or not data.get('span'):
            raise EraError('%s: a writer file is {"writer": N, "span": [FROM, TO], "events": [...]}' % name)
        data['file'] = name
        writers.append(data)
    return seed, writers


def merge(k, masters, writers):
    """Place every era event in its gap. Gap g lies between master g and master g+1 (the last gap after the last
    master). Each writer file owns the gaps of its span; no two files may own the same gap.
    -> gaps: list (len(masters)) of lists of era events, in order; problems (fatal)."""
    idx = {e['id']: i for i, e in enumerate(masters)}
    n = len(masters)
    gaps = [[] for _ in range(n)]
    owner = {}
    problems = []
    for w in writers:
        name = w['file']
        span = w['span']
        if not (isinstance(span, list) and len(span) == 2):
            problems.append('%s: span must be [FROM, TO]' % name)
            continue
        a = idx.get(span[0])
        b = n if span[1] == 'end' else idx.get(span[1])
        if a is None or b is None or b <= a:
            problems.append('%s: span %s must be two master ids of Age %s in order (TO may be "end")' % (name, span, k))
            continue
        for g in range(a, b):
            if g in owner:
                problems.append('%s: span %s overlaps %s (the gap after %s)' % (name, span, owner[g], masters[g]['id']))
                break
            owner[g] = name
        g = a
        for e in w['events']:
            if isinstance(e, dict) and set(e) == {'after'}:
                j = idx.get(e['after'])
                if j is None or j < g or j >= b:
                    problems.append('%s: {"after": "%s"} must be a master id inside the span, in master order' % (name, e['after']))
                    continue
                g = j
                continue
            e = dict(e)
            e['_file'] = name
            e['_writer'] = w.get('writer')
            gaps[g].append(e)
    return gaps, problems


# ---------------------------------------------------------------- dating
def pool():
    album_years, months_ok, days_ok = reckoning.load_pool()
    return album_years, months_ok, days_ok


def stretch_years(k, album_years):
    for a, b, keys in reckoning.STRETCHES:
        if k in keys:
            return reckoning.reachable_years(album_years, a, b)
    raise EraError('no stretch for age %s' % k)


def window(e, k, lo, hi, dated, problems):
    """The years (continuous count) event e may take inside [lo, hi]."""
    w_lo, w_hi = lo, hi
    if e.get('era_between'):
        a, b = e['era_between']
        w_lo, w_hi = max(w_lo, era_to_y(a, k)), min(w_hi, era_to_y(b, k))
    if e.get('between'):
        w_lo, w_hi = max(w_lo, e['between'][0]), min(w_hi, e['between'][1])
    wi = e.get('within')
    if wi and wi[0] in dated:
        y0 = dated[wi[0]]['y']
        w_lo = max(w_lo, y0 + (int(wi[2]) if len(wi) > 2 else 0))
        w_hi = min(w_hi, y0 + int(wi[1]))
    if w_lo > w_hi:
        problems.append('%s: its window (%s) cannot hold between its master neighbours (years %s..%s); spread evenly instead'
                        % (e['id'], e.get('era_between') or e.get('between') or e.get('within'), lo, hi))
        return None
    return [w_lo, w_hi]


def date_gap(k, L, R, evs, years_ok, months_ok, days_ok, dated, warn):
    """Date the era events of one gap, between the fixed days L and R. An event with an exact day ("on") must fall
    inside the gap and after any earlier exact day, or the build stops; it then cuts the gap in two, and the events
    on each side are dated inside their own part (_date_run). -> [(y, m, d)] for evs."""
    out, lo, start = [], L, 0
    dated = dict(dated)
    for i, e in enumerate(evs):
        if not e.get('on'):
            continue
        ey, m, d = e['on']
        y = era_to_y(int(ey), k)
        if not (1 <= m <= 12 and 1 <= d <= month_len(y, m)) or not (lo <= (y, m, d) <= R):
            raise EraError('%s (%s): "on" %s is not a day between its neighbours (%s .. %s)'
                           % (e['id'], e['_file'], e['on'], reckoning.display(*lo, age=k), reckoning.display(*R, age=k)))
        part = _date_run(k, lo, (y, m, d), evs[start:i], years_ok, months_ok, days_ok, dated, warn)
        for ev, ymd in zip(evs[start:i], part):
            dated[ev['id']] = {'y': ymd[0]}
        dated[e['id']] = {'y': y}
        out += part + [(y, m, d)]
        lo, start = (y, m, d), i + 1
    return out + _date_run(k, lo, R, evs[start:], years_ok, months_ok, days_ok, dated, warn)


def _date_run(k, L, R, evs, years_ok, months_ok, days_ok, dated, warn):
    """Date a run of era events with no exact day, in their order, between the fixed days L and R (tuples y, m, d), inclusive.
    Years come from reckoning.date_age (the master's own interpolation, with windows and 'within'), run on the
    list [L, events..., R] with L and R pinned; months and days from the album pool as reckoning.month_days does.
    Every date is clamped into [L, R]: nothing here can reach outside the gap. -> [(y, m, d)] for evs."""
    if not evs:
        return []
    items = [{'id': '__L', 'keep': L}]
    on = {}
    for i, e in enumerate(evs):
        x = {'id': e['id']}
        if e.get('seed'):
            x['seed'] = e['seed']
        if e.get('on'):
            ey, m, d = e['on']
            y = era_to_y(int(ey), k)
            if not (1 <= m <= 12 and 1 <= d <= month_len(y, m)) or not (L <= (y, m, d) <= R):
                raise EraError('%s (%s): "on" %s is not a day between its master neighbours (%s .. %s)'
                               % (e['id'], e['_file'], e['on'], reckoning.display(*L, age=k), reckoning.display(*R, age=k)))
            if on and max(on.values()) > (y, m, d):
                raise EraError('%s (%s): "on" %s comes before an earlier event\'s "on" in the same gap' % (e['id'], e['_file'], e['on']))
            on[i] = (y, m, d)
            x['keep'] = (y, m, d)
        else:
            w = window(e, k, L[0], R[0], dated, warn)
            if w:
                x['between'] = w
            wi = e.get('within')
            if wi and wi[0] not in dated and wi[0] in {v['id'] for v in evs[:i]}:
                x['within'] = wi                      # a neighbour in the same gap: date_age holds it itself
        items.append(x)
    items.append({'id': '__R', 'keep': R})
    relaxed = []
    years = reckoning.date_age(items, L[0], R[0], years_ok, relaxed)
    assert years[0] == L[0] and years[-1] == R[0], 'the gap bounds moved'
    for r in relaxed:
        warn.append('%s: window dropped, it contradicted the list order' % r)
    years = [min(max(y, L[0]), R[0]) for y in years[1:-1]]

    def slots(y, lo=L, hi=R):
        return [(m, d) for m in months_ok for d in days_ok if d <= month_len(y, m) and lo <= (y, m, d) <= hi]

    out = []
    groups = {}
    for i, y in enumerate(years):
        groups.setdefault(y, []).append(i)
    md = [None] * len(evs)
    for y, ids in groups.items():
        inner = [s for s in slots(y) if L < (y,) + s < R] or slots(y)
        if not inner:                                   # no pool day inside the gap in this year: take a bound's day
            inner = [L[1:]] if y == L[0] else [R[1:]]
        picks = sorted(inner[reckoning.slot_hash(evs[i].get('seed') or evs[i]['id']) % len(inner)] for i in ids)
        for a in range(1, len(picks)):
            if picks[a] <= picks[a - 1]:
                later = [s for s in inner if s > picks[a - 1]]
                picks[a] = later[0] if later else picks[a - 1]
        for pos, i in enumerate(ids):
            md[i] = picks[pos]
    dates = [(years[i],) + md[i] for i in range(len(evs))]
    for i, d in on.items():
        dates[i] = d
    for i, e in enumerate(evs):
        if e.get('first_of_year') and i not in on:
            s = slots(dates[i][0])
            if s:
                dates[i] = (dates[i][0],) + min(s)
    for i, e in enumerate(evs):                         # the day of the event before it (L for the first)
        if e.get('same_day') and i not in on:
            dates[i] = dates[i - 1] if i else L
    for i in range(len(evs) - 1, -1, -1):                # the eve of the event after it (R for the last)
        if evs[i].get('eve') and i not in on:
            nxt = dates[i + 1] if i + 1 < len(evs) else R
            dates[i] = days_before(nxt, 1 if evs[i]['eve'] is True else int(evs[i]['eve']))
    # never backwards, never outside the gap; an exact "on" day stays as written
    prev = L
    for i in range(len(evs)):
        d = min(max(dates[i], prev), R)
        if i in on and d != on[i]:
            raise EraError('%s: "on" %s cannot hold in list order' % (evs[i]['id'], evs[i]['on']))
        dates[i] = d
        prev = d
    return dates


def date_era(k):
    """-> (dated events of the age in order, warnings). Raises EraError on anything the build cannot honour."""
    masters = master_events(k)
    if not masters:
        raise EraError('Age %s has no master events' % k)
    seed, writers = load_sources(k)
    if [e.get('id') for e in seed] != [e['id'] for e in masters]:
        raise EraError('annals/age_%s_master.json does not hold exactly the master events of Age %s in order '
                       '(re-copy it: python build_era.py %s --seed)' % (k, k, k))
    gaps, problems = merge(k, masters, writers)
    if problems:
        raise EraError('\n'.join(problems))
    ids = {}
    all_master = {e['id'] for e in json.load(open(os.path.join(LEG, 'annals_dated.json'), encoding='utf-8'))}
    for g in gaps:
        for e in g:
            i = e.get('id')
            m = ERA_ID.match(i or '')
            if not m or m.group(1) != k:
                problems.append('%s (%s): an era event of Age %s has an id E%s-nnnn' % (i, e['_file'], k, k))
            if i in ids or i in all_master:
                problems.append('%s (%s): id already used (%s)' % (i, e['_file'], ids.get(i, 'master')))
            ids[i] = e['_file']
            bad = [f for f in FORBIDDEN if f in e]
            if bad:
                problems.append('%s (%s): era events may not carry %s' % (i, e['_file'], ', '.join(bad)))
            if not e.get('title') or not e.get('body'):
                problems.append('%s (%s): needs a title and a body' % (i, e['_file']))
    if problems:
        raise EraError('\n'.join(problems))
    album_years, months_ok, days_ok = pool()
    years_ok = stretch_years(k, album_years)
    end = bounds(k, masters)
    dated = {}
    out, warn = [], []

    def keep(e, ymd, is_master, src):
        y, m, d = ymd
        rec = {kk: v for kk, v in e.items() if kk not in CONTROL and not kk.startswith('_')
               and kk not in ('y', 'm', 'd', 'age', 'era', 'ey', 'date')}
        rec.update(y=y, m=m, d=d, age=k, era=reckoning.ERA[k][3], ey=reckoning.era_year(y, k),
                   date=reckoning.display(y, m, d, k), master=is_master, src=src)
        dated[rec['id']] = rec
        out.append(rec)

    for g, me in enumerate(masters):
        keep(me, (me['y'], me['m'], me['d']), True, 'age_%s_master.json' % k)
        L = (me['y'], me['m'], me['d'])
        R = (masters[g + 1]['y'], masters[g + 1]['m'], masters[g + 1]['d']) if g + 1 < len(masters) else end
        for e, ymd in zip(gaps[g], date_gap(k, L, R, gaps[g], years_ok, months_ok, days_ok, dated, warn)):
            keep(e, ymd, False, e['_file'])
    verify(k, out, masters)
    return out, warn


def verify(k, out, masters):
    """The promises of this module, asserted on every build."""
    by = {e['id']: e for e in out}
    for m in masters:
        e = by[m['id']]
        assert (e['y'], e['m'], e['d'], e['date']) == (m['y'], m['m'], m['d'], m['date']), '%s moved' % m['id']
    order = [(e['y'], e['m'], e['d']) for e in out]
    assert order == sorted(order), 'the era annals run backwards somewhere'
    assert [e['id'] for e in out if e['master']] == [m['id'] for m in masters], 'the master events are out of order'
    for e in out:
        assert reckoning.era_of(e['y'], e['m'], e['d']) == k, '%s falls outside the era of Age %s' % (e['id'], k)


# ---------------------------------------------------------------- places, tokens, the record
def load_places(k):
    p = os.path.join(age_dir(k), 'places.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


class EraRecord(build_book.Record):
    """The master Record (its names, gazetteer, reckoning and token resolver) with the era's events in front:
    {{date:ID}} and {{year:ID}} look in the era annals first and then in the whole master record; {{place:REF}}
    looks in the era's places.json first and then in the master map."""

    def __init__(self, k, events):
        super().__init__()
        self.k = k
        self.master_all = self.events
        self.events = events
        self.by_id = {e['id']: e for e in self.master_all}
        self.by_id.update({e['id']: e for e in events})
        self.places = load_places(k)
        for ref, p in self.places.items():
            if p.get('name'):
                self.names[ref] = p['name']
        self.at = {}
        for e in events:
            if e.get('place'):
                self.at.setdefault(e['place'], []).append(e)
        self.era_gaz = self.load_era_gazetteer()

    def load_era_gazetteer(self):
        gaz = {}
        for f in sorted(glob.glob(os.path.join(age_dir(self.k), 'gazetteer', '*.json'))):
            for bid, g in json.load(open(f, encoding='utf-8')).items():
                g = dict(g)
                g['_file'] = os.path.basename(f)
                if bid in gaz:
                    self.missing.append('gazetteer burg %s twice (%s, %s)' % (bid, gaz[bid]['_file'], g['_file']))
                gaz[bid] = g
        for bid, g in gaz.items():
            g['founded'] = self.era_founding(bid, g)
        return gaz

    def burg_facts(self, bid):
        """name, province and the rest for a gazetteer entry: the entry's own words for the age, else the era
        place, else the master map."""
        b = dict(self.burg.get(int(bid), {})) if str(bid).isdigit() else {}
        b.update({kk: v for kk, v in self.places.get('burg:%s' % bid, {}).items()})
        return b

    def era_founding(self, bid, g):
        ev = self.by_id.get(g.get('founded_event') or '')
        if ev:
            return {'y': ev['y'], 'm': ev['m'], 'd': ev['d'], 'date': ev['date']}
        mg = self.gaz.get(int(bid)) if str(bid).isdigit() else None
        if mg and (not g.get('founded_age') or g.get('founded_age') == mg.get('founded_age')):
            return mg['founded']                         # a master town keeps its master founding day
        age = g.get('founded_age') or self.k
        first, last = build_book.AGE_SPAN.get(age, build_book.AGE_SPAN[self.k])
        lo, hi = first, last
        if g.get('founded_between'):
            lo, hi = max(lo, g['founded_between'][0]), min(hi, g['founded_between'][1])
        evs = [e for e in self.at.get('burg:%s' % bid, []) if e['y'] >= lo]
        if evs:
            hi = min(hi, evs[0]['y'] - 1 if evs[0]['y'] != 1 else -1)
        if lo > hi:
            hi = lo
        y, m, d = self.reckon(lo, hi, 'founding:%s' % bid)
        opens = reckoning.openings().get(age)
        if opens and (y, m, d) < opens:
            y1 = reckoning.nz(opens[0] + 1)
            y, m, d = self.reckon(y1, y1, 'founding:%s' % bid)
        return {'y': y, 'm': m, 'd': d, 'date': reckoning.display(y, m, d)}


# ---------------------------------------------------------------- links between events
def raw_era_events(k):
    """An age's era events as written, undated: for link targets when that age does not date yet."""
    out = []
    for f in sorted(glob.glob(os.path.join(age_dir(k), 'annals', '*.json'))):
        data = json.load(open(f, encoding='utf-8'))
        if isinstance(data, dict):
            out += [dict(e, age=k, master=False) for e in data.get('events', []) if isinstance(e, dict) and e.get('id')]
    return out


_DATED = {}


def link_universe(k, events):
    """Every event a link may point at: the whole master record, every era that has annals, and this era as
    it is being built. -> ({id: event}, [ages that did not date and are linked undated])."""
    uni = {e['id']: dict(e, master=True) for e in json.load(open(os.path.join(LEG, 'annals_dated.json'), encoding='utf-8'))}
    undated = []
    for o in KEYS:
        if o == k or not os.path.isdir(os.path.join(age_dir(o), 'annals')):
            continue
        if o not in _DATED:
            try:
                _DATED[o] = date_era(o)[0]
            except (EraError, AssertionError):
                _DATED[o] = None
        if _DATED[o] is None:
            undated.append(o)
            for e in raw_era_events(o):
                uni.setdefault(e['id'], e)
        else:
            for e in _DATED[o]:
                if not e['master']:
                    uni[e['id']] = e
    for e in events:
        uni[e['id']] = e
    return uni, undated


def year_of_event(e):
    return reckoning.display_year(e['y'], e['m'], e['d'], e['age'])


def resolved_links(k, events):
    uni, undated = link_universe(k, events)
    return event_links.resolve(uni, lambda e: year_of_event(e) if e.get('y') is not None else None), uni, undated


def link_note(k, links, source=None, when=None):
    """One annals entry's links, as a footnote: same-age links jump to the entry in this book; a link into an earlier
    age prints '→ <age>, <year>' and opens that age's own legendarium (era-pdf: becomes a GoToR link in relink_pdf).
    Given the entry's event (source), links to later events are left out: the volume points back only, and the
    forward links live in the Atlas (atlas.json)."""
    return event_links.footnote_html(links, k, lambda a: 'era-pdf:../age_%s/%s' % (a, pdf_name(a)),
                                     lambda a: build_book.AGE_NAMES[a][0], source=source, when=when)


def _registry(name, key):
    p = os.path.join(ERAS, name)
    if not os.path.exists(p):
        return {}
    raw = json.load(open(p, encoding='utf-8'))
    rows = raw.get(key, []) if isinstance(raw, dict) else raw
    return {r['id']: r for r in rows if isinstance(r, dict) and r.get('id')}


def threads():
    """eras/THREADS.json: {id: {id, dt, gloss, colour, description}}"""
    return _registry('THREADS.json', 'threads')


def people():
    """eras/PEOPLE.json: {id: {id, name, born, died, parents, children, houses, first, last}}"""
    return _registry('PEOPLE.json', 'people')


def heading_anchor(text):
    """A book heading's anchor for "told_in": accents dropped, lower case, every other run of characters a hyphen.
    '## IV. Of the Sunwise Turn' -> 'iv-of-the-sunwise-turn'"""
    t = build_book.fold(re.sub(r'[*_`]', '', text))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def book_anchors(path):
    """{anchor: heading} of every #, ## and ### heading of a book file."""
    out = {}
    for m in re.finditer(r'^#{1,3} (.+)$', build_book.read_md(path), re.M):
        out.setdefault(heading_anchor(m.group(1)), m.group(1).strip())
    return out


def told_in(k, ref):
    """Resolve "told_in": "book/<file>.md#<anchor>" against the era's own books, then the master's
    (legendarium/book/) for a master event. -> {ref, file, anchor, book, section, where} or None."""
    if not isinstance(ref, str) or not re.match(r'^book/[^#/]+\.md(#[a-z0-9-]+)?$', ref):
        return None
    f, _, a = ref.partition('#')
    for where, base in (('era', age_dir(k)), ('master', LEG)):
        p = os.path.join(base, f)
        if os.path.exists(p):
            anchors = book_anchors(p)
            if a and a not in anchors:
                return None
            first = next(iter(anchors.values()), '')
            return {'ref': ref, 'file': f, 'anchor': a or None, 'book': first, 'section': anchors.get(a) if a else None,
                    'where': where}
    return None


def gaps_over(events, years=100):
    """Where the timeline passes more than `years` years between two events: the Atlas's '~ ~ ~ 312 years ~ ~ ~'."""
    out = []
    for a, b in zip(events, events[1:]):
        n = b['y'] - a['y'] - (1 if a['y'] < 0 < b['y'] else 0)
        if n > years:
            out.append({'after': a['id'], 'before': b['id'], 'years': n})
    return out


def atlas_data(k, events, links, rec):
    """What the Atlas timeline needs for one era: its header, every event with its category and its links both
    ways (each with the target's era, date and title), and the long gaps."""
    rn = build_book.AGE_NAMES[k][0]
    era = reckoning.ERA[k]
    evs = []
    for e in events:
        x = {kk: e.get(kk) for kk in ('id', 'date', 'y', 'm', 'd', 'era', 'ey', 'title', 'body', 'place', 'kind',
                                      'category', 'master')}
        x['title'] = rec.resolve(x['title'] or '', link=False)
        x['body'] = rec.resolve(x['body'] or '', link=False)
        x['year'] = year_of_event(e)
        x['category_name'] = event_links.CATEGORIES.get(e.get('category'))
        if e.get('place'):
            x['place_name'] = rec.place_name(e['place'])
        x['links'] = links.get(e['id'], [])
        x['threads'] = e.get('threads') or []
        x['people'] = e.get('people') or []
        x['told_in'] = told_in(k, e['told_in']) if e.get('told_in') else None
        evs.append(x)
    th, pp = threads(), people()
    used_t = sorted({t for x in evs for t in x['threads']})
    used_p = sorted({q for x in evs for q in x['people']})
    return {'age': k, 'name': rn, 'english': build_book.AGE_NAMES[k][1], 'era': era[3], 'era_name': era[5],
            'span': reckoning.display_span(k), 'header': '%s — %s' % (rn, reckoning.display_span(k)),
            'pdf': pdf_name(k), 'categories': event_links.CATEGORIES,
            'link_types': {t: {'arrow': a, 'out': o, 'in': i} for t, (a, o, i) in event_links.TYPES.items()},
            'threads': {t: th[t] for t in used_t if t in th}, 'people': {q: pp[q] for q in used_p if q in pp},
            'events': evs, 'gaps': gaps_over(events)}


def relink_pdf(path):
    """Make every era-pdf: link a GoToR action: the other age's PDF by its relative file name, opened at the
    entry's named destination."""
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject, TextStringObject, DictionaryObject, BooleanObject
    except ImportError:
        print('  (pypdf is not installed: links to the other ages\' PDFs stay as written)')
        return 0
    r = PdfReader(path)
    w = PdfWriter(clone_from=r)
    n = 0
    for page in w.pages:
        for a in page.get('/Annots') or []:
            a = a.get_object()
            act = a.get('/A')
            act = act.get_object() if act is not None else None
            uri = act.get('/URI') if act is not None else None
            if uri and str(uri).startswith('era-pdf:'):
                f, _, dest = str(uri)[len('era-pdf:'):].partition('#')
                a[NameObject('/A')] = DictionaryObject({
                    NameObject('/S'): NameObject('/GoToR'), NameObject('/F'): TextStringObject(f),
                    NameObject('/D'): TextStringObject(dest), NameObject('/NewWindow'): BooleanObject(True)})
                n += 1
    if n:
        w.write(path)
    return n


# ---------------------------------------------------------------- the era's markdown
def first_heading(md):
    m = re.search(r'^(#{1,2}) (.+)$', md, re.M)
    return m


PART_MARK = re.compile(r'^\*Part ([A-Z][a-z]+): (.+?)\*[ \t]*\n?', re.M)
NUMBER_WORDS = ('One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen Fifteen Sixteen '
                'Seventeen Eighteen Nineteen').split()
TENS_WORDS = {2: 'Twenty', 3: 'Thirty', 4: 'Forty', 5: 'Fifty', 6: 'Sixty', 7: 'Seventy', 8: 'Eighty', 9: 'Ninety'}


def number_word(n):
    if n < 20:
        return NUMBER_WORDS[n - 1]
    t, u = divmod(n, 10)
    return TENS_WORDS[t] + ('-' + NUMBER_WORDS[u - 1].lower() if u else '')


def book_parts(k, rec):
    """The era's book/*.md files in file order. Each file is one chapter of the age's novel: its first '# ' heading
    is the chapter's title, printed '# Chapter <N>: <title>'. A file whose heading is already in the master form
    '# The Fourth Book: ...' is kept as a Book. A chapter that opens a Part carries, between its title and its first
    '## ' section, a line '*Part <Number>: <Title>*'; that line becomes a '# Part <Number>: <Title>' heading set
    before the chapter, and the chapters after it stand under that Part until the next."""
    out, chapter = [], 0
    for p in sorted(glob.glob(os.path.join(age_dir(k), 'book', '*.md'))):
        md = rec.resolve(build_book.read_md(p), link=False)
        m = re.search(r'^# (.+)$', md, re.M)
        if not m:
            raise EraError('%s: a book file opens with a "# Title" heading' % os.path.relpath(p, ROOT))
        title = m.group(1).strip()
        if re.match(r'^The \w+ Book: ', title):
            out.append(md)
            continue
        chapter += 1
        rest = md[m.end():]
        sec = re.search(r'^## ', rest, re.M)
        head_len = sec.start() if sec else len(rest)
        pm = PART_MARK.search(rest[:head_len])
        if pm:
            out.append('# Part %s: %s' % (pm.group(1), pm.group(2).strip()))
            rest = rest[:pm.start()] + rest[pm.end():]
        out.append(md[:m.start()] + '# Chapter %s: %s' % (number_word(chapter), title) + rest)
    return out


def appendix_parts(k, rec):
    """Each appendices/*.md is one appendix: 'Appendix X — Title' kept as written, else lettered by file order."""
    out = []
    for n, p in enumerate(sorted(glob.glob(os.path.join(age_dir(k), 'appendices', '*.md')))):
        md = rec.resolve(build_book.read_md(p), link=False)
        m = first_heading(md)
        if not m:
            raise EraError('%s: an appendix opens with a "# Title" heading' % os.path.relpath(p, ROOT))
        title = m.group(2).strip()
        mm = re.match(r'^Appendix ([A-Z]) — (.*)$', title)
        head = '# Appendix %s — %s' % ((mm.group(1), mm.group(2)) if mm else (LETTERS[n], title))
        out.append(md[:m.start()] + head + md[m.end():])
    return out


def annal_sections(k, events):
    """Split the annals by spans of era years, so the contents can find them: 10-20 sections an age."""
    last_ey = reckoning.era_year(reckoning.ERA[k][2], k)
    step = next(s for s in (5, 10, 25, 50, 100, 200, 250, 500, 1000, 2000) if last_ey / s <= 20)
    secs = {}
    for e in events:
        secs.setdefault((e['ey'] - 1) // step, []).append(e)
    abbr = reckoning.ERA[k][3]
    for s in sorted(secs):
        a, b = s * step + 1, min((s + 1) * step, last_ey)
        yield 'The Years %s %s – %s' % (abbr, reckoning.year_count(a), reckoning.year_count(b)), secs[s]


def gazetteer_md(rec):
    out = []
    letter = None
    rows = []
    for bid, g in rec.era_gaz.items():
        b = rec.burg_facts(bid)
        name = g.get('name') or b.get('name') or 'burg %s' % bid
        rows.append((build_book.fold(name), bid, name, b, g))
    for _, bid, name, b, g in sorted(rows):
        if build_book.fold(name)[:1].upper() != letter:
            letter = build_book.fold(name)[:1].upper()
            out += ['#### ' + letter, '']
        now = b.get('name') if str(bid).isdigit() and b.get('name') and b.get('name') != name else None
        prov = g.get('province') or b.get('province', '')
        head = '**%s**%s%s. ' % (name, ' (now %s)' % now if now else '', ' (%s)' % prov if prov else '')
        text = 'Founded %s%s. %s' % (g['founded']['date'], ' by ' + g['founded_by'] if g.get('founded_by') else '',
                                     rec.resolve(g.get('history', ''), link=False))
        if g.get('known_for'):
            text += ' Known for %s.' % rec.resolve(g['known_for'], link=False).rstrip('.')
        out += [head + text, '']
    return out


def to_markdown(k, rec, links=None):
    rn, en, _ = build_book.AGE_NAMES[k]
    links = links or {}
    days = {e['id']: (e['y'], e['m'], e['d']) for e in rec.events if e.get('y') is not None}
    out = ['# ' + full_title(k), '']
    for md in book_parts(k, rec):
        out += [build_book.plain(md).rstrip(), '']
    out += ['# The Annals of the Age', '']
    for head, evs in annal_sections(k, rec.events):
        out += ['## ' + head, '']
        for e in evs:
            pl = ' (%s)' % rec.place_name(e['place']) if e.get('place') else ''
            out.append('- <a id="%s"></a>**%s** — *%s*%s. %s%s' % (
                event_links.anchor(e['id']), e['date'], rec.resolve(e['title'], link=False), pl,
                rec.resolve(e['body'], link=False), link_note(k, links.get(e['id'], []), e, days.get)))
        out.append('')
    if rec.era_gaz:
        out += ['# A Gazetteer of the Age', ''] + gazetteer_md(rec)
    for md in appendix_parts(k, rec):
        out += [build_book.plain(md).rstrip(), '']
    return '\n'.join(out)


# ---------------------------------------------------------------- the PDF
def front_html(k):
    rn, en, _ = build_book.AGE_NAMES[k]
    era = reckoning.ERA[k]
    fp = os.path.join(age_dir(k), 'front.json')
    front = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
    ep = front.get('epigraph')
    esc = build_pdf.html.escape
    h = ['<style>.titlepage .tage{font-family:\'Uncial\',serif; font-size:19pt; line-height:1.15; color:#1a1612; '
         'margin:0 0 2mm; text-align:center} .fl a[href]{color:#6d1f14}</style>',
         '<div class="halftitle"><h1>%s</h1></div>' % esc(english_name(k)),
         '<div class="titlepage">',
         '  <p class="t1">%s</p>' % esc(era[5]),
         '  <h1>The Legendarium<br>of Dia-thìr</h1>',
         '  <p class="tage">— %s</p>' % esc(english_name(k)),
         '  <p class="t2">(%s)</p>' % esc(rn),
         '  <div class="rule"></div>',
         '  <p class="t3">being the Books of the age, the Annals of its years,<br>a Gazetteer of its towns, and the Appendices'
         '<br>%s, %s</p>' % (esc(era[4]), esc(reckoning.display_span(k))),
         '</div>']
    if ep:
        h += ['<div class="epipage">', '  <p class="ro">%s</p>' % esc(ep.get('ro', '')),
              '  <p class="en">%s</p>' % esc(ep.get('en', '')), '  <p class="src">%s</p>' % esc(ep.get('src', '')), '</div>']
    return '\n'.join(h) + '\n'


def cfg(k):
    return {'doc_title': full_title(k), 'annals': 'The Annals of the Age', 'gazetteer': 'A Gazetteer of the Age',
            'books_line': 'The Books of the Age', 'appendices': 'The Appendices'}


# ---------------------------------------------------------------- build
def build(k, pdf=True, quiet=False):
    events, warn = date_era(k)
    d = age_dir(k)
    json.dump(events, open(os.path.join(d, 'annals_dated.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rec = EraRecord(k, events)
    links, uni, undated = resolved_links(k, events)
    for o in undated:
        print('  note: Age %s does not date yet; links into it are printed without a date' % o)
    # for the Atlas: this era's timeline (events, categories, links both ways, gaps); and the master overview's links
    json.dump(atlas_data(k, events, links, rec), open(os.path.join(d, 'atlas.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    master_ids = [i for i, e in uni.items() if e.get('master')]
    json.dump({i: links[i] for i in master_ids if i in links},
              open(os.path.join(ERAS, 'master_links.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = to_markdown(k, rec, links)
    open(os.path.join(d, 'LEGENDARIUM.md'), 'w', encoding='utf-8').write(md)
    n_master = sum(1 for e in events if e['master'])
    print('Age %s: %d events (%d master, %d era), %s .. %s' % (k, len(events), n_master, len(events) - n_master,
                                                               events[0]['date'], events[-1]['date']))
    for w in warn[:40] if not quiet else []:
        print('  note:', w)
    print('  LEGENDARIUM.md: about %s words' % format(len(md.split()), ','))
    if rec.missing:
        raise EraError('unresolved references: %s' % ', '.join(sorted(set(rec.missing))[:40]))
    if pdf:
        out = os.path.join(d, pdf_name(k))
        doc = build_pdf.compose_html(md.split('\n'), cfg(k), front_html(k))
        pages = build_pdf.write_pdf(doc, out)
        n = relink_pdf(out)
        print('  wrote %s (%d pages, %d links to other ages\' books)' % (os.path.relpath(out, ROOT), pages, n))
        return pages
    return None


def main():
    ap = argparse.ArgumentParser(description='Build an age\'s own legendarium.')
    ap.add_argument('age', help='I..VII or all')
    ap.add_argument('--no-pdf', action='store_true', help='date the annals and write LEGENDARIUM.md only')
    ap.add_argument('--seed', action='store_true', help='(re)write annals/age_<K>_master.json from the master annals')
    a = ap.parse_args()
    keys = KEYS if a.age == 'all' else [a.age]
    if any(k not in KEYS for k in keys):
        sys.exit('age must be one of %s or all' % ', '.join(KEYS))
    if a.seed:
        for k in keys:
            write_seed(k)
        return
    if a.age == 'all':
        keys = [k for k in keys if os.path.isdir(os.path.join(age_dir(k), 'annals'))]
    try:
        for k in keys:
            build(k, pdf=not a.no_pdf)
    except EraError as e:
        sys.exit('build_era: %s' % e)


if __name__ == '__main__':
    main()
