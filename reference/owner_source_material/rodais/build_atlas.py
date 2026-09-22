"""
build_atlas.py -- assemble the Rodos Atlas: the chronicle of Rodos and the live Azgaar map in one program.

    python build_atlas.py <azgaar-build-dir>

<azgaar-build-dir> is Azgaar's Fantasy Map Generator built in its desktop mode (relative paths, no
analytics), version 1.153.1, the version that saved the Rodos map:

    git clone https://github.com/Azgaar/Fantasy-Map-Generator && cd Fantasy-Map-Generator
    npm ci --ignore-scripts && npx vite build --mode electron      # -> dist-electron/renderer

Output: Rodos_Atlas/ next to this file --

    Rodos Atlas.bat     double-click on Windows
    atlas.py            the launcher: serves the folder on 127.0.0.1 and opens the browser
    index.html          the chronicle (timeline) and the map tab, wired together
    Rodos.map           Rodos_finished.map, with the chronicle's events added to the notes of the places
    fmg/                Azgaar's Fantasy Map Generator (MIT, see fmg/LICENSE)

A timeline event that happened somewhere has a place; clicking it switches to the map, flies there
and marks the spot. On the map, the Chronicle panel lists the same events, and every such place's
marker note in Azgaar carries its events too.
"""
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'Rodos_Atlas')
CHRONICLE = os.path.join(HERE, 'CHRONICLE.html')
MAP = os.path.join(HERE, 'Rodos_finished.map')
FMG_VERSION = '1.153.1'

if len(sys.argv) != 2 or not os.path.isfile(os.path.join(sys.argv[1], 'index.html')):
    sys.exit(__doc__)
FMG = sys.argv[1]

# ---------------------------------------------------------------- the chronicle, taken apart
page = open(CHRONICLE, encoding='utf-8').read()
style = re.search(r'<style>(.*?)</style>', page, re.S).group(1)
fonts = re.search(r'<link href="(https://fonts.googleapis.com[^"]+)"', page).group(1)
header = re.search(r'<header>.*?</header>', page, re.S).group(0)
timeline = re.search(r'<div id="panel-timeline">.*?</footer>\s*</div>', page, re.S).group(0)

# places: every pin of the old picture map, with its map coordinates and the events recorded there
places = {}
for pid, cat, left, top in re.findall(
        r'<div class="pin" id="pin-(\w+)" data-cat="(\w+)" style="left:([\d.]+)%; top:([\d.]+)%;"', page):
    start = page.index('<div class="popup" id="popup-%s"' % pid)
    ends = [i for i in (page.find('<div class="pin"', start), page.find('<script', start)) if i > 0]
    seg = page[start:min(ends)]
    name = re.search(r'<h4>(.*?)</h4>', seg).group(1)
    events = re.findall(r'<div class="pdate">(.*?)</div><div class="ptitle">(.*?)</div><div class="pbody">(.*?)</div>', seg)
    places[pid] = {'name': name, 'cat': cat, 'x': round(float(left) / 100 * 1536, 2),
                   'y': round(float(top) / 100 * 702, 2), 'events': [{'date': d, 'title': t, 'body': b} for d, t, b in events]}

# ---------------------------------------------------------------- the map, with the chronicle in its notes
records = open(MAP, encoding='utf-8', newline='').read().split('\r\n')
assert len(records) == 53, 'Rodos_finished.map should have 53 CRLF records'
markers, burgs = json.loads(records[35]), json.loads(records[15])


def near(items, x, y):
    best = min((o for o in items if isinstance(o, dict) and 'x' in o), key=lambda o: (o['x'] - x) ** 2 + (o['y'] - y) ** 2)
    return best if (best['x'] - x) ** 2 + (best['y'] - y) ** 2 < 1 else None


def chronicle_note(events):
    rows = ''.join('<p><b>%s</b> — %s. %s</p>' % (e['date'], e['title'], e['body']) for e in events)
    return '<hr><p><i>From the chronicle of Rodos:</i></p>' + rows


for pid, pl in places.items():
    m = near(markers, pl['x'], pl['y'])
    b = near(burgs, pl['x'], pl['y']) if pid == 'capital' else None
    target = b or m
    if target is None:
        sys.exit('place %s has no marker or burg at (%s, %s)' % (pid, pl['x'], pl['y']))
    pl['kind'], pl['i'] = ('burg', b['i']) if b else ('marker', m['i'])
    target['note'] = (target.get('note') or '') + chronicle_note(pl['events'])
records[35] = json.dumps(markers, ensure_ascii=False, separators=(',', ':'))
records[15] = json.dumps(burgs, ensure_ascii=False, separators=(',', ':'))
for n in (15, 35):   # keep the escaped half-emoji of the source as escapes, as finish_map.py does
    records[n] = re.sub('[\ud800-\udfff]', lambda m_: '\\u%04x' % ord(m_.group()), records[n])

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
index = (TEMPLATE.replace('/*STYLE*/', style).replace('FONTS_URL', html.escape(fonts))
         .replace('<!--TIMELINE-->', timeline.replace('<div id="panel-timeline">', '<div id="panel-timeline">' + header, 1))
         .replace('/*PLACES*/null', json.dumps(places, ensure_ascii=False))
         .replace('FMG_VERSION', FMG_VERSION))
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(index)
shutil.copy(os.path.join(HERE, 'atlas.py'), os.path.join(OUT, 'atlas.py'))
with open(os.path.join(OUT, 'Rodos Atlas.bat'), 'w', encoding='utf-8', newline='\r\n') as fh:
    fh.write('@echo off\ncd /d "%~dp0"\nwhere py >nul 2>nul && (py atlas.py) || (python atlas.py)\n'
             'if errorlevel 1 pause\n')
print('Rodos_Atlas written: %d places wired to the map, %d events' % (len(places), sum(len(p['events']) for p in places.values())))
