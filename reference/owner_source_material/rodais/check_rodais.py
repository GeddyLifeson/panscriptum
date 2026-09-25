"""
check_rodais.py -- verify everything in this folder in one run.

  1. the engine's self-test (rodais_engine.py)
  2. LEXICON.json: every entry complete, every Dia-thìris field already in Dia-thìris
     spelling, and a caol-le-caol report (real exceptions are exempt in the
     engine; what remains is loanwords, names and unhyphenated compounds,
     listed, not failed)
  3. TEXTS.json: every line paired with its translation, Dia-thìris spelling
  4. Rodos_finished.map: the rewritten sections parse, no pre-Ròdais name
     survives, every saved burg label matches its burg, every layer edit of
     legendarium/reconcile/ is in, the roads are drawn as roads, the island
     lies in the Atlantic west of the Hebrides at 0.14 miles to the unit, with a
     mild oceanic climate (no glacier, no ice, a mild sea-level temperature), and dubhan, not charcoal, is the traded fuel
  5. the legendarium: every event dated and in order, every reference
     resolves, world.json is the digest of the map as it stands, and no glacier,
     ice cap or iceberg anywhere in the history
  6. the seven ages and their eras: seven contiguous ages, each opening in year 1
     of its era, each age's annals holding exactly the events dated in its era
     (an event's age is its annals file, never the numeral of its id), every date written in the era form ("12 am Màrt, AE 67") with
     an era year of at least 1, no date left in the old continuous count
     (BDE / DE / Diosal Era) and no "New Age" anywhere that is delivered (the
     books, annals, appendices and gazetteer, the language book's chapters and
     texts, the dictionary, world.json, the map's notes), the map's calendar the
     Dubhan Era at the present year and its wars dated in that era, each book's
     date line its age's span, and every age and era name in Dia-thìris spelling

  7. the books: the Telling of the Making and the seven Books speak only of their own age and before, with nothing
     of a later age in them (eras/quality/future_check.py, the owner's rule)

Exit status 0 only when every check holds.  python check_rodais.py
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rodais_engine as R  # noqa: E402

fails = []


def check(ok, what):
    print(('ok    ' if ok else 'FAIL  ') + what)
    if not ok:
        fails.append(what)


def words(text):
    return [w for w in re.split(r"[\s,.?!;:()\"“”—–…/]+|'(?=\s)|(?<=\s)'", text) if w and w != "'"]


# 1. engine
check(R._selftest(), 'engine self-test')

# 2. lexicon
lex = json.load(open(os.path.join(HERE, 'LEXICON.json'), encoding='utf-8'))['entries']
check(len(lex) >= 16000 and len({e['id'] for e in lex}) == len(lex), 'lexicon: at least 16,000 entries, every id distinct (%d)' % len(lex))
check(all(e.get('rod') and e.get('pos') and e.get('en') for e in lex), 'lexicon: every entry has headword, part of speech, English')
check(all(e.get('g') in ('m', 'f') for e in lex if e['pos'] == 'n'), 'lexicon: every noun has a gender')
check(all(e.get('root') for e in lex if e['pos'] == 'v'), 'lexicon: every verb has a root')
ken = [e for e in lex if e.get('kenning')]
check(all(e.get('lit') for e in ken), 'lexicon: every old-root compound has its literal sense (%d)' % len(ken))
kl = {}
for e in ken:
    kl.setdefault(e['rod'].lower(), set()).add(e['lit'].lower())
check(all(len(v) == 1 for v in kl.values()), 'lexicon: an old-root compound means one thing (a headword shared by kennings has one literal sense)')
check(not [e for e in ken if R.check_agreement(e['rod'].strip('?!.'))], 'lexicon: every old-root compound obeys caol le caol')
fields = [(e['id'], e[k]) for e in lex for k in ('rod', 'pl', 'root') if e.get(k)]
check(all(R.normalize(v) == v for _, v in fields), 'lexicon: every Dia-thìris field is in Dia-thìris spelling (no acute, no sg)')
flag = sorted({w for _, v in fields for w in words(v) if R.check_agreement(w)}, key=str.lower)
print('      caol le caol: %d words left outside the rule (loanwords, names, unhyphenated compounds): %s' % (len(flag), ', '.join(flag)))

# 3. texts
texts = json.load(open(os.path.join(HERE, 'TEXTS.json'), encoding='utf-8'))['texts']
check(all(len(t['paras']) == len(t['paras_en']) for t in texts), 'texts: every line paired with its English (%d texts)' % len(texts))
check(all(R.normalize(p) == p for t in texts for p in t['paras'] + [t['title']]), 'texts: Dia-thìris spelling throughout')
tflag = sorted({w for t in texts for p in t['paras'] for w in words(p) if R.check_agreement(w)}, key=str.lower)
print('      caol le caol in texts: %s' % (', '.join(tflag) or 'none'))

# 4. map
# 53 CRLF-joined records in Azgaar's save order (see finish_map.py); the SVG is record 5
lines = open(os.path.join(HERE, 'Rodos_finished.map'), encoding='utf-8', newline='').read().split('\r\n')
check(len(lines) == 53, 'map: 53 CRLF-separated records, as Azgaar writes them (%d)' % len(lines))
parsed = {}
for n in (12, 14, 15, 29, 30, 32, 35, 37, 38, 52):
    try:
        parsed[n] = json.loads(lines[n])
    except Exception as e:  # noqa: BLE001
        parsed[n] = None
        check(False, 'map: section at line %d parses (%s)' % (n, e))
check(all(v is not None for v in parsed.values()), 'map: every rewritten section parses')
OLD = ['Luteley', 'Grantesham', 'Kiverton', 'Marltash', 'Albridge', 'Penrith', 'Towbigham', 'Hatlexe', 'Uxblean',
       'Tuton', 'Clitle', 'Shkell', 'Seann Dhunn', 'Seann Tharr', 'Seann Tholl', 'City-State Rodos', 'Wincland']
left = [w for w in OLD if any(w in lines[n] for n in list(parsed) + [5])]
check(not left, 'map: no pre-Ròdais name left (%s)' % (', '.join(left) or 'none'))
burgs = {b['i']: b['name'] for b in parsed[15] if isinstance(b, dict) and b.get('name')}
labels = re.findall(r'<text id="burgLabel\d+" data-label-type="burg" data-id="(\d+)"[^>]*>([^<]*)</text>', lines[5])
check(labels and all(burgs.get(int(i)) == t for i, t in labels), 'map: all %d saved burg labels match their burgs' % len(labels))
names = [o['name'] for n in (12, 15, 29, 30, 32, 35, 37, 38) for o in parsed[n] if isinstance(o, dict) and o.get('name')]
check(all(R.normalize(x) == x for x in names), 'map: every name in Dia-thìris spelling (%d names)' % len(names))
mflag = sorted({w for x in names for w in words(x) if R.check_agreement(w)})
check(not mflag, 'map: every name obeys caol le caol (%s)' % (', '.join(mflag) or 'no exceptions'))
feat = json.load(open(os.path.join(HERE, 'legendarium', 'burg_features.json'), encoding='utf-8'))
live = [b for b in parsed[15] if isinstance(b, dict) and b.get('i') and not b.get('removed')]
off = [b['i'] for b in live if str(b['i']) not in feat or any(b.get(k) != feat[str(b['i'])][k] for k in ('citadel', 'walls', 'plaza', 'temple', 'shanty'))
       or ('port' in feat[str(b['i'])] and b.get('port'))]
anchors = {int(i) for i in re.findall(r'<use id="anchor(\d+)" data-id="\1"', lines[5])}
check(anchors == {b['i'] for b in live if b.get('port')}, 'map: a saved anchor icon for every port and for no other burg (%d)' % len(anchors))
cell_burg = lines[17].split(',')
check(all(cell_burg[b['cell']] == str(b['i']) for b in live) and sum(1 for v in cell_burg if v != '0') == len(live),
      'map: the cells record every burg in its own cell and no other')
moves = json.load(open(os.path.join(HERE, 'legendarium', 'burg_moves.json'), encoding='utf-8'))
byid = {b['i']: b for b in live}
check(all(byid[int(i)]['cell'] == m['to']['cell'] and byid[int(i)]['x'] == m['to']['x'] and byid[int(i)]['port'] == m['port'] for i, m in moves.items()),
      'map: the %d harbour towns of legendarium/burg_moves.json stand on the shore' % len(moves))
old_cells = {m['from']['cell'] for m in moves.values()} - {b['cell'] for b in live}
route_ends = [r['i'] for r in json.loads(lines[37]) for c in (r['points'][0][2], r['points'][-1][2]) if c in old_cells]
check(not route_ends, 'map: no route still ends where a moved town used to stand (%s)' % (', '.join(map(str, route_ends[:8])) or 'none'))
check(not off, 'map: every burg has the town features legendarium/burg_features.json gives it (%s)' % (', '.join(map(str, off[:8])) or '%d burgs' % len(live)))
sys.path.insert(0, os.path.join(HERE, 'legendarium'))
import map_reconcile  # noqa: E402
again = list(lines)
try:
    redo = sorted(map_reconcile.reconcile_records(again))
except AssertionError as e:  # an edit whose "old" no longer matches: the map predates the reconcile files
    redo = ['%s' % e]
check(not redo, 'map: every reconciled layer edit of legendarium/reconcile/ is in (%s)' % (', '.join(map(str, redo)) or 'nothing left to apply'))
routes = json.loads(lines[37])
road_ids = {r['i'] for r in routes if r.get('group') == 'roads'}
g = re.search(r'<g id="roads" data-group="roads"[^>]*>(.*?)</g>', lines[5])
check(road_ids and g and {int(i) for i in re.findall(r'<path id="route(\d+)"', g.group(1))} == road_ids,
      'map: the %d roads are drawn in the roads group and nowhere else' % len(road_ids))
# an island alone in the Atlantic west of the Hebrides, about the size of Northern Ireland, with a mild oceanic
# climate: no glacier, no ice, a mild sea-level temperature
biomes = json.loads(lines[3])
glacier = [b['i'] for b in biomes if b['name'] == 'Glacier']
cell_biome = lines[16].split(',')
check(not any(v in {str(i) for i in glacier} for v in cell_biome), 'map: no Glacier biome cell (%d cells)' % len(cell_biome))
ice = re.search(r'<g id="ice"[^>]*?(/?)>', lines[5])
check(json.loads(lines[39]) == [] and ice and ice.group(1) == '/', 'map: no icebergs, and the ice layer saved empty')
geo = json.loads(lines[1])['geography']['coordinates']
temps = [int(v) for v in lines[11].split(',')]
units = json.loads(lines[1])['units']['distance']
check(56 <= geo['latS'] and geo['latN'] <= 57.6 and geo['lonE'] < -7.6 and units == {'unit': 'mi', 'scale': 0.14}
      and min(temps) > -5,
      'map: the frame at %s-%s N, %s-%s W (no real coast in it), %s mi to the unit, and no grid cell cold enough for ice'
      ' (the coldest %d C)' % (geo['latS'], geo['latN'], -geo['lonW'], -geo['lonE'], units['scale'], min(temps)))
goods = [g['name'] for g in json.loads(lines[41]) if isinstance(g, dict)]
check('Dubhan' in goods and 'Charcoal' not in goods and 'Coal' not in goods, 'map: dubhan is a trade good, and charcoal and coal are not')
world = json.load(open(os.path.join(HERE, 'legendarium', 'world.json'), encoding='utf-8'))
digest = map_reconcile.world_digest(lines)
check(all(world[k] == digest[k] for k in digest), 'legendarium/world.json is the digest of the map as it stands')

# 5. the legendarium: every event dated and in order, every reference resolves, every place is on the map
LEG = os.path.join(HERE, 'legendarium')
sys.path.insert(0, LEG)
import build_book  # noqa: E402
rec = build_book.Record()
evs = rec.events
check(all(e.get('y') and e.get('m') and e.get('d') and e.get('date') for e in evs), 'legendarium: every one of %d events has a day, month and year' % len(evs))
order = [(e['y'], e['m'], e['d']) for e in evs]
check(order == sorted(order), 'legendarium: the annals run in order of date, age to age')
check(len({e['id'] for e in evs}) == len(evs), 'legendarium: event ids unique')
canon = [e for e in evs if e.get('canon') and build_book.reckoning.canon_anchor(e)]
held = [e for e in canon if build_book.reckoning.canon_anchor(e)[0] != e['y']]
check(len(held) <= 2, 'legendarium: every chronicle year kept (%d of %d; approximate ones moved: %s)' % (
    len(canon) - len(held), len(canon), ', '.join(e['id'] for e in held) or 'none'))
badplace = [e['id'] for e in evs if e.get('place') and e['place'] not in rec.names]
check(not badplace, 'legendarium: every event place is on the map (%s)' % (', '.join(badplace[:8]) or 'all'))
check(len(rec.gaz) == len(rec.burg), 'legendarium: gazetteer covers all %d burgs (%d)' % (len(rec.burg), len(rec.gaz)))
build_book.compose(rec)
check(not rec.missing, 'legendarium: every {{date}}/{{year}}/{{place}} reference resolves (%s)' % (', '.join(sorted(set(rec.missing))[:8]) or 'all'))
srcs = [open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(LEG, 'book', '*.md')) + glob.glob(os.path.join(LEG, 'appendices', '*.md'))]
check(not any(re.search('[\u00e1\u00e9\u00ed\u00f3\u00fa]', t) for t in srcs), 'legendarium: no acute accents in the books and appendices')
history = srcs + [open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(LEG, 'annals', 'age_*.json'))
                  + glob.glob(os.path.join(LEG, 'gazetteer', 'out_*.json')) + [os.path.join(LEG, 'appendices', 'houses.json')]]
history += [m.get('note', '') for m in json.loads(lines[35])]
icy = sorted({m.group(0).lower() for t in history for m in re.finditer(r'(?i)\bglacier|\bice[ -]?caps?\b|\biceberg|\bdrift[ -]ice\b', t)})
check(not icy, 'legendarium: no glacier, ice cap or iceberg in the history (%s)' % (', '.join(icy) or 'none'))

# 6. the seven ages and their eras
RK = build_book.reckoning
keys = RK.AGE_KEYS
check(keys == ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'] and all(os.path.exists(os.path.join(LEG, 'annals', 'age_%s.json' % k)) for k in keys)
      and all(os.path.exists(os.path.join(LEG, 'book', 'age_%s.md' % k)) for k in keys)
      and sorted(os.path.basename(f) for f in glob.glob(os.path.join(LEG, 'annals', 'age_*.json'))) == sorted('age_%s.json' % k for k in keys)
      and sorted(os.path.basename(f) for f in glob.glob(os.path.join(LEG, 'book', 'age_*.md'))) == sorted('age_%s.md' % k for k in keys),
      'ages: seven ages, each with its annals and its book, and no annals or book outside them (%s)' % ', '.join(keys))
in_file = {}
for k in keys:
    for e in json.load(open(os.path.join(LEG, 'annals', 'age_%s.json' % k), encoding='utf-8')):
        in_file[e['id']] = k
check(all(in_file.get(e['id']) == e['age'] for e in evs) and len(in_file) == len(evs),
      'ages: every event dated in the age of the annals file it stands in (an id\'s numeral is not its age)')
check([e['age'] for e in evs] == sorted((e['age'] for e in evs), key=keys.index) and set(e['age'] for e in evs) == set(keys),
      'ages: every event in one of the seven ages, the ages in order and none empty')
check(all(RK.AGES[i][2] == RK.AGES[i + 1][1] for i in range(len(keys) - 1)),
      'ages: contiguous, each era ending in the year the next age opens')
opens = {}
for e in evs:
    opens.setdefault(e['age'], e)
check(all(opens[k]['y'] == RK.ERA[k][1] and RK.era_year(opens[k]['y'], k) == 1 for k in keys),
      'ages: every age opens in year 1 of its era (%s)' % ', '.join('%s %s' % (k, opens[k]['id']) for k in keys))
check(all(RK.era_of(e['y'], e['m'], e['d']) == e['age'] and e.get('era') == RK.ERA[e['age']][3] for e in evs),
      'ages: every event falls in the era of its own age')
ERA_DATE = re.compile(r'^\d{1,2} (%s), (%s) [1-9][\d,]*$' % ('|'.join(RK.MONTHS), '|'.join(a[3] for a in RK.AGES)))
dates = [e['date'] for e in evs] + [g['founded']['date'] for g in rec.gaz.values()] + \
        [p[f] for h in rec.houses for p in h.get('members', []) for f in ('born', 'died') if p.get(f + '_between')]
bad = [d for d in dates if not ERA_DATE.match(d)]
check(not bad, 'eras: all %d dates (events, foundings, houses) in the era form with a year of at least 1 (%s)' % (len(dates), ', '.join(bad[:5]) or 'all'))
check(all(e.get('ey', 0) >= 1 for e in evs) and all(RK.era_year(y, k) >= 1 for k, y in
      [(RK.era_of(g['founded']['y'], g['founded']['m'], g['founded']['d']), g['founded']['y']) for g in rec.gaz.values()]),
      'eras: every era year is at least 1')
text = build_book.to_markdown(rec) + re.sub(r'<[^>]+>', ' ', build_book.compose(rec)[1])
old = sorted({m.group(0) for m in re.finditer(r'\d[\d,]*\s+B?DE\b|\bBDE\b|Diosal (?:Era|Age)|\bNew Age\b', text)})
check(not old, 'eras: no date left in the old continuous count in the book, annals, appendices or gazetteer (%s)' % (', '.join(old[:8]) or 'none'))
# the same for everything else that is delivered: the language book's chapters and texts, the dictionary, the
# map's digest and the map itself (its calendar, the state's war, the regiments' and markers' notes)
OLD_COUNT = re.compile(r'\d[\d,]*\s+B?DE\b|\bBDE\b|Diosal (?:Era|Age)|\bNew Age\b')
delivered = {f: open(os.path.join(HERE, f), encoding='utf-8').read() for f in
             ('PHONOLOGY.md', 'GRAMMAR.md', 'GRAMMAR_MORPHOLOGY.md', 'GRAMMAR_SYNTAX.md', 'NAMING_LAYER.md', 'TEXTS.md', 'TEXTS.json')}
delivered['LEXICON.json'] = json.dumps([[e.get('en'), e.get('sense'), e.get('rod')] for e in lex], ensure_ascii=False)
delivered['legendarium/world.json'] = json.dumps(world, ensure_ascii=False)
delivered['the annals'] = json.dumps([[e['title'], e['body']] for e in evs], ensure_ascii=False)
for n in (1, 14, 35):
    delivered['map record %d' % n] = json.dumps(json.loads(lines[n]), ensure_ascii=False)
old = sorted({'%s: %s' % (k, m.group(0)) for k, t in delivered.items() for m in OLD_COUNT.finditer(t)})
check(not old, 'eras: no "Diosal Era", "New Age" or year of the old continuous count in the language book, the dictionary, '
      'the annals, world.json or the map (%s)' % (', '.join(old[:6]) or 'none'))
cal = json.loads(lines[1])['lore']['calendar']
now = RK.era_year(evs[-1]['y'], evs[-1]['age'])
check(cal == {'year': now, 'era': 'Dubhan Era', 'eraShort': RK.ERA[keys[-1]][3]},
      'eras: the map reckons in the Dubhan Era, year %d, the present year (%s)' % (now, cal))
war = [c for st in parsed[14] if isinstance(st, dict) for c in (st.get('campaigns') or [])]
check(all(1 <= c['start'] <= c.get('end', c['start']) <= now for c in war),
      'eras: the map\'s wars are dated in years of the Dubhan Era (%s)' % ', '.join('%s %s-%s' % (c['name'], c['start'], c.get('end')) for c in war))
span_bad = []
for k in keys:
    ln = open(os.path.join(LEG, 'book', 'age_%s.md' % k), encoding='utf-8').read().split('\n')
    if ln[2] != '*%s*' % RK.display_span(k) or not ln[0].startswith('# %s: %s, %s' % (build_book.BOOK_TITLES[k], build_book.AGE_NAMES[k][0], build_book.AGE_NAMES[k][1])):
        span_bad.append(k)
check(not span_bad, 'eras: every book opens with its age\'s name and its span in its era (%s)' % (', '.join(span_bad) or 'all seven'))
rnames = [build_book.AGE_NAMES[k][0] for k in keys] + [RK.ERA[k][5] for k in keys]
check(all(R.normalize(x) == x and not [w for w in x.split() if R.check_agreement(w)] for x in rnames),
      'eras: every age and era name in Dia-thìris spelling and caol le caol (%s)' % ', '.join(rnames))

# 7. the owner's rule: a book speaks only of its present and its past. The Telling of the Making and each of the seven
# Books name nothing of a later age: no token, era, name or town of it, and no foreshadowing (eras/quality/future_check.py)
sys.path.insert(0, os.path.join(HERE, 'eras', 'quality'))
import future_check  # noqa: E402
ahead = future_check.check_master()
for where, rule, matched, why, snip in ahead[:12]:
    print('      %s: %s "%s" (%s)' % (where, rule, matched, why))
check(not ahead, 'books: the Telling and the seven Books speak only of their own age and before (%s)'
      % ('%d forward reference(s); python eras/quality/future_check.py master' % len(ahead) if ahead else 'none'))

print('\n%s' % ('ALL CHECKS HOLD' if not fails else '%d CHECK(S) FAILED' % len(fails)))
sys.exit(1 if fails else 0)
