"""
finish_map.py -- finish the Ròdais renaming of the Rodos map.

The first pass (Rodos_renamed.map) renamed the 505 burgs, 157 rivers and 123
provinces, the three cultures and the state's full name. It left the rest of
the map in the generator's English, and it left the labels drawn into the
saved SVG showing the old burg names, so the map opened in Azgaar still read
"Luteley" where the data said "Cathair dhearg".

This pass:
  * redraws every saved burg label and the state label from the data;
  * re-derives the substrate names with the corrected lenition rules
    (Seann Skell, not Seann Shkell; Seann Dunn, not Seann Dhunn) and carries
    the change into the provinces named after those burgs;
  * names the ocean, islands and lake; the religions and their deities; the
    war; the regiments and fleets; the markers; the named routes; the zones;
    and the quest journey -- all in Ròdais, through rodais_engine;
  * rewrites the English notes so they name places that exist on this map;
  * gives every burg the town features (citadel, walls, plaza, temple, shanty) its history
    supports, from legendarium/burg_features.json.

Descriptive notes stay in English, as the first pass left the Azgaar UI
text (biomes, trade goods, unit types). Only names are Ròdais.

Run:  python finish_map.py            (reads Rodos_renamed.map, writes Rodos_finished.map + MAP_CHANGES.md)
Deterministic: the same input gives the same output byte for byte.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rodais_engine import normalize, lenite, place_name, substrate_name, check_agreement  # noqa: E402

SRC = os.path.join(HERE, 'Rodos_renamed.map')
DST = os.path.join(HERE, 'Rodos_finished.map')
LOG = os.path.join(HERE, 'MAP_CHANGES.md')

# A .map file is 53 records joined by CRLF, in the order Azgaar's save.ts writes them; the SVG
# (record 5) contains plain LF newlines of its own. These are the records this pass touches.
L_SVG, L_FEATURES, L_STATES, L_BURGS, L_RELIGIONS, L_PROVINCES, L_RIVERS = 5, 12, 14, 15, 29, 30, 32
L_MARKERS, L_ROUTES, L_ZONES, L_JOURNEYS = 35, 37, 38, 52
RECORDS = 53

changes = []   # (section, old, new)


def rename(section, obj, key, new):
    old = obj.get(key)
    new = normalize(new)
    if old != new:
        changes.append((section, old, new))
        obj[key] = new


# ---------------------------------------------------------------- load
# newline='' keeps the CRLF record separators; text mode would turn them into LF and fuse the records
lines = open(SRC, encoding='utf-8', newline='').read().split('\r\n')
assert len(lines) == RECORDS, 'expected %d records, got %d' % (RECORDS, len(lines))
J = {n: json.loads(lines[n]) for n in (L_FEATURES, L_STATES, L_BURGS, L_RELIGIONS, L_PROVINCES,
                                       L_RIVERS, L_MARKERS, L_ROUTES, L_ZONES, L_JOURNEYS)}
burgs = [b for b in J[L_BURGS] if isinstance(b, dict) and b.get('name') and not b.get('removed')]
burg_by_id = {b['i']: b for b in burgs}
burg_by_cell = {b['cell']: b for b in burgs}
rivers = [r for r in J[L_RIVERS] if isinstance(r, dict) and r.get('name')]

# cell -> (x, y), from every object that records both (routes, markers, burgs, journeys, regiments)
cell_xy = {}
for rt in J[L_ROUTES]:
    for p in rt.get('points', []):
        if len(p) == 3:
            cell_xy.setdefault(p[2], (p[0], p[1]))
for b in burgs:
    cell_xy[b['cell']] = (b['x'], b['y'])
for m in J[L_MARKERS]:
    cell_xy.setdefault(m['cell'], (m['x'], m['y']))


def nearest_burg(x, y):
    return min(burgs, key=lambda b: (b['x'] - x) ** 2 + (b['y'] - y) ** 2)


def nearest_river(x, y):
    best, bd = None, None
    for r in rivers:
        for c in r.get('cells', []):
            if c in cell_xy:
                cx, cy = cell_xy[c]
                d = (cx - x) ** 2 + (cy - y) ** 2
                if bd is None or d < bd:
                    best, bd = r, d
    return best or max(rivers, key=lambda r: r.get('length', 0))


def burg_near_cells(cells):
    for c in cells:
        if c in burg_by_cell:
            return burg_by_cell[c]
    pts = [cell_xy[c] for c in cells if c in cell_xy]
    if pts:
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        return nearest_burg(x, y)
    return None


# ---------------------------------------------------------------- 1. burgs: substrate names
def unlenite(w):
    return w[0] + w[2:] if len(w) > 2 and w[1] == 'h' and w[0].lower() in 'bcdfgmpst' else w


old_burg_names = {}
for b in burgs:
    old_burg_names[b['i']] = b['name']
    if b['name'].startswith('Seann '):
        rename('burg', b, 'name', substrate_name(unlenite(b['name'][6:])))
    else:
        rename('burg', b, 'name', b['name'])            # normalize only

# provinces are named after their seat
for p in J[L_PROVINCES]:
    if isinstance(p, dict) and p.get('burg') in burg_by_id:
        seat = burg_by_id[p['burg']]['name']
        if old_burg_names.get(p['burg']) == p.get('name'):
            rename('province', p, 'name', seat)
            rename('province', p, 'fullName', 'Siorrachd ' + seat)

# ---------------------------------------------------------------- 2. the state and the war
state = J[L_STATES][1]
rename('state', state, 'name', 'Ròdos')
rename('state', state, 'form', 'Monarchy')
rename('state', state, 'formName', 'Kingdom')
WAR, WAR_EN = 'An Cogadh Fada', 'the Long War'
for c in state.get('campaigns', []):
    rename('campaign', c, 'name', WAR)

ORDINALS = ["a' chiad", "an dàrna", "an treas", "an ceathramh", "an còigeamh", "an siathamh",
            "an seachdamh", "an t-ochdamh", "an naoidheamh", "an deicheamh", "an aonamh deug", "an dàrna deug"]


def ordinal_name(n, noun):
    o = ORDINALS[n] if n < len(ORDINALS) else 'an %d-mh' % (n + 1)
    w = lenite(noun) if n == 0 else noun          # a' chiad lenites
    s = o + ' ' + w
    return s[0].upper() + s[1:]


counts = {}
for reg in state.get('military', []):
    naval = 'Fleet' in reg.get('name', '')
    kind = 'cabhlach' if naval else 'rèisimeid'
    n = counts.get(kind, 0)
    counts[kind] = n + 1
    base = nearest_burg(reg.get('bx', reg['x']), reg.get('by', reg['y']))['name']
    old = reg['name']
    rename('regiment', reg, 'name', '%s (%s)' % (ordinal_name(n, kind), base))
    note = reg.get('note', '')
    m = re.match(r'Regiment was formed in (\d+) Diosal Era during the (.+?)\. .*? is (stationed|based) in (.+?)\. (.*)$', note, re.S)
    if m:
        reg['note'] = ('Regiment was formed in %s Diosal Era during %s (%s). %s is %s in %s. %s'
                       % (m.group(1), WAR, WAR_EN, reg['name'], m.group(3), base, m.group(5)))
    else:
        reg['note'] = note.replace(old, reg['name'])

# ---------------------------------------------------------------- 3. ocean, islands, lake
QUALIFIERS = ['mòr', 'beag', 'dubh', 'geal', 'bàn', 'dearg', 'ruadh', 'uaine', 'glas', 'fada', 'domhain',
              'ìseal', 'fiadhaich', 'naomh', 'fionn', 'ciar', 'gorm', 'sean', 'òg', 'garbh', 'min', 'caol',
              'leathan', 'crom', 'dìreach', 'àrsaidh']
used = set()


def pick_qualifier(generic, seed):
    """Deterministic, and never the same generic+qualifier twice."""
    h = sum(ord(c) * (i + 1) for i, c in enumerate(seed))
    for k in range(len(QUALIFIERS)):
        name = place_name(generic, QUALIFIERS[(h + k) % len(QUALIFIERS)])
        if name not in used:
            used.add(name)
            return name
    return place_name(generic, seed)


for f in J[L_FEATURES]:
    if not isinstance(f, dict) or not f.get('name'):
        continue
    if f.get('type') == 'ocean':
        rename('feature', f, 'name', 'An Cuan Siar')
    elif f.get('type') == 'island' and f.get('cells', 0) > 1000:
        rename('feature', f, 'name', 'Ròdos')          # the island itself
    elif f.get('type') == 'island':
        rename('feature', f, 'name', pick_qualifier('Eilean', f['name']))
    elif f.get('type') == 'lake':
        rename('feature', f, 'name', pick_qualifier('Loch', f['name']))

# ---------------------------------------------------------------- 4. religions and deities
RELIGIONS = {
    'No religion':               ('Gun chreideamh', None),
    'Kiverton Beliefs':          ('Creideamh nan Tuathach', 'Donn, an Sìorraidh'),
    'Old Marltash Spirits':      ('Seann Spioradan nan Ròdach', 'Crom, an t-Àrd-Spiorad'),
    'Knutskirkism':              ('Creideamh na Sgairpe Buidhe', 'Cnut, an Sgairp Bhuidhe'),
    'Marltash Faith':            ('Creideamh nan Ròdach', 'Dòrsair, Uilebheist nan Geataichean'),
    'Marltashism':               ('Creideamh an t-Seabhaig', 'Mòd, an Seabhag Acrach'),
    'Clitlese Philosophy':       ('Feallsanachd an Fhèidh', 'Camaran, am Fiadh Rìoghail'),
    'Axbridan Faith':            ('Creideamh an Aon-adharcaich Dhuibh', 'Uallach, an t-Aon-adharcach Dubh'),
    'Chistonism':                ('Creideamh a\' Mhadaidh-allaidh', 'Clach, am Madadh-allaidh Lainnireach'),
    'Arcanum of the Grey Night': ('Rùn-dìomhair na h-Oidhche Glaise', 'Sìne, an Gèadh Sìtheil'),
}
religion_names = []
for r in J[L_RELIGIONS]:
    if isinstance(r, dict) and r.get('name') in RELIGIONS:
        name, deity = RELIGIONS[r['name']]
        rename('religion', r, 'name', name)
        if deity and r.get('deity'):
            rename('deity', r, 'deity', deity)
        if r['i']:
            religion_names.append(r['name'])

# ---------------------------------------------------------------- 5. markers
FIXED = {
    'The Lucky Buffalo': 'Am Buabhall Fortanach', 'The Sunny Inn': 'An Taigh-òsta Grianach',
    'The Yellow Lion': 'An Leòmhann Buidhe', 'The Frozen Tavern': 'An Taigh-seinnse Reòta',
    'The Golden Tavern': 'An Taigh-seinnse Òir', 'The Major Tavern': 'An Taigh-seinnse Mòr',
    'The Far Turtle': "An Sligeanach Fad' às", 'Dungeon': 'Toll-dubh', 'Pirates': 'Spùinneadairean-mara',
    'Ruined Outpost': 'Làrach an Dùin-fhaire', 'Ruined Fortress': 'Làrach an Dùin',
    'Ruined Temple': 'Làrach an Teampaill', 'Travelling Incomprehensible Circus': 'An Siorcas Siubhail Do-thuigsinn',
    'Minor Jetty': 'Cidhe Beag', 'Panthers migration': 'Imrich nam Pantar', 'Random encounter': 'Coinneachadh',
    'The Party': 'A\' Bhuidheann', 'Berkeham Creek of Luck': "Allt an Àigh", 'Miden Monster': 'Uilebheist na Mara',
}
PATTERNS = [   # (regex on the English name, Ròdais template; {b} = nearest burg, {r} = nearest river)
    (r'^Hot Springs of (\w+)$', 'Fuarain Theth {b}'),
    (r'^(\w+) — silver mining town$', '{b} — baile mèinne airgid'),
    (r'^(\w+) Bridge$', 'Drochaid {b}'),
    (r'^(\w+) Lighthouse$', 'Taigh-solais {b}'),
    (r'^(\w+) Battlefield$', 'Àraich {b}'),
    (r'^(\w+) Undead$', 'Marbh-bheò {b}'),
    (r'^(\w+) Forest$', 'Coille Naomh {b}'),
    (r'^(\w+) Obelisk$', 'Carragh {b}'),
    (r'^(\w+) Pillar$', 'Colbh {b}'),
    (r'^(\w+) Column$', 'Calbh {b}'),
    (r'^(\w+) Library$', 'Leabharlann {b}'),
    (r'^(\w+) Melee$', 'Còmhrag {b}'),
    (r'^(\w+) Fair$', 'Fèill {b}'),
    (r'^(\w+) Mausoleum$', 'Tuam {b}'),
]
for i, mk in enumerate(J[L_MARKERS]):
    eng = mk['name']
    b = nearest_burg(mk['x'], mk['y'])['name']
    note = mk.get('note', '')
    new = FIXED.get(eng)
    old_place = None
    if new is None:
        for rx, tpl in PATTERNS:
            m = re.match(rx, eng)
            if m:
                old_place = m.group(1)
                new = tpl.format(b=b)
                break
    if new is None:
        print('unhandled marker:', eng)
        continue
    rename('marker', mk, 'name', new)
    # notes: point the English text at places that exist on this map
    if old_place:
        note = note.replace(old_place, b)
    for rv in set(re.findall(r'the (\w+) River', note)):
        note = note.replace('the %s River' % rv, 'the river %s' % nearest_river(mk['x'], mk['y'])['name'])
    for rv in set(re.findall(r'the (\w+) River', note) + re.findall(r'of the (\w+) River', note)):
        note = note.replace('%s River' % rv, nearest_river(mk['x'], mk['y'])['name'])
    note = note.replace('the Uxblean War', '%s (%s)' % (WAR, WAR_EN)).replace('Uxblean War', WAR)
    note = re.sub(r'local (Pantheon of the Yellow Elephant|Maltont Religion)',
                  lambda m_, i=i: 'the ' + religion_names[i % len(religion_names)], note)
    mk['note'] = note

# ---------------------------------------------------------------- 6. routes
GENERIC = {'trail': 'Slighe', 'path': 'Frith-rathad', 'pass': 'Bealach', 'track': 'Ceum', 'route': 'Slighe-mhara',
           'lane': 'Seòlaid', 'passage': 'Caolas', 'way': 'Slighe-uisge'}
ADJ = {'Misty': 'ceòthach', 'Rustic': 'dùthchail', 'Ancient': 'àrsaidh', 'Twilight': 'ciar', 'Ebon': 'dubh',
       'Cobbled': 'clachach', 'Cracked': 'sgàinte', 'Echoing': 'fuaimneach', 'Great': 'mòr', 'Obscure': 'dorcha',
       'Sacred': 'naomh', 'Shaky': 'critheanach', 'Shrouded': 'falaichte', 'Winding': 'lùbach', 'Breezy': 'gaothach',
       'Spectral': 'taibhseil', 'Frozen': 'reòta', 'Gilded': 'òrach', 'Crimson': 'dearg', 'Divine': 'diadhaidh',
       'Dusk': 'ciar', 'Enchanted': 'seunta', 'Eternal': 'sìorraidh', 'New': 'ùr', 'Old': 'sean', 'Wild': 'fiadhaich',
       'Twisted': 'lùbach', 'Forest': 'coillteach', 'Thorn': 'droighneach', 'Storm': 'stoirmeil',
       'Thunder': 'tàirneanach', 'Rain': 'fliuch', 'Sapphire': 'gorm', 'Whisperwind': 'ciùin', 'Whisper': 'ciùin'}
GEN = {'Moon': 'na gealaich', 'Moonlit': 'na gealaich', 'Raven': 'an fhithich', 'Falcon': 'an t-seabhaig',
       'Phoenix': 'an fhìnics', 'Serpent': 'na nathrach', 'Aurora': 'nam Fear Chlis', 'Flower': 'nam flùr',
       'Dawn': 'na camhanaich'}
for rt in J[L_ROUTES]:
    eng = rt.get('name')
    if not eng:
        continue
    words = eng.split()
    if words[-2:] == ['water', 'way']:
        words = words[:-2] + ['way']
    generic = GENERIC[words[-1]]
    rest = [w for w in words[:-1] if w != 'The']
    new = None
    for w in rest:
        if w in ADJ:
            new = place_name(generic, ADJ[w]); break
        if w in GEN:
            new = generic + ' ' + GEN[w]; break
    if new is None:
        p = rt['points'][0]
        new = generic + ' ' + nearest_burg(p[0], p[1])['name']
    rename('route', rt, 'name', new)

# ---------------------------------------------------------------- 7. zones
ZONE = {'Disease': ("A' Phlàigh Uaine", None), 'Disaster': (None, None), 'Fault': ('Sgàineadh {b}', None),
        'Tsunami': ('Tonn Mhòr {b}', None)}
for z in J[L_ZONES]:
    b = burg_near_cells(z.get('cells', []))
    bn = b['name'] if b else 'Ròdos'
    eng = z['name']
    if eng.endswith('Famine'):
        new = 'Gorta ' + bn
    elif eng.endswith('Drought'):
        new = 'Tiormachd ' + bn
    elif z['type'] == 'Disease':
        new = "A' Phlàigh Uaine"
    elif z['type'] == 'Fault':
        new = 'Sgàineadh ' + bn
    elif z['type'] == 'Tsunami':
        new = 'Tonn Mhòr ' + bn
    else:
        print('unhandled zone:', eng); continue
    rename('zone', z, 'name', new)

# ---------------------------------------------------------------- 8. the quest journey
inn_by_eng = {'The Bold Goblet': 'An Cupa Dàna'}
for jr in J[L_JOURNEYS]:
    if jr.get('name') == 'The Company of the Leaden Hawk':
        rename('journey', jr, 'name', "Buidheann an t-Seabhaig Luaidhe")
    for seg in jr.get('segments', []):
        eng = seg['name']
        pts = seg.get('points', [])
        start = nearest_burg(pts[0][0], pts[0][1])['name'] if pts else 'Ròdos'
        end = nearest_burg(pts[-1][0], pts[-1][1])['name'] if pts else 'Ròdos'
        m = re.match(r'^Meeting at (.+)$', eng)
        if m:
            new = 'Coinneamh aig ' + inn_by_eng.get(m.group(1), 'an taigh-òsta')
        elif re.match(r'^Out of \w+ into the grasslands$', eng):
            new = 'A-mach à %s gu na raointean feòir' % start
        elif eng.startswith('Out of '):
            new = 'A-mach à ' + start
        elif eng.startswith('Rumours in '):
            new = 'Fathannan ann an ' + end
        elif eng == 'Watches kept in the grasslands':
            new = 'Faire anns na raointean feòir'
        elif eng.startswith('On to '):
            new = 'Air adhart gu ' + end
        else:
            print('unhandled journey segment:', eng); continue
        rename('journey', seg, 'name', new)

# ---------------------------------------------------------------- 9. the saved SVG labels
svg = lines[L_SVG]

# One state, one capital. The first pass left burg 1 flagged as a capital beside the real one
# (state.capital, Cathair dhearg); Azgaar then reports a data-integrity error on load and keeps
# the FIRST as capital, which would move the capital to the wrong town. Demote the extra ones to
# cities, in the data and in the saved icon, anchor and label groups.
def move_into_group(svg, element_re, group_open_re):
    m = re.search(element_re, svg)
    if not m:
        return svg
    el = m.group(0)
    svg = svg[:m.start()] + svg[m.end():]
    g = re.search(group_open_re, svg)
    return svg[:g.end()] + el + svg[g.end():]


for b in burgs:
    if b.get('capital') and b['i'] != state['capital']:
        changes.append(('capital', '%s (capital)' % b['name'], '%s (city)' % b['name']))
        b['capital'] = 0
        b['group'] = 'city'
        i = b['i']
        svg = move_into_group(svg, r'<use id="burg%d" [^>]*/>' % i, r'<g id="city" data-group="city"[^>]*data-icon="#icon-circle">')
        svg = move_into_group(svg, r'<use id="anchor%d" [^>]*/>' % i, r'<g id="city" data-group="city"[^>]*data-icon="#icon-anchor">')
        svg = move_into_group(svg, r'<text id="burgLabel%d" [^>]*>[^<]*</text>' % i, r'<g id="labels-city" data-group="city"[^>]*>')


def fix_label(m):
    b = burg_by_id.get(int(m.group(2)))
    if not b:
        return m.group(0)
    if m.group(3) != b['name']:
        changes.append(('burg label', m.group(3), b['name']))
    return m.group(1) + b['name'] + m.group(4)


svg = re.sub(r'(<text id="burgLabel\d+" data-label-type="burg" data-id="(\d+)"[^>]*>)([^<]*)(</text>)', fix_label, svg)
m = re.search(r'(<textPath href="#textPath_stateLabel1"[^>]*>)([^<]*)(</textPath>)', svg)
if m and m.group(2) != state['fullName']:
    changes.append(('state label', m.group(2), state['fullName']))
    svg = svg[:m.start()] + m.group(1) + state['fullName'] + m.group(3) + svg[m.end():]
lines[L_SVG] = svg

# ---------------------------------------------------------------- 10. town features from the history
# citadel, walls, plaza, temple and shanty for every burg, from legendarium/burg_features.json (the
# town plans Azgaar links to are drawn from these); see legendarium/burg_features.py
sys.path.insert(0, os.path.join(HERE, 'legendarium'))
from burg_features import apply as apply_burg_features, finish_records  # noqa: E402
apply_burg_features(J[L_BURGS])
finish_records(lines, J[L_BURGS], J[L_ROUTES])       # anchors of cleared ports out of the SVG; the fort group's town plan

# ---------------------------------------------------------------- write
for n, data in J.items():
    # the source carries some surrogates as \\u escapes (half-emoji in generated notes); write them back the same way
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    lines[n] = re.sub('[\ud800-\udfff]', lambda m: '\\u%04x' % ord(m.group()), text)
out = '\r\n'.join(lines)
open(DST, 'w', encoding='utf-8', newline='').write(out)

# ---------------------------------------------------------------- verify
check = open(DST, encoding='utf-8', newline='').read().split('\r\n')
assert len(check) == RECORDS, 'output has %d records' % len(check)
for n in J:
    json.loads(check[n])                                        # every rewritten section still parses
LEFTOVER = ['Luteley', 'Grantesham', 'Kiverton', 'Marltash', 'Albridge', 'Penrith', 'Towbigham', 'Hatlexe',
            'Bostedbury', 'Uxblean', 'Tuton', 'Clitle', 'Shkell', 'Seann Dhunn', 'City-State Rodos']
left = {w: sum(check[n].count(w) for n in list(J) + [L_SVG]) for w in LEFTOVER}
names = set()
for sec in (L_FEATURES, L_BURGS, L_PROVINCES, L_RIVERS, L_MARKERS, L_ROUTES, L_ZONES, L_RELIGIONS):
    for o in json.loads(check[sec]):
        if isinstance(o, dict) and o.get('name'):
            names.add(o['name'])
agreement = sorted({w for nm in names for w in re.split(r"[\s—()']+", nm) if w and check_agreement(w)})

sections = {}
for sec, old, new in changes:
    sections.setdefault(sec, []).append((old, new))
with open(LOG, 'w', encoding='utf-8') as fh:
    fh.write('# Map changes (finish_map.py)\n\n')
    fh.write('Input `Rodos_renamed.map`, output `Rodos_finished.map`. %d changes.\n\n' % len(changes))
    fh.write('Old names left anywhere in the rewritten sections: %s.\n\n'
             % (', '.join('%s x%d' % kv for kv in left.items() if kv[1]) or 'none'))
    fh.write('Words in map names that break caol le caol: %s.\n\n' % (', '.join(agreement) or 'none'))
    for sec, rows in sections.items():
        fh.write('## %s (%d)\n\n| before | after |\n|---|---|\n' % (sec, len(rows)))
        for old, new in rows:
            fh.write('| %s | %s |\n' % (old, new))
        fh.write('\n')

print('changes:', len(changes), {k: len(v) for k, v in sections.items()})
print('leftover old names:', {k: v for k, v in left.items() if v} or 'none')
print('agreement flags:', agreement or 'none')
