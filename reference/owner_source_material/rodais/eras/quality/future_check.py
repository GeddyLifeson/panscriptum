"""future_check.py -- a book speaks only of its own present and its past (the owner's rule, permanent canon).

    "If a book is writing about its history in the legendarium, it doesn't reference events into the future.
     Books should only talk about their present and their past."

    python future_check.py master          # the Telling of the Making and the seven Books of the master legendarium
    python future_check.py IV              # Age IV's era legendarium (book, appendices, gazetteer, era annals)
    python future_check.py eras            # every age's era legendarium
    python future_check.py path/to/file.md IV   # one file, told as at the close of Age IV
    python future_check.py master --allowed     # also print the hits the allow-list lets stand

A text told within age K (the master Book of age K; everything in eras/age_K/) may name only what stands by the end
of age K. An era annals entry may not look past its own date. The Telling of the Making is told within the First
Age (the Keeper of the Kin gave it in the grove of Doire ghlas) and is held to Age I. Per line it flags:

  token    a {{date:}}/{{year:}} token for an event of a later age (a later day, for an annals entry), a
           {{reckon:}} whose years fall in a later age, a {{place:burg:N}} for a town founded in a later age
  era      a later age's or era's name or abbreviation (VE GE FE LE AE SE DE, "the Holy Age", "Linn an Teine", ...),
           from reckoning.AGES, build_book.AGE_NAMES and the kind age/era entries of eras/NAMES.json
  name     a proper name of eras/NAMES.json whose first-attested event (`first`) is in a later age
  person   a person of eras/PEOPLE.json whose first event is in a later age
  burg     the name of a town founded in a later age (the master gazetteer's founded_age; an era's own gazetteer
           and places.json for its declared towns)
  phrase   a forward-looking phrase: "ages later", "in time to come", "was to become", "what became", "would later",
           "one day would", "long afterward", "as would be seen", "the Library would" ...

The master appendices, gazetteer and annals are the Library's reference as of the present (DE 27) and may span every
age; they are not held to this rule, except that an annals entry may not foreshadow past its own day (the phrase list
only, reported by `python future_check.py master-annals`, not failed).

False positives go in future_allow.txt beside this file: one per line,
    <file, relative to rodais/> | <rule> | <the exact matched text> | <a context snippet on the same line> | <reason>
A hit is allowed when file, rule and matched text agree and the snippet occurs in the line. Keep it tight.

Exit status 1 when any hit is left. check_rodais.py runs it on the master Books; eras/check_era.py on each era.
"""
import glob
import json
import os
import re
import sys

Q = os.path.dirname(os.path.abspath(__file__))
ERAS = os.path.dirname(Q)
ROOT = os.path.dirname(ERAS)
LEG = os.path.join(ROOT, 'legendarium')
sys.path.insert(0, LEG)
import reckoning as RK  # noqa: E402

KEYS = RK.AGE_KEYS
IDX = {k: i for i, k in enumerate(KEYS)}
AGE_NAMES = {   # as build_book.AGE_NAMES (kept here so the check does not load the whole book builder)
    'I': ('An Aois Àrsaidh', 'the Ancient Age'), 'II': ('An Aois Ailein', 'the Age of Ailean'),
    'III': ('An Aois Naomh', 'the Holy Age'), 'IV': ('An Aois Scaraidh', 'the Age of Sundering'),
    'V': ('An Aois Choigreach', 'the Age of Strangers'), 'VI': ('An Aois Rìoghachd', 'the Age of the Kingdom'),
    'VII': ('An Aois Dhubhain', 'the Age of Dubhan')}
ORDINAL = {'I': 'First', 'II': 'Second', 'III': 'Third', 'IV': 'Fourth', 'V': 'Fifth', 'VI': 'Sixth', 'VII': 'Seventh'}
ALLOW_FILE = os.path.join(Q, 'future_allow.txt')

TOKEN = re.compile(r'\{\{(date|year|reckon|reckonyear|place):([^}]+)\}\}')
PHRASES = re.compile(r"(?i)\b(?:"
                     r"(?:ages|centuries|generations|lifetimes) (?:later|after(?:ward)?s?|to come|hence)|"
                     r"long (?:after(?:ward)?s?|years? after(?:ward)?s?)(?! (?:the|that|this|his|her|their|its|he|she|they|it|a)\b)|"
                     r"in (?:time|years|days|ages) to come|in (?:after|later) (?:years|days|ages|times)|in after-(?:years|days|ages)|"
                     r"(?:was|were|is|are) (?:one day |later |in time )?to (?:become|be called|be named|be known|come|be)\b(?= (?:the|a|an|known|called|named|its|his|her|their)\b)|"
                     r"would (?:later|one day|in time|afterwards?|come to be|come to|be remembered|be called|be named|be known|become|never again)|"
                     r"(?:was|were|is|are|be) later\b|later (?:became|become|becomes|called|named|known|still|ages|years|times|generations|tellers|writers|scholars|hands)|"
                     r"what (?:became|would become|is now|was later|later became)|(?:is|are) now (?:called|named|known)|"
                     r"as would be seen|as (?:we|you) shall see|as (?:it|they|he|she) (?:would|was to) prove|"
                     r"one day (?:would|will|should|shall)|in the time of the humans|the Library (?:would|will|was to|later)|"
                     r"afterwards the"
                     r")")
ERA_ABBR = re.compile(r'\b(VE|GE|FE|LE|AE|SE|DE)\b')
LONG = re.compile('[àèìòùÀÈÌÒÙ]')
# "three centuries later", "sixteen centuries after": a span counted inside the tale, not the teller looking ahead
COUNTED = re.compile(r"(?i)\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
                     r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|"
                     r"thousand|a few|few|several|\d[\d,]*)\s+$")


def load(p):
    return json.load(open(p, encoding='utf-8'))


class World:
    def __init__(self):
        self.ev = {e['id']: e for e in load(os.path.join(LEG, 'annals_dated.json'))}
        for k in KEYS:                                   # era events, where an era has dated its annals
            p = os.path.join(ERAS, 'age_%s' % k, 'annals_dated.json')
            if os.path.exists(p):
                for e in load(p):
                    self.ev.setdefault(e['id'], dict(e, age=e.get('age') or k))
        world = load(os.path.join(LEG, 'world.json'))
        gaz = {}
        for f in glob.glob(os.path.join(LEG, 'gazetteer', 'out_*.json')):
            gaz.update(load(f))
        self.burg_age = {}                               # burg id -> founding age
        self.burg_names = {}                             # name -> the earliest founding age of any town of that name
        for b in world['burgs']:
            a = (gaz.get(str(b['id'])) or {}).get('founded_age')
            if a in IDX:
                self.burg_age['burg:%s' % b['id']] = a
                if b['name'] not in self.burg_names or IDX[a] < IDX[self.burg_names[b['name']]]:
                    self.burg_names[b['name']] = a
        # later ages' and eras' names
        self.era_terms = {k: set() for k in KEYS}
        for a in RK.AGES:
            k = a[0]
            self.era_terms[k] |= {a[4], a[4][4:].strip(), a[5], AGE_NAMES[k][0], AGE_NAMES[k][1], AGE_NAMES[k][1][4:],
                                  'Age %s' % k, 'the %s Age' % ORDINAL[k], 'the %s Book' % ORDINAL[k]}
        self.names = []                                  # (term, age, rule)
        npath = os.path.join(ERAS, 'NAMES.json')
        if os.path.exists(npath):
            raw = load(npath)
            for n in raw.get('names', []):
                terms = {t for t in [n.get('en'), n.get('dt')] + list(n.get('variants') or []) if t}
                if n.get('kind') == 'age':
                    k = next((kk for kk in KEYS if AGE_NAMES[kk][1] == n.get('en')), None)
                    if k:
                        self.era_terms[k] |= {t for t in terms if not ERA_ABBR.fullmatch(t)}
                    continue
                if n.get('kind') == 'era' and n.get('en') in {a[4] for a in RK.AGES}:
                    k = next(a[0] for a in RK.AGES if a[4] == n['en'])
                    self.era_terms[k] |= {t for t in terms if not ERA_ABBR.fullmatch(t)}
                    continue
                f = self.ev.get(n.get('first') or '')
                if f:
                    for t in terms:
                        # a lower-case English form ("the crossing", "the chronicle", "the mist") is a common noun as
                        # often as a name: only a form with a capital or a Dia-thìris letter is looked for
                        if t != t.lower() or LONG.search(t):
                            self.names.append((t, f['age'], 'name'))
        ppath = os.path.join(ERAS, 'PEOPLE.json')
        if os.path.exists(ppath):
            for p in load(ppath).get('people', []):
                f = self.ev.get(p.get('first') or '')
                if f and p.get('name'):
                    self.names.append((p['name'], f['age'], 'person'))
        for t, a in self.burg_names.items():
            self.names.append((t, a, 'burg'))
        self.era_abbr = {a[3]: a[0] for a in RK.AGES}

    def add_era_places(self, k):
        """An era's own declared towns (places.json, its gazetteer) count as founded in that era at the latest."""
        d = os.path.join(ERAS, 'age_%s' % k)
        p = os.path.join(d, 'places.json')
        if os.path.exists(p):
            for ref, pl in (load(p).get('places', load(p)) if isinstance(load(p), dict) else {}).items():
                if isinstance(pl, dict) and pl.get('name'):
                    a = pl.get('founded_age') or k
                    self.burg_age.setdefault(ref, a)
                    self.names.append((pl['name'], a, 'burg'))

    @staticmethod
    def later(a, k):
        return a in IDX and IDX[a] > IDX[k]

    def term_re(self, k):
        """One regex of every later term, longest first, with its (age, rule)."""
        tab = {}
        for kk in KEYS:
            if IDX[kk] > IDX[k]:
                for t in self.era_terms[kk]:
                    tab.setdefault(t, (kk, 'era'))
        # a name that a person or place of age K or before also bears (two people called Aonghas Mòr, one of Age V
        # and one of Age VII) is that earlier bearer's name in an age-K text, not a forward reference
        held = {t for t, a, rule in self.names if a in IDX and not self.later(a, k)}
        # and a later person known by a bare given name ("Cailean") does not claim that name from an earlier
        # person who bears it first ("Cailean mac Eachainn", called Cailean in the telling)
        held |= {t.split()[0] for t, a, rule in self.names if rule == 'person' and a in IDX and not self.later(a, k)
                 and ' ' in t}
        for t, a, rule in self.names:
            if self.later(a, k) and not (rule == 'person' and t in held):
                tab.setdefault(t, (a, rule))
        terms = sorted((t for t in tab if len(t) >= 4), key=len, reverse=True)
        rx = re.compile(r'(?<![\w-])(?:%s)(?![\w-])' % '|'.join(map(re.escape, terms))) if terms else None
        # names already standing by age K (a landmark of NAMES.json first attested by then, "Carragh Cnoc bheag"): a later
        # town's name inside one of them is the older place-name the town took, not the town
        known = sorted({t for t, a, rule in self.names if rule == 'name' and a in IDX and IDX[a] <= IDX[k] and ' ' in t},
                       key=len, reverse=True)
        self.known_rx = re.compile(r'(?<![\w-])(?:%s)(?![\w-])' % '|'.join(map(re.escape, known))) if known else None
        return rx, tab


def strip_comments(text):
    """Blank <!-- --> writers' notes (never printed), keeping line numbers."""
    return re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text, flags=re.S)


def units(path):
    """[(where, text)] of one file: Markdown lines, or the prose strings of a JSON file."""
    if path.endswith('.json'):
        out = []

        def walk(x, tag):
            if isinstance(x, dict):
                t = x.get('id') if isinstance(x.get('id'), str) else tag
                for key, v in x.items():
                    if key in ('id', 'to', 'type', 'place', 'kind', 'category', 'dt', 'src', 'told_in', 'status', 'first',
                               'last', 'born', 'died', 'after', 'span', 'threads', 'people', 'links'):
                        continue
                    if isinstance(v, str):
                        out.append(('%s.%s' % (t, key), v))
                    else:
                        walk(v, t)
            elif isinstance(x, list):
                for i, v in enumerate(x):
                    walk(v, '%s[%d]' % (tag, i))
        walk(load(path), os.path.basename(path))
        return out
    text = strip_comments(open(path, encoding='utf-8').read())
    return [(str(i), ln) for i, ln in enumerate(text.split('\n'), 1) if ln.strip()]


def scan_text(W, text, k, rx, tab, upto=None, phrases_only=False):
    """Hits in one unit: [(rule, matched, why)]. upto: (y, m, d) an annals entry may not look past."""
    hits = []
    if not phrases_only:
        for m in TOKEN.finditer(text):
            kind, arg = m.group(1), m.group(2)
            if kind in ('date', 'year'):
                e = W.ev.get(arg)
                if e and (W.later(e['age'], k) or (upto and (e['y'], e['m'], e['d']) > upto)):
                    hits.append(('token', m.group(0), 'event of %s' % e['date']))
            elif kind in ('reckon', 'reckonyear'):
                a = int(arg.split(':')[0])
                ak = RK.era_of(a)
                if W.later(ak, k):
                    hits.append(('token', m.group(0), 'a year of Age %s' % ak))
            elif kind == 'place' and W.later(W.burg_age.get(arg, ''), k):
                hits.append(('token', m.group(0), 'a town founded in Age %s' % W.burg_age[arg]))
        plain = TOKEN.sub(' ', text)
        for m in ERA_ABBR.finditer(plain):
            a = W.era_abbr[m.group(1)]
            if W.later(a, k):
                hits.append(('era', m.group(0), 'the era of Age %s' % a))
        spans = [m.span() for m in W.known_rx.finditer(plain)] if W.known_rx else []
        if rx:
            for m in rx.finditer(plain):
                if any(a <= m.start() and m.end() <= b for a, b in spans):
                    continue
                a, rule = tab[m.group(0)]
                hits.append((rule, m.group(0), 'of Age %s' % a))
    plain = TOKEN.sub(' ', text)
    for m in PHRASES.finditer(plain):
        if not m.group(0).lower().startswith('ages') and COUNTED.search(plain[:m.start()]):
            continue
        hits.append(('phrase', m.group(0), 'looks ahead'))
    return hits


def load_allow():
    out = []
    if os.path.exists(ALLOW_FILE):
        for ln in open(ALLOW_FILE, encoding='utf-8'):
            if ln.strip() and not ln.startswith('#'):
                parts = [p.strip() for p in ln.split('|')]
                if len(parts) >= 5 and parts[4]:
                    out.append(tuple(parts[:4]))
    return out


def allowed(allow, rel, rule, matched, line):
    return any(f == rel and r == rule and t == matched and s in line for f, r, t, s in allow)


def check_file(W, path, k, allow, show_allowed=False, phrases_only=False, annals_upto=False):
    """-> [(rel:where, rule, matched, why, snippet)] left after the allow-list."""
    rx, tab = W.term_re(k)
    rel = os.path.relpath(path, ROOT)
    out = []
    for where, text in units(path):
        upto = None
        if annals_upto:
            e = W.ev.get(where.split('.')[0])
            if e:
                upto = (e['y'], e['m'], e['d'])
        for rule, matched, why in scan_text(W, text, k, rx, tab, upto, phrases_only):
            ok = allowed(allow, rel, rule, matched, text)
            if ok and not show_allowed:
                continue
            i = text.find(matched)
            snip = text[max(0, i - 50): i + len(matched) + 50].replace('\n', ' ')
            out.append(('%s:%s' % (rel, where), rule + (' (allowed)' if ok else ''), matched, why, snip))
    return out


def master_files():
    return [(os.path.join(LEG, 'book', 'creation.md'), 'I')] + [(os.path.join(LEG, 'book', 'age_%s.md' % k), k) for k in KEYS]


def era_files(k):
    d = os.path.join(ERAS, 'age_%s' % k)
    out = []
    for pat in ('book/*.md', 'appendices/*.md', 'gazetteer/*.json', 'places.json', 'front.json'):
        out += sorted(glob.glob(os.path.join(d, pat)))
    ann = [f for f in sorted(glob.glob(os.path.join(d, 'annals', '*.json'))) if not f.endswith('_master.json')]
    return [(f, k, False) for f in out] + [(f, k, True) for f in ann]


def check_master(W=None, allow=None, show_allowed=False):
    W, allow = W or World(), load_allow() if allow is None else allow
    return [h for f, k in master_files() for h in check_file(W, f, k, allow, show_allowed)]


def check_era(k, W=None, allow=None, show_allowed=False):
    W, allow = W or World(), load_allow() if allow is None else allow
    W.add_era_places(k)
    return [h for f, kk, ann in era_files(k) for h in check_file(W, f, kk, allow, show_allowed, annals_upto=ann)]


def check_master_annals(W=None, allow=None):
    """Phrase hits in the master annals entries (each read as at its own day): reported, not failed."""
    W, allow = W or World(), load_allow() if allow is None else allow
    return [h for k in KEYS for h in check_file(W, os.path.join(LEG, 'annals', 'age_%s.json' % k), k, allow,
                                                   phrases_only=True, annals_upto=True)]


def show(hits):
    for where, rule, matched, why, snip in hits:
        print('%s: %s: "%s" (%s): ...%s...' % (where, rule, matched, why, snip))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    show_allowed = '--allowed' in sys.argv
    if not args:
        sys.exit(__doc__)
    W = World()
    t = args[0]
    if t == 'master':
        hits = check_master(W, show_allowed=show_allowed)
    elif t == 'master-annals':
        show(check_master_annals(W))
        return
    elif t == 'eras':
        hits = [h for k in KEYS for h in check_era(k, W, show_allowed=show_allowed)]
    elif t in KEYS:
        hits = check_era(t, W, show_allowed=show_allowed)
    elif os.path.isfile(t) and len(args) > 1 and args[1] in KEYS:
        hits = check_file(W, os.path.abspath(t), args[1], load_allow(), show_allowed)
    else:
        sys.exit(__doc__)
    show(hits)
    left = [h for h in hits if not h[1].endswith('(allowed)')]
    print('%d forward reference(s)' % len(left))
    sys.exit(1 if left else 0)


if __name__ == '__main__':
    main()
