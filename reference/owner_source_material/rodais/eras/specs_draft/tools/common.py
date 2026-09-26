"""Shared loader, builder and validator for the era spec drafts (phase 1b).

Reads the master record read-only: Rodos_finished.map (records as in legendarium/map_reconcile.py),
legendarium/annals_dated.json and legendarium/gazetteer/out_*.json. Each age module (age_I.py ...
age_VII.py) builds one dict with the Spec class and writes eras/specs_draft/age_<K>.json.

    python3 eras/specs_draft/tools/build_all.py
"""
import json
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
DRAFT = os.path.dirname(HERE)
RODAIS = os.path.dirname(os.path.dirname(DRAFT))
sys.path.insert(0, RODAIS)
import rodais_engine as RE  # noqa: E402

AGES = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']


def aidx(a):
    return AGES.index(a)


# ------------------------------------------------------------------ the master map
_L = open(os.path.join(RODAIS, 'Rodos_finished.map'), encoding='utf-8', newline='').read().split('\r\n')
assert len(_L) == 53
# the people one of Azgaar's population units stands for (units.population.scale, record 1): 50 since the owner's
# decision of 2026-09-25, some 1.8 million on the island (eras/POP_LOG.md). Every population in the drafts is people.
RATE = json.loads(_L[1])['units']['population']['scale']
# the generator's own town sizes (1,000 people to the unit), against which the Age of Ailean's villages were sized
_G = open(os.path.join(RODAIS, 'Rodos_renamed.map'), encoding='utf-8', newline='').read().split('\r\n')
GEN_POP = {b['i']: int(round(b['population'] * 1000)) for b in json.loads(_G[15])
           if isinstance(b, dict) and b.get('i') and not b.get('removed')}


def _cells(n):
    return [int(float(x)) for x in _L[n].split(',')]


CELL_BIOME = _cells(16)
CELL_BURG = _cells(17)
CELL_CULT = _cells(19)
CELL_RELIG = _cells(26)
CELL_PROV = _cells(27)
NCELLS = len(CELL_PROV)
_J = {n: json.loads(_L[n]) for n in (13, 14, 15, 29, 30, 35, 37, 38)}
CULTURES = {c['i']: c for c in _J[13]}
STATE = _J[14][1]
RELIGIONS = {r['i']: r for r in _J[29]}
BURGS = {b['i']: b for b in _J[15] if isinstance(b, dict) and b.get('i') and not b.get('removed')}
PROVINCES = {p['i']: p for p in _J[30] if isinstance(p, dict)}
MARKERS = {m['i']: m for m in _J[35]}
ROUTES = {r['i']: r for r in _J[37]}
ZONES = {z['i']: z for z in _J[38]}
for _b in BURGS.values():
    _b['prov'] = CELL_PROV[_b['cell']]
    _b['pop'] = int(round(_b['population'] * RATE))

LAND_CELLS = [c for c in range(NCELLS) if CELL_BIOME[c]]
PROV_CELLS = collections.Counter(CELL_PROV[c] for c in LAND_CELLS)


def route_burgs(r):
    out = []
    for p in r['points']:
        b = CELL_BURG[p[2]]
        if b and b not in out:
            out.append(b)
    return out


ROUTE_BURGS = {i: route_burgs(r) for i, r in ROUTES.items()}

# cell -> (x, y) where the map records both (route points, burgs, markers)
CELLXY = {}
for _r in ROUTES.values():
    for _x, _y, _c in _r['points']:
        CELLXY.setdefault(_c, (_x, _y))
for _b in BURGS.values():
    CELLXY[_b['cell']] = (_b['x'], _b['y'])
for _m in MARKERS.values():
    CELLXY.setdefault(_m['cell'], (_m['x'], _m['y']))


def free_cell_near(x, y, prov=None, taken=()):
    """The nearest land cell with a known position, no master burg and not already taken."""
    best = None
    for c, (cx, cy) in CELLXY.items():
        if CELL_BURG[c] or not CELL_BIOME[c] or c in taken:
            continue
        if prov is not None and CELL_PROV[c] != prov:
            continue
        d = (cx - x) ** 2 + (cy - y) ** 2
        if best is None or d < best[0]:
            best = (d, c)
    return best[1] if best else None


def xy_of(ref):
    kind, i = ref
    if kind == 'burg':
        b = BURGS[i]
        return b['x'], b['y'], b['prov']
    if kind == 'marker':
        m = MARKERS[i]
        return m['x'], m['y'], CELL_PROV[m['cell']]
    if kind == 'cell':
        x, y = CELLXY[i]
        return x, y, CELL_PROV[i]
    raise ValueError(ref)


# ------------------------------------------------------------------ the record
ANNALS = json.load(open(os.path.join(RODAIS, 'legendarium', 'annals_dated.json'), encoding='utf-8'))
AID = {e['id']: e for e in ANNALS}
GAZ = {}
for _i in range(3):
    GAZ.update({int(k): v for k, v in json.load(open(os.path.join(RODAIS, 'legendarium', 'gazetteer', 'out_%d.json' % _i),
                                                      encoding='utf-8')).items()})

APPENDIX_REFS = {'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'}
CITE_RE = re.compile(r'^(?:[IVX]+-\d{4}[a-z]?|App\.[A-J](?: .*)?|gazetteer B\d+|book [IVX]+(?: .*)?|map .*|NAMING_LAYER.*|AGES7_BRIEF.*)$')


def ann(i):
    return AID[i]


def ann_date(i):
    return AID[i]['date']


# ------------------------------------------------------------------ names
_NAME_LOG = []


def dt(name, where, kind='place'):
    """Register a Dia-thìris name for validation. kind: place | polity | person | seann (Old Ones' root,
    not Dia-thìris) | phrase. Returns the name unchanged."""
    if name is not None:
        _NAME_LOG.append((name, where, kind))
    return name


def name_problems(name, kind):
    probs = []
    if RE.normalize(name) != name:
        probs.append('normalize changes it to %r' % RE.normalize(name))
    if kind not in ('seann',):
        v = RE.check_agreement(name)
        if v:
            probs.append('check_agreement: %s' % v)
    return probs


# ------------------------------------------------------------------ populations and kinds
def kind_for(pop, age):
    if aidx(age) > 1:
        pop = pop / KIND_SCALE[age]
    if aidx(age) <= 1:
        if pop < 50:
            return 'hearth'
        if pop < 200:
            return 'hamlet'
        return 'village'
    if pop < 100:
        return 'hamlet'
    if pop < 500:
        return 'village'
    if pop < 2500:
        return 'large village'
    if pop < 10000:
        return 'town'
    return 'city'


def rnd(n, age):
    if n < 100:
        return int(round(n / 5.0) * 5)
    if n < 1000:
        return int(round(n, -1))
    if n < 10000:
        return int(round(n, -2))
    return int(round(n, -3))


# ------------------------------------------------------------------ the spec
class Spec:
    def __init__(self, age, header):
        self.age = age
        self.d = collections.OrderedDict()
        self.d['schema'] = 'era-spec-draft/1'
        self.d.update(header)
        self.d['population_scale'] = collections.OrderedDict([
            ('people_per_unit', RATE), ('kind_scale', round(KIND_SCALE[age], 6)), ('people', ERA_PEOPLE.get(age)),
            ('note', 'populations are people; the master counts %d to its population unit in the country and sets '
                     'each town outright; "people" is the whole island at the close of the age' % RATE)])
        self.d['burgs'] = []
        self.d['burgs_absent'] = []
        self.d['new_burgs'] = []
        self.d['polities'] = []
        self.d['province_polity'] = {}
        self.d['diplomacy'] = []
        self.d['cultures'] = []
        self.d['faiths'] = []
        self.d['routes'] = collections.OrderedDict([('rule', ''), ('master', []), ('absent', []), ('new', [])])
        self.d['markers'] = collections.OrderedDict([('master', []), ('absent', []), ('new', [])])
        self.d['zones'] = []
        self.d['labels'] = []
        self.d['military'] = collections.OrderedDict([('hosts', []), ('campaigns', [])])
        self.d['arms'] = []
        self.d['notes'] = collections.OrderedDict([('polities', collections.OrderedDict()),
                                                   ('burgs', collections.OrderedDict())])
        self._taken_cells = set()

    # -- burgs
    def burg(self, i, **kw):
        b = BURGS[i]
        e = collections.OrderedDict()
        e['id'] = i
        e['master_name'] = b['name']
        for k in ('era_name', 'era_name_en', 'name_note', 'population', 'kind', 'role', 'culture', 'faith', 'order',
                  'polity', 'walls', 'port', 'cites', 'inferred', 'note'):
            if k in kw and kw[k] is not None:
                e[k] = kw[k]
        if kw.get('era_name'):
            dt(kw['era_name'], 'burg %d era_name' % i, kw.get('name_kind', 'place'))
        self.d['burgs'].append(e)
        return e

    def absent(self, i, reason, cites, inferred=False, state='not yet founded'):
        e = collections.OrderedDict([('id', i), ('master_name', BURGS[i]['name']), ('state', state),
                                     ('reason', reason), ('cites', cites)])
        if inferred:
            e['inferred'] = True
        self.d['burgs_absent'].append(e)

    def new_burg(self, key, name, name_en, near, **kw):
        x, y, prov = xy_of(near)
        cell = kw.pop('cell', None) or free_cell_near(x, y, kw.pop('prov', prov), self._taken_cells)
        if cell is None:
            cell = free_cell_near(x, y, None, self._taken_cells)
        self._taken_cells.add(cell)
        e = collections.OrderedDict([('key', key), ('name', name), ('name_en', name_en), ('cell', cell),
                                     ('province', CELL_PROV[cell]), ('near', {near[0]: near[1]})])
        e.update(kw)
        if name:
            dt(name, 'new burg %s' % key, kw.get('name_kind', 'place'))
        e.pop('name_kind', None)
        self.d['new_burgs'].append(e)
        return e

    # -- polities
    def polity(self, key, name, name_en, **kw):
        e = collections.OrderedDict([('key', key), ('name', name), ('name_en', name_en)])
        e.update(kw)
        if name:
            dt(name, 'polity %s' % key, 'polity')
        self.d['polities'].append(e)
        return e

    def assign(self, mapping):
        """mapping: {polity_key: [province ids]}; every province 1..123 must end up assigned exactly once."""
        for k, provs in mapping.items():
            for p in provs:
                assert str(p) not in self.d['province_polity'], 'province %d assigned twice (%s)' % (p, k)
                self.d['province_polity'][str(p)] = k

    def marker(self, i, **kw):
        m = MARKERS[i]
        e = collections.OrderedDict([('id', i), ('master_name', m['name'])])
        e.update(kw)
        if kw.get('era_name'):
            dt(kw['era_name'], 'marker %d era_name' % i, kw.get('name_kind', 'place'))
        e.pop('name_kind', None)
        self.d['markers']['master'].append(e)

    def new_marker(self, key, name, name_en, at, **kw):
        e = collections.OrderedDict([('key', key), ('name', name), ('name_en', name_en)])
        kind, ref = at
        e[kind] = ref
        if kind == 'cell':
            e['province'] = CELL_PROV[ref]
        e.update(kw)
        if name:
            dt(name, 'new marker %s' % key, kw.get('name_kind', 'place'))
        e.pop('name_kind', None)
        self.d['markers']['new'].append(e)

    # -- write
    def finish(self):
        return self.d


# ------------------------------------------------------------------ validation
def validate(spec, age):
    errs, warns = [], []
    d = spec
    present = {b['id'] for b in d['burgs']}
    absent = {b['id'] for b in d['burgs_absent']}
    for b in d['burgs']:
        if b['id'] not in BURGS:
            errs.append('burg %s not in master' % b['id'])
    if present & absent:
        errs.append('burgs both present and absent: %s' % sorted(present & absent))
    if len(present) != len(d['burgs']):
        errs.append('duplicate burg entries')
    polkeys = {p['key'] for p in d['polities']}
    for p in range(1, 124):
        k = d['province_polity'].get(str(p))
        if k is None:
            errs.append('province %d unassigned' % p)
        elif k != 'unclaimed' and k not in polkeys:
            errs.append('province %d -> unknown polity %s' % (p, k))
    for k in d['province_polity']:
        if int(k) not in PROVINCES:
            errs.append('province %s not in master' % k)
    newkeys = {n['key'] for n in d['new_burgs']}
    for pol in d['polities']:
        cap = pol.get('capital')
        if cap:
            if 'burg' in cap and cap['burg'] not in present:
                errs.append('polity %s capital burg %s not present' % (pol['key'], cap['burg']))
            if 'new_burg' in cap and cap['new_burg'] not in newkeys:
                errs.append('polity %s capital new burg %s missing' % (pol['key'], cap['new_burg']))
        for u in pol.get('admin_units', []):
            for p in u.get('provinces', []):
                if p not in PROVINCES:
                    errs.append('admin unit %s province %s' % (u.get('name_en'), p))
    for b in d['burgs']:
        if b.get('polity') and b['polity'] not in polkeys and b['polity'] != 'unclaimed':
            errs.append('burg %d polity %s unknown' % (b['id'], b['polity']))
    cult_keys = {c['key'] for c in d['cultures']}
    faith_keys = {f['key'] for f in d['faiths']}
    for b in d['burgs'] + d['new_burgs']:
        if b.get('culture') and b['culture'] not in cult_keys:
            errs.append('burg %s culture %s unknown' % (b.get('id', b.get('key')), b['culture']))
        if b.get('faith') and b['faith'] not in faith_keys:
            errs.append('burg %s faith %s unknown' % (b.get('id', b.get('key')), b['faith']))
    for n in d['new_burgs']:
        if not (0 <= n['cell'] < NCELLS) or not CELL_BIOME[n['cell']]:
            errs.append('new burg %s cell %s not land' % (n['key'], n['cell']))
        if CELL_BURG[n['cell']]:
            errs.append('new burg %s on master burg cell' % n['key'])
    cells = [n['cell'] for n in d['new_burgs']]
    if len(cells) != len(set(cells)):
        errs.append('two new burgs share a cell')
    rr = d['routes']
    seen = set()
    for r in rr['master']:
        if r['id'] not in ROUTES:
            errs.append('route %s not in master' % r['id'])
        seen.add(r['id'])
    for r in rr['absent']:
        if r not in ROUTES:
            errs.append('absent route %s not in master' % r)
        if r in seen:
            errs.append('route %s both present and absent' % r)
        seen.add(r)
    if seen != set(ROUTES):
        errs.append('routes not all classified: missing %s' % sorted(set(ROUTES) - seen)[:20])
    for r in rr['new']:
        for b in r.get('burgs', []):
            if isinstance(b, int) and b not in present:
                errs.append('new route %s burg %s not present' % (r['key'], b))
            if isinstance(b, str) and b not in newkeys:
                errs.append('new route %s new burg %s missing' % (r['key'], b))
    ms = set()
    for m in d['markers']['master']:
        if m['id'] not in MARKERS:
            errs.append('marker %s not in master' % m['id'])
        ms.add(m['id'])
    for m in d['markers']['absent']:
        mid = m['id'] if isinstance(m, dict) else m
        if mid in ms:
            errs.append('marker %s both present and absent' % mid)
        ms.add(mid)
    if ms != set(MARKERS):
        errs.append('markers not all classified: %s' % sorted(set(MARKERS) - ms))
    for m in d['markers']['new']:
        if 'burg' in m and m['burg'] not in present and m['burg'] not in BURGS:
            errs.append('new marker %s burg %s' % (m['key'], m['burg']))
        if 'burg' in m and m['burg'] not in present:
            warns.append('new marker %s sits at burg %s which is not present this age (used as a place only)' % (m['key'], m['burg']))
        if 'marker' in m and m['marker'] not in MARKERS:
            errs.append('new marker %s at unknown marker' % m['key'])
        if 'cell' in m and not (0 <= m['cell'] < NCELLS):
            errs.append('new marker %s bad cell' % m['key'])
    # every cite
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ('cites', 'cite') and isinstance(v, list):
                    for c in v:
                        if not isinstance(c, str) or not CITE_RE.match(c):
                            errs.append('bad cite %r at %s' % (c, path))
                        elif re.match(r'^[IVX]+-\d{4}[a-z]?$', c) and c not in AID:
                            errs.append('unknown annals id %s at %s' % (c, path))
                else:
                    walk(v, path + '.' + str(k))
        elif isinstance(o, list):
            for j, v in enumerate(o):
                walk(v, '%s[%d]' % (path, j))
    walk(d, age)
    # burgs referenced anywhere by id must exist in master
    for z in d['zones']:
        for b in z.get('burgs', []):
            if b not in BURGS:
                errs.append('zone %s burg %s' % (z.get('key'), b))
        for p in z.get('provinces', []):
            if p not in PROVINCES and p != 0:
                errs.append('zone %s province %s' % (z.get('key'), p))
        if 'master_zone' in z and z['master_zone'] not in ZONES:
            errs.append('zone %s master zone %s' % (z.get('key'), z['master_zone']))
    for h in d['military']['hosts']:
        st = h.get('station', {})
        if 'burg' in st and st['burg'] not in present:
            errs.append('host %s station burg %s not present' % (h.get('name_en'), st['burg']))
    return errs, warns


def name_report():
    out = []
    seen = set()
    for name, where, kind in _NAME_LOG:
        if (name, kind) in seen:
            continue
        seen.add((name, kind))
        probs = name_problems(name, kind)
        out.append({'name': name, 'kind': kind, 'first_use': where, 'problems': probs})
    return out


def reset_names():
    del _NAME_LOG[:]


def write(spec, age):
    path = os.path.join(DRAFT, 'age_%s.json' % age)
    ma = spec.get('markers', {}).get('absent', [])
    ma[:] = [m if isinstance(m, dict) else {'id': m, 'reason': 'not yet made or founded in this age', 'cites': ['map Rodos_finished.map record 35']} for m in ma]
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    return path


def near_cell(ref, prov=None, taken=None):
    x, y, p = xy_of(ref)
    return free_cell_near(x, y, prov, taken or ())


FEATURE_FIRST_CELL = {f['i']: f.get('firstCell') for f in json.loads(_L[12]) if isinstance(f, dict)}


# ------------------------------------------------------------------ routes
# Named routes whose making the annals date: route id -> list of (from_age, era_name or None, group, cites, note)
def classify_routes(spec, age, present, named, default_rule, rule_text):
    """named: {route_id: dict(first=age, name=..., group=..., cites=[...], note=..., last=age or None)}
    default_rule(route_id, touched, present) -> (bool, flag note or None)."""
    rr = spec['routes']
    rr['rule'] = rule_text
    for i in sorted(ROUTES):
        r = ROUTES[i]
        touched = ROUTE_BURGS[i]
        if i in named:
            n = named[i]
            ok = aidx(age) >= aidx(n['first']) and (n.get('last') is None or aidx(age) <= aidx(n['last']))
            if ok:
                e = collections.OrderedDict([('id', i), ('master_name', r.get('name')), ('group', n.get('group', r['group']))])
                if n.get('name') is not None:
                    e['era_name'] = n['name']
                    dt(n['name'], 'route %d era_name' % i, 'place')
                e['basis'] = 'named in the annals'
                e['cites'] = n['cites']
                if n.get('note'):
                    e['note'] = n['note']
                if n.get('inferred'):
                    e['inferred'] = True
                rr['master'].append(e)
            else:
                # before its making a named road may still run as a plain track between towns
                if n.get('track_before') and aidx(age) < aidx(n['first']):
                    ok2, flag = default_rule(i, touched, present)
                    if ok2:
                        e = collections.OrderedDict([('id', i), ('master_name', r.get('name')), ('group', 'trails'),
                                                     ('era_name', None), ('basis', 'track between towns of the age, before the road was made'),
                                                     ('cites', n['cites'])])
                        e['inferred'] = True
                        rr['master'].append(e)
                        continue
                rr['absent'].append(i)
            continue
        ok, flag = default_rule(i, touched, present)
        if ok:
            e = collections.OrderedDict([('id', i), ('master_name', r.get('name')), ('group', r['group']),
                                         ('basis', flag or 'links towns present in this age'), ('inferred', True)])
            rr['master'].append(e)
        else:
            rr['absent'].append(i)


def touched_rule(min_touch=1, allow_empty=False, slack=True):
    def rule(i, touched, present):
        if not touched:
            return (allow_empty, 'an unnamed lane touching no town; kept as the age had coasting and tracks' if allow_empty else None)
        if len(touched) < min_touch:
            return (False, None)
        missing = [b for b in touched if b not in present]
        if not missing:
            return (True, 'links towns present in this age')
        if slack and touched[0] in present and touched[-1] in present and len(missing) <= max(1, len(touched) // 4):
            return (True, 'links towns present in this age; passes the site of %s, not yet a town' %
                    ', '.join('%s (burg %d)' % (BURGS[b]['name'], b) for b in missing))
        return (False, None)
    return rule


# ------------------------------------------------------------------ defaults for towns the annals say little of
GENERIC_ROLE = [
    ('Seann ', "harbour on an Old Ones' site"), ('Baile Mòr ', 'great farm town'), ('Baile ', 'farm town'),
    ('Cathair ', 'town'), ('Dùn ', 'hill-fort'), ('Caol ', 'strait harbour'), ('Ros ', 'headland harbour'),
    ('Ceann ', 'headland village'), ('Cuan ', 'harbour'), ('Inis ', 'river-island village'), ('Àth ', 'ford village'),
    ('Muileann ', 'mill village'), ('Cnoc ', 'hill village'), ('Doire ', 'grove village'), ('Tobar ', 'well village'),
    ('Achadh ', 'field village'), ('Cill ', 'chapel village'), ('Eilean ', 'island'),
]


def generic_role(i):
    b = BURGS[i]
    name = b['name']
    for pre, role in GENERIC_ROLE:
        if name.startswith(pre):
            if b.get('port') and 'harbour' not in role:
                return role + ' with a landing'
            return role
    return 'harbour' if b.get('port') else 'village'


# the share of the master (present-day) population each age is drawn at, where the annals give no figure
# (the present-day towns are those of a real country of 1.8 million since round 2 of eras/pop_sweep.py: a third of the
# people in towns, the capital the largest at 55,000; the shares and clamps are the drafts' own, in people)
POP_FACTOR = {'III': 0.035, 'IV': 0.12, 'V': 0.45, 'VI': 0.85, 'VII': 1.0}
POP_CLAMP = {'III': (40, 2500), 'IV': (60, 9000), 'V': (100, 40000), 'VI': (150, 70000), 'VII': (0, 10 ** 9)}
# kinds are read from people as they stand (kind_for); the scale is kept for the drafts' population_scale record
KIND_SCALE = {a: 1.0 for a in AGES}
# the people on the island at the close of each age, given outright: the era map's country is scaled so that its
# towns and country together hold this many (the present is the master's own, some 1.8 million)
ERA_PEOPLE = {'I': 18000, 'II': 111000, 'III': 300000, 'IV': 570000, 'V': 1000000, 'VI': 1500000}


def default_pop(i, age):
    f = POP_FACTOR[age]
    lo, hi = POP_CLAMP[age]
    return rnd(max(lo, min(hi, BURGS[i]['pop'] * f)), age)


def province_seat_age(p):
    seat = PROVINCES[p].get('burg')
    if not seat:
        return None
    return GAZ[seat]['founded_age']


def nearest_province(p, allowed):
    x, y = PROVINCES[p]['pole']
    return min(allowed, key=lambda q: (PROVINCES[q]['pole'][0] - x) ** 2 + (PROVINCES[q]['pole'][1] - y) ** 2)


def master_faith_of_province(p):
    c = collections.Counter(CELL_RELIG[x] for x in LAND_CELLS if CELL_PROV[x] == p)
    return c.most_common(1)[0][0] if c else 0


def master_culture_of_province(p):
    c = collections.Counter(CELL_CULT[x] for x in LAND_CELLS if CELL_PROV[x] == p)
    return c.most_common(1)[0][0] if c else 2


def burg_master_faith(i):
    return CELL_RELIG[BURGS[i]['cell']]


def burg_master_culture(i):
    return BURGS[i]['culture']


# ------------------------------------------------------------------ the orders of the Old Faith by shire (App.B §V, present day)
ORDER_SHIRES = {
    'seabhag': [9, 45, 6, 51],
    'manannan': [117, 73, 3, 77, 64, 38, 15, 95],
    'cloch': [10, 17, 25, 72, 78, 108, 2, 22],
    'bride': [4, 63, 116, 80],
}


def present_order(p):
    """The order of the Old Faith that stands first in shire p today (App.B §V): the named shires, then Macha's block in
    the middle and south of the island and the schools' block in the north-east and the eastern hills."""
    for k, ps in ORDER_SHIRES.items():
        if p in ps:
            return k
    x, y = PROVINCES[p]['pole']
    if x < 880 and y > 280:
        return 'macha'
    return 'sgoiltean'


def shire_arms():
    """App.J §IV: {province id: (blazon, note)} for the 123 shires of the roll of arms (SE 4)."""
    out = {}
    txt = open(os.path.join(RODAIS, 'legendarium', 'appendices', 'J_arms.md'), encoding='utf-8').read()
    for line in txt.split('\n'):
        m = re.match(r'^\| (\d+) \| (?:\{\{place:province:(\d+)\}\}|[^|]+) \| [^|]* \| ([^|]+) \| ([^|]*) \|$', line)
        if m and int(m.group(1)) <= 123:
            p = int(m.group(1))
            note = re.sub(r'\{\{[^}]+\}\}', '', m.group(4)).replace('()', '').strip()
            note = re.sub(r'\s+([.,;])', r'\1', note)
            out[p] = (m.group(3).strip(), note)
    return out


TUATH_SHIRES = [7, 14, 23, 28, 36, 75, 86, 88, 105, 107, 122]
