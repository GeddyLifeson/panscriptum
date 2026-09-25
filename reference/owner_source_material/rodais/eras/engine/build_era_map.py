"""
build_era_map.py -- build an era's Azgaar map from the master map and a spec.

    python3 build_era_map.py SPEC.json OUT.map [--master MAP] [--verify] [--shots DIR] [--report FILE]

The master (default: the spec's "master", else ../../Rodos_finished.map) is opened in Azgaar's own Fantasy Map
Generator (Diathir_Atlas/fmg/), headless, through driver.js; era_engine.js edits Azgaar's data to the spec and
recalculates what follows from it with Azgaar's own functions; every layer is redrawn; and the .map is written
by Azgaar's own save (Save.prepareMapData). The master is never written to.

--verify   then loads OUT.map fresh in a new page and checks it: no page errors, no error dialogs, no
           "[Data integrity]" complaints, the counts the spec asks for, the cells of each state's shires in
           that state, every layer drawn, and a round trip (load, save again, compare).
--shots    with --verify: screenshots of the states, cultures, religions, routes and provinces layers.
--report   the build report as JSON (default: OUT.map + ".report.json"): warnings, the ids given to new
           elements ("@key" -> id), counts, and the verification.

Needs Node with Playwright (npm -g) and Chromium: NODE_PATH defaults to `npm root -g`, CHROMIUM_PATH to
/opt/pw-browsers/chromium when that exists. See SPEC.md for the spec.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # the RODAIS folder, served to the browser
FMG = os.path.join(ROOT, 'Diathir_Atlas', 'fmg')
WORK = os.path.join(HERE, '.work')
RECORDS = 53
L_STATES, L_BURGS, L_CELL_STATE, L_CELL_PROVINCE = 14, 15, 25, 27
L_MARKERS, L_ROUTES, L_ZONES = 35, 37, 38
KNOWN = {'name', 'seed', 'master', 'description', 'lore', 'features', 'rivers', 'cultures', 'religions', 'burgs',
         'states', 'provinces', 'diplomacy', 'diplomacy_default', 'campaigns', 'military', 'routes', 'markers',
         'zones', 'labels', 'economy', 'journeys', 'notes', 'rural_population', 'layers', 'land', 'comment',
         'expect', 'units'}


def fail(msg):
    sys.exit('build_era_map: ' + msg)


def env():
    e = dict(os.environ)
    if not e.get('NODE_PATH'):
        try:
            e['NODE_PATH'] = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            pass
    if not e.get('CHROMIUM_PATH') and os.path.exists('/opt/pw-browsers/chromium'):
        e['CHROMIUM_PATH'] = '/opt/pw-browsers/chromium'
    return e


def served(path):
    """The URL path of a file under ROOT, copying it into eras/engine/.work/ when it lies elsewhere."""
    path = os.path.abspath(path)
    if not path.startswith(ROOT + os.sep):
        os.makedirs(WORK, exist_ok=True)
        dst = os.path.join(WORK, os.path.basename(path))
        shutil.copyfile(path, dst)
        path = dst
    return '/' + os.path.relpath(path, ROOT).replace(os.sep, '/')


class Server:
    def __enter__(self):
        self.p = subprocess.Popen([sys.executable, os.path.join(HERE, 'serve.py'), '0', ROOT],
                                  stdout=subprocess.PIPE, text=True)
        line = self.p.stdout.readline().split()
        if len(line) != 2 or line[0] != 'READY':
            fail('the local server did not start')
        self.base = 'http://127.0.0.1:%s' % line[1]
        return self

    def __exit__(self, *a):
        self.p.terminate()
        self.p.wait()


def run_driver(cfg, e):
    os.makedirs(WORK, exist_ok=True)
    cpath = os.path.join(WORK, 'driver_%s_%d.json' % (cfg['mode'], os.getpid()))
    with open(cpath, 'w', encoding='utf-8') as fh:
        json.dump(cfg, fh)
    r = subprocess.run(['node', os.path.join(HERE, 'driver.js'), cpath], env=e, capture_output=True, text=True,
                       timeout=900)
    os.remove(cpath)
    if r.returncode:
        fail('driver (%s) failed:\n%s%s' % (cfg['mode'], r.stdout[-3000:], r.stderr[-3000:]))
    with open(cfg['report'], encoding='utf-8') as fh:
        return json.load(fh)


def records(path):
    lines = open(path, encoding='utf-8', newline='').read().split('\r\n')
    if len(lines) != RECORDS:
        fail('%s has %d records, not %d' % (path, len(lines), RECORDS))
    return lines


def check_shires(spec, master_lines, out_lines, ids):
    """Every land cell of a state's shires (the master provinces it lists) is in that state on the new map,
    unless the spec moved that cell by cells / cell_state; returns (checked, [problems])."""
    st = spec.get('states')
    if not st:
        return 0, []
    lst = st if isinstance(st, list) else st.get('list', [])
    opts = {} if isinstance(st, list) else st
    mprov = [int(x) for x in master_lines[L_CELL_PROVINCE].split(',')]
    # a capital's cell always goes to its own state (the engine warns when that overrides a shire)
    burgs = json.loads(out_lines[L_BURGS])
    capitals = {b['cell'] for b in burgs if isinstance(b, dict) and b.get('capital') and not b.get('removed')}
    nstate = [int(x) for x in out_lines[L_CELL_STATE].split(',')]
    overridden = set(int(c) for c in opts.get('cell_state', {})) | capitals
    for s in lst:
        overridden.update(s.get('cells', []))
    problems, checked = [], 0
    for k, s in enumerate(lst):
        shires = set(s.get('shires', []))
        for c, p in enumerate(mprov):
            if p in shires and c not in overridden:
                checked += 1
                if nstate[c] != k + 1:
                    problems.append('cell %d (shire %d): state %d, spec says %d' % (c, p, nstate[c], k + 1))
    return checked, problems


def expected_counts(spec, report):
    """What the spec asks for, to compare with the loaded map (only what the spec states outright)."""
    exp = {}
    st = spec.get('states')
    if st:
        exp['states'] = len(st if isinstance(st, list) else st.get('list', []))
    b = spec.get('burgs', {})
    if isinstance(b.get('keep'), list):
        exp['burgs'] = len(set(b['keep']) - set(b.get('remove', []))) + len(b.get('add', []))
    m = spec.get('markers', {})
    if isinstance(m.get('keep'), list):
        exp['markers'] = len(set(m['keep']) - set(m.get('remove', []))) + len(m.get('add', []))
    r = spec.get('routes', {})
    if isinstance(r.get('keep'), list):
        exp['routes'] = len(set(r['keep']) - set(r.get('remove', []))) + len(r.get('add', []))
    z = spec.get('zones', {})
    if isinstance(z.get('keep'), list):
        exp['zones'] = len(set(z['keep']) - set(z.get('remove', []))) + len(z.get('add', []))
    exp.update(spec.get('expect', {}))
    return exp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('out')
    ap.add_argument('--master')
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--shots')
    ap.add_argument('--report')
    a = ap.parse_args()

    spec = json.load(open(a.spec, encoding='utf-8'))
    unknown = set(spec) - KNOWN
    if unknown:
        fail('unknown top-level keys in the spec: %s (see SPEC.md)' % ', '.join(sorted(unknown)))
    if spec.get('land'):
        fail('"land" (turning cells between land and water) is not supported: see SPEC.md, "Land and water"')
    spec_dir = os.path.dirname(os.path.abspath(a.spec))
    master = a.master or (os.path.join(spec_dir, spec['master']) if spec.get('master') else os.path.join(ROOT, 'Rodos_finished.map'))
    master = os.path.abspath(master)
    out = os.path.abspath(a.out)
    if out == master:
        fail('the output would overwrite the master')
    report_path = a.report or out + '.report.json'
    saves = glob.glob(os.path.join(FMG, 'save-*.js'))
    if len(saves) != 1:
        fail('expected one save-*.js in %s, found %d' % (FMG, len(saves)))
    e = env()
    master_lines = records(master)

    with Server() as srv:
        head = master_lines[0].split('|')
        common = {'base': srv.base, 'fmg': '/Diathir_Atlas/fmg/', 'save': os.path.basename(saves[0]), 'root': ROOT,
                  'width': int(head[4]), 'height': int(head[5])}
        # the spec is read by node from disk; relative paths in it are not used
        rep = run_driver(dict(common, mode='build', map=served(master), spec=os.path.abspath(a.spec), out=out,
                              report=report_path), e)
        if rep.get('integrity'):
            print('integrity problems after the edit:', *rep['integrity'][:20], sep='\n  ')
        out_lines = records(out)
        for n in (L_STATES, L_BURGS, L_MARKERS, L_ROUTES, L_ZONES):
            json.loads(out_lines[n])
        for w in rep['warnings']:
            print('warning:', w)
        print('built %s: %d bytes, counts %s' % (os.path.relpath(out), rep['bytes'], rep['counts']))
        if a.verify:
            v = run_driver(dict(common, mode='verify', map=served(out), report=report_path + '.verify.json',
                                shots=os.path.abspath(a.shots) if a.shots else None,
                                prefix=os.path.splitext(os.path.basename(out))[0].strip('_') + '_',
                                againOut=os.path.join(WORK, 'roundtrip.map')), e)
            os.remove(report_path + '.verify.json')
            checked, problems = check_shires(spec, master_lines, out_lines, rep['ids'])
            exp = expected_counts(spec, rep)
            mism = {k: (want, v.get('counts', {}).get(k)) for k, want in exp.items() if v.get('counts', {}).get(k) != want}
            v['shires'] = {'cells_checked': checked, 'problems': problems[:50]}
            v['expected_counts'] = exp
            v['count_mismatches'] = mism
            ok = (v['load'].get('loaded') and not v['load']['pageErrors'] and not v['load']['integrity']
                  and not v['load']['dialogs'] and not v.get('integrity') and not problems and not mism
                  and not v.get('pageErrorsAfterDraw'))
            v['ok'] = bool(ok)
            rep['verify'] = v
            print('verify: %s' % ('OK' if ok else 'PROBLEMS'))
            print('  loaded=%s pageErrors=%d dialogs=%d integrity-messages=%d engine-integrity=%d'
                  % (v['load'].get('loaded'), len(v['load']['pageErrors']), len(v['load']['dialogs']),
                     len(v['load']['integrity']), len(v.get('integrity') or [])))
            print('  counts:', v.get('counts'), 'expected:', exp, 'mismatches:', mism or 'none')
            print('  shire cells checked: %d, wrong state: %d' % (checked, len(problems)))
            print('  drawn:', v.get('draw'))
            rt = v.get('roundTrip', {})
            print('  round trip: identical=%s, differing records=%s' % (rt.get('identical'), [d['record'] for d in rt.get('differing', [])]))
            for s in (v.get('shots') or {}).values():
                print('  screenshot:', s)
        with open(report_path, 'w', encoding='utf-8') as fh:
            json.dump(rep, fh, ensure_ascii=False, indent=1)
    if a.verify and not rep['verify']['ok']:
        sys.exit(2)


if __name__ == '__main__':
    main()
