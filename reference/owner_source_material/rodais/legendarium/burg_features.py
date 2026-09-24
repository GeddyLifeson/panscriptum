"""
burg_features.py -- give every burg on the Dia-thìr map the town features its history supports.

Azgaar's Fantasy Map Generator draws no town plans itself. Each burg's preview is a link to Watabou's
generators, built from the burg's data: for a capital, city or town the City Generator gets citadel,
walls, plaza (and greens), temple, shantytown and coast; for a village the Village Generator gets
"palisade" from walls and "no square" unless there is a plaza. The generator set those flags at random
from population, so the old map had 11 temples among 505 burgs and a capital with no market square.

burg_features.json is the reviewed table, one entry per burg:

    {"19": {"name": "Cathair dhearg", "citadel": 1, "walls": 1, "plaza": 1, "temple": 1, "shanty": 0,
            "why": "the reason, citing the gazetteer, the annals or the appendices"}, ...}

An entry may also carry "port": 0. That clears the port of a burg whose map cell lies inland with no
haven: Azgaar would still send coast=1 and Watabou would draw a sea on a random side of the town. Its
plan keeps river=1 where the burg stands on a river. Only 0 is accepted; the table never makes a port.

This script writes those flags into the burgs record of the map (record 15), removes the saved anchor
icon (<use id="anchorN" data-id="N"> in the SVG, record 5) of every burg that is not a port, and gives
the burg groups in the settings (record 1) the town-plan previews in GROUP_PREVIEWS, so the forts get a
plan. It changes nothing else: not names, groups, populations, positions or cells. Each record it
touches must round-trip byte for byte before it writes, and afterwards no other record may differ.

burg_moves.json moves harbour towns whose map cell lay inland onto the nearest free coastal cell with a
haven in the same province and state, as Azgaar's own burg editor relocates a burg (x, y, cell and the
cells' burg array, record 17) and with the port Azgaar gives a coastal burg (the haven's water feature,
the position at the water's edge). In the saved SVG the burg's icon and label move with it and its anchor
is placed in its group in id order. Azgaar's relocate leaves routes alone; route_extensions.json carries
each route that ended at a moved town's old cell on to its new cell (over adjacent land for trails; for
boat routes, by water and river cells where it can), with the path Azgaar's Routes.getPath draws for the
new points, the saved <path id="routeN"> in the SVG, and the cells' route links (record 36).

    python burg_features.py      # Rodos_finished.map, Diathir_Atlas/Diathir.map and world.json, in place

finish_map.py calls apply() too, so rebuilding Rodos_finished.map from Rodos_renamed.map keeps the
features. Running this twice changes nothing the second time.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TABLE = os.path.join(HERE, 'burg_features.json')
WORLD = os.path.join(HERE, 'world.json')
MOVES = os.path.join(HERE, 'burg_moves.json')
ROUTE_EXT = os.path.join(HERE, 'route_extensions.json')
MAPS = [os.path.join(ROOT, 'Rodos_finished.map'), os.path.join(ROOT, 'Diathir_Atlas', 'Diathir.map')]

FLAGS = ('citadel', 'walls', 'plaza', 'temple', 'shanty')
RECORDS, L_SETTINGS, L_SVG, L_BURGS, L_CELL_BURG = 53, 1, 5, 15, 17   # a .map is 53 CRLF-joined records (see finish_map.py)
L_CELL_ROUTES, L_ROUTES = 36, 37
GROUP_PREVIEWS = {'fort': 'watabou-city'}            # Azgaar's fort group has no town plan by default
ANCHOR = re.compile(r'<use id="anchor(\d+)" data-id="\1" href="#icon-anchor"[^>]*/>')


def load_table(path=TABLE):
    table = {int(k): v for k, v in json.load(open(path, encoding='utf-8')).items()}
    for i, row in table.items():
        for k in FLAGS:
            assert row.get(k) in (0, 1), 'burg %d: %s must be 0 or 1' % (i, k)
        assert row.get('why'), 'burg %d has no reason' % i
        assert row.get('port', 0) == 0, 'burg %d: the table may only clear a port (port: 0)' % i
    return table


def apply(burgs, table=None):
    """Set the five flags on every burg in the table. Returns [(burg id, flag, old, new)]."""
    table = load_table() if table is None else table
    live = {b['i']: b for b in burgs if isinstance(b, dict) and b.get('i') and not b.get('removed')}
    missing = sorted(set(live) - set(table))
    unknown = sorted(set(table) - set(live))
    assert not missing and not unknown, 'table and map disagree: missing %s, unknown %s' % (missing, unknown)
    changes = []
    for i, b in sorted(live.items()):
        row = table[i]
        assert row.get('name', b['name']) == b['name'], 'burg %d is %s on the map, %s in the table' % (i, b['name'], row['name'])
        for k in FLAGS:
            old = int(bool(b.get(k)))
            if b.get(k) != row[k]:
                if old != row[k]:
                    changes.append((i, k, old, row[k]))
                b[k] = row[k]
        if 'port' in row and b.get('port'):
            changes.append((i, 'port', b['port'], 0))
            b['port'] = 0
    return changes


def drop_anchors(svg, burgs):
    """Remove the saved anchor icon of every burg that is not a port; nothing else in the SVG."""
    ports = {b['i'] for b in burgs if isinstance(b, dict) and b.get('port')}
    gone = []

    def cut(m):
        if int(m.group(1)) in ports:
            return m.group(0)
        gone.append(int(m.group(1)))
        return ''
    out = ANCHOR.sub(cut, svg)
    assert len(out) == len(svg) - sum(len(m.group(0)) for m in ANCHOR.finditer(svg) if int(m.group(1)) not in ports)
    return out, gone


def set_group_previews(settings_text):
    settings = json.loads(settings_text)
    assert dump(settings) == settings_text, 'the settings record does not round-trip; refusing to rewrite it'
    for g in settings['burgs']['groups']:
        if g.get('name') in GROUP_PREVIEWS:
            g['preview'] = GROUP_PREVIEWS[g['name']]
    return dump(settings)


def jsnum(v):
    return str(int(v)) if float(v).is_integer() else repr(float(v))


def set_xy(svg, element_re, x, y):
    m = re.search(element_re, svg)
    if not m:
        return svg, False
    el = re.sub(r' x="[^"]*"', ' x="%s"' % jsnum(x), m.group(0), count=1)
    el = re.sub(r' y="[^"]*"', ' y="%s"' % jsnum(y), el, count=1)
    return svg[:m.start()] + el + svg[m.end():], True


def place_anchor(svg, i, group, x, y):
    """Put burg i's anchor into its group under <g id="anchors">, in id order (the order Azgaar draws)."""
    svg = re.sub(r'<use id="anchor%d" data-id="%d" [^>]*/>' % (i, i), '', svg)
    top = svg.index('<g id="anchors" data-group="anchors">')
    g = re.compile(r'<g id="%s" data-group="%s"[^>]*data-icon="#icon-anchor"(/?)>' % (group, group)).search(svg, top)
    assert g, 'no anchor group %s' % group
    if g.group(1):                                   # an empty group is saved self-closing
        svg = svg[:g.start()] + g.group(0)[:-2] + '></g>' + svg[g.end():]
        g = re.compile(re.escape(g.group(0)[:-2] + '>')).search(svg, g.start())
    end = svg.index('</g>', g.end())
    at = end
    for m in ANCHOR.finditer(svg, g.end(), end):
        if int(m.group(1)) > i:
            at = m.start()
            break
    el = '<use id="anchor%d" data-id="%d" href="#icon-anchor" x="%s" y="%s"/>' % (i, i, jsnum(x), jsnum(y))
    return svg[:at] + el + svg[at:]


def load_moves(path=MOVES):
    return {int(k): v for k, v in json.load(open(path, encoding='utf-8')).items()} if os.path.isfile(path) else {}


def move_burgs(lines, burgs, moves=None):
    """Relocate the burgs in burg_moves.json; idempotent."""
    moves = load_moves() if moves is None else moves
    by_id = {b['i']: b for b in burgs if isinstance(b, dict) and b.get('i')}
    cell_burg = lines[L_CELL_BURG].split(',')
    svg = lines[L_SVG]
    for i, mv in sorted(moves.items()):
        b = by_id[i]
        assert b['name'] == mv['name'], 'burg %d is %s on the map, %s in burg_moves.json' % (i, b['name'], mv['name'])
        old, new = mv['from']['cell'], mv['to']['cell']
        assert b['cell'] in (old, new), 'burg %d is at cell %s, expected %s or %s' % (i, b['cell'], old, new)
        assert cell_burg[new] in ('0', str(i)), 'cell %d already holds burg %s' % (new, cell_burg[new])
        if cell_burg[old] == str(i):
            cell_burg[old] = '0'
        cell_burg[new] = str(i)
        b['cell'], b['x'], b['y'], b['port'] = new, mv['to']['x'], mv['to']['y'], mv['port']
        svg, ok = set_xy(svg, r'<use id="burg%d" data-id="%d" [^>]*/>' % (i, i), b['x'], b['y'])
        assert ok, 'no icon for burg %d' % i
        svg, _ = set_xy(svg, r'<text id="burgLabel%d" data-label-type="burg" data-id="%d"[^>]*>' % (i, i), b['x'], b['y'])
        svg = place_anchor(svg, i, b['group'], b['x'], b['y'])
    lines[L_CELL_BURG] = ','.join(cell_burg)
    lines[L_SVG] = svg


def extend_routes(lines, routes, ext=None):
    """Carry the routes that ended at a moved town's old cell on to its new cell; idempotent."""
    ext = ({int(k): v for k, v in json.load(open(ROUTE_EXT, encoding='utf-8')).items()} if os.path.isfile(ROUTE_EXT) else {}) if ext is None else ext
    by_id = {r['i']: r for r in routes}
    links = json.loads(lines[L_CELL_ROUTES])
    assert dump(links) == lines[L_CELL_ROUTES], 'the cell-routes record does not round-trip; refusing to rewrite it'
    svg = lines[L_SVG]
    for i, e in sorted(ext.items()):
        r = by_id[i]
        assert r['points'] in (e['before'], e['points']), 'route %d is neither as saved nor as extended' % i
        r['points'] = e['points']
        for a, b in e['links']:
            links.setdefault(str(a), {}).setdefault(str(b), i)
            links.setdefault(str(b), {}).setdefault(str(a), i)
        m = re.search(r'<path id="route%d" d="[^"]*"' % i, svg)
        assert m, 'no saved path for route %d' % i
        svg = svg[:m.start()] + '<path id="route%d" d="%s"' % (i, e['d']) + svg[m.end():]
    lines[L_CELL_ROUTES] = dump(links)
    lines[L_SVG] = svg


def finish_records(lines, burgs, routes=None):
    """After apply(): the moves, the routes, the SVG anchors and the group previews, on a list of raw records.
    finish_map.py passes its parsed routes (it writes record 37 itself); otherwise record 37 is parsed here."""
    move_burgs(lines, burgs)
    if routes is None:
        parsed = json.loads(lines[L_ROUTES])
        assert dump(parsed) == lines[L_ROUTES], 'the routes record does not round-trip; refusing to rewrite it'
        extend_routes(lines, parsed)
        lines[L_ROUTES] = dump(parsed)
    else:
        extend_routes(lines, routes)
    lines[L_SVG], gone = drop_anchors(lines[L_SVG], burgs)
    lines[L_SETTINGS] = set_group_previews(lines[L_SETTINGS])
    return gone


def dump(data):
    # the same serialisation as finish_map.py: compact, UTF-8, surrogates written back as \u escapes
    text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return re.sub('[\ud800-\udfff]', lambda m: '\\u%04x' % ord(m.group()), text)


def apply_to_map(path, table):
    raw = open(path, encoding='utf-8', newline='').read()      # newline='' keeps the CRLF record separators
    lines = raw.split('\r\n')
    assert len(lines) == RECORDS, '%s: expected %d records, got %d' % (path, RECORDS, len(lines))
    burgs = json.loads(lines[L_BURGS])
    assert dump(burgs) == lines[L_BURGS], '%s: the burgs record does not round-trip; refusing to rewrite it' % path
    changes = apply(burgs, table)
    new = list(lines)
    finish_records(new, burgs)
    new[L_BURGS] = dump(burgs)
    out = '\r\n'.join(new)
    if out != raw:
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            fh.write(out)
    check = open(path, encoding='utf-8', newline='').read().split('\r\n')
    assert len(check) == RECORDS
    assert set(n for n in range(RECORDS) if check[n] != lines[n]) <= {L_SETTINGS, L_SVG, L_BURGS, L_CELL_BURG, L_CELL_ROUTES, L_ROUTES}, '%s: an unexpected record changed' % path
    assert check[L_SVG].count('<') - check[L_SVG].count('<use id="anchor') == lines[L_SVG].count('<') - lines[L_SVG].count('<use id="anchor') + check[L_SVG].count('></g>') - lines[L_SVG].count('></g>')
    assert len(check[L_CELL_BURG].split(',')) == len(lines[L_CELL_BURG].split(','))
    json.loads(check[L_BURGS])
    json.loads(check[L_SETTINGS])
    return changes


def apply_to_world(table):
    """world.json is the map as data for the writers; keep its citadel/walls/temple/port in step with the map."""
    raw = open(WORLD, encoding='utf-8').read()
    world = json.loads(raw)
    assert json.dumps(world, ensure_ascii=False, indent=0) == raw, 'world.json does not round-trip; refusing to rewrite it'
    n = 0
    for b in world['burgs']:
        row = table[b['id']]
        for k in ('citadel', 'walls', 'temple'):
            if b.get(k) != bool(row[k]):
                b[k] = bool(row[k])
                n += 1
        if 'port' in row and b.get('port'):
            b['port'] = False
            n += 1
    for i, mv in load_moves().items():
        b = next(o for o in world['burgs'] if o['id'] == i)
        for k, v in (('x', mv['to']['x']), ('y', mv['to']['y']), ('port', True)):
            if b.get(k) != v:
                b[k] = v
                n += 1
    out = json.dumps(world, ensure_ascii=False, indent=0)
    if out != raw:
        open(WORLD, 'w', encoding='utf-8').write(out)
    return n


def counts(path):
    burgs = json.loads(open(path, encoding='utf-8', newline='').read().split('\r\n')[L_BURGS])
    live = [b for b in burgs if isinstance(b, dict) and b.get('i') and not b.get('removed')]
    c = {k: sum(1 for b in live if b.get(k)) for k in FLAGS + ('port',)}
    c['anchors'] = len(ANCHOR.findall(open(path, encoding='utf-8', newline='').read().split('\r\n')[L_SVG]))
    return c


if __name__ == '__main__':
    table = load_table()
    for path in MAPS:
        if not os.path.isfile(path):
            print('skip (not built):', os.path.relpath(path, ROOT))
            continue
        before = counts(path)
        changes = apply_to_map(path, table)
        print('%s: %d flag changes; before %s; after %s' % (os.path.relpath(path, ROOT), len(changes), before, counts(path)))
    print('world.json: %d flag changes' % apply_to_world(table))
    sys.exit(0)
