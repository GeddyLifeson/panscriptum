"""
atlas_data.py -- the Atlas's data beyond the master annals, gathered fresh on every build_atlas.py run.

    collect(rec, master_map) -> {'master': [...], 'eras': {K: {...}}, 'meta': {...}, 'maps': [(src, dst)], 'shots': [...]}

It reads, and never writes:
    eras/age_<K>/annals/*.json       each age's annals (dated here by eras/build_era.py's own code, so the Atlas
                                     shows what the writers have written as of this build); if an age will not
                                     date, its last eras/age_<K>/atlas.json is used, and failing that its master
                                     events alone
    eras/THREADS.json, PEOPLE.json, NAMES.json   the threads, people and Dia-thìris names
    legendarium/appendices/A_rulers.md, houses.json   the family trees and ruler lists (Appendix A)
    eras/maps/Diathir_Age_<K>.map (+ age_<K>.report.json, shots/)   the seven era maps
    book sections named by "told_in"  for "Read the telling"
    eras/audio/names/ (optional)     recordings of the names for the glossary's play buttons

The Atlas links forward and back freely (every link both ways); the PDFs point back only. That rule lives in
event_links.footnote_html and is not applied here.
"""
import glob
import html
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ERAS = os.path.join(HERE, 'eras')
LEG = os.path.join(HERE, 'legendarium')
MAPS = os.path.join(ERAS, 'maps')
KEYS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
sys.path.insert(0, LEG)
sys.path.insert(0, ERAS)
import reckoning  # noqa: E402
import event_links  # noqa: E402
import build_book  # noqa: E402

CAT_STYLE = {   # colour and a text glyph (U+FE0E asks for the plain, not the emoji, form)
    'rulers': ('#c9a435', '♛'), 'war': ('#b5473f', '⚔︎'), 'faith': ('#9d6bff', '✶'),
    'coal': ('#d9822b', '◆'), 'trade': ('#7f9a52', '⚖︎'), 'land': ('#4f8fbf', '▲'),
    'law': ('#8fa3c0', '✎︎'), 'humans': ('#b06a3a', '⚓︎'), 'coalblood': ('#d4506e', '❖'),
}
KIND_CAT = {'war': 'war', 'battle': 'war', 'faith': 'faith', 'omen': 'faith', 'reign': 'rulers', 'death': 'rulers',
            'birth': 'rulers', 'law': 'law', 'record': 'law', 'culture': 'law', 'trade': 'trade', 'craft': 'trade',
            'building': 'trade', 'disaster': 'land', 'founding': 'land', 'discovery': 'land', 'voyage': 'land',
            'people': 'land'}
HUMANS = re.compile(r'\b(humans?|the Company|Administration|Commissioners?|settlers?|colonists?|Christian\w*|church|priests?)\b')
COAL = re.compile(r'\b(vein|coals?|galler(?:y|ies)|mines?|miners?|hewers?|seams?|pits?)\b', re.I)
BLOOD = re.compile(r'fuil-ghuail|coal-blood', re.I)


def fold(s):
    return unicodedata.normalize('NFD', str(s).lower()).encode('ascii', 'ignore').decode()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', fold(s)).strip('-')[:60]


def guess_category(e):
    """The category a writer gave, else a guess from the event's kind and words (shown the same; marked guessed)."""
    if e.get('category') in event_links.CATEGORIES:
        return e['category'], False
    text = '%s %s' % (e.get('title', ''), e.get('body', ''))
    if BLOOD.search(text):
        return 'coalblood', True
    k = KIND_CAT.get(e.get('kind'))
    if k in ('war', 'faith', 'rulers'):
        return k, True
    if HUMANS.search(text):
        return 'humans', True
    if COAL.search(text):
        return 'coal', True
    return k or 'land', True


def warn(out, msg):
    out['warnings'].append(msg)
    print('  atlas note:', msg)


# ---------------------------------------------------------------- the annals of every age
def shape(e, rec, links, told=None):
    """One event as the Atlas timeline reads it (the shape of eras/build_era.py's atlas.json)."""
    x = {k: e.get(k) for k in ('id', 'age', 'date', 'y', 'm', 'd', 'era', 'ey', 'title', 'body', 'place', 'kind')}
    x['title'] = rec.resolve(x['title'] or '', link=False)
    x['body'] = rec.resolve(x['body'] or '', link=False)
    x['master'] = bool(e.get('master', True))
    if e.get('canon'):
        x['canon'] = True
    x['year'] = reckoning.display_year(e['y'], e['m'], e['d'], e['age']) if e.get('y') is not None else ''
    x['category'], guessed = guess_category(e)
    if guessed:
        x['cat_guess'] = True
    if e.get('place'):
        x['place_name'] = rec.place_name(e['place'])
    x['links'] = links.get(e['id'], [])
    x['threads'] = [t for t in (e.get('threads') or []) if isinstance(t, str)]
    x['people'] = [p for p in (e.get('people') or []) if isinstance(p, str)]
    x['told_in'] = told if told is not None else None
    return x


def collect_annals(rec, out):
    """-> {K: [event, ...]} in each age's order, master and era events together."""
    try:
        import build_era
    except Exception as ex:                               # noqa: BLE001 -- the Atlas still builds from the master
        warn(out, 'eras/build_era.py would not load (%s); the Atlas shows the master annals only' % ex)
        build_era = None
    dated, recs = {}, {}
    if build_era:
        for k in KEYS:
            if not os.path.isdir(os.path.join(ERAS, 'age_%s' % k, 'annals')):
                continue
            try:
                evs, _ = build_era.date_era(k)
                dated[k], recs[k] = evs, build_era.EraRecord(k, evs)
            except Exception as ex:                       # noqa: BLE001 -- a writer's file mid-edit
                warn(out, 'Age %s would not date (%s)' % (k, str(ex).split('\n')[0][:200]))
    links = {}
    if build_era and dated:
        k0 = next(iter(dated))
        try:
            links = build_era.resolved_links(k0, dated[k0])[0]   # the universe is every age: links both ways, all eras
        except Exception as ex:                           # noqa: BLE001
            warn(out, 'links would not resolve (%s)' % ex)
    if not links:
        uni = {e['id']: dict(e, master=True) for e in rec.events}
        links = event_links.resolve(uni, lambda e: reckoning.display_year(e['y'], e['m'], e['d'], e['age']))
    ages = {}
    for k in KEYS:
        if k in dated:
            r = recs[k]
            ages[k] = [shape(e, r, links, build_era.told_in(k, e['told_in']) if e.get('told_in') else None)
                       for e in dated[k]]
            if r.missing:
                warn(out, 'Age %s: unresolved references %s' % (k, sorted(set(r.missing))[:8]))
            continue
        fb = os.path.join(ERAS, 'age_%s' % k, 'atlas.json')
        if os.path.exists(fb):
            try:
                data = json.load(open(fb, encoding='utf-8'))
                evs = []
                for e in data['events']:
                    e = dict(e, age=k)
                    x = shape(e, rec, {e['id']: e.get('links') or []}, e.get('told_in'))
                    evs.append(x)
                ages[k] = evs
                warn(out, 'Age %s: using its last eras/age_%s/atlas.json' % (k, k))
                continue
            except Exception as ex:                       # noqa: BLE001
                warn(out, 'Age %s: atlas.json unreadable (%s)' % (k, ex))
        ages[k] = [shape(e, rec, links) for e in rec.events if e['age'] == k]
    return ages, (build_era if dated else None)


# ---------------------------------------------------------------- "Read the telling"
def section_of(path, anchor, heading_anchor):
    """The markdown of one book section: from its heading to the next heading of the same or a higher level."""
    text = build_book.read_md(path)
    heads = list(re.finditer(r'^(#{1,3}) (.+)$', text, re.M))
    for i, m in enumerate(heads):
        if not anchor or heading_anchor(m.group(2)) == anchor:
            lvl = len(m.group(1))
            end = next((h.start() for h in heads[i + 1:] if len(h.group(1)) <= lvl), len(text))
            return m.group(2).strip(), text[m.end():end].strip()
    return None, None


def tellings(ages, build_era, rec, out):
    import markdown
    got = {}
    for k, evs in ages.items():
        for e in evs:
            t = e.get('told_in')
            if not t or not build_era:
                continue
            key = '%s|%s|%s' % (k, t.get('where'), t.get('ref'))
            e['told_in'] = dict(t, key=key)
            if key in got:
                continue
            base = os.path.join(ERAS, 'age_%s' % k) if t.get('where') == 'era' else LEG
            head, body = section_of(os.path.join(base, t['file']), t.get('anchor'), build_era.heading_anchor)
            if body is None:
                continue
            body = build_book.plain(rec.resolve(body, link=False))
            words = body.split(' ')
            more = len(words) > 6000
            if more:
                body = ' '.join(words[:6000]) + ' …'
            got[key] = {'book': re.sub(r'[*_]', '', t.get('book') or ''), 'section': re.sub(r'[*_]', '', head or ''),
                        'html': markdown.markdown(body), 'more': more}
    return got


# ---------------------------------------------------------------- Appendix A: family trees and ruler lists
TOKEN = re.compile(r'\{\{(?:date|year):([^}]+)\}\}')


def cell_text(rec, s):
    return build_book.plain(rec.resolve(s.strip(), link=False)).strip()


def trees_and_people(rec, out):
    trees, people, by_name = [], {}, {}

    def person(pid, name, tree, **kw):
        key = fold(re.sub(r'[*_]', '', name.split(',')[0])).strip()
        if key in by_name:
            p = people[by_name[key]]
        else:
            p = people.setdefault(pid, {'id': pid, 'name': re.sub(r'[*_]', '', name), 'trees': [], 'events': [],
                                        'parents': [], 'children': [], 'houses': []})
            by_name[key] = pid
        if tree not in p['trees']:
            p['trees'].append(tree)
        for f, v in kw.items():
            if v and f in ('events',):
                p['events'] += [x for x in v if x not in p['events']]
            elif v and f in ('houses',):
                p['houses'] += [x for x in v if x not in p['houses']]
            elif v and not p.get(f):
                p[f] = v
        return p['id']

    def kin(parent, child):
        if parent and child and parent != child:
            if child not in people[parent]['children']:
                people[parent]['children'].append(child)
            if parent not in people[child]['parents']:
                people[child]['parents'].append(parent)

    path = os.path.join(LEG, 'appendices', 'A_rulers.md')
    if os.path.exists(path):
        text = build_book.read_md(path)
        part = re.split(r'^### II\.', text, flags=re.M)[0]
        blocks = re.split(r'^(?=\*\*)', part, flags=re.M)
        for b in blocks:
            m = re.match(r'\*\*(.+?)\*\*(.*?)\n\s*\n(\|.+?)(?:\n\s*\n|\Z)', b, re.S)
            if not m:
                continue
            title = m.group(1).strip().rstrip('.')
            intro = cell_text(rec, m.group(2))
            lines = [ln for ln in m.group(3).strip().split('\n') if ln.startswith('|')]
            head = [c.strip() for c in lines[0].strip('|').split('|')]
            tid = slug(re.sub(r'\(.*?\)', '', title))
            rows = []
            rel_col = next((c for c in head if re.search(r'came to rule|came to the flame|how they came|generations', c, re.I)), None)
            lineage = bool(re.search(r'generations', rel_col or '', re.I))
            prev = None
            for ln in lines[2:]:
                cells = [c.strip() for c in ln.strip().strip('|').split('|')]
                cells += [''] * (len(head) - len(cells))
                row = dict(zip(head, cells))
                raw_name = row.get('Name', cells[1] if head[0].startswith('No') else cells[0])
                evs = [i for c in cells for i in TOKEN.findall(c)]
                vals = {h: cell_text(rec, v) for h, v in row.items() if h not in ('No.', 'Name')}
                gap = raw_name.startswith('*') and raw_name.endswith('*') and not any(v for h, v in vals.items() if h not in ('Told of in', 'Reign', 'Keeping'))
                name = re.sub(r'[*_]', '', cell_text(rec, raw_name))
                node = {'name': name, 'cells': vals, 'events': evs}
                if gap:
                    node['gap'] = True
                    rows.append(node)
                    prev = None
                    continue
                pid = person('%s-%s' % (tid, len(rows) + 1), raw_name, tid, events=evs,
                             deed=vals.get('The deed') or vals.get('The reign') or vals.get('The keeping') or '')
                node['person'] = pid
                rel = (vals.get(rel_col) or '') if rel_col else ''
                node['rel'] = rel
                if prev and rel_col:
                    before = rows[-1]['cells'].get(rel_col, '')
                    if (lineage and re.match(r'none: (his|her) (son|daughter) follows', before, re.I)) or \
                            (not lineage and re.match(r'(his|her) (son|daughter)\b', rel, re.I)):
                        kin(prev, pid)
                rows.append(node)
                prev = pid
            kind = 'line' if lineage else 'list'
            trees.append({'id': tid, 'title': title, 'intro': intro, 'kind': kind, 'columns': head, 'rel': rel_col,
                          'rows': rows})
    for h in getattr(rec, 'houses', []) or []:
        tid = 'house-' + slug(h['house'])
        members = []
        ids = {}
        for pr in h.get('members', []):
            evs = TOKEN.findall(pr.get('note', ''))
            pid = person('%s-%s' % (tid, pr['id']), pr['name'], tid, events=evs, houses=[h['house']],
                         note=cell_text(rec, pr.get('note', '')), born_date=pr.get('born'), died_date=pr.get('died'),
                         spouse=pr.get('spouse'))
            ids[pr['id']] = pid
            members.append({'id': pr['id'], 'person': pid, 'name': pr['name'], 'parent': pr.get('parent'),
                            'spouse': pr.get('spouse'), 'born': pr.get('born'), 'died': pr.get('died'),
                            'note': cell_text(rec, pr.get('note', '')), 'events': evs})
        for mb in members:
            if mb['parent'] in ids:
                kin(ids[mb['parent']], mb['person'])
        trees.append({'id': tid, 'title': h['house'], 'intro': cell_text(rec, h.get('note', '')), 'kind': 'house',
                      'members': members})
    # eras/PEOPLE.json: the writers' people, merged by id or by name with those of the appendix
    reg = os.path.join(ERAS, 'PEOPLE.json')
    if os.path.exists(reg):
        try:
            raw = json.load(open(reg, encoding='utf-8'))
            for r in (raw.get('people', []) if isinstance(raw, dict) else raw):
                if not isinstance(r, dict) or not r.get('id'):
                    continue
                key = fold(r.get('name', '')).strip()
                pid = by_name.get(key, r['id'])
                p = people.setdefault(pid, {'id': pid, 'name': r.get('name', pid), 'trees': [], 'events': [],
                                            'parents': [], 'children': [], 'houses': []})
                if pid != r['id']:
                    p['alias'] = r['id']
                for f in ('born', 'died', 'first', 'last'):
                    if r.get(f):
                        p[f] = r[f]
                p['houses'] += [x for x in r.get('houses') or [] if x not in p['houses']]
                p['parents'] += [x for x in r.get('parents') or [] if x not in p['parents']]
                p['children'] += [x for x in r.get('children') or [] if x not in p['children']]
        except (ValueError, OSError) as ex:
            warn(out, 'eras/PEOPLE.json unreadable (%s)' % ex)
    return trees, people


# ---------------------------------------------------------------- the maps
def burgs_of(path):
    rows = open(path, encoding='utf-8', newline='').read().split('\r\n')
    if len(rows) != 53:
        raise ValueError('%s should have 53 CRLF records' % os.path.basename(path))
    b = json.loads(rows[15])
    return b


def map_meta(master_map, out):
    maps, copies, names = {}, [], {}
    listing = [('M', master_map, 'Diathir.map')] + [(k, os.path.join(MAPS, 'Diathir_Age_%s.map' % k),
                                                     'maps/Diathir_Age_%s.map' % k) for k in KEYS]
    for key, src, dst in listing:
        if not os.path.exists(src):
            warn(out, 'no map for Age %s (%s)' % (key, os.path.relpath(src, HERE)))
            continue
        try:
            b = burgs_of(src)
        except (ValueError, OSError) as ex:
            warn(out, 'map %s unreadable (%s)' % (os.path.basename(src), ex))
            continue
        live = [x for x in b[1:] if isinstance(x, dict) and x.get('i') and not x.get('removed')]
        probe = live[0] if live else {'i': 0, 'name': ''}
        m = {'file': dst, 'n': len(b), 'burgs': len(live), 'probe': [probe['i'], probe.get('name', '')]}
        rp = os.path.join(MAPS, 'age_%s.report.json' % key)
        if key != 'M' and os.path.exists(rp):
            try:
                rep = json.load(open(rp, encoding='utf-8'))
                m['placeIds'] = rep.get('placeIds') or {}
            except ValueError:
                pass
        maps[key] = m
        for x in live:
            names.setdefault(str(x['i']), {})[key] = x.get('name', '')
        if key != 'M':
            copies.append((src, dst))
    shots = {}
    for f in sorted(glob.glob(os.path.join(MAPS, 'shots', 'Diathir_Age_*_*.png'))):
        m = re.match(r'Diathir_Age_([IVX]+)_(\w+)\.png$', os.path.basename(f))
        if m and m.group(1) in KEYS:
            shots.setdefault(m.group(1), []).append(m.group(2))
            copies.append((f, 'maps/shots/' + os.path.basename(f)))
    return maps, names, shots, copies


# ---------------------------------------------------------------- names, threads, audio
def names_list(out):
    p = os.path.join(ERAS, 'NAMES.json')
    if not os.path.exists(p):
        return []
    try:
        raw = json.load(open(p, encoding='utf-8'))
    except ValueError as ex:
        warn(out, 'eras/NAMES.json unreadable (%s)' % ex)
        return []
    rows = raw.get('names', []) if isinstance(raw, dict) else raw
    dead = {'rejected', 'retired', 'withdrawn', 'dropped'}
    return [[e['dt'], e.get('gloss') or e.get('en') or '', e.get('en') or '', e.get('variants') or [], e.get('kind') or '']
            for e in rows if isinstance(e, dict) and e.get('dt') and str(e.get('status', '')).lower() not in dead]


def threads_list(out):
    p = os.path.join(ERAS, 'THREADS.json')
    if not os.path.exists(p):
        return {}
    try:
        raw = json.load(open(p, encoding='utf-8'))
    except ValueError as ex:
        warn(out, 'eras/THREADS.json unreadable (%s)' % ex)
        return {}
    rows = raw.get('threads', []) if isinstance(raw, dict) else raw
    return {r['id']: r for r in rows if isinstance(r, dict) and r.get('id')}


def audio(names, out):
    """eras/audio/names/: a manifest.json {dt: file} or files named by the name's slug (.mp3/.ogg/.wav/.m4a)."""
    d = os.path.join(ERAS, 'audio', 'names')
    got, copies = {}, []
    if not os.path.isdir(d):
        return got, copies
    man = os.path.join(d, 'manifest.json')
    listed = json.load(open(man, encoding='utf-8')) if os.path.exists(man) else {}
    files = {os.path.splitext(f)[0]: f for f in os.listdir(d) if f.lower().endswith(('.mp3', '.ogg', '.wav', '.m4a'))}
    for n in names:
        f = listed.get(n[0]) or files.get(slug(n[0]))
        if f and os.path.exists(os.path.join(d, f)):
            got[n[0]] = 'audio/names/' + f
            copies.append((os.path.join(d, f), 'audio/names/' + f))
    return got, copies


# ---------------------------------------------------------------- all of it
def collect(rec, master_map):
    out = {'warnings': []}
    ages, build_era = collect_annals(rec, out)
    tell = tellings(ages, build_era, rec, out)
    trees, people = trees_and_people(rec, out)
    known = {e['id'] for evs in ages.values() for e in evs}
    for evs in ages.values():                            # the events each person takes part in
        for e in evs:
            for pid in e['people']:
                p = people.get(pid) or next((q for q in people.values() if q.get('alias') == pid), None)
                if p and e['id'] not in p['events']:
                    p['events'].append(e['id'])
    for p in people.values():
        p['events'] = [i for i in p['events'] if i in known]
    maps, burg_names, shots, copies = map_meta(master_map, out)
    names = names_list(out)
    sounds, acopies = audio(names, out)
    threads = threads_list(out)
    counts = {}
    for evs in ages.values():
        for e in evs:
            for t in e['threads']:
                counts[t] = counts.get(t, 0) + 1
    for t, r in threads.items():
        r['count'] = counts.get(t, 0)
    ages_meta = []
    for k in KEYS:
        era = reckoning.ERA[k]
        dt, en, css = build_book.AGE_NAMES[k]
        ages_meta.append({'key': k, 'dt': dt, 'en': en, 'css': '--' + css, 'span': reckoning.display_span(k),
                          'abbr': era[3], 'era': era[4], 'era_dt': era[5], 'first': era[1], 'last': era[2],
                          'events': len(ages.get(k, [])), 'era_events': sum(1 for e in ages.get(k, []) if not e['master'])})
    meta = {'ages': ages_meta,
            'categories': {c: {'name': n, 'color': CAT_STYLE[c][0], 'icon': CAT_STYLE[c][1]} for c, n in event_links.CATEGORIES.items()},
            'link_types': {t: {'arrow': a, 'out': o, 'in': i} for t, (a, o, i) in event_links.TYPES.items()},
            'threads': threads, 'people': people, 'trees': trees, 'names': names, 'audio': sounds,
            'months': reckoning.MONTHS, 'months_en': reckoning.ENGLISH_MONTHS, 'maps': maps, 'burgs': burg_names,
            'shots': shots, 'tellings': tell, 'warnings': out['warnings']}
    return {'ages': ages, 'meta': meta, 'copies': copies + acopies}
