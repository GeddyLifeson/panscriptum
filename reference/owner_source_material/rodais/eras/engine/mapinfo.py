"""mapinfo.py -- a summary of an Azgaar .map for spec writers: the ids a spec refers to.

    python3 mapinfo.py [MAP] [--json]      (default MAP: the master, Rodos_finished.map)

Lists the states, provinces (shires: id, name, seat burg, pole, land cells), cultures, religions, burgs,
routes, markers, zones and journeys, with their ids. --json prints the same as one JSON object.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
L_CULTURES, L_STATES, L_BURGS, L_CELL_STATE, L_CELL_PROVINCE, L_HEIGHT = 13, 14, 15, 25, 27, 7
L_RELIGIONS, L_PROVINCES, L_MARKERS, L_ROUTES, L_ZONES, L_JOURNEYS = 29, 30, 35, 37, 38, 52


def load(path):
    lines = open(path, encoding='utf-8', newline='').read().split('\r\n')
    assert len(lines) == 53, '%s: %d records, expected 53' % (path, len(lines))
    return lines


def summary(lines):
    J = {n: json.loads(lines[n]) for n in (L_CULTURES, L_STATES, L_BURGS, L_RELIGIONS, L_PROVINCES, L_MARKERS,
                                           L_ROUTES, L_ZONES, L_JOURNEYS)}
    prov_cells = {}
    for p in lines[L_CELL_PROVINCE].split(','):
        prov_cells[int(p)] = prov_cells.get(int(p), 0) + 1
    burgs = [b for b in J[L_BURGS] if isinstance(b, dict) and b.get('i') and not b.get('removed')]
    by_id = {b['i']: b for b in burgs}
    out = {
        'states': [{'id': s['i'], 'name': s['name'], 'fullName': s.get('fullName'), 'capital': s.get('capital'),
                    'cells': s.get('cells')} for s in J[L_STATES] if not s.get('removed')],
        'provinces': [{'id': p['i'], 'name': p['name'], 'seat': p.get('burg'),
                       'seat_name': by_id.get(p.get('burg'), {}).get('name'), 'pole': p.get('pole'),
                       'cells': prov_cells.get(p['i'], 0), 'state': p.get('state')}
                      for p in J[L_PROVINCES] if isinstance(p, dict) and not p.get('removed')],
        'cultures': [{'id': c['i'], 'name': c['name'], 'cells': c.get('cells')} for c in J[L_CULTURES] if not c.get('removed')],
        'religions': [{'id': r['i'], 'name': r['name'], 'type': r.get('type'), 'deity': r.get('deity')}
                      for r in J[L_RELIGIONS] if not r.get('removed')],
        'burgs': [{'id': b['i'], 'name': b['name'], 'cell': b['cell'], 'x': b['x'], 'y': b['y'],
                   'population': b.get('population'), 'group': b.get('group'), 'capital': b.get('capital', 0)}
                  for b in burgs],
        'routes': [{'id': r['i'], 'name': r.get('name'), 'group': r['group'], 'points': len(r['points']),
                    'ends': [r['points'][0][2], r['points'][-1][2]]} for r in J[L_ROUTES]],
        'markers': [{'id': m['i'], 'type': m['type'], 'name': m.get('name'), 'cell': m['cell']} for m in J[L_MARKERS]],
        'zones': [{'id': z['i'], 'name': z['name'], 'type': z['type'], 'cells': len(z['cells'])} for z in J[L_ZONES]],
        'journeys': [{'index': k, 'name': j.get('name'), 'segments': len(j.get('segments', []))}
                     for k, j in enumerate(J[L_JOURNEYS])],
    }
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(ROOT, 'Rodos_finished.map')
    s = summary(load(path))
    if '--json' in sys.argv:
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return
    for key, rows in s.items():
        print('## %s (%d)' % (key, len(rows)))
        for r in rows:
            print('  ' + ', '.join('%s=%s' % kv for kv in r.items()))
        print()


if __name__ == '__main__':
    main()
