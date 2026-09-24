"""
build_atlas.py -- assemble the Rodos Atlas: the annals, the book and the live Azgaar map in one program.

    python build_atlas.py <azgaar-build-dir>

<azgaar-build-dir> is Azgaar's Fantasy Map Generator built in its desktop mode (relative paths, no
analytics), version 1.153.1, the version that saved the Rodos map:

    git clone https://github.com/Azgaar/Fantasy-Map-Generator && cd Fantasy-Map-Generator
    npm ci --ignore-scripts && npx vite build --mode electron      # -> dist-electron/renderer

Output: Rodos_Atlas/ next to this file --

    Rodos Atlas.bat     double-click on Windows
    atlas.py            the launcher: serves the folder on 127.0.0.1 and opens the browser
    index.html          three tabs: the Annals (every dated event), the Map, and the Book (legendarium/build_book.py)
    Rodos.map           Rodos_finished.map
    fmg/                Azgaar's Fantasy Map Generator (MIT, see fmg/LICENSE)

An annals event that happened somewhere has a place; its map button switches to the map, flies there
and marks the spot, and the Record panel shows that place's history and every event recorded there.
Clicking a town or marker on the map opens the same record; every place named in the Book opens the map.
"""
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'Rodos_Atlas')
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
with open(os.path.join(OUT, 'Rodos.map'), 'w', encoding='utf-8', newline='') as fh:
    fh.write('\r\n'.join(records))

TEMPLATE = open(os.path.join(HERE, 'atlas_template.html'), encoding='utf-8').read()

def js(o):
    return json.dumps(o, ensure_ascii=False).replace('</', '<\\/')


index = (TEMPLATE.replace('/*STYLE*/', style).replace('/*BOOKCSS*/', build_book.BOOK_CSS).replace('FONTS_URL', html.escape(fonts))
         .replace('/*EVENTS*/[]', js(events)).replace('/*PLACES*/{}', js(places)).replace('/*AGES*/[]', js(ages))
         .replace('<!--TOC-->', build_book.toc_html(toc)).replace('<!--BOOK-->', book)
         .replace('FMG_VERSION', FMG_VERSION))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(index)
shutil.copy(os.path.join(HERE, 'atlas.py'), os.path.join(OUT, 'atlas.py'))
with open(os.path.join(OUT, 'Rodos Atlas.bat'), 'w', encoding='utf-8', newline='\r\n') as fh:
    fh.write('@echo off\ncd /d "%~dp0"\nwhere py >nul 2>nul && (py atlas.py) || (python atlas.py)\n'
             'if errorlevel 1 pause\n')
print('Rodos_Atlas written: %d events, %d with a place on the map; %d places; book of about %s words'
      % (len(events), sum(1 for e in events if e[5]), len(places), format(len(re.sub(r'<[^>]+>', ' ', book).split()), ',')))
