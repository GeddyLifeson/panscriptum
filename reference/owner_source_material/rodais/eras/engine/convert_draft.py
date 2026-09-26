"""
convert_draft.py -- turn the era-spec drafts (eras/specs_draft/age_<K>.json, schema era-spec-draft/1) into engine
specs (eras/specs/age_<K>.json, see SPEC.md) and log every place where the draft asks for more than the engine can
draw in eras/specs/CONVERT_NOTES.md.

    python3 convert_draft.py                 # all seven ages
    python3 convert_draft.py II V            # some ages
    python3 convert_draft.py --prose-notes   # accepted for old scripts: the notes always carry the prose now

Map text and notes
- Names: the draft's Dia-thìris `name` where it has one; else a NAMES.json form whose English (or a variant) is the
  draft's English name; else, for an element the master already names (burg, marker, zone, culture, faith), the
  master's name; else the English gloss, with every NAMES.json English form in it written as its Dia-thìris form.
  A town the age's own record names (its gazetteer, places.json, PLAN_names.json "site of burg N") takes that name,
  and so does a new town whose place id (1000×K+n) the age's gazetteer names; an English gloss that is an entry of
  the age's PLAN_names.json takes its Dia-thìris form.
- Free labels with no Dia-thìris text are not drawn.
- Notes are for a reader of the map: the draft's English prose (what the place or thing is in this age), with its
  proper nouns in Dia-thìris by eras/quality/names_convert.py (humans' names as they are), then "Told of in:" and the
  annals events it cites, by title and date ("The mason's fire (VE 1)"). No ids, no build terms.
- The map's settings (distance scale, geography and coordinates) are the master's: the spec overrides none.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ERAS = os.path.dirname(HERE)
ROOT = os.path.dirname(ERAS)
DRAFTS = os.path.join(ERAS, 'specs_draft')
OUT = os.path.join(ERAS, 'specs')
MASTER = os.path.join(ROOT, 'Diathir_Atlas', 'Diathir.map')
MASTER_REL = '../../Diathir_Atlas/Diathir.map'           # relative to eras/specs/
AGES = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
NUM = {k: i + 1 for i, k in enumerate(AGES)}
PERSONAL = {'person', 'people-personal', 'human'}
COMMON_NOUNS = {'crossing'}          # NAMES variants that are also plain nouns in the drafts' glosses (a river crossing)
POLITY_KINDS = {'institution', 'guild', 'company', 'people', 'house', 'region'}
MANUAL = '<!-- manual: everything below this line is kept when convert_draft.py rewrites the file -->'

_NC = None
EVENTS = {}          # event id -> (title, date, place, age), filled by main()


def names_convert():
    """eras/quality/names_convert.py (the owner's rule for proper nouns in English prose), loaded on first use."""
    global _NC
    if _NC is None:
        sys.path.insert(0, os.path.join(ERAS, 'quality'))
        import names_convert as nc  # noqa: E402
        _NC = nc
    return _NC


# ---------------------------------------------------------------------------------------------- master map


class Master:
    def __init__(self, path):
        lines = open(path, encoding='utf-8', newline='').read().split('\r\n')
        assert len(lines) == 53, 'the master has %d records' % len(lines)
        J = lambda n: json.loads(lines[n])  # noqa: E731
        self.options = J(1)
        self.cultures = J(13)
        self.states = J(14)
        self.burgs = {b['i']: b for b in J(15) if isinstance(b, dict) and b.get('i') and not b.get('removed')}
        self.religions = J(29)
        self.provinces = {p['i']: p for p in J(30) if isinstance(p, dict) and p.get('i') and not p.get('removed')}
        self.markers = {m['i']: m for m in J(35)}
        self.routes = {r['i']: r for r in J(37)}
        self.zones = {z['i']: z for z in J(38)}
        self.journeys = J(52)
        self.cell_province = [int(x) for x in lines[27].split(',')]
        # the culture and faith most of each shire's cells hold on the master
        self.shire_culture = self.majority([int(x) for x in lines[19].split(',')])
        self.shire_religion = self.majority([int(x) for x in lines[26].split(',')])
        self.burg_province = {i: self.cell_province[b['cell']] for i, b in self.burgs.items()}
        self.cell_burg = {b['cell']: i for i, b in self.burgs.items()}
        self.scale = self.options['units']['distance']['scale']
        self.rate = self.options['units']['population']['scale']     # people to Azgaar's population unit (38)
        self.rural = sum(float(x) for x in lines[21].split(','))     # the country's people, in units
        xs = [b['x'] for b in self.burgs.values()]
        ys = [b['y'] for b in self.burgs.values()]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))    # the island, by its burgs
        self.width = self.options['graph']['width']
        self.height = self.options['graph']['height']


    def majority(self, per_cell):
        count = defaultdict(Counter)
        for c, p in enumerate(self.cell_province):
            if p:
                count[p][per_cell[c]] += 1
        return {p: cnt.most_common(1)[0][0] for p, cnt in count.items()}


# ---------------------------------------------------------------------------------------------- NAMES.json


class Names:
    def __init__(self, path):
        raw = json.load(open(path, encoding='utf-8'))
        self.exact = {}
        self.polity_forms = []
        forms = []
        for e in raw['names']:
            if str(e.get('kind', '')).lower() in PERSONAL:
                continue
            for en in [e['en']] + [v for v in e.get('variants') or [] if isinstance(v, str)]:
                self.exact.setdefault(self.key(en), e['dt'])
                core = re.sub(r'^(?i:the)\s+', '', en)
                if len(core) >= 3 and core != e['dt'] and core not in COMMON_NOUNS:
                    forms.append((core, e['dt']))
                    if e.get('kind') in POLITY_KINDS:
                        self.polity_forms.append((core, e['dt']))
        forms.sort(key=lambda f: -len(f[0]))
        self.polity_forms.sort(key=lambda f: -len(f[0]))
        self.forms = forms

    @staticmethod
    def key(s):
        s = re.sub(r'\([^)]*\)', '', s)
        s = re.sub(r'^(?i:the)\s+', '', s.strip())
        return re.sub(r'\s+', ' ', s).strip().lower()

    def lookup(self, en):
        """The Dia-thìris form of an English name given whole (parentheses and 'the' aside), or None."""
        return self.exact.get(self.key(en or '')) if en else None

    def contained(self, en, everything=False):
        """The Dia-thìris form of the longest NAMES English form of a body or people inside `en` (for polity
        names), or None."""
        for core, dt in (self.forms if everything else self.polity_forms):
            if re.search(r'(?<![\w\-])%s(?![\w\-])' % re.escape(core), en or ''):
                return dt
        return None

    def sub(self, text):
        """Every NAMES English form in `text` written as its Dia-thìris form (dropping an English 'the' before it)."""
        if not text:
            return text
        if not hasattr(self, '_rx'):             # one pass, longest form first, so nothing is replaced twice
            self._dt = {core: dt for core, dt in reversed(self.forms)}
            self._rx = re.compile(r'(?<![\w\-])(?:[Tt]he )?(%s)(?![\w\-])' % '|'.join(re.escape(c) for c, _ in self.forms))
        return self._rx.sub(lambda m: self._dt[m.group(1)], text)


# ---------------------------------------------------------------------------------------------- helpers

HEX = re.compile(r'#[0-9a-fA-F]{6}')
AZ_GROUPS = {'capital', 'city', 'fort', 'monastery', 'caravanserai', 'trading_post', 'town', 'village', 'hamlet'}
AZ_FORMS = ['Polytheism', 'Monotheism', 'Dualism', 'Pantheism', 'Non-theism', 'Shamanism', 'Animism',
            'Ancestor Worship', 'Nature Worship', 'Totemism', 'Cult', 'Dark Cult', 'Sorcery', 'Heresy']
ZONE_TYPES = [(r'invasion|war|conquest|front|feud|raid|host|siege|battle', 'Invasion'),
              (r'rebel|rising|strike', 'Rebels'),
              (r'faith|proselyt|mission', 'Proselytism'),
              (r'plague|disease|cough|sick', 'Disease'),
              (r'fault|tremor|rending|crack', 'Fault'),
              (r'tsunami|wave|swell', 'Tsunami'),
              (r'flood|drown', 'Flood'),
              (r'famine|drought|dearth|hunger|storm|disaster|dry', 'Disaster')]
UNIT_NAMES = {'infantry', 'cavalry', 'riflemen', 'artillery', 'fleet'}


def hexcolor(s):
    m = HEX.search(s or '')
    return m.group(0).lower() if m else None


def era_year(date):
    """'30 an Lùnastal, GE 4,603' -> 4603 (the first year number after the era abbreviation)."""
    m = re.search(r'\b[A-Z]{2}\s+(-?[\d,]+)', date or '')
    return int(m.group(1).replace(',', '')) if m else None


def cites(x):
    c = x.get('cites') or []
    return 'cites: ' + ', '.join(c) if c else None


def joined(*parts):
    return ' · '.join(p for p in parts if p)


# ---------------------------------------------------------------------------------------------- the annals


def load_events():
    """Event id -> (title, date) of every age's annals (eras/age_<K>/atlas.json, as the Atlas shows them)."""
    out = {}
    for k in AGES:
        p = os.path.join(ERAS, 'age_%s' % k, 'atlas.json')
        if os.path.exists(p):
            for e in json.load(open(p, encoding='utf-8'))['events']:
                out[e['id']] = (re.sub(r'<[^>]+>', '', e.get('title') or '').strip(), e.get('date') or '', e.get('place'), k)
    return out


def short_date(date):
    """'20 am Faoilleach, VE 1' -> 'VE 1'."""
    m = re.search(r'\b([A-Z]{2})\s+(-?[\d,]+)', date or '')
    return '%s %s' % (m.group(1), m.group(2)) if m else (date or '')


def sentence(text):
    """A note's sentence: capital first letter, a full stop at the end."""
    text = re.sub(r'\s+', ' ', text or '').strip().rstrip(';,:')
    if not text:
        return ''
    if text[0].islower():
        text = text[0].upper() + text[1:]
    if not re.search(r'[.!?]["”’)]?$', text):
        text += '.'
    return text


BUILD_CLAUSE = re.compile(r"gazetteer|\bplaced (?:on|at|near|in|by)\b|\bnot a later town\b|\b(?:is|are) drawn(?:,| from| as| here)|"
                          r"\bmaster\b|\bspec\b|\bdraft\b|\bfeature \d|\bburgs? \d|\bcells? \d|\bprovinces? \d|\bengine\b|"
                          r"\bNAMES\b|\bPLAN\b|\bApp\.|\b[IVX]+-\d{4}|\binferred\b|\b(?:is|are) drawn\.?$", re.I)


def clean(text):
    """The draft's prose without its build talk: "(inferred)", ids, "the snapshot", and any clause about where or how
    a thing is drawn or sourced."""
    text = re.sub(r'\s*\((?:inferred|feature \d+|cells? \d+|burgs? \d+|[IVX]+-\d{4}[a-z]?)[^)]*\)', '', text or '')
    text = re.sub(r'\b(standing |a ruin |ruins )?at the snapshot\b', lambda m: (m.group(1) or '') + 'at the close of the age', text)
    text = re.sub(r'\bthe snapshot\b', 'the close of the age', text)
    out = []
    for sent in re.split(r'(?<=[.!?])\s+', text):
        keep = [c for c in sent.split(';') if not BUILD_CLAUSE.search(c.strip().rstrip('.'))]
        if keep:
            t = ';'.join(keep).strip()
            if t and not re.search(r'[.!?]["”’)]?$', t) and re.search(r'[.!?]["”’)]?$', sent):
                t += '.'
            out.append(t)
    return ' '.join(t for t in out if t)


def article(word):
    return 'an' if re.match(r'(?i)[aeiouàèìòù]', word or '') else 'a'


def group_for(kind, pop):
    k = (kind or '').lower()
    if k in AZ_GROUPS and k != 'capital':
        return k
    table = {'large village': 'village', 'hearth': 'hamlet', 'watch-tower': 'fort', 'flint pit': 'hamlet',
             'gathering-ground': 'hamlet', 'camp': 'hamlet'}
    if k in table:
        return table[k]
    if re.search(r'post|fort|tower|barrack|garrison', k):
        return 'fort'
    if re.search(r'guest-house|shrine|temple|lodge', k):
        return 'monastery'
    if re.search(r'camp|shelter|fair|landing|hearth|dwelling|residency|store', k):
        return 'hamlet' if pop < 1000 else 'village'
    if pop < 150:
        return 'hamlet'
    if pop < 2000:
        return 'village'
    if pop < 5000:
        return 'town'
    return 'city'


def state_form(p):
    f = (p.get('form') or '').lower()
    if re.search(r'monarch|king|crown|queen', f):
        return 'Monarchy', 'Kingdom'
    if re.search(r'keeper|custod|hall|priest|order|slab', f):
        return 'Theocracy', 'Theocracy'
    if re.search(r'council|moot|guild|league|republic|assembly', f):
        return 'Republic', 'Republic'
    if re.search(r'no ruler|landings|headman|families|hearths|kindred|people', f):
        return 'Anarchy', 'Tribes'
    return 'Monarchy', 'Kingdom'


def relation(rel):
    r = (rel or '').lower()
    if re.search(r'suzerain|vassal|sworn|tributary|subject', r):
        return 'Suzerain'
    if re.search(r'war|hostile|enem', r) and not re.search(r'ended|over|peace', r):
        return 'Enemy'
    if re.search(r'truce|unreconciled|defeated|reckoning|suspic', r):
        return 'Suspicion'
    if re.search(r'rival', r):
        return 'Rival'
    if re.search(r'\ball', r):
        return 'Ally'
    if re.search(r'kin|trade|friend|shared', r):
        return 'Friendly'
    if re.search(r'unknown', r):
        return 'Unknown'
    return 'Neutral'


def religion_type(t):
    t = t or ''
    for az in ('Folk', 'Organized', 'Cult', 'Heresy'):
        if az.lower() in t.lower():
            return az, True
    return 'Folk', False


def religion_form(form, fallback):
    f = (form or '').lower()
    for az in AZ_FORMS:
        if az.lower() in f:
            return az
    if 'ancestor' in f:
        return 'Ancestor Worship'
    if 'hearth' in f or 'spirit' in f:
        return 'Animism'
    return fallback


def deity_of(d):
    if not d:
        return None
    d = re.split(r'[;,(]', d)[0].strip()
    return re.sub(r'\s+first$', '', d)


# ---------------------------------------------------------------------------------------------- one age


class Converter:
    def __init__(self, K, master, names, prose):
        self.K, self.n, self.M, self.N = K, NUM[K], master, names
        self.d = json.load(open(os.path.join(DRAFTS, 'age_%s.json' % K), encoding='utf-8'))
        assert self.d.get('schema') == 'era-spec-draft/1', 'age %s: schema %s' % (K, self.d.get('schema'))
        # the drafts give people; the kinds and town works below are read at the sizes they were set for
        self.kind_scale = self.d.get('population_scale', {}).get('kind_scale', 1.0)
        self.log = defaultdict(list)          # section -> [lines]
        self.counts = Counter()
        self.spec = {}
        self.polity_name = {}
        self.canon_names()

    # -------- the age's own names for its towns and things
    def canon_names(self):
        """site_name {master burg id: name} and new_name {place id: name} from the age's gazetteer, places.json and
        PLAN_names.json; plan {English key: dt} from PLAN_names.json."""
        adir = os.path.join(ERAS, 'age_%s' % self.K)
        self.site_name, self.new_name, self.plan, self.gaz, self.place_site = {}, {}, {}, {}, {}
        gaz = {}
        for f in sorted(glob.glob(os.path.join(adir, 'gazetteer', '*.json'))):
            g = json.load(open(f, encoding='utf-8'))
            if isinstance(g, dict):
                gaz.update(g)
        for k, v in gaz.items():
            if isinstance(v, dict) and v.get('name') and k.isdigit():
                (self.new_name if int(k) >= 1000 else self.site_name)[int(k)] = v['name']
        pp = os.path.join(adir, 'places.json')
        places = json.load(open(pp, encoding='utf-8')) if os.path.exists(pp) else {}
        # the age's gazetteer entry of each town: a master burg's by its id (or by the place standing at its site), a
        # new town's by its place id when the gazetteer names it
        for k, v in gaz.items():
            if not (isinstance(v, dict) and k.isdigit()):
                continue
            i = int(k)
            near = re.match(r'burg:(\d+)$', (places.get('burg:%d' % i) or {}).get('near') or '')
            if i < 1000:
                self.gaz.setdefault(i, v)
            elif near:
                self.gaz[int(near.group(1))] = v
            elif v.get('name'):
                self.gaz[('new', i)] = v
        for ref, v in places.items():
            m = re.match(r'burg:(\d+)$', ref)
            if not m or not v.get('name'):
                continue
            near = re.match(r'burg:(\d+)$', v.get('near') or '')
            if near:                                   # a place at the site of a master burg in this age
                self.site_name.setdefault(int(near.group(1)), v['name'])
            else:
                self.new_name.setdefault(int(m.group(1)), v['name'])
        pn = os.path.join(adir, 'PLAN_names.json')
        for e in (json.load(open(pn, encoding='utf-8')) if os.path.exists(pn) else []):
            if str(e.get('kind', '')).lower() in PERSONAL or not e.get('dt'):
                continue
            m = re.search(r'site of burg (\d+)|\(burg (\d+) in this age\)', e.get('gloss') or '')
            if m:
                self.site_name.setdefault(int(m.group(1) or m.group(2)), e['dt'])
                pl = re.search(r'place (\d+), site of burg (\d+)', e.get('gloss') or '')
                if pl:
                    self.place_site[int(pl.group(1))] = int(pl.group(2))
            if e.get('kind') not in ('place-root', 'title', 'book', 'section-title'):
                self.plan.setdefault(Names.key(e['en']), e['dt'])
        for pid, bid in self.place_site.items():      # a place of the age standing at a master burg's site
            if str(pid) in gaz:
                self.gaz[bid] = gaz[str(pid)]

    def burg_name(self, b):
        """A kept burg's name in this age: the age's own record, else the draft's era name, else the master's."""
        return self.site_name.get(b['id']) or b.get('era_name') or b['master_name']

    # -------- notes for a reader
    def prose(self, text):
        """English prose with its proper nouns in Dia-thìris (names_convert.py's rules for this age)."""
        if not text or not isinstance(text, str):
            return ''
        if not hasattr(self, '_nc'):
            self._nc = names_convert().Converter(self.K)
        return self._nc.convert(clean(text), 'map note')

    def told(self, x, more=()):
        """'Told of in: <title> (<date>); ...' for the annals events a draft element cites (and `more`)."""
        seen, items = set(), []
        for c in list(x.get('cites') or []) + list(more):
            if c in EVENTS and c not in seen:
                seen.add(c)
                t, dt = EVENTS[c][:2]
                items.append('%s (%s)' % (t.rstrip('.'), short_date(dt)) if dt else t.rstrip('.'))
        return ('Told of in: ' + '; '.join(items) + '.') if items else ''

    def note(self, section, msg):
        self.log[section].append(msg)

    def pnote(self, x, *parts, prose_keys=('note',), lead=(), more=()):
        """A note for a reader: `lead` sentences, the draft's prose (`prose_keys`), `parts` sentences, then the
        annals events it is told of in. Never ids or build terms."""
        out = [sentence(self.prose(t)) for t in lead]
        out += [sentence(self.prose(x.get(k))) for k in prose_keys if isinstance(x.get(k), str)]
        out += [sentence(p) for p in parts]
        out.append(self.told(x, more))
        seen = []
        for t in out:
            if t and t not in seen:
                seen.append(t)
        return ' '.join(seen)

    def name(self, x, what, master_name=None, en_key='name_en'):
        """Map name for a draft element (see the module docstring); logs every fallback."""
        if x.get('name'):
            return x['name']
        en = x.get(en_key) or ''
        dt = self.N.lookup(en)
        if dt:
            self.counts['name from NAMES.json'] += 1
            return dt
        dt = self.plan.get(Names.key(en))
        if dt:
            self.counts['name from the age\'s PLAN_names.json'] += 1
            return dt
        if master_name:
            self.counts['name kept from the master'] += 1
            return master_name
        self.counts['name from the English gloss'] += 1
        self.note('names', '%s: no Dia-thìris name; English gloss used: "%s"' % (what, self.N.sub(en)))
        return self.N.sub(en)

    # -------- places
    def place_cell(self, at, where):
        """The master pack cell of {burg|new_burg|marker|cell}."""
        if 'cell' in at:
            return at['cell']
        if 'burg' in at:
            return self.M.burgs[at['burg']]['cell']
        if 'new_burg' in at:
            return self.new_cells[at['new_burg']]
        if 'marker' in at:
            mid = at['marker']
            if isinstance(mid, str):
                return self.new_marker_cells[mid]
            return self.M.markers[mid]['cell']
        raise ValueError('%s: no place in %r' % (where, at))

    def burg_ref(self, at):
        if 'burg' in at:
            return at['burg']
        if 'new_burg' in at:
            return self.place_ids[at['new_burg']]
        return None

    # -------- the whole age
    def run(self):
        d, M = self.d, self.M
        snap = d['snapshot']
        era = d['era']
        self.spec = {
            'name': 'Diathir_Age_%s' % self.K,
            'seed': 'era-age-%s' % self.K,
            'comment': 'Made by eras/engine/convert_draft.py from eras/specs_draft/age_%s.json (%s). Do not edit; '
                       'edit the draft and convert again.' % (self.K, d['schema']),
            'master': MASTER_REL,
            'lore': {'name': 'Dia-thìr', 'description': '%s · %s' % (d['age_name']['name'], snap_date(snap['date'], era['abbr'])),
                     'calendar': {'year': snap_year(snap['date'], era['abbr']),
                                  'era': re.sub(r'^the\s+', '', era['name_en']).strip(), 'eraShort': era['abbr']}},
        }
        # units and geography (scale, latitude, longitude, coordinates) are the master's: the spec sets none
        self.province_culture = {}
        self.new_cells = {nb['key']: nb['cell'] for nb in d['new_burgs']}
        self.new_marker_cells = {}
        self.place_ids = {}
        for nb in d['new_burgs']:
            m = re.search(r'N(\d+)$', nb['key'])
            self.place_ids[nb['key']] = 1000 * self.n + int(m.group(1))
        self.cultures()
        self.religions()
        self.states()           # decides which polities are states (needed by burgs)
        self.burgs()
        self.provinces()
        self.diplomacy()
        self.military()
        self.markers()          # before routes and labels (a route may run to a new marker)
        self.routes()
        self.zones()
        self.labels()
        self.misc()
        return self.spec

    def keep_master_cells(self, shires, ref, majority, what):
        """Age VII is the master: a shire whose master majority already is the draft's keeps its master cells
        (with their minorities); only the shires that differ are assigned whole. Other ages assign every shire."""
        shires = sorted(shires)
        if self.K != 'VII' or not isinstance(ref, int):
            return shires
        diff = [p for p in shires if majority.get(p) != ref]
        if len(diff) < len(shires):
            self.counts['%s: shires keeping the master\'s cells' % what] += len(shires) - len(diff)
        return diff

    # -------- cultures
    def cultures(self):
        d, M = self.d, self.M
        out = {'edit': {}, 'add': [], 'assign': [], 'remove': {}}
        used_master = set()
        self.culture_ref = {}
        covered = set()
        for c in d['cultures']:
            mc = c.get('master_culture')
            nm = self.name(c, 'culture %s' % c['key'], M.cultures[mc]['name'] if mc not in (None, 0) else None)
            if mc not in (None, 0) and mc not in used_master:
                used_master.add(mc)
                self.culture_ref[c['key']] = mc
                if nm != M.cultures[mc]['name']:
                    out['edit'][str(mc)] = {'name': nm}
            elif c['provinces']:
                key = 'c_' + c['key']
                base = M.cultures[mc] if mc is not None else M.cultures[2]
                out['add'].append({'key': key, 'name': nm, 'base': base.get('base', 43), 'type': base.get('type') or 'Naval',
                                   'shield': base.get('shield') or 'round', 'code': re.sub(r'[^A-Za-zÀ-ÿ]', '', nm)[:2]})
                self.culture_ref[c['key']] = '@' + key
                if mc == 0:
                    self.note('cultures', '%s: master culture 0 is the wildland slot, so the people are added as a '
                                          'culture of their own' % nm)
            else:
                self.note('cultures', '%s: holds no land at the snapshot; not on the map' % nm)
                continue
            if c['provinces']:
                sh = self.keep_master_cells(c['provinces'], self.culture_ref[c['key']], M.shire_culture, 'culture')
                if sh:
                    out['assign'].append({'culture': self.culture_ref[c['key']], 'shires': sh})
                for p in c['provinces']:
                    self.province_culture[p] = self.culture_ref[c['key']]
                covered.update(c['provinces'])
        rest = sorted(set(M.provinces) - covered)
        if rest and self.K == 'VII':
            self.note('cultures', 'shires in no culture of the draft keep the master\'s cells: %s' % rest)
        elif rest:
            out['assign'].insert(0, {'culture': 0, 'shires': rest})
            self.note('cultures', 'shires with no people in the draft (culture 0, unpeopled): %s' % rest)
        main = self.culture_ref.get(d['cultures'][0]['key'], 2)
        main_num = main if isinstance(main, int) else 2
        for c in M.cultures:
            if c['i'] and c['i'] not in used_master:
                out['remove'][str(c['i'])] = main_num if main_num in used_master else 0
                self.note('cultures', 'master culture %d (%s) is not on this map (removed)' % (c['i'], c['name']))
        # a culture 'removed' onto another that is also listed would move nothing: the assign already covers all
        self.spec['cultures'] = {k: v for k, v in out.items() if v}

    # -------- religions
    def religions(self):
        d, M = self.d, self.M
        out = {'edit': {}, 'add': [], 'assign': [], 'remove': {}}
        used = set()
        self.faith_ref = {}
        self.order_name = {}
        covered = set()
        for f in d['faiths']:
            for o in f.get('orders') or []:
                if o.get('key'):
                    self.order_name[o['key']] = o.get('name') or self.N.lookup(o.get('name_en')) or None
            for o in f.get('bodies') or []:
                if o.get('key'):
                    self.order_name[o['key']] = o.get('name') or self.N.lookup(o.get('name_en')) or None
            mr = f.get('master_religion')
            if mr == 0:
                self.faith_ref[f['key']] = 0
                sh = self.keep_master_cells(f['provinces'], 0, M.shire_religion, 'faith')
                if sh:
                    out['assign'].append({'religion': 0, 'shires': sh})
                covered.update(f['provinces'])
                continue
            nm = self.name(f, 'faith %s' % f['key'], M.religions[mr]['name'] if mr else None)
            typ, ok = religion_type(f.get('type'))
            if not ok:
                self.note('faiths', '%s: type "%s" is not one of Azgaar\'s (Folk, Organized, Cult, Heresy); drawn as %s'
                          % (nm, f.get('type'), typ))
            if mr and mr not in used:
                used.add(mr)
                mrel = M.religions[mr]
                form = religion_form(f.get('form'), mrel.get('form'))
                val = {k: v for k, v in (('name', nm), ('type', typ), ('form', form), ('deity', deity_of(f.get('deity'))))
                       if v != mrel.get(k)}
                if val:
                    out['edit'][str(mr)] = val
                self.faith_ref[f['key']] = mr
            elif f['provinces']:
                key = 'f_' + f['key']
                out['add'].append({'key': key, 'name': nm, 'type': typ, 'form': religion_form(f.get('form'), 'Animism'),
                                   'deity': deity_of(f.get('deity')), 'expansion': 'culture',
                                   'code': re.sub(r'[^A-Za-zÀ-ÿ]', '', nm)[:2]})
                self.faith_ref[f['key']] = '@' + key
            else:
                self.note('faiths', '%s: held in no shire at the snapshot; not on the map' % nm)
                continue
            if f['provinces']:
                sh = self.keep_master_cells(f['provinces'], self.faith_ref[f['key']], M.shire_religion, 'faith')
                if sh:
                    out['assign'].append({'religion': self.faith_ref[f['key']], 'shires': sh})
                covered.update(f['provinces'])
            n_orders = len(f.get('orders') or []) + len(f.get('bodies') or [])
            if n_orders:
                self.note('faiths', '%s: %d orders/bodies are not faiths of their own on the map; each burg\'s order '
                                    'or body is named in its note' % (nm, n_orders))
        rest = sorted(set(M.provinces) - covered)
        if rest and self.K == 'VII':
            self.note('faiths', 'shires in no faith of the draft keep the master\'s cells: %s' % rest)
        elif rest:
            out['assign'].insert(0, {'religion': 0, 'shires': rest})
            self.note('faiths', 'shires with no faith in the draft (religion 0): %s' % rest)
        for r in M.religions:
            if r['i'] and r['i'] not in used:
                out['remove'][str(r['i'])] = next(iter(sorted(used)), 0) if used else 0
                self.note('faiths', 'master faith %d (%s) is not on this map (removed)' % (r['i'], r['name']))
        self.spec['religions'] = {k: v for k, v in out.items() if v}

    # -------- states
    def states(self):
        d, M = self.d, self.M
        pp = d['province_polity']
        prov_of = defaultdict(list)
        for p, k in pp.items():
            prov_of[k].append(int(p))
        self.prov_of = prov_of
        burgs_of = defaultdict(list)
        for b in d['burgs']:
            burgs_of[b['polity']].append(b)
        lst = []
        self.state_ref = {}
        self.capital_of = {}
        arms = {a['polity']: a for a in d.get('arms', []) if a.get('polity')}
        coa_by_blazon = self.blazon_coas()
        for p in d['polities']:
            k = p['key']
            provs = sorted(prov_of.get(k, []))
            cap = self.burg_ref(p['capital']) if p.get('capital') else None
            if cap is None:
                cands = sorted(burgs_of.get(k, []), key=lambda b: -b['population'])
                if cands:
                    cap = cands[0]['id']
                    self.note('states', '%s: no capital in the draft; its largest burg %d (%s) is drawn as the capital'
                              % (p.get('name') or p['name_en'], cap, cands[0]['master_name']))
            if not provs and cap is None:
                self.note('states', '%s: holds no shire and has no seat at the snapshot; not drawn as a state'
                          % (p.get('name') or p['name_en']))
                continue
            if not provs:
                self.note('states', '%s: holds no shire; drawn as a state of its capital\'s cell alone' % (p.get('name') or p['name_en']))
            nm = p.get('name') or self.N.lookup(p['name_en']) or self.N.contained(p['name_en'])
            if not nm:
                cb = self.M.burgs.get(cap)
                nm = self.era_burg_name(cap) if cb else p['name_en']
                self.note('names', 'polity %s: no Dia-thìris name; named after its capital, "%s"' % (k, nm))
            form, form_name = state_form(p)
            st = {'key': k, 'name': nm, 'fullName': nm, 'form': form, 'formName': form_name, 'capital': cap,
                  'shires': provs}
            if p.get('culture') in self.culture_ref:
                st['culture'] = self.culture_ref[p['culture']]
            col = hexcolor(p.get('color'))
            if col:
                st['color'] = col
            master_state = M.states[1]
            if self.K == 'VII' and cap == master_state['capital']:
                # the master's own state: keep its arms, taxes, treasury, regiments and campaigns
                st['base'] = 1
                st['military'] = 'keep'
                if nm == master_state.get('fullName'):
                    st['name'], st['fullName'] = master_state['name'], master_state['fullName']
                st['form'], st['formName'] = master_state['form'], master_state['formName']
            else:
                a = arms.get(k)
                coa = None
                if a and a.get('master_coa'):
                    coa = a['master_coa']
                elif a and a.get('blazon') and a['blazon'] in coa_by_blazon:
                    coa = coa_by_blazon[a['blazon']]
                if coa:
                    st['coa'] = coa
                    self.counts['state arms from the master roll'] += 1
                else:
                    st['coa'] = 'generate'
                    self.note('arms', '%s: %s; Azgaar needs arms, so they are generated (seeded)' % (
                        nm, 'no arms at the snapshot' if not (a and a.get('blazon')) else 'blazon "%s" has no master arms to copy' % a['blazon']))
            ruler = p.get('ruler') or {}
            title = self.prose(ruler.get('title')) if ruler.get('title') else ''
            if ruler.get('name'):
                rs = 'Its ruler at the close of the age: %s%s' % (ruler['name'], ', ' + title if title else '')
            else:
                rs = 'Ruled by %s' % title if title else ''
            st['note'] = self.pnote(p, rs, prose_keys=(), lead=[d.get('notes', {}).get('polities', {}).get(k)])
            self.polity_name[k] = nm
            lst.append(st)
            self.state_ref[k] = '@' + k
            self.capital_of[k] = cap
        unclaimed = sorted(int(p) for p, k in pp.items() if k not in self.state_ref)
        if unclaimed:
            self.note('states', 'neutral shires (unclaimed, or of a polity not drawn): %s' % unclaimed)
        self.spec['states'] = {'list': lst, 'cell_state': {}, 'neutral_name': M.states[0]['name']}
        if not self.d['diplomacy'] and len(lst) < 2:
            pass

    def blazon_coas(self):
        """Blazon -> master coa, from Age VII's roll (the master's arms)."""
        if not hasattr(Converter, '_blazons'):
            vii = json.load(open(os.path.join(DRAFTS, 'age_VII.json'), encoding='utf-8'))
            Converter._blazons = {a['blazon']: a['master_coa'] for a in vii.get('arms', []) if a.get('blazon') and a.get('master_coa')}
        return Converter._blazons

    def era_burg_name(self, bid):
        for b in self.d['burgs']:
            if b['id'] == bid:
                return self.burg_name(b)
        for nb in self.d['new_burgs']:
            if self.place_ids.get(nb['key']) == bid:
                return self.new_burg_name(nb, log=False)
        return self.M.burgs[bid]['name'] if bid in self.M.burgs else str(bid)

    # -------- burgs
    def burgs(self):
        d, M = self.d, self.M
        keep = sorted(b['id'] for b in d['burgs'])
        edit, add = {}, []
        pp = d['province_polity']
        cell_state = self.spec['states']['cell_state']
        capitals = set(self.capital_of.values())
        faith_diff = 0
        for b in d['burgs']:
            mb = M.burgs[b['id']]
            e = {}
            nm = self.burg_name(b)
            if nm != (b.get('era_name') or b['master_name']):
                self.note('names', 'burg %d: "%s", the age\'s own name for it (gazetteer, places.json or PLAN_names.json), '
                                   'not "%s"' % (b['id'], nm, b.get('era_name') or b['master_name']))
            if nm != mb['name']:
                e['name'] = nm
            pop = round(max(b['population'], 1) / float(M.rate), 3)
            if abs(b['population'] - mb.get('population', 0) * M.rate) > 0.5:       # more than the rounding to a person
                e['population'] = pop
            if b['id'] not in capitals:
                g = group_for(b['kind'], b['population'] / self.kind_scale)
                if g != mb.get('group'):
                    e['group'] = g
            feats = self.features(b, mb)
            if feats:
                e['features'] = feats
            prov = M.burg_province[b['id']]
            want = self.culture_ref.get(b['culture'])
            if want is not None and want != self.province_culture.get(prov):
                e['culture'] = want
            if b.get('faith') and self.faith_ref.get(b['faith']) is not None:
                prov_faith = self.province_faith(prov)
                if prov_faith is not None and prov_faith != b['faith']:
                    faith_diff += 1
            if self.K != 'VII' or b['id'] in self.gaz:
                e['note'] = self.burg_note(b, nm)
            # else Age VII (the present) keeps the master's note: the gazetteer's telling of the town as it stands
            if e:
                edit[str(b['id'])] = e
            # the burg's polity against its shire's
            owner = b['polity']
            shire_owner = pp.get(str(prov))
            if owner != shire_owner:
                cell_state[str(mb['cell'])] = self.state_ref.get(owner, 0)
                self.note('states', 'burg %d (%s): polity %s in a shire of %s; its cell goes to %s' % (
                    b['id'], nm, owner, shire_owner, owner if owner in self.state_ref else 'no state'))
        if faith_diff:
            self.note('faiths', '%d burgs keep a faith other than their shire\'s; Azgaar gives a burg the faith of its '
                                'cell, so only the note tells it' % faith_diff)
        for nb in d['new_burgs']:
            pid = self.place_ids[nb['key']]
            nm = self.new_burg_name(nb)
            a = {'key': nb['key'].replace('-', '_'), 'id': pid, 'name': nm, 'cell': nb['cell'],
                 'population': round(max(nb['population'], 1) / float(M.rate), 3),
                 'group': group_for(nb['kind'], nb['population'] / self.kind_scale),
                 'note': self.burg_note(nb, nm, new=True)}
            if nb['cell'] in M.cell_burg:
                raise ValueError('new burg %s: cell %d holds master burg %d' % (nb['key'], nb['cell'], M.cell_burg[nb['cell']]))
            if self.culture_ref.get(nb['culture']) is not None:
                a['culture'] = self.culture_ref[nb['culture']]
            add.append(a)
            shire_owner = pp.get(str(nb['province']))
            if nb['polity'] != shire_owner:
                cell_state[str(nb['cell'])] = self.state_ref.get(nb['polity'], 0)
            if pid in capitals:
                del a['group']
        self.spec['burgs'] = {'keep': keep, 'edit': edit}
        if add:
            self.spec['burgs']['add'] = add

    def new_burg_name(self, nb, log=True):
        """A new town's name: the draft's, else the age's gazetteer or places.json name for its place id, else as
        name() gives it."""
        own = self.new_name.get(self.place_ids[nb['key']])
        if not nb.get('name') and own:
            if log:
                self.counts['new burg named from the age\'s gazetteer or places.json'] += 1
            return own
        return self.name(nb, 'new burg %s' % nb['key']) if log else (nb.get('name') or self.N.lookup(nb.get('name_en')) or
                                                                  self.plan.get(Names.key(nb.get('name_en') or '')) or
                                                                  self.N.sub(nb.get('name_en')))

    def burg_note(self, b, nm, new=False):
        """A town's note: the draft's popup prose, what the town is in this age (kind, polity, role), its order or
        church, why it stands (a new town), then the events it is told of in (cited, or placed there in this age)."""
        kind = (b.get('kind') or '').strip()
        role = self.prose(b.get('role')).strip().rstrip('.')
        pol = self.polity_name.get(b.get('polity'))
        head = '%s %s' % (article(kind), kind) if kind else 'A place'
        if pol:
            head += ' of %s' % pol
        head = head[0].upper() + head[1:]
        if role and role[0].islower() and len(role.split()) <= 4 and not re.search(r'[,;:]', role) \
                and not re.match(r'(the|a|an|its|their|his|her)\b', role):
            parts = ['%s %s%s' % (article(role).capitalize(), role, ' of %s' % pol if pol else '')]
        elif re.match(r'(a|an|the)\b', role):
            parts = ['%s: %s' % (head, role)]
        elif re.match(r'its\b', role):
            parts = ['%s, known for %s' % (head, role)]
        else:
            parts = [head, role]
        on = self.order_name.get(b.get('order'))
        if on:
            parts.append('Its people keep the rite of %s' % on)
        cb = self.order_name.get(b.get('church_body'))
        if cb:
            parts.append('Its church is of %s' % cb)
        pid = self.place_ids.get(b.get('key')) if new else b['id']
        here = [i for i, (t, dt, pl, age) in EVENTS.items() if pl == 'burg:%s' % pid and age == self.K]
        g = self.gaz.get(('new', pid) if new else b['id']) or {}
        # the age's gazetteer telling of the town, else the draft's popup lines
        parts.append(g.get('history') or ('' if new else self.d.get('notes', {}).get('burgs', {}).get(str(b['id']))))
        parts.append(b.get('note'))
        if new and not g.get('history'):
            parts.append(b.get('reason'))
        if g.get('known_for'):
            parts.append('Known for %s' % g['known_for'])
        return self.pnote(b, prose_keys=(), lead=[p for p in parts if p], more=here[:6])

    def province_faith(self, prov):
        for f in self.d['faiths']:
            if prov in f['provinces']:
                return f['key']
        return None

    def features(self, b, mb):
        """Burg features: the draft's list where it gives one; hamlets and villages lose the master's town works."""
        keys = ('citadel', 'walls', 'plaza', 'temple', 'shanty')
        if b.get('features'):
            f = set(b['features'])
            want = {k: int(k in f) for k in ('citadel', 'walls', 'temple')}
        elif b.get('walls'):
            want = {'walls': 1}
        elif self.K != 'VII' and b['population'] / self.kind_scale < 1000:
            want = {k: 0 for k in keys}
        else:
            return None
        diff = {k: v for k, v in want.items() if int(mb.get(k, 0) or 0) != v}
        return diff or None

    # -------- provinces
    def provinces(self):
        d, M = self.d, self.M
        units = []
        for p in d['polities']:
            if p['key'] not in self.state_ref:
                continue
            for a in p.get('admin_units', []):
                units.append((p, a))
        # the partition: the admin list whose units cover the most shires, each at most once
        best, best_cov = None, 0
        for p, a in units + [(p, a) for p in d['polities'] if p['key'] not in self.state_ref for a in p.get('admin_units', [])]:
            us = a.get('units') or []
            cov = [x for u in us for x in u.get('provinces', [])]
            if us and len(cov) == len(set(cov)) and len(cov) > best_cov:
                best, best_cov = (p, a), len(cov)
        out = {}
        taken = set()
        if best and best_cov >= 60:
            bp, ba = best
            if bp['key'] not in self.state_ref:
                self.note('provinces', 'the provinces are the units of %s ("%s"), which is not a state at the snapshot; '
                                       'kept as the era\'s provinces' % (bp.get('name') or bp['name_en'], ba['name_en']))
            merge, edit = [], {}
            for u in ba['units']:
                sh = sorted(u.get('provinces', []))
                if not sh:
                    continue
                seat = self.burg_ref(u['seat']) if u.get('seat') else None
                name, form = self.split_form(u.get('name'))
                if not name:
                    name, form = (self.era_burg_name(seat) if seat else None), ''
                    if not name:
                        continue
                    self.counts['province named after its seat'] += 1
                val = {'name': name, 'formName': form, 'fullName': joined_name(form, name)}
                if seat is not None:
                    val['burg'] = seat
                note = self.pnote(u)
                if note or self.K != 'VII':       # never the master's (present-day) shire note in an earlier age
                    val['note'] = note
                mp = M.provinces[sh[0]]
                if len(sh) > 1:
                    merge.append(dict(val, into=sh[0], **{'from': sh[1:]}))
                else:
                    val = {k: v for k, v in val.items() if v != mp.get(k)}
                    if val:
                        edit[str(sh[0])] = val
                taken.update(sh)
            out['merge'] = merge
            out['edit'] = edit
            out['remove'] = sorted(set(M.provinces) - taken)
            if merge:
                self.note('provinces', '%d units of "%s" span several shires; merged' % (len(merge), ba['name_en']))
            if out['remove']:
                self.note('provinces', 'shires in no unit of "%s" are not provinces in this age: %s' % (ba['name_en'], out['remove']))
            used = best
        else:
            out['base'] = 'none'
            used = None
            self.note('provinces', 'no subdivision of the island in this age covers it; provinces start from none')
        add = []
        for p, a in units:
            if (p, a) == used:
                continue
            sh = set(a.get('provinces') or [])
            what = '%s: "%s" (%s)' % (p.get('name') or p['key'], a['name_en'], a['kind'])
            if a.get('units') and not sh:
                if not any(u.get('provinces') for u in a['units']):
                    self.note('provinces', '%s: %d units with no ground of their own (towns, boards, markets); in the '
                                           'burg notes only' % (what, len(a['units'])))
                    continue
                self.note('provinces', '%s: overlaps the era\'s provinces; not drawn' % what)
                continue
            if not sh:
                self.note('provinces', '%s: no shires given; not drawn' % what)
                continue
            if re.search(r'extent|not bounded', a['kind']) or sh == set(self.prov_of.get(p['key'], [])):
                self.note('provinces', '%s: the whole polity or unbounded; not drawn as a province' % what)
                continue
            if sh & taken:
                self.note('provinces', '%s: overlaps a province already drawn (shires %s); not drawn' % (what, sorted(sh & taken)))
                continue
            name, form = self.split_form(a.get('name'))
            if not name:
                cands = sorted((b for b in self.d['burgs'] if M.burg_province[b['id']] in sh), key=lambda b: -b['population'])
                if not cands:
                    self.note('provinces', '%s: no name and no burg to name it after; not drawn' % what)
                    continue
                name, form = self.burg_name(cands[0]), ''
                self.note('names', 'province "%s": no Dia-thìris name; named after its largest burg, "%s"' % (a['name_en'], name))
            v = {'key': 'u%d' % len(add), 'name': name, 'formName': form, 'fullName': joined_name(form, name),
                 'shires': sorted(sh)}
            note = self.pnote(a)
            if note:
                v['note'] = note
            add.append(v)
            taken.update(sh)
        if add:
            out['add'] = add
        self.spec['provinces'] = {k: v for k, v in out.items() if v}

    @staticmethod
    def split_form(name):
        if not name:
            return None, ''
        m = re.match(r"^(Siorrachd|Mòr-roinn|Roinn|Tighearnas|Iarlachd|Crìoch)\s+(.+)$", name)
        if m:
            return m.group(2), m.group(1)
        return name, ''

    # -------- diplomacy
    def diplomacy(self):
        d = self.d
        rows = {}
        for r in d['diplomacy']:
            a, b = r['a'], r['b']
            if a not in self.state_ref or b not in self.state_ref:
                self.note('diplomacy', '%s / %s (%s): not both states on the map; not drawn' % (a, b, r['relation']))
                continue
            rel = relation(r['relation'])
            if rel == 'Suzerain':
                sa = next((p for p in d['polities'] if p['key'] == b), {}).get('suzerain')
                if sa == a:
                    pass
                elif next((p for p in d['polities'] if p['key'] == a), {}).get('suzerain') == b:
                    a, b = b, a
            rows[frozenset((a, b))] = [self.state_ref[a], self.state_ref[b], rel]
            self.counts['diplomacy: "%s" -> %s' % (r['relation'][:40], rel)] += 1
        for p in d['polities']:
            s = p.get('suzerain')
            if s and p['key'] in self.state_ref and s in self.state_ref:
                k = frozenset((s, p['key']))
                if k in rows and rows[k][2] != 'Suzerain':
                    self.note('diplomacy', '%s / %s: "%s" in the diplomacy list, but %s is its suzerain; drawn as Suzerain/Vassal'
                              % (s, p['key'], rows[k][2], s))
                rows[k] = [self.state_ref[s], self.state_ref[p['key']], 'Suzerain']
        self.spec['diplomacy'] = list(rows.values())
        self.spec['diplomacy_default'] = 'Neutral'

    # -------- military
    def military(self):
        mil = self.d.get('military', {})
        n_hosts = 0
        for h in mil.get('hosts', []):
            if h.get('master_regiment') is not None and self.K == 'VII':
                continue
            if h.get('units') and h.get('polity') in self.state_ref:
                self.note('military', 'host "%s" with units outside the master regiments is not converted' % h.get('name'))
            n_hosts += 1
        if n_hosts:
            self.note('military', '%d hosts given only in words (no units): not drawn as regiments' % n_hosts)
        camps = mil.get('campaigns', [])
        if self.K != 'VII' and camps:
            self.note('military', '%d campaigns: their sides are people, not the map\'s states; not in the states\' '
                                  'campaign lists (battles are markers where the draft gives them)' % len(camps))
        elif camps:
            other = [c for c in camps if c.get('master_campaign') is None]
            if other:
                self.note('military', '%d campaigns besides the master\'s are not in the campaign list' % len(other))

    # -------- markers
    def markers(self):
        d, M = self.d, self.M
        mk = d['markers']
        keep = sorted(m['id'] for m in mk['master'])
        edit = {}
        for m in mk['master']:
            mm = M.markers[m['id']]
            e = {}
            if m.get('era_name') and m['era_name'] != mm.get('name'):
                e['name'] = m['era_name']
            if m.get('icon') and m['icon'] != mm.get('icon'):
                e['icon'] = m['icon']
            if self.K != 'VII':
                e['note'] = self.pnote(m)
            if e:
                edit[str(m['id'])] = e
        add = []
        for m in mk['new']:
            where = 'marker %s' % m['key']
            cell = self.place_cell(m, where)
            self.new_marker_cells[m['key']] = cell
            a = {'key': m['key'].replace('-', '_'), 'type': 'battlefields' if m.get('icon') == '⚔️' else 'custom',
                 'icon': m.get('icon') or '📍', 'name': self.name(m, where), 'cell': cell,
                 'note': self.pnote(m, more=[m['event']] if m.get('event') else [])}
            add.append(a)
        if self.K == 'VII':
            self.note('markers', 'the master\'s markers keep the master\'s notes')
        self.spec['markers'] = {'keep': keep, 'edit': edit, 'add': add}

    # -------- routes
    def routes(self):
        d = self.d
        r = d['routes']
        keep = sorted(x['id'] for x in r['master'])
        edit = {}
        for x in r['master']:
            nm = x.get('era_name') or x.get('name')
            e = {}
            if nm and nm != self.M.routes[x['id']].get('name'):
                e['name'] = nm
            if self.K != 'VII' and (x.get('note') or self.M.routes[x['id']].get('note')):
                e['note'] = self.pnote(x)         # the age's own words, never the master's (present-day) note
            if e:
                edit[str(x['id'])] = e
        add = []
        gmap = {'railways': 'roads', 'rivers': 'trails'}
        for x in r['new']:
            where = 'route %s' % x['key']
            group = gmap.get(x['group'], x['group'])
            if group != x['group']:
                self.note('routes', '%s (%s): Azgaar draws no "%s" group; drawn as %s' % (x['key'], self.N.sub(x['name_en']), x['group'], group))
            stops = []
            for pt in x['points']:
                c = self.place_cell(pt, where)
                if not stops or stops[-1] != c:
                    stops.append(c)
            if len(stops) < 2:
                self.note('routes', '%s: fewer than two distinct places; not drawn' % x['key'])
                continue
            a = {'key': x['key'].replace('-', '_'), 'name': self.name(x, where), 'group': group, 'stops': stops,
                 'note': self.pnote(x)}
            add.append(a)
        self.spec['routes'] = {'keep': keep, 'edit': edit, 'add': add}

    # -------- zones
    def zones(self):
        d, M = self.d, self.M
        keep, edit, add = [], {}, []
        for z in d['zones']:
            where = 'zone %s' % z['key']
            mz = z.get('master_zone')
            if mz is not None and mz in M.zones:
                if mz in keep:
                    self.note('zones', '%s: master zone %d is already drawn for another zone; drawn from its shires' % (z['key'], mz))
                else:
                    keep.append(mz)
                    e = {'note': self.pnote(z)} if self.K != 'VII' else {}
                    if z.get('name') and z['name'] != M.zones[mz]['name']:
                        e['name'] = z['name']
                    if e:
                        edit[str(mz)] = e
                    continue
            provs = list(z.get('provinces') or [])
            if not provs and isinstance(z.get('sides'), dict):
                provs = sorted({p for v in z['sides'].values() for p in v})
                self.note('zones', '%s: the front is drawn as the ground of all its sides (%d shires)' % (z['key'], len(provs)))
            a = {'key': z['key'].replace('-', '_'), 'name': self.name(z, where), 'type': zone_type(z['type']),
                 'note': self.pnote(z)}
            if provs:
                a['shires'] = sorted(provs)
            if z.get('cells'):
                a['cells'] = z['cells']
            if not provs and not z.get('cells'):
                if z.get('sea') or z['type'] == 'sea':
                    dirs = self.sea_directions(z)
                    a['water_box'] = [self.sea_box(k) for k in dirs]
                    self.note('zones', '%s: a sea zone with no cells in the draft; drawn on the coastal water to the %s '
                                       '(from its name, its sea and the age\'s mist land changes)' % (z['key'], ' and '.join(dirs)))
                else:
                    self.note('zones', '%s (%s): no ground in the draft; not drawn' % (z['key'], a['name']))
                    continue
            if a['type'] == 'Custom':
                a['color'] = 'url(#hatch4)'
            add.append(a)
        # land changes the engine cannot draw as land: drowned ground becomes a Flood zone and a label
        for i, lc in enumerate(d.get('land_changes', [])):
            txt = lc.get('what', '')
            if re.search(r'under the sea|drowned strand|drowned|let flood|flooded', txt) and not re.search(r'^None|is already an island', txt):
                cells = self.cells_named(txt)
                if not cells:
                    self.note('land', 'land change %d ("%s"): no place on the map to hang it on' % (i + 1, txt[:80]))
                    continue
                nm = self.N.contained(txt, everything=True) or self.N.lookup(txt)
                place = self.M.burgs[self.M.cell_burg[cells[0]]]['name']
                a = {'key': 'land%d' % (i + 1), 'name': nm or place, 'type': 'Flood',
                     'around': {'cells': cells, 'steps': 2},
                     'note': self.pnote(lc, 'Ground the sea has taken', prose_keys=())}
                add.append(a)
                if nm:
                    self.spec.setdefault('labels', {'add': []})['add'].append({'text': nm, 'cell': cells[0], 'fontSize': 12})
                self.note('land', 'land change %d: "%s" -- no land/water flip; a Flood zone%s instead' % (
                    i + 1, txt[:90], ' and the label "%s"' % nm if nm else ''))
            else:
                self.note('land', 'land change %d: "%s" -- not drawn (the engine keeps the master\'s land, biomes and rivers)'
                          % (i + 1, txt[:110]))
        self.spec['zones'] = {'keep': keep, 'edit': edit, 'add': add}

    SEA_DIRS = ('north', 'east', 'south', 'west')

    def sea_directions(self, z):
        """Where a sea zone lies: the directions its English name gives (else its `sea`), with those of the age's
        land changes about the mist when the zone is the mist (Manannan's mist lies north-about and east)."""
        found = lambda t: [k for k in self.SEA_DIRS if re.search(r'\b%s' % k, (t or '').lower())]  # noqa: E731
        dirs = found(z.get('name_en')) or found(z.get('sea')) or found(z.get('note'))
        if re.search(r'mist', (z.get('name_en') or '') + (z.get('note') or ''), re.I):
            for lc in self.d.get('land_changes', []):
                if re.search(r'mist', lc.get('what', ''), re.I):
                    dirs += [k for k in found(lc['what']) if k != 'west' or 'west' in dirs]
        stale = [k for k in found(z.get('sea')) if k not in dirs]
        if stale:
            self.note('zones', '%s: its `sea` says %s, its name %s; the name is followed' % (
                z['key'], '/'.join(stale), '/'.join(found(z.get('name_en'))) or '(none)'))
        return sorted(set(dirs), key=self.SEA_DIRS.index) or ['west']

    def sea_box(self, k):
        x0, y0, x1, y1 = self.M.bbox
        W, H = self.M.width, self.M.height
        return {'north': [0, 0, W, y0 + 15], 'south': [0, y1 - 15, W, H],
                'east': [x1 - 15, 0, W, H], 'west': [0, 0, x0 + 25, H]}[k]

    def nw_port(self):
        """The north-westernmost port standing in this age (by its master position)."""
        ports = [b for b in self.d['burgs'] if self.M.burgs[b['id']].get('port')]
        b = min(ports, key=lambda b: self.M.burgs[b['id']]['x'] + 2 * self.M.burgs[b['id']]['y'])
        return b

    def cells_named(self, txt):
        """Cells of the burgs whose master or era names appear in the text."""
        out = []
        texts = (txt, self.N.sub(txt))
        found = lambda nm: nm and any(re.search(r'(?<![\w\-])%s(?![\w\-])' % re.escape(nm), t) for t in texts)  # noqa: E731
        for b in self.d['burgs'] + [{'id': k, 'master_name': v['name']} for k, v in self.M.burgs.items()]:
            for nm in {b.get('era_name'), b.get('master_name')}:
                if found(nm):
                    c = self.M.burgs[b['id']]['cell']
                    if c not in out:
                        out.append(c)
        if not out:                              # else a marker of the age (master or new) named in the text
            for m in self.d['markers']['master']:
                if found(m.get('era_name')) or found(m.get('master_name')):
                    out.append(self.M.markers[m['id']]['cell'])
            for m in self.d['markers']['new']:
                if found(m.get('name') or self.N.lookup(m.get('name_en'))):
                    out.append(self.new_marker_cells[m['key']])
        return sorted(set(out), key=out.index)

    # -------- labels
    def labels(self):
        add = self.spec.get('labels', {}).get('add', [])
        for l in self.d.get('labels', []):
            if not l.get('text') and re.match(r'the departed\b', l.get('text_en') or ''):
                # the departed sailed from the north-west ports, north-about: the label is the Setting-Out there
                b = self.nw_port()
                text = self.N.lookup('the Setting-Out')
                add.append({'text': text, 'cell': self.M.burgs[b['id']]['cell'], 'fontSize': 14,
                            'note': self.pnote(l, prose_keys=('text_en',))})
                self.note('labels', 'label "%s": no Dia-thìris text; drawn as "%s" (the Setting-Out, NAMES.json) at the '
                                    'north-westernmost port, %s (the fleet went north-about)' % (
                                        l['text_en'], text, b.get('era_name') or b['master_name']))
                continue
            if not l.get('text'):
                self.note('labels', 'label "%s": no Dia-thìris text; not drawn' % self.N.sub(l['text_en']))
                continue
            add.append({'text': l['text'], 'cell': self.place_cell(l['at'], 'label'), 'fontSize': 14,
                        'note': self.pnote(l, prose_keys=('text_en',))})
        if add:
            self.spec['labels'] = {'add': add}

    # -------- the rest
    def misc(self):
        d, M = self.d, self.M
        self.spec['economy'] = {'mode': 'prune'}
        self.spec['journeys'] = {'keep': [j.get('i', k) for k, j in enumerate(M.journeys)] if self.K == 'VII' else []}
        if self.K != 'VII':
            self.note('map', 'the master\'s journey (%s) is later than this age; dropped' % ', '.join(j.get('name', '?') for j in M.journeys))
            master_pop = sum(b.get('population', 0) for b in M.burgs.values())
            era_pop = (sum(b['population'] for b in d['burgs']) + sum(nb['population'] for nb in d['new_burgs'])) / float(M.rate)
            people = d.get('population_scale', {}).get('people')
            if people:      # the whole island given outright: the country holds what the towns do not
                scale = round(max(0.002, min(1.0, (people / float(M.rate) - era_pop) / M.rural)), 4)
                self.note('map', 'rural population scaled by %.4f, so the island holds some %s people (%s of them in its '
                                 'towns)' % (scale, format(people, ','), format(int(round(era_pop * M.rate)), ',')))
            else:
                scale = round(max(0.002, min(1.0, era_pop / master_pop)), 4)
                self.note('map', 'rural population scaled by %.4f (the era\'s town population over the master\'s)' % scale)
            self.spec['rural_population'] = {'scale': scale}
            self.note('map', 'the master\'s markets, goods and deals are pruned to this age\'s burgs (Azgaar\'s economy has no era)')
        self.note('map', 'draft popup prose (notes.polities, notes.burgs, roles, reasons, notes) carried into the map notes, '
                         'proper nouns in Dia-thìris; each note ends with the annals events it is told of in')


# a snapshot dated in the next era's reckoning (Age IV closes on the eve of the Crossing, AE 1): the same day in the
# age's own era, for the map's calendar
SAME_DAY = {('AE', 1): ('LE', 1820)}


def snap_date(date, abbr):
    """The snapshot date for the map's description: without its English aside, unless it is dated in another era's
    reckoning (then the aside says which day it is)."""
    m = re.search(r'\b([A-Z]{2})\s+(-?[\d,]+)', date or '')
    return date if m and m.group(1) != abbr else plain_date(date)


def snap_year(date, abbr):
    m = re.search(r'\b([A-Z]{2})\s+(-?[\d,]+)', date or '')
    if m and m.group(1) != abbr:
        return SAME_DAY.get((m.group(1), int(m.group(2).replace(',', ''))), (abbr, era_year(date)))[1]
    return era_year(date)


def plain_date(date):
    """An annals date without its English aside: '4 am Faoilleach, LE 1,820 (the eve of ...)' -> '4 am Faoilleach, LE 1,820'."""
    return re.sub(r'\s*\([^)]*\)', '', date).strip() if date else date


def joined_name(form, name):
    return '%s %s' % (form, name) if form else name


def zone_type(t):
    t = (t or '').lower()
    for rx, az in ZONE_TYPES:
        if re.search(rx, t):
            return az
    return 'Custom'


# ---------------------------------------------------------------------------------------------- main

def write_notes(results):
    path = os.path.join(OUT, 'CONVERT_NOTES.md')
    manual = ''
    if os.path.exists(path):
        txt = open(path, encoding='utf-8').read()
        if MANUAL in txt:
            manual = txt.split(MANUAL, 1)[1]
    out = ['# Converting the era drafts to engine specs', '',
           'Written by `eras/engine/convert_draft.py` from `eras/specs_draft/age_<K>.json` (era-spec-draft/1) into '
           '`eras/specs/age_<K>.json`. Each age lists what the engine could not draw as the draft asks, and how it was '
           'drawn instead. Rerun the converter after changing a draft; the part below the marker at the end is kept.', '',
           '## Rules for every age', '',
           '- **Names.** The draft\'s Dia-thìris `name`; else the NAMES.json form of the English name; else the master\'s '
           'name for an element the master already names; else the English gloss, with NAMES.json forms written as '
           'their Dia-thìris (`dt`) form. Polities with no name take a NAMES.json name found in their English '
           'description, else their capital\'s name.',
           '- **Notes** are for a reader of the map: the drafts\' English prose (what the place or thing is in the age), '
           'proper nouns in Dia-thìris by eras/quality/names_convert.py (humans\' names as they are), then "Told of in:" '
           'and the annals events cited, by title and date. No ids, no build terms. A town the age\'s own record names '
           '(gazetteer, places.json, PLAN_names.json) takes that name.',
           '- **Land.** The engine does not turn land into water or back. Drowned ground is a Flood zone (and a label '
           'where NAMES.json names it); biome, river and coast changes are logged and not drawn.',
           '- **Place ids.** New burgs take 1000×K+n from their draft key `<Age>-N<n>`.',
           '- **Provinces.** The era\'s provinces are the admin list that partitions the most shires (merged where a unit '
           'spans shires); other non-overlapping holdings are added; unbounded or overlapping ones are logged.',
           '- **Economy.** `prune`: markets move to the largest burg left or close; no `add_markets` (it clears every deal).',
           '- **Settings.** Distance scale, geography and coordinates are the master\'s (the spec overrides none); '
           'rebuild every age after the master changes.', '']
    for K, conv in results:
        out += ['## Age %s' % K, '']
        if conv.counts:
            out.append('Counts: ' + '; '.join('%s %d' % kv for kv in sorted(conv.counts.items())) + '.')
            out.append('')
        for sec in sorted(conv.log):
            items = conv.log[sec]
            out.append('**%s**' % sec)
            out.append('')
            shown = items if len(items) <= 25 else items[:25] + ['… and %d more' % (len(items) - 25)]
            out += ['- ' + x for x in shown]
            out.append('')
    out += [MANUAL]
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + (manual if manual else '\n'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ages', nargs='*', default=AGES)
    ap.add_argument('--prose-notes', action='store_true', help='accepted for old scripts; the prose is always carried')
    a = ap.parse_args()
    EVENTS.update(load_events())
    master = Master(MASTER)
    names = Names(os.path.join(ERAS, 'NAMES.json'))
    os.makedirs(OUT, exist_ok=True)
    results = []
    for K in AGES:
        conv = Converter(K, master, names, True)
        spec = conv.run()
        if K in a.ages:
            path = os.path.join(OUT, 'age_%s.json' % K)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(spec, fh, ensure_ascii=False, indent=1)
            print('wrote %s: %d states, %d burgs kept + %d new, %d markers kept + %d new, %d routes kept + %d new, %d zones'
                  % (os.path.relpath(path), len(spec['states']['list']), len(spec['burgs']['keep']),
                     len(spec['burgs'].get('add', [])), len(spec['markers']['keep']), len(spec['markers']['add']),
                     len(spec['routes']['keep']), len(spec['routes']['add']),
                     len(spec['zones']['keep']) + len(spec['zones']['add'])))
        results.append((K, conv))
    write_notes(results)


if __name__ == '__main__':
    main()
