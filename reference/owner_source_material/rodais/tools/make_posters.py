"""
make_posters.py -- a print-quality poster of the island in every age, from whatever maps exist now.

    python3 tools/make_posters.py                 all eight: the seven ages' maps and today's (the master)
    python3 tools/make_posters.py IV VII M        only these (M is today's map)
    python3 tools/make_posters.py --scale 4       sharper maps (default 3: the map is 4,608 px wide)

For each map it loads the map in Azgaar's generator (Diathir_Atlas/fmg/, so build the Atlas first), headless
(Playwright + Chromium: /opt/pw-browsers/chromium when it exists; NODE_PATH from `npm root -g`), and writes:

    Diathir_Atlas/posters/Diathir_Poster_<Age_I..VII | Today>.png   the poster: the map at high resolution, a title
                                cartouche (the volume's title in Dia-thìris and English, the age, its span in its era,
                                the date the map shows), a legend of its realms and signs, and a strip of the age's
                                chief events (today's poster: the seven ages)
    Diathir_Atlas/posters/thumbs/*.jpg          small pictures for the Atlas's Posters gallery
    Diathir_Atlas/posters/print/*.jpg           a print copy of each poster, for the PDF
    Diathir_Atlas/posters/Diathir_Posters.pdf   every poster in the folder, one to a page
    Diathir_Atlas/posters/posters.js            the gallery's list (ATLAS_LOAD('posters', ...))
    eras/maps/overlays/<map>.json               each map's realms as Azgaar draws them, for the Atlas's
                                                "realms of another age" overlay (build_atlas.py carries them in)
    eras/maps/shots/Diathir_Master_<layer>.png  today's map pictured exactly as the era maps are (their shots/), for
                                                "then and now" in the Atlas

It only reads the maps, so it can run while they are being improved; run it again (and build_atlas.py) after
they change. build_atlas.py keeps Diathir_Atlas/posters/ when it rebuilds the Atlas.
"""
import argparse
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
ATLAS = os.path.join(ROOT, 'Diathir_Atlas')
FMG = os.path.join(ATLAS, 'fmg')
MAPS = os.path.join(ROOT, 'eras', 'maps')
OUT = os.path.join(ATLAS, 'posters')
WORK = os.path.join(TOOLS, '.work_posters')
MASTER = os.path.join(ROOT, 'Rodos_finished.map')        # the master; build_atlas.py copies it to Diathir_Atlas/Diathir.map
KEYS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
PW, PH = 1800, 1180                                      # the poster in CSS px (printed at --pscale times this)
LAYERS = ['states', 'borders', 'burgIcons', 'labels', 'rivers', 'lakes', 'coastline', 'routes', 'markers', 'relief', 'scaleBar']

sys.path.insert(0, os.path.join(ROOT, 'legendarium'))
import build_book  # noqa: E402
import reckoning  # noqa: E402

AGE_CSS = {}
for m in re.finditer(r'--(\w+):(#[0-9a-fA-F]{3,6})', open(os.path.join(ROOT, 'atlas_style.css'), encoding='utf-8').read()):
    AGE_CSS.setdefault(m.group(1), m.group(2))
esc = html.escape


def fail(msg):
    sys.exit('make_posters: ' + msg)


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


class Server:
    """eras/engine/serve.py on a free port, serving this folder to 127.0.0.1 only; stopped (by its own process,
    which holds the port) when done."""
    def __enter__(self):
        self.p = subprocess.Popen([sys.executable, os.path.join(ROOT, 'eras', 'engine', 'serve.py'), '0', ROOT],
                                  stdout=subprocess.PIPE, text=True)
        line = self.p.stdout.readline().split()
        if len(line) != 2 or line[0] != 'READY':
            self.p.terminate()
            fail('the local server did not start')
        self.port = int(line[1])
        self.base = 'http://127.0.0.1:%d' % self.port
        return self

    def __exit__(self, *a):
        self.p.terminate()
        try:
            self.p.wait(10)
        except subprocess.TimeoutExpired:
            self.p.kill()


def url_of(path):
    return '/' + os.path.relpath(os.path.abspath(path), ROOT).replace(os.sep, '/')


def run(cfg, name):
    os.makedirs(WORK, exist_ok=True)
    cp = os.path.join(WORK, 'cfg_%s.json' % name)
    json.dump(cfg, open(cp, 'w', encoding='utf-8'))
    r = subprocess.run(['node', os.path.join(TOOLS, 'posters_driver.js'), cp], env=env(), text=True, timeout=3600)
    if r.returncode:
        fail('the headless browser failed (%s)' % name)


# ---------------------------------------------------------------- what each poster says
def file_key(k):
    return 'Today' if k == 'M' else 'Age_' + k


def snapshot(k, info):
    """The date the map shows: the era spec's (eras/specs/age_<K>.json lore), else the map's own calendar."""
    if k != 'M':
        sp = os.path.join(ROOT, 'eras', 'specs', 'age_%s.json' % k)
        try:
            d = json.load(open(sp, encoding='utf-8')).get('lore', {}).get('description', '')
            if ' · ' in d:
                return d.split(' · ', 1)[1].strip()
        except (OSError, ValueError):
            pass
    if info.get('year') and info.get('eraShort'):
        return '%s %s' % (info['eraShort'], format(int(info['year']), ','))
    return reckoning.display_span(k if k != 'M' else 'VII').split('–')[-1].strip()


def strip_md(s):
    return re.sub(r'[*_]', '', build_book.plain(s) if hasattr(build_book, 'plain') else s).strip()


def chief_events(rec, k, n=7):
    evs = sorted([e for e in rec.events if e['age'] == k and e.get('y') is not None], key=lambda e: (e['y'], e['m'], e['d']))
    canon = [e for e in evs if e.get('canon')]
    pool = canon if len(canon) >= 4 else evs
    if len(pool) <= n:
        pick = pool
    else:
        pick = [pool[round(i * (len(pool) - 1) / (n - 1))] for i in range(n)]
    out = []
    for e in pick:
        t = strip_md(rec.resolve(e['title'], link=False))
        out.append({'y': e['y'], 'date': e.get('date') or '', 'year': reckoning.display_year(e['y'], e['m'], e['d'], k),
                    'title': t if len(t) <= 70 else t[:68].rsplit(' ', 1)[0] + '…'})
    return out


def front(k):
    if k == 'M':
        return {'kicker': 'Leabhar nan Aoisean', 'dt': 'Rìoghachd Dia-thìr', 'en': 'The Legendarium of Dia-thìr',
                'age': 'Dia-thìr today, at the close of the seven ages', 'span': 'VE 1 to %s' % reckoning.display_span('VII').split('–')[-1].strip(),
                'color': AGE_CSS.get('dubhan', '#8fa3c0'), 'epi': None}
    dt, en, css = build_book.AGE_NAMES[k]
    era = reckoning.ERA[k]
    fp = os.path.join(ROOT, 'eras', 'age_%s' % k, 'front.json')
    epi = None
    try:
        epi = json.load(open(fp, encoding='utf-8')).get('epigraph') if os.path.exists(fp) else None
    except ValueError:
        pass
    en_cap = en[0].upper() + en[1:]
    return {'kicker': era[5], 'dt': dt, 'en': 'The Legendarium of Dia-thìr — ' + en_cap, 'age': 'Age %s · %s' % (k, en_cap),
            'span': '%s, %s' % (era[4][0].upper() + era[4][1:], reckoning.display_span(k)), 'color': AGE_CSS.get(css, '#c9a435'),
            'epi': epi}


CSS = """
@font-face{font-family:'Uncial';src:url('/legendarium/fonts/UncialAntiqua-Regular.ttf')}
@font-face{font-family:'Cinzel';src:url('/legendarium/fonts/Cinzel[wght].ttf');font-weight:400 900}
@font-face{font-family:'Garamond';src:url('/legendarium/fonts/EBGaramond[wght].ttf');font-weight:400 800}
@font-face{font-family:'Garamond';font-style:italic;src:url('/legendarium/fonts/EBGaramond-Italic[wght].ttf');font-weight:400 800}
@page{margin:0}
*{box-sizing:border-box}
html,body{margin:0;background:#efe4cc}
.poster{position:relative;width:%(pw)dpx;height:%(ph)dpx;overflow:hidden;background:#efe4cc;color:#2a2018;font-family:'Garamond',serif;
  break-after:page;page-break-after:always}
.poster:last-child{break-after:auto;page-break-after:auto}
.frame{position:absolute;inset:18px;border:3px double #6d4a22}
.map{position:absolute;left:34px;top:34px;width:%(mw)dpx;height:%(mh)dpx;border:1px solid #6d4a22;overflow:hidden}
.map img{display:block;width:100%%;height:100%%}
.cart{position:absolute;left:58px;top:58px;width:470px;background:rgba(247,240,224,.93);border:2px solid #6d4a22;outline:1px solid #6d4a22;
  outline-offset:4px;padding:16px 22px 14px;text-align:center;box-shadow:0 4px 18px rgba(0,0,0,.25)}
.cart .k{font-family:'Cinzel';font-size:13px;letter-spacing:.32em;text-transform:uppercase;color:#6d4a22;margin:0 0 6px}
.cart h1{font-family:'Uncial';font-weight:400;font-size:40px;line-height:1.05;margin:0 0 4px;color:var(--c)}
.cart .en{font-style:italic;font-size:19px;margin:0 0 8px;line-height:1.25}
.cart .rule{width:90px;border-top:1px solid #6d4a22;margin:8px auto}
.cart .age{font-family:'Cinzel';font-size:14px;letter-spacing:.08em;margin:0 0 3px}
.cart .span{font-size:17px;margin:0 0 3px}
.cart .snap{font-size:15px;margin:0;color:#4a3a28}
.cart .epi{font-style:italic;font-size:14px;margin:8px 0 0;color:#4a3a28}
.legend{position:absolute;right:58px;top:58px;width:300px;background:rgba(247,240,224,.93);border:1px solid #6d4a22;padding:10px 14px;
  font-size:14px;box-shadow:0 4px 14px rgba(0,0,0,.2)}
.legend h2{font-family:'Cinzel';font-size:13px;letter-spacing:.2em;text-transform:uppercase;margin:0 0 6px;color:#6d4a22}
.legend .row{display:flex;align-items:center;gap:8px;margin:3px 0;line-height:1.2}
.legend .sw{flex:none;width:22px;height:14px;border:1px solid rgba(0,0,0,.45)}
.legend svg{flex:none}
.legend .more{font-style:italic;color:#4a3a28}
.strip{position:absolute;left:34px;right:34px;bottom:34px;height:%(sh)dpx;border:1px solid #6d4a22;background:#f5ecd8}
.strip h2{position:absolute;left:14px;top:8px;margin:0;font-family:'Cinzel';font-size:13px;letter-spacing:.2em;text-transform:uppercase;color:#6d4a22}
.strip .axis{position:absolute;left:40px;right:40px;top:%(ay)dpx;height:4px;background:var(--c);border-radius:2px}
.strip .ev{position:absolute;width:210px;margin-left:-105px;text-align:center;font-size:14px;line-height:1.2}
.strip .ev .d{display:block;font-family:'Cinzel';font-size:11.5px;letter-spacing:.04em;color:#6d4a22}
.strip .ev.up{bottom:%(up)dpx}.strip .ev.dn{top:%(dn)dpx}
.strip .tick{position:absolute;top:%(ty)dpx;width:12px;height:12px;margin-left:-6px;border-radius:50%%;background:#f5ecd8;border:3px solid var(--c)}
.strip .end{position:absolute;top:%(ey)dpx;font-family:'Cinzel';font-size:12px;color:#6d4a22}
.strip .band{position:absolute;top:%(by)dpx;height:78px;border-left:1px solid #6d4a22;padding:6px 8px;font-size:13.5px;line-height:1.2}
.strip .band b{display:block;font-family:'Uncial';font-weight:400;font-size:17px}
.foot{position:absolute;right:44px;bottom:21px;font-size:9.5px;color:#6d4a22;font-family:'Cinzel';letter-spacing:.1em}
"""


def legend_html(info):
    rows = []
    states = sorted(info['states'], key=lambda s: -(s.get('cells') or 0))
    for s in states[:9]:
        rows.append('<div class="row"><span class="sw" style="background:%s"></span><span>%s</span></div>'
                    % (esc(s['color'] or '#999'), esc(s['full'] or s['name'])))
    if len(states) > 9:
        rows.append('<div class="row more">and %d more realms</div>' % (len(states) - 9))
    sym = []
    sym.append('<div class="row"><svg width="22" height="14"><circle cx="11" cy="7" r="4.2" fill="#fff" stroke="#3a2a1a" stroke-width="1.4"/>'
               '<circle cx="11" cy="7" r="1.6" fill="#3a2a1a"/></svg><span>a seat of a realm</span></div>')
    sym.append('<div class="row"><svg width="22" height="14"><circle cx="11" cy="7" r="3" fill="#fff" stroke="#3a2a1a" stroke-width="1.2"/></svg>'
               '<span>a town (%s in all)</span></div>' % format(info['burgs'], ','))
    if info.get('routes', {}).get('roads') or info.get('routes', {}).get('trails'):
        sym.append('<div class="row"><svg width="22" height="14"><path d="M1 9 Q11 3 21 8" fill="none" stroke="#8b4513" stroke-width="1.6" stroke-dasharray="3 1.5"/></svg><span>roads and trails</span></div>')
    if info.get('routes', {}).get('searoutes'):
        sym.append('<div class="row"><svg width="22" height="14"><path d="M1 8 Q11 2 21 8" fill="none" stroke="#fff" stroke-width="1.4" stroke-dasharray="1.5 2"/></svg><span>sea roads</span></div>')
    sym.append('<div class="row"><svg width="22" height="14"><path d="M1 10 C6 4 12 12 21 4" fill="none" stroke="#5d97bb" stroke-width="2"/></svg><span>rivers and lochs</span></div>')
    if info.get('markers'):
        sym.append('<div class="row"><svg width="22" height="14"><path d="M11 13 L6 6 A5 5 0 1 1 16 6 Z" fill="#9e2a2a" stroke="#fff" stroke-width=".8"/></svg>'
                   '<span>a storied place (%d)</span></div>' % info['markers'])
    return '<div class="legend"><h2>%s</h2>%s<h2 style="margin-top:10px">Signs</h2>%s</div>' % (
        'The realm' if len(states) == 1 else 'The realms', ''.join(rows), ''.join(sym))


def strip_html(rec, k, sh):
    if k == 'M':   # today's poster: the seven ages, side by side
        w = (PW - 68) / 7.0
        bands = []
        for i, a in enumerate(KEYS):
            dt, en, css = build_book.AGE_NAMES[a]
            bands.append('<div class="band" style="left:%.1fpx;width:%.1fpx;background:linear-gradient(%s33,transparent)"><b style="color:%s">%s</b>'
                         '%s<br><span style="font-family:Cinzel;font-size:11.5px;color:#6d4a22">%s</span></div>'
                         % (i * w, w, AGE_CSS.get(css, '#999'), AGE_CSS.get(css, '#333'), esc(dt), esc(en[0].upper() + en[1:]), esc(reckoning.display_span(a))))
        return '<div class="strip" style="--c:#6d4a22"><h2>The seven ages</h2>%s</div>' % ''.join(bands)
    evs = chief_events(rec, k)
    era = reckoning.ERA[k]
    lo, hi = era[1], era[2]
    left, right = 40 + 105 - 40, PW - 68 - 40 - 105 + 40     # keep every label inside the strip
    out = ['<div class="strip"><h2>The chief events of the age</h2><div class="axis"></div>']
    last_x = {True: -1e9, False: -1e9}
    for i, e in enumerate(evs):
        f = (e['y'] - lo) / float(max(1, hi - lo))
        x = 40 + f * (PW - 68 - 80)
        x = max(left, min(right, x))
        up = i % 2 == 0
        if x - last_x[up] < 215:                 # two labels on one side would touch: nudge along
            x = last_x[up] + 215
        x = min(right, x)
        last_x[up] = x
        out.append('<span class="tick" style="left:%.1fpx"></span><div class="ev %s" style="left:%.1fpx"><span class="d">%s</span>%s</div>'
                   % (40 + f * (PW - 68 - 80), 'up' if up else 'dn', x, esc(e['year']), esc(e['title'])))
    out.append('<span class="end" style="left:44px">%s 1</span><span class="end" style="right:44px">%s</span></div>'
               % (esc(era[3]), esc(reckoning.display_span(k).split('–')[-1].strip())))
    return ''.join(out)


def poster_html(rec, k, info, img):
    f = front(k)
    sh = 200
    mw = PW - 68
    mh = PH - 68 - sh - 14
    snap = snapshot(k, info)
    epi = ''
    if f['epi']:
        epi = '<p class="epi">“%s”<br>%s</p>' % (esc(f['epi'].get('ro', '')), esc(f['epi'].get('en', '')))
    body = ('<div class="poster" style="--c:%s"><div class="frame"></div><div class="map"><img src="%s" alt=""></div>'
            '<div class="cart"><p class="k">%s</p><h1>%s</h1><p class="en">%s</p><div class="rule"></div><p class="age">%s</p>'
            '<p class="span">%s</p><p class="snap">%s</p>%s</div>%s%s<div class="foot">Dia-thìr · made %s</div></div>'
            % (f['color'], img, esc(f['kicker']), esc(f['dt']), esc(f['en']), esc(f['age']), esc(f['span']),
               esc(('The island today: ' if k == 'M' else 'The island at the close of the age: ') + snap), epi,
               legend_html(info), strip_html(rec, k, sh), datetime.date.today().isoformat()))
    return body, {'mw': mw, 'mh': mh, 'sh': sh}


def page(bodies, dims):
    d = dict(pw=PW, ph=PH, mw=dims['mw'], mh=dims['mh'], sh=dims['sh'], ay=112, ty=108, up=104, dn=128, ey=150, by=40)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Dia-thìr posters</title><style>%s</style></head><body>%s</body></html>'
            % (CSS % d, ''.join(bodies)))


# ---------------------------------------------------------------- all of it
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('keys', nargs='*', help='I..VII and M (today); all when none are given')
    ap.add_argument('--scale', type=float, default=3, help='the map picture at this many times its size (default 3)')
    ap.add_argument('--pscale', type=float, default=2.6, help='the poster PNG at this many times %dx%d (default 2.6)' % (PW, PH))
    ap.add_argument('--no-pdf', action='store_true')
    a = ap.parse_args()
    if not os.path.isfile(os.path.join(FMG, 'index.html')):
        fail('Diathir_Atlas/fmg/ is missing: build the Atlas first (build_atlas.py)')
    want = [k for k in (a.keys or ['M'] + KEYS)]
    bad = [k for k in want if k not in KEYS + ['M']]
    if bad:
        fail('unknown map %s (I..VII or M)' % bad)
    maps = []
    for k in want:
        src = MASTER if k == 'M' else os.path.join(MAPS, 'Diathir_Age_%s.map' % k)
        if not os.path.exists(src):
            print('  no map for %s (%s): skipped' % (k, os.path.relpath(src, ROOT)))
            continue
        m = {'key': k, 'path': url_of(src),
             'overlay': os.path.join(MAPS, 'overlays', ('Diathir_Master' if k == 'M' else 'Diathir_Age_' + k) + '.json')}
        if k == 'M':
            m['shots'] = os.path.join(MAPS, 'shots')
            m['shotPrefix'] = 'Diathir_Master_'
        maps.append(m)
    if not maps:
        fail('no maps to draw')
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    os.makedirs(os.path.join(OUT, 'thumbs'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    rec = build_book.Record()
    with Server() as srv:
        run({'mode': 'maps', 'base': srv.base, 'fmg': '/Diathir_Atlas/fmg/', 'work': WORK, 'scale': a.scale,
             'layers': LAYERS, 'maps': maps}, 'maps')
        posters, dims = [], None
        for m in maps:
            k = m['key']
            info = json.load(open(os.path.join(WORK, 'info_%s.json' % k), encoding='utf-8'))
            body, dims = poster_html(rec, k, info, 'map_%s.png' % k)
            hp = os.path.join(WORK, 'poster_%s.html' % k)
            open(hp, 'w', encoding='utf-8').write(page([body], dims))
            f = front(k)
            posters.append({'key': k, 'url': url_of(hp), 'png': os.path.join(OUT, 'Diathir_Poster_%s.png' % file_key(k)),
                            'thumb': os.path.join(OUT, 'thumbs', 'Diathir_Poster_%s.jpg' % file_key(k)),
                            'print': os.path.join(OUT, 'print', 'Diathir_Poster_%s.jpg' % file_key(k)),
                            'meta': {'key': k, 'file': 'posters/Diathir_Poster_%s.png' % file_key(k),
                                     'thumb': 'posters/thumbs/Diathir_Poster_%s.jpg' % file_key(k),
                                     'dt': f['dt'], 'en': f['en'], 'age': f['age'], 'span': f['span'], 'snap': snapshot(k, info)}})
        # the PDF holds every poster in the folder (those made now and those of earlier runs), one to a page,
        # from their print copies (posters/print/*.jpg, written with each PNG)
        pdf = None
        if not a.no_pdf:
            made = {p['key'] for p in posters}
            imgs = []
            for k in KEYS + ['M']:
                jp = os.path.join(OUT, 'print', 'Diathir_Poster_%s.jpg' % file_key(k))
                if k in made or os.path.exists(jp):
                    imgs.append('<div class="poster"><img src="%s" style="width:%dpx;height:%dpx;display:block"></div>'
                                % (os.path.relpath(jp, WORK).replace(os.sep, '/'), PW, PH))
            pp = os.path.join(WORK, 'print_all.html')
            open(pp, 'w', encoding='utf-8').write(page(imgs, dims))
            pdf = {'url': url_of(pp), 'out': os.path.join(OUT, 'Diathir_Posters.pdf')}
        run({'mode': 'compose', 'base': srv.base, 'pw': PW, 'ph': PH, 'pscale': a.pscale,
             'posters': [{k: p[k] for k in ('url', 'png', 'thumb', 'print')} for p in posters], 'pdf': pdf}, 'compose')
    # the gallery's list: every poster in the folder (so a partial run keeps the others)
    listing = {}
    lp = os.path.join(OUT, 'posters.json')
    if os.path.exists(lp):
        try:
            listing = {x['key']: x for x in json.load(open(lp, encoding='utf-8'))['posters']}
        except (ValueError, KeyError):
            listing = {}
    for p in posters:
        listing[p['key']] = p['meta']
    order = [k for k in KEYS + ['M'] if k in listing and os.path.exists(os.path.join(ATLAS, listing[k]['file']))]
    data = {'posters': [listing[k] for k in order], 'made': datetime.date.today().isoformat(),
            'pdf': 'posters/Diathir_Posters.pdf' if os.path.exists(os.path.join(OUT, 'Diathir_Posters.pdf')) else None}
    json.dump(data, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, 'posters.js'), 'w', encoding='utf-8') as fh:
        fh.write('ATLAS_LOAD("posters", %s);\n' % json.dumps(data, ensure_ascii=False))
    shutil.rmtree(WORK, ignore_errors=True)
    print('posters: %s in %s' % (', '.join(p['key'] for p in posters), os.path.relpath(OUT, ROOT)))
    print('  overlays in eras/maps/overlays/, today\'s pictures in eras/maps/shots/: run build_atlas.py to carry them in')


if __name__ == '__main__':
    main()
