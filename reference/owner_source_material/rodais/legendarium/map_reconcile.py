"""
map_reconcile.py -- bring the Dia-thìr map into line with its history, layer by layer.

Every layer Azgaar generated (faiths, goods and markets, the state and its shires, the regiments, the land,
markers and routes, the arms) was read against the annals, the gazetteer and the appendices. Each layer's
findings are in reconcile/<layer>.json; their "map_edits" say what on the map had to change. This script
applies all of them, in a fixed order, and then the integrator's own edits in reconcile/integration.json
(which also lists the few proposal edits it sets aside; INTEGRATION.md gives the reasons).
Last come the faiths as they are now (reconcile/faiths.json): three, and the land that keeps none.

    python map_reconcile.py     # Rodos_finished.map, Diathir_Atlas/Diathir.map and world.json, in place

finish_map.py calls reconcile_records() after burg_features.finish_records(), so the edits land on the map
as it stands after the harbour towns were moved (the faith of a moved town is set on its NEW cell).

Edit forms (a .map is 53 CRLF-joined records; see finish_map.py):
    {"record": 29, "path": "[2].center", "old": 40, "value": 3104}     JSON record: set the value at the path
    {"record": 1, "path": ".units.distance.scale", "value": 0.2}       (object records; the leading dot is optional)
    {"record": 26, "path": "[2973]", "old": 3, "value": 7}              comma record (a cell array): set one cell
    {"record": 16, "path": "(whole record: ...)", "value": "0,0,..."}   replace a cell array whole
    {"record": 15, "path": "[419].production", "op": "append", "value": {...}}   append to a list, once
    {"record": 35, "path": "", "op": "append", "value": {...}}          append to a record that is itself a list, once
    {"record": 35, "path": "[28].note", "mode": "replace-substring", "old": "...", "value": "..."}
    {"record": 31, "path": "append as name base 43 ...", "value": "Dia-thìris|7|18||0|..."}
    {"record": 49, "action": "delete_indices", "indices": [...], "match": [...]}  remove relief icons
    {"record": 29, "action": "replace_religions", "old_names": [...], "value": [...],     the faiths list anew,
     "cells": {"remap": {"4": 1, ...}, "by_culture": {"3": {"1": 3, "2": 1}}}}          and the cells to match
"old", where given, must be what the map holds (or the value itself, when the edit is already in).

replace_religions (reconcile/faiths.json) sets record 29 whole and renumbers the cell religion array (record 26):
each cell's faith goes through "remap", or, for a faith in "by_culture", through the table for the cell's culture
(record 19). The edits of earlier layers on records 26 and 29 were written against the old list; on a map where the
new list is already in, the record-29 edits before it are passed over and each record-26 edit before it is checked
against its value as renumbered, so a second run changes nothing.

The climate, the sea, dubhan and the loose ends of the roads come after the faiths (reconcile/climate.json,
dubhan.json, loose_ends.json), then the tellings read against the Gaelic tales (reconcile/tales.json), and last the calendar
(reconcile/calendar.json: the map's era and year, and every dated note, in the Dubhan Era), with four more edit forms:
    {"record": 39, "path": "(whole record: pack.ice)", "value": []}      a JSON record replaced whole
    {"record": 11, "action": "recompute_temperature"}                    grid.cells.temp made anew, as Azgaar's
        Temperature.compute() makes it, from the settings (record 1: climate.temperature, geography.coordinates,
        units.height.exponent, graph.height), the grid's points and cellsX (record 6) and its heights (record 7);
        so the temperatures always agree with the latitude and climate set in record 1; with "frame": {latT, latN,
        ...} they are computed for that frame instead of record 1's (the climate was set for the frame of
        climate.json, and the later place layer moves the frame without changing the weather)
    {"record": 5, "action": "empty_svg_group", "group": "ice"}           a saved SVG group emptied (the drawn ice)
    {"record": 37, "action": "split_route", "route": 119, "points": [...], "pieces": [{"i": 119, "from": 0,
        "to": 3, "group": "trails", "name": "...", "d": "M..."}, {"i": 446, ...}, ...]}
        one route cut at its junctions into pieces (the first keeps the route's id, the others are new routes
        appended with the next free ids): each piece's points, group and name; the cells' route links
        (record 36) of each piece's stretch; and the saved <path id="routeN"> of each piece, with the path
        Azgaar's Routes.getPath draws for it ("d"), placed after the route's own path

After the calendar comes the creation (reconcile/creation.json): the summit of the island named for the Mason's
line, Binnean a' Chlachair, as a marker of its own (record 35).

After the creation comes the prose (reconcile/prose.json): the map's visible notes, the markers' (record 35) and
the regiments' and fleets' (record 14), each set whole in the voice of the island's place-lore; the earlier edits
of those same notes are set aside by its "skip" list, so the notes as they stand are the only ones checked.

Last comes the place (reconcile/place.json): the distance scale (0.14 miles to the unit, an island about the size
of Northern Ireland) and the map's frame in the Atlantic west of the Hebrides; its "skip" list sets aside the
earlier layers' scale and frame, and its temperatures stay those computed for the climate layer's frame.

Beside the edits it derives what follows from them: a route regrouped to "roads" has its saved
<path id="routeN"> moved from <g id="trails"> into <g id="roads"> (record 5), in route order as Azgaar draws
them; and the rural totals of the cultures (record 13) and of the states (record 14) follow the cell culture,
state and population arrays.

Byte-safe like burg_features.py: records are split on CRLF, every record it rewrites must round-trip before it
is touched, only the records named in RECORDS_TOUCHED may change, and running it twice changes nothing.
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RECON = os.path.join(HERE, 'reconcile')
WORLD = os.path.join(HERE, 'world.json')
MAPS = [os.path.join(ROOT, 'Rodos_finished.map'), os.path.join(ROOT, 'Diathir_Atlas', 'Diathir.map')]

RECORDS = 53
L_SETTINGS, L_BIOMES, L_SVG, L_TEMP, L_FEATURES, L_CULTURES, L_STATES, L_BURGS = 1, 3, 5, 11, 12, 13, 14, 15
L_BIOME, L_CELL_BURG, L_CELL_CULTURE, L_POP, L_CELL_STATE, L_CELL_RELIGION, L_CELL_PROVINCE = 16, 17, 19, 21, 25, 26, 27
L_RELIGIONS, L_PROVINCES, L_NAMEBASES, L_RIVERS, L_MARKERS, L_ROUTES, L_ZONES = 29, 30, 31, 32, 35, 37, 38
L_CELL_GOOD, L_GOODS, L_RELIEF = 40, 41, 49
L_GRID, L_HEIGHT, L_CELL_ROUTES, L_ICE = 6, 7, 36, 39
CELL_ARRAYS = {11, 16, 19, 21, 26, 40}
JSON_RECORDS = {1, 3, 13, 14, 15, 29, 30, 35, 36, 37, 39, 41, 49}
RECORDS_TOUCHED = CELL_ARRAYS | JSON_RECORDS | {L_SVG, L_NAMEBASES}

# the order the layers are applied in: the state and its shires first, the land (whole cell arrays) last
ORDER = ['state', 'heraldry', 'religions', 'economy', 'military', 'markers_routes', 'land', 'integration', 'faiths',
         'climate', 'dubhan', 'loose_ends', 'tales', 'calendar', 'creation', 'prose', 'place']


def dump(data):
    # the serialisation of finish_map.py and burg_features.py: compact, UTF-8, lone surrogates as \u escapes
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return re.sub('[\ud800-\udfff]', lambda m: '\\u%04x' % ord(m.group()), text)


def load_edits():
    """[(layer, edit)] in ORDER, less the edits a later layer ("skip": integration.json, faiths.json) sets aside."""
    props = {}
    for layer in ORDER:
        path = os.path.join(RECON, layer + '.json')
        props[layer] = json.load(open(path, encoding='utf-8'))
    skip = {(s['layer'], s['record'], s['path']) for layer in ORDER for s in props[layer].get('skip', [])}
    out = []
    for layer in ORDER:
        for e in props[layer]['map_edits']:
            if (layer, e.get('record'), e.get('path')) in skip:
                continue
            out.append((layer, e))
    return out


# ---------------------------------------------------------------- paths into JSON records
TOKEN = re.compile(r'\[(\d+)\]|\.?([A-Za-z_][A-Za-z_0-9]*)')


def parse_path(path):
    keys, pos = [], 0
    while pos < len(path):
        m = TOKEN.match(path, pos)
        assert m and m.end() > pos, 'bad path %r' % path
        keys.append(int(m.group(1)) if m.group(1) is not None else m.group(2))
        pos = m.end()
    return keys


def walk(data, keys):
    for k in keys[:-1]:
        data = data[k]
    return data, keys[-1]


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------- one edit
def apply_json_edit(data, e, where):
    if e.get('op') == 'append' and e['path'] == '':      # the record is itself the list (markers: once by id,
        v = e['value']                                   # so a later layer may still set the new one's note)
        had = [x for x in data if same(x, v) or (isinstance(x, dict) and 'i' in v and x.get('i') == v['i'])]
        if had:
            assert had[0].get('name') == v.get('name'), '%s: id %s is already taken by %r' % (where, v.get('i'), had[0].get('name'))
        else:
            data.append(v)
        return
    keys = parse_path(e['path'])
    parent, k = walk(data, keys)
    if e.get('op') == 'append':
        lst = parent[k]
        if not any(same(x, e['value']) for x in lst):
            lst.append(e['value'])
        return
    if e.get('mode') == 'replace-substring':
        cur = parent[k]
        if e['old'] in cur:
            assert cur.count(e['old']) == 1, '%s: %r is not unique' % (where, e['old'])
            parent[k] = cur.replace(e['old'], e['value'])
        else:
            assert e['value'] in cur, '%s: neither the old nor the new text is there' % where
        return
    exists = (k in parent) if isinstance(parent, dict) else (k < len(parent))
    cur = parent[k] if exists else None
    if 'old' in e and not same(cur, e['value']):
        assert same(cur, e['old']), '%s: expected %r, found %r' % (where, e['old'], cur)
    parent[k] = e['value']


def relief_edits(icons, edits, where):
    """Record 49: the icon renames (made before the deletions, as the land layer lists them) and the deletions."""
    dels = [e for e in edits if e.get('action') == 'delete_indices']
    assert len(dels) <= 1
    gone = sorted(dels[0]['indices']) if dels else []
    match = dict(zip(dels[0]['indices'], dels[0]['match'])) if dels else {}
    done = bool(gone) and not all(i < len(icons) and same(icons[i], match[i]) for i in gone)

    def at(i):                                          # an index as it was before the deletions
        return i - sum(1 for g in gone if g < i) if done else i
    for e in edits:
        if e.get('action'):
            continue
        keys = parse_path(e['path'])
        keys[0] = at(keys[0])
        apply_json_edit(icons, dict(e, path=''.join('[%d]' % k if isinstance(k, int) else '.' + k for k in keys)), where)
    if gone and not done:
        for i in sorted(gone, reverse=True):
            assert same(icons[i], match[i]), '%s: relief icon %d is not the one to delete' % (where, i)
            del icons[i]


def regroup_routes(svg, routes):
    """Every route in the "roads" group gets its saved path in <g id="roads">, in route order; out of any other group."""
    roads = [r['i'] for r in routes if r.get('group') == 'roads']
    if not roads:
        return svg
    els = {}
    for i in roads:
        m = re.search(r'<path id="route%d" [^>]*/>' % i, svg)
        assert m, 'no saved path for route %d' % i
        els[i] = m.group(0)
        svg = svg[:m.start()] + svg[m.end():]
    g = re.search(r'<g id="roads" data-group="roads"[^>]*?(/?)>', svg)
    assert g, 'no roads group in the SVG'
    if g.group(1):                                     # an empty group is saved self-closing
        svg = svg[:g.start()] + g.group(0)[:-2] + '></g>' + svg[g.end():]
        g = re.search(r'<g id="roads" data-group="roads"[^>]*>', svg)
    end = svg.index('</g>', g.end())
    assert not re.search(r'<path id="route', svg[g.end():end]), 'roads group holds a route that is not a road'
    return svg[:g.end()] + ''.join(els[i] for i in roads) + svg[end:]


def cells(text):
    return text.split(',')


def renumber_faith(value, culture, e):
    """A cell's faith under a replace_religions edit: by the cell's culture where the table has one."""
    c = e['cells']
    v = str(value)
    if v in c.get('by_culture', {}):
        return str(c['by_culture'][v][str(culture)])
    return str(c['remap'][v])


def replace_religions(parsed, arrays, e, where):
    names = [r.get('name') for r in parsed[L_RELIGIONS]]
    assert names == e['old_names'], '%s: the faiths on the map are %s' % (where, names)
    arrays[L_CELL_RELIGION] = [renumber_faith(v, c, e) for v, c in zip(arrays[L_CELL_RELIGION], arrays[L_CELL_CULTURE])]
    parsed[L_RELIGIONS] = json.loads(json.dumps(e['value']))


def num(s):
    return float(s) if s else 0.0


def js_round(v, d=0):
    """Math.round as JavaScript does it (halves up), to d places: Azgaar's rn()."""
    m = 10 ** d
    return math.floor(v * m + 0.5) / m


def recompute_temperature(settings, grid, heights, frame=None):
    """grid.cells.temp, as Azgaar's Temperature.compute() makes it: a sea-level temperature for each row of the
    grid from its latitude (between the equator's and the pole's), less a lapse with height above sea level."""
    t = settings['climate']['temperature']
    eq, north, south = t['equator'], t['northPole'], t['southPole']
    tropics, flat = (16, -20), 0.15
    tn = eq - tropics[0] * flat
    kn = (tn - north) / (90 - tropics[0])
    ts = eq + tropics[1] * flat
    ks = (ts - south) / (90 + tropics[1])
    exponent = settings['units']['height']['exponent']

    def sea(lat):
        if tropics[1] <= lat <= tropics[0]:
            return eq - abs(lat) * flat
        return tn - (lat - tropics[0]) * kn if lat > 0 else ts + (lat - tropics[1]) * ks

    def lapse(h):
        return 0 if h < 20 else js_round((h - 18) ** exponent / 1000 * 6.5)
    co = frame or settings['geography']['coordinates']
    height = settings['graph']['height']
    cx, points = grid['cellsX'], grid['points']
    out = []
    for row in range(0, len(heights), cx):
        lat = co['latN'] - points[row][1] / height * co['latT']
        s = sea(lat)
        for k in range(row, row + cx):
            out.append(str(int(max(-128, min(127, s - lapse(int(heights[k])))))))   # Int8Array: truncated
    return out


def empty_svg_group(svg, gid):
    """<g id="gid" ...>...</g> saved empty, as Azgaar saves a layer with nothing in it (<g id="gid" .../>)."""
    m = re.search(r'<g id="%s"([^>]*?)(/?)>' % re.escape(gid), svg)
    assert m, 'no <g id="%s"> in the SVG' % gid
    if m.group(2):
        return svg
    end = svg.index('</g>', m.end())
    assert '<g' not in svg[m.end():end], 'the %s group holds groups of its own' % gid
    return svg[:m.start()] + '<g id="%s"%s/>' % (gid, m.group(1)) + svg[end + 4:]


def split_route(routes, links, e, where):
    """Record 37 and the cells' route links (record 36): one route cut into the pieces the edit gives.
    Returns [(route id, d, the route whose saved path it follows)] for the saved SVG."""
    rid = e['route']
    pts = e['points']
    byid = {r['i']: r for r in routes}
    pieces = e['pieces']
    assert pieces[0]['i'] == rid and pieces[0]['from'] == 0 and pieces[-1]['to'] == len(pts) - 1, where
    for a, b in zip(pieces, pieces[1:]):
        assert a['to'] == b['from'], '%s: the pieces must meet' % where
    done = all(p['i'] in byid and same(byid[p['i']]['points'], pts[p['from']:p['to'] + 1]) for p in pieces)
    if not done:
        assert same(byid[rid]['points'], pts), '%s: route %d is not the one to split' % (where, rid)
        for p in pieces[1:]:
            assert p['i'] not in byid, '%s: route %d already exists' % (where, p['i'])
    for p in pieces:
        seg = [list(x) for x in pts[p['from']:p['to'] + 1]]
        if p['i'] in byid:
            r = byid[p['i']]
        else:
            r = {'i': p['i'], 'group': p['group'], 'name': p['name'], 'feature': byid[rid]['feature'], 'points': seg}
            routes.append(r)
            byid[p['i']] = r
        r['group'], r['points'] = p['group'], seg
        if p.get('name'):
            r['name'] = p['name']
        for a, b in zip(seg, seg[1:]):
            for x, y in ((a[2], b[2]), (b[2], a[2])):
                cell = links.get(str(x), {})
                if cell.get(str(y)) in (rid, p['i']):
                    cell[str(y)] = p['i']
    assert [r['i'] for r in routes] == sorted(r['i'] for r in routes), '%s: routes out of id order' % where
    return [(p['i'], p['d'], rid) for p in pieces]


def draw_route_splits(svg, paths):
    """The saved path of each piece of a split route: the route's own path redrawn, each new one after the piece
    before it."""
    prev = None
    for i, d, rid in paths:
        el = '<path id="route%d" d="%s"/>' % (i, d)
        m = re.search(r'<path id="route%d" d="[^"]*"/>' % i, svg)
        if m:
            svg = svg[:m.start()] + el + svg[m.end():]
        else:
            m = re.search(r'<path id="route%d" d="[^"]*"/>' % prev, svg)
            svg = svg[:m.end()] + el + svg[m.end():]
        prev = i
    return svg


def reconcile_records(lines, edits=None):
    """Apply every edit to a list of 53 raw records, in place. Returns the numbers of the records it changed."""
    assert len(lines) == RECORDS
    edits = load_edits() if edits is None else edits
    before = list(lines)
    parsed = {}
    for n in JSON_RECORDS:
        parsed[n] = json.loads(lines[n])
        assert dump(parsed[n]) == lines[n], 'record %d does not round-trip; refusing to rewrite it' % n
    arrays = {n: cells(lines[n]) for n in CELL_ARRAYS}
    for n, a in arrays.items():
        assert ','.join(a) == lines[n]
    old_pop, old_culture = list(arrays[L_POP]), list(arrays[L_CELL_CULTURE])
    relief, svg_groups, route_paths = [], [], []
    faiths = [k for k, (_, e) in enumerate(edits) if e.get('action') == 'replace_religions']
    assert len(faiths) <= 1
    faiths_at = faiths[0] if faiths else None
    faiths_in = faiths_at is not None and same(parsed[L_RELIGIONS], edits[faiths_at][1]['value'])
    for k, (layer, e) in enumerate(edits):
        n = e['record']
        where = '%s record %d %s' % (layer, n, e.get('path') or e.get('action'))
        if faiths_at is not None and k <= faiths_at and n in (L_RELIGIONS, L_CELL_RELIGION):
            fe = edits[faiths_at][1]
            if k == faiths_at:
                if not faiths_in:
                    replace_religions(parsed, arrays, fe, where)
                continue
            if not faiths_in:
                pass                                   # the old list is still there: apply the edit as written
            elif n == L_RELIGIONS:
                continue                               # made on the old list, which the new one replaced
            else:
                assert not e['path'].startswith('(whole record'), where
                i = parse_path(e['path'])[0]
                want = renumber_faith(e['value'], arrays[L_CELL_CULTURE][i], fe)
                assert arrays[n][i] == want, '%s: expected %s (renumbered), found %s' % (where, want, arrays[n][i])
                continue
        if e.get('action') == 'recompute_temperature':
            assert n == L_TEMP, where
            arrays[n] = recompute_temperature(parsed[L_SETTINGS], json.loads(lines[L_GRID]), cells(lines[L_HEIGHT]),
                                              e.get('frame'))
            assert len(arrays[n]) == len(cells(before[n])), where
        elif e.get('action') == 'empty_svg_group':
            assert n == L_SVG, where
            svg_groups.append(e['group'])
        elif e.get('action') == 'split_route':
            assert n == L_ROUTES, where
            route_paths.extend(split_route(parsed[L_ROUTES], parsed[L_CELL_ROUTES], e, where))
        elif n == L_RELIEF:
            relief.append(e)
        elif n == L_NAMEBASES:
            assert e['path'].startswith('append as name base'), where
            bases = lines[n].split('/')
            if e['value'] not in bases:
                assert not any(b.split('|')[0] == e['value'].split('|')[0] for b in bases), '%s: another base of that name' % where
                lines[n] = lines[n] + '/' + e['value']
        elif n in CELL_ARRAYS:
            if e['path'].startswith('(whole record'):
                new = cells(e['value'])
                assert len(new) == len(arrays[n]), '%s: %d values for %d cells' % (where, len(new), len(arrays[n]))
                arrays[n] = new
            else:
                i = parse_path(e['path'])[0]
                cur = arrays[n][i]
                if 'old' in e and cur != str(e['value']):
                    assert cur == str(e['old']), '%s: expected %s, found %s' % (where, e['old'], cur)
                arrays[n][i] = str(e['value'])
        elif n in JSON_RECORDS and e.get('path', '').startswith('(whole record'):
            parsed[n] = json.loads(json.dumps(e['value']))
        elif n in JSON_RECORDS:
            apply_json_edit(parsed[n], e, where)
        else:
            raise AssertionError('%s: no edits are expected in record %d' % (where, n))
    if relief:
        relief_edits(parsed[L_RELIEF], relief, 'relief')
    # the cultures' rural totals follow the cells (population in thousands, as Azgaar keeps it)
    for i, (p0, c0, p1, c1) in enumerate(zip(old_pop, old_culture, arrays[L_POP], arrays[L_CELL_CULTURE])):
        if p0 != p1 or c0 != c1:
            parsed[L_CULTURES][int(c0)]['rural'] -= num(p0)
            parsed[L_CULTURES][int(c1)]['rural'] += num(p1)
    for c in parsed[L_CULTURES]:
        if abs(c['rural']) < 1e-3:                    # a culture left with no cells (the cell array rounds to 4 places)
            c['rural'] = 0
    # and so do the states' (the cell state array itself is not edited)
    for p0, p1, st in zip(old_pop, arrays[L_POP], cells(lines[L_CELL_STATE])):
        if p0 != p1:
            parsed[L_STATES][int(st)]['rural'] -= num(p0)
            parsed[L_STATES][int(st)]['rural'] += num(p1)
    for st in parsed[L_STATES]:
        if abs(st.get('rural', 0)) < 1e-3:
            st['rural'] = 0
    for gid in svg_groups:
        lines[L_SVG] = empty_svg_group(lines[L_SVG], gid)
    lines[L_SVG] = draw_route_splits(lines[L_SVG], route_paths)
    lines[L_SVG] = regroup_routes(lines[L_SVG], parsed[L_ROUTES])
    for n in JSON_RECORDS:
        lines[n] = dump(parsed[n])
    for n in CELL_ARRAYS:
        lines[n] = ','.join(arrays[n])
    changed = {n for n in range(RECORDS) if lines[n] != before[n]}
    assert changed <= RECORDS_TOUCHED, 'an unexpected record changed: %s' % sorted(changed - RECORDS_TOUCHED)
    for n in CELL_ARRAYS:
        assert len(cells(lines[n])) == len(cells(before[n]))
    assert lines[L_SVG].count('<path id="route') == len(parsed[L_ROUTES]), 'a route without its saved path, or a path without its route'
    return changed


# ---------------------------------------------------------------- world.json, the map as data for the writers
def strip_note(note):
    t = re.sub(r'<iframe.*?</iframe>', '', note or '', flags=re.S)
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub('[\ud800-\udfff]', '', t).strip()     # without the half-glyphs of the carved inscriptions


def world_digest(lines):
    """The digest of names and ids the history is written against (legendarium/world.json)."""
    J = {n: json.loads(lines[n]) for n in (L_CULTURES, L_STATES, L_BURGS, L_RELIGIONS, L_PROVINCES, L_RIVERS,
                                           L_MARKERS, L_ZONES, L_FEATURES)}
    cult = {c['i']: c['name'] for c in J[L_CULTURES]}
    rel = {r['i']: r['name'] for r in J[L_RELIGIONS]}
    prov = {p['i']: p['name'] for p in J[L_PROVINCES] if isinstance(p, dict)}
    cell_rel = cells(lines[L_CELL_RELIGION])
    cell_prov = cells(lines[L_CELL_PROVINCE])
    cell_burg = cells(lines[L_CELL_BURG])
    state = J[L_STATES][1]
    burgs = [b for b in J[L_BURGS] if isinstance(b, dict) and b.get('i') and not b.get('removed')]
    by_id = {b['i']: b for b in burgs}
    w = {'state': {'name': state['name'], 'fullName': state['fullName'],
                   'capital': '%s (burg %d)' % (by_id[state['capital']]['name'], state['capital'])}}
    w['cultures'] = [{'id': c['i'], 'name': c['name']} for c in J[L_CULTURES]]
    w['faiths'] = [{'id': r['i'], 'name': r['name'], 'type': r['type'], 'form': r['form'], 'deity': r.get('deity'),
                    'culture': cult[r['culture']]} for r in J[L_RELIGIONS] if r['i']]
    w['provinces'] = [{'id': p['i'], 'name': p['name'], 'fullName': p['fullName'], 'seat': p.get('burg', 0)}
                      for p in J[L_PROVINCES] if isinstance(p, dict)]
    w['burgs'] = [{'id': b['i'], 'name': b['name'], 'x': b['x'], 'y': b['y'], 'culture': cult[b['culture']],
                   'province': prov.get(int(cell_prov[b['cell']]), ''), 'faith': rel[int(cell_rel[b['cell']])],
                   'population': int(round(b['population'] * 1000)), 'port': bool(b.get('port')),
                   'capital': bool(b.get('capital')), 'citadel': bool(b.get('citadel')), 'walls': bool(b.get('walls')),
                   'temple': bool(b.get('temple')), 'group': b['group']} for b in burgs]
    w['rivers'] = [{'id': r['i'], 'name': r['name'], 'length': int(round(r.get('length', 0))), 'type': r.get('type')}
                   for r in J[L_RIVERS]]

    def nearest(x, y):
        return min(burgs, key=lambda b: ((b['x'] - x) ** 2 + (b['y'] - y) ** 2, b['i']))['i']
    w['markers'] = [{'id': m['i'], 'type': m['type'], 'name': m['name'], 'x': m['x'], 'y': m['y'],
                     'note': strip_note(m.get('note')), 'nearest_burg': nearest(m['x'], m['y'])} for m in J[L_MARKERS]]
    w['zones'] = []
    for z in J[L_ZONES]:
        seen = []
        for c in z['cells']:
            b = int(cell_burg[c])
            if b and b not in seen:
                seen.append(b)
        w['zones'].append({'id': z['i'], 'name': z['name'], 'type': z['type'], 'cells': len(z['cells']), 'burgs': seen})
    w['military'] = [{'name': r['name'], 'type': 'fleet' if r.get('n') else 'regiment', 'x': r['x'], 'y': r['y'],
                      'stationed_burg': nearest(r.get('bx', r['x']), r.get('by', r['y']))} for r in state.get('military', [])]
    w['features'] = [{'id': f['i'], 'type': f['type'], 'name': f['name']} for f in J[L_FEATURES] if isinstance(f, dict)]
    return w


def write_world(lines):
    raw = open(WORLD, encoding='utf-8').read()
    old = json.loads(raw)
    new = world_digest(lines)
    # keep the digest's own order of keys and any key it carries that the map does not give
    out = {k: new.get(k, v) for k, v in old.items()}
    text = json.dumps(out, ensure_ascii=False, indent=0)
    if text != raw:
        open(WORLD, 'w', encoding='utf-8').write(text)
    return text != raw


def apply_to_map(path, edits=None):
    raw = open(path, encoding='utf-8', newline='').read()       # newline='' keeps the CRLF record separators
    lines = raw.split('\r\n')
    assert len(lines) == RECORDS, '%s: expected %d records, got %d' % (path, RECORDS, len(lines))
    new = list(lines)
    changed = reconcile_records(new, edits)
    out = '\r\n'.join(new)
    if out != raw:
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(out)
    check = open(path, encoding='utf-8', newline='').read().split('\r\n')
    assert len(check) == RECORDS and check == new
    return changed, check


if __name__ == '__main__':
    edits = load_edits()
    last = None
    for path in MAPS:
        if not os.path.isfile(path):
            print('skip (not built):', os.path.relpath(path, ROOT))
            continue
        changed, last = apply_to_map(path, edits)
        print('%s: records changed %s' % (os.path.relpath(path, ROOT), sorted(changed) or 'none'))
    if last:
        print('world.json:', 'rewritten' if write_world(last) else 'unchanged')
    sys.exit(0)
