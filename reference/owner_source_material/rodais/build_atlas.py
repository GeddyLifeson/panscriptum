"""
build_atlas.py -- assemble the Dia-thìr Atlas: the annals and the live Azgaar map in one program.

    python build_atlas.py <azgaar-build-dir>

<azgaar-build-dir> is Azgaar's Fantasy Map Generator built in its desktop mode (relative paths, no
analytics), version 1.153.1, the version that saved the Dia-thìr map:

    git clone https://github.com/Azgaar/Fantasy-Map-Generator && cd Fantasy-Map-Generator
    npm ci --ignore-scripts && npx vite build --mode electron      # -> dist-electron/renderer

Output: Diathir_Atlas/ next to this file --

    Diathir Atlas.bat     double-click on Windows
    Diathir Atlas.command double-click on a Mac
    atlas.py            the launcher: serves the folder on 127.0.0.1 and opens the browser
    index.html          two tabs: the Annals (every dated event) and the Map; the book itself is the PDF (legendarium/build_pdf.py)
    Diathir.map         a copy of Rodos_finished.map, the finished map
    maps/               the seven ages' own maps (eras/maps/Diathir_Age_I..VII.map) and their pictures (shots/)
    atlas/              the Atlas's own scripts and styles, copied from atlas_ui/ (timeline, eras and maps, people and
                        family trees, glossary, this day, the web of links)
    data/               meta.js, master.js and era_<K>.js: every age's annals, links both ways, threads, people,
                        names and trees, gathered fresh by atlas_data.py on every build (the writers' new events,
                        links, threads, people and told_in show up on the next run)
    fmg/                Azgaar's Fantasy Map Generator (MIT, see fmg/LICENSE)

The Annals are a timeline after the Middle-earth interactive map's (ERA_PLAN.md): an age ribbon that switches the
annals and the map together, a detail switch (Highlights, Standard, Everything), a search in English or Dia-thìris,
and everything else behind "⋯". Links (#III/EIII-0412, #person/<id>, #place/burg:19, #thread/<id>) can be shared.

An annals event that happened somewhere has a place; its map button switches to the map, flies there
and marks the spot, and the Record panel shows that place's history and every event recorded there.
Clicking a town or marker on the map, or a place in the Record's list, opens the same record.
"""
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'Diathir_Atlas')
STYLE = os.path.join(HERE, 'atlas_style.css')
MAP = os.path.join(HERE, 'Rodos_finished.map')
FMG_VERSION = '1.153.1'

if len(sys.argv) != 2 or not os.path.isfile(os.path.join(sys.argv[1], 'index.html')):
    sys.exit(__doc__)
FMG = sys.argv[1]

# ---------------------------------------------------------------- the record: annals, book, gazetteer
sys.path.insert(0, os.path.join(HERE, 'legendarium'))
import build_book  # noqa: E402

style = open(STYLE, encoding='utf-8').read()
fonts = re.search(r'Fonts: (\S+)', style).group(1)
rec = build_book.Record()
toc, book = build_book.compose(rec)
if rec.missing:
    sys.exit('unresolved references in the book: %s' % sorted(set(rec.missing))[:40])

events = [[e['id'], e['age'], e['date'], e['title'], e['body'], e.get('place'), bool(e.get('canon'))] for e in rec.events]
places = {}
for ref, name in rec.names.items():
    kind, i = ref.split(':')
    i = int(i)
    p = {'name': name}
    if kind == 'burg':
        b, g = rec.burg[i], rec.gaz.get(i, {})
        p['facts'] = ' · '.join(str(x) for x in (b.get('group'), b.get('province'), b.get('culture'), b.get('faith'),
                                                 'pop. %s' % format(b.get('population', 0), ',')) if x)
        if g:
            p.update(founded=g['founded']['date'], by=g.get('founded_by', ''), history=g.get('history', ''), known=g.get('known_for', ''))
    elif kind == 'marker':
        mk = next(o for o in rec.world['markers'] if o['id'] == i)
        p['facts'] = mk.get('type', '').replace('-', ' ')
        p['history'] = re.sub(r'<[^>]+>', ' ', mk.get('note', '') or '').strip()
    elif kind == 'province':
        pr = next(o for o in rec.world['provinces'] if o['id'] == i)
        p['name'] = pr.get('fullName', name)
        p['facts'] = 'shire; seat %s' % rec.names.get('burg:%s' % pr.get('seat'), '')
    else:
        p['facts'] = {'zone': 'region of the chronicle', 'river': 'river', 'feature': 'water or land'}[kind]
    if kind == 'burg' or ref in rec.at:
        places[ref] = p
ages = [[k, build_book.AGE_NAMES[k][0], build_book.AGE_NAMES[k][1], '--' + build_book.AGE_NAMES[k][2],
         build_book.reckoning.display_span(k), build_book.reckoning.ERA[k][4], build_book.reckoning.ERA[k][3]]
        for k in build_book.reckoning.AGE_KEYS]

records = open(MAP, encoding='utf-8', newline='').read().split('\r\n')
assert len(records) == 53, 'Rodos_finished.map should have 53 CRLF records'

# ---------------------------------------------------------------- the eras: timelines, maps, people, names
import atlas_data  # noqa: E402   (atlas_data.py, next to this file)
ERA_DATA = atlas_data.collect(rec, MAP)

# ---------------------------------------------------------------- write the program
if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(FMG, os.path.join(OUT, 'fmg'))
for lic in (os.path.join(FMG, 'LICENSE'), os.path.join(FMG, '..', '..', 'LICENSE')):   # the build dir, or the repo it came from
    if os.path.isfile(lic):
        shutil.copy(lic, os.path.join(OUT, 'fmg', 'LICENSE'))
        break
else:
    sys.exit('Azgaar\'s LICENSE (MIT) not found next to the build; it must ship with the program')
# an error catcher that runs before any of the map-maker's own scripts, so the Atlas can report why a load stalled
_fi = os.path.join(OUT, 'fmg', 'index.html')
_h = open(_fi, encoding='utf-8').read()
_catch = ('<script>window.__atlasErrors=[];window.addEventListener("error",function(e){window.__atlasErrors.push((e.message||"a file failed to load")'
          '+(e.filename?" ("+e.filename.split("/").pop()+")":(e.target&&e.target.src?" ("+new URL(e.target.src).pathname.replace(/^.*?\/fmg\//,"")+")":"")))},true);'
          'window.addEventListener("unhandledrejection",function(e){var r=e.reason;window.__atlasErrors.push(String(r&&(r.stack||r.message)||r).slice(0,300))});</script>')
import re as _re
_h = _re.sub(r'<script>window.__atlasErrors=.*?</script>', '', _h, flags=_re.S)
if True:
    _h = _h.replace('<head>', '<head>' + _catch, 1)
    open(_fi, 'w', encoding='utf-8').write(_h)
with open(os.path.join(OUT, 'Diathir.map'), 'w', encoding='utf-8', newline='') as fh:
    fh.write('\r\n'.join(records))

TEMPLATE = open(os.path.join(HERE, 'atlas_template.html'), encoding='utf-8').read()

def js(o):
    return json.dumps(o, ensure_ascii=False).replace('</', '<\\/')


index = (TEMPLATE.replace('/*STYLE*/', style).replace('FONTS_URL', html.escape(fonts))
         .replace('/*PLACES*/{}', js(places)).replace('/*AGES*/[]', js(ages))
         
         .replace('FMG_VERSION', FMG_VERSION))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(index)

# the Atlas's own scripts and styles (atlas_ui/), its data (data/, script files so they load from the folder too),
# the seven era maps and their pictures (maps/), and any recordings of the names (audio/)
shutil.copytree(os.path.join(HERE, 'atlas_ui'), os.path.join(OUT, 'atlas'))
os.makedirs(os.path.join(OUT, 'data'))


def data_js(name, *args):
    with open(os.path.join(OUT, 'data', name), 'w', encoding='utf-8') as fh:
        fh.write('ATLAS_LOAD(%s);\n' % ','.join(js(a) for a in args))


data_js('meta.js', 'meta', ERA_DATA['meta'])
data_js('master.js', 'master', [e for k in atlas_data.KEYS for e in ERA_DATA['ages'].get(k, []) if e['master']])
for k, evs in ERA_DATA['ages'].items():
    data_js('era_%s.js' % k, 'era', k, {'order': [e['id'] for e in evs], 'events': [e for e in evs if not e['master']]})
for src, dst in ERA_DATA['copies']:
    os.makedirs(os.path.dirname(os.path.join(OUT, dst)), exist_ok=True)
    shutil.copyfile(src, os.path.join(OUT, dst))
shutil.copy(os.path.join(HERE, 'atlas.py'), os.path.join(OUT, 'atlas.py'))
with open(os.path.join(OUT, 'Diathir Atlas.bat'), 'w', encoding='utf-8', newline='\r\n') as fh:
    fh.write('@echo off\ncd /d "%~dp0"\nwhere py >nul 2>nul && (py atlas.py) || (python atlas.py)\n'
             'if errorlevel 1 (echo. & echo The Atlas needs Python 3 from python.org. & pause)\n')
with open(os.path.join(OUT, 'Diathir Atlas.command'), 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('#!/bin/sh\ncd "$(dirname "$0")"\npython3 atlas.py || python atlas.py\n')
os.chmod(os.path.join(OUT, 'Diathir Atlas.command'), 0o755)
print('Diathir_Atlas written: %d events, %d with a place on the map; %d places; book of about %s words'
      % (len(events), sum(1 for e in events if e[5]), len(places), format(len(re.sub(r'<[^>]+>', ' ', book).split()), ',')))
print('  eras: %s; %d people, %d family trees and ruler lists, %d maps%s'
      % (', '.join('%s %d (%d era)' % (k, len(v), sum(1 for e in v if not e['master'])) for k, v in ERA_DATA['ages'].items()),
         len(ERA_DATA['meta']['people']), len(ERA_DATA['meta']['trees']), len(ERA_DATA['meta']['maps']),
         '; %d notes' % len(ERA_DATA['meta']['warnings']) if ERA_DATA['meta']['warnings'] else ''))
