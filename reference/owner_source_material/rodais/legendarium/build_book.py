"""
build_book.py -- assemble the legendarium of Rodos from its sources.

    python build_book.py        -> LEGENDARIUM.md (the whole record as plain text; the Atlas's Book tab shows it)

Sources, all in this folder:
    annals_dated.json       every event of the six ages, dated by reckoning.py
    book/creation.md        the Telling of the Making, which stands before the Six Books
    book/age_I..VI.md       the prose account of each age
    appendices/*.md         the appendices, in file-name order
    appendices/houses.json  the houses and their people (optional), dated here
    gazetteer/out_*.json    every burg of the map: founding, history, what it is known for
    world.json              the map's names and ids

Writers never type dates. In any .md source:
    {{date:ID}}             the full date of annals event ID, in the era of its age   -> 30 am Faoilleach, AE 75
    {{year:ID}}             its year                                                  -> AE 75
    {{reckon:A:B:KEY}}      a day the reckoning makes between years A and B of the continuous count
                            (negative before its year 1), the same for the same KEY every time,
                            in the era the day falls in                               -> 4 an Dàmhair, LE 1,661
    {{reckonyear:A:B:KEY}}  just its year
    {{place:REF}}           a place by map id (burg:19, marker:3, province:1, zone:0, river:5, feature:2)

build_atlas.py imports this module to put the same record into the Rodos Atlas.
"""
import glob
import html
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reckoning  # noqa: E402


def fold(s):
    """Sort key: case and accents ignored, so Àth files under A."""
    return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode()

AGE_NAMES = {
    'I': ('An Aois Àrsaidh', 'the Ancient Age', 'myth'),
    'II': ('An Aois Naomh', 'the Holy Age', 'holy'),
    'III': ('An Aois Scaraidh', 'the Age of Sundering', 'sunder'),
    'IV': ('An Aois Choigreach', 'the Age of Strangers', 'colonial'),
    'V': ('An Aois Rìoghachd', 'the Age of the Kingdom', 'kingdom'),
    'VI': ('An Aois Dhubhain', 'the Age of Dubhan', 'dubhan'),
}
AGES = reckoning.AGE_KEYS
# a town's founding is dated in the stretch of years its age is dated in (reckoning.STRETCHES)
AGE_SPAN = {k: (a, b) for a, b, keys in reckoning.STRETCHES for k in keys}
BOOK_TITLES = {'I': 'The First Book', 'II': 'The Second Book', 'III': 'The Third Book',
               'IV': 'The Fourth Book', 'V': 'The Fifth Book', 'VI': 'The Sixth Book'}


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding='utf-8'))


# ---------------------------------------------------------------- the record
class Record:
    def __init__(self):
        self.events = load('annals_dated.json')
        self.by_id = {e['id']: e for e in self.events}
        self.world = load('world.json')
        album_years, self.months_ok, self.days_ok = reckoning.load_pool()
        self.years_ok = sorted({y for a, b, _ in reckoning.STRETCHES for y in reckoning.reachable_years(album_years, a, b)})
        self.names = {}
        for kind in ('burgs', 'provinces', 'rivers', 'markers', 'zones', 'features'):
            for o in self.world[kind]:
                self.names['%s:%s' % (kind[:-1], o['id'])] = o['name']
        self.burg = {b['id']: b for b in self.world['burgs']}
        self.gaz = {}
        for f in sorted(glob.glob(os.path.join(HERE, 'gazetteer', 'out_*.json'))):
            for k, v in json.load(open(f, encoding='utf-8')).items():
                self.gaz[int(k)] = v
        self.at = {}                                   # place ref -> its events, in order
        for e in self.events:
            if e.get('place'):
                self.at.setdefault(e['place'], []).append(e)
        self.missing = []
        self.date_founding()
        self.houses = self.load_houses()

    # -- dates the reckoning makes for things that are not annals events
    def reckon(self, lo, hi, key):
        lo, hi = min(lo, hi), max(lo, hi)
        cands = [y for y in self.years_ok if lo <= y <= hi] or [reckoning.nz(lo)]
        h = reckoning.slot_hash(key)
        y = cands[h % len(cands)]
        slots = [(m, d) for m in self.months_ok for d in self.days_ok
                 if d <= reckoning.calendar.monthrange(y if y > 0 else 2001, m)[1]]
        m, d = slots[(h >> 8) % len(slots)]
        return y, m, d

    def date_founding(self):
        """Every burg's founding: in its age (and the writer's window), before anything else recorded there."""
        for bid, g in self.gaz.items():
            ev = self.by_id.get(g.get('founded_event') or '')
            if ev:                                     # the annals tell the founding itself: take its day
                g['founded'] = {'y': ev['y'], 'm': ev['m'], 'd': ev['d'], 'date': ev['date']}
                continue
            first, last = AGE_SPAN.get(g.get('founded_age') or 'II', AGE_SPAN['II'])
            lo, hi = first, last
            if g.get('founded_between'):
                lo, hi = max(lo, g['founded_between'][0]), min(hi, g['founded_between'][1])
            # before the first thing the annals record there in or after its age (earlier events happened
            # at the site before the town was there)
            evs = [e for e in self.at.get('burg:%d' % bid, []) if e['y'] >= lo]
            if evs:
                hi = min(hi, evs[0]['y'] - 1 if evs[0]['y'] != 1 else -1)
            if lo > hi:
                hi = lo
            y, m, d = self.reckon(lo, hi, 'founding:%d' % bid)
            # never before its age opens (the eras count from the opening event): held to the year after it
            opens = reckoning.openings().get(g.get('founded_age') or 'II')
            if opens and (y, m, d) < opens:
                y1 = reckoning.nz(opens[0] + 1)
                y, m, d = self.reckon(y1, y1, 'founding:%d' % bid)
            g['founded'] = {'y': y, 'm': m, 'd': d, 'date': reckoning.display(y, m, d)}

    def load_houses(self):
        p = os.path.join(HERE, 'appendices', 'houses.json')
        if not os.path.exists(p):
            return []
        houses = json.load(open(p, encoding='utf-8'))
        for h in houses:
            for pr in h.get('members', []):
                for f in ('born', 'died'):
                    w = pr.get(f + '_between')
                    if w:
                        y, m, d = self.reckon(w[0], w[1], '%s:%s:%s' % (h.get('house'), pr.get('id'), f))
                        pr[f] = reckoning.display(y, m, d)
                        pr[f + '_y'] = y
                if pr.get('born_y') and pr.get('died_y') and pr['died_y'] <= pr['born_y']:
                    self.missing.append('%s: died before born' % pr.get('id'))
        return houses

    # -- tokens
    def place_name(self, ref):
        return self.names.get(ref, ref)

    def resolve(self, text, link=True):
        def sub(m):
            kind, arg = m.group(1), m.group(2)
            if kind in ('date', 'year'):
                e = self.by_id.get(arg)
                if not e:
                    self.missing.append(arg)
                    return '[?%s]' % arg
                if kind == 'date':
                    return e['date']
                return reckoning.display_year(e['y'], e['m'], e['d'], e['age'])
            if kind in ('reckon', 'reckonyear'):
                a, b, key = arg.split(':', 2)
                y, mo, d = self.reckon(int(a), int(b), key)
                full = reckoning.display(y, mo, d)
                return full if kind == 'reckon' else year_of(full)
            if kind == 'place':
                name = self.place_name(arg)
                if name == arg:
                    self.missing.append(arg)
                return '\u27e6%s|%s\u27e7' % (arg, name) if link else name
            return m.group(0)
        # a full date in the middle of a sentence takes a comma after its year, as a written-out date does
        # ("On 19 an Giblean, LE 40, the fleet sailed"), unless and/or/to/until joins it to what follows
        text = re.sub(r'(\{\{(?:date|reckon):[^}]+\}\})(?= (?!(?:and|or|nor|to|until|till)\b)(?:[^\W\d_]|\{\{place:|\*\*))',
                      r'\1,', text)
        return re.sub(r'\{\{(date|year|reckon|reckonyear|place):([^}]+)\}\}', sub, text)


def plain(md):
    return re.sub('\u27e6[^|\u27e7]+\\|([^\u27e7]*)\u27e7', r'\1', md)


def year_of(full):
    """'4 an Dàmhair, LE 1,661' -> 'LE 1,661'"""
    parts = full.split(' ')
    return ' '.join(parts[-2:])


# ---------------------------------------------------------------- a small markdown
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub('\u27e6([^|\u27e7]+)\\|([^\u27e7]*)\u27e7', r'<a class="pl" data-ref="\1">\2</a>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    s = re.sub(r'(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])', r'<em>\1</em>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    s = s.replace(' -- ', ' – ')
    return s


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', re.sub(r'<[^>]+>', '', s).lower()).strip('-')[:60]


def md_to_html(md, prefix, toc):
    """Paragraphs, #-headings, > quotes, - and 1. lists, | tables |, --- rules, *em* and **strong**."""
    out, lines, i = [], md.split('\n'), 0
    tops = [len(m.group(1)) for m in re.finditer(r'^(#{1,4})\s', md, re.M)]
    shift = 2 - min(tops) if tops else 1          # the file's top heading is an h2, the next level h3, ...
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', ln)
        if m:
            lvl, txt = len(m.group(1)), inline(m.group(2).strip())
            hid = '%s-%s' % (prefix, slug(txt))
            if lvl <= 3:
                toc.append((lvl, hid, re.sub(r'<[^>]+>', '', txt)))
            h = min(6, lvl + shift)
            out.append('<h%d id="%s">%s</h%d>' % (h, hid, txt, h))
            i += 1
            continue
        if re.match(r'^\s*(-{3,}|\*{3,})\s*$', ln):
            out.append('<hr>')
            i += 1
            continue
        if ln.startswith('>'):
            buf = []
            while i < len(lines) and lines[i].startswith('>'):
                buf.append(lines[i][1:].lstrip())
                i += 1
            out.append('<blockquote>%s</blockquote>' % md_to_html('\n'.join(buf), prefix + 'q', []))
            continue
        if ln.lstrip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            body = [r for r in rows if not all(re.match(r'^:?-{2,}:?$', c) for c in r if c)]
            if body:
                t = '<div class="tw"><table><thead><tr>%s</tr></thead><tbody>' % ''.join('<th>%s</th>' % inline(c) for c in body[0])
                t += ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(c) for c in r) for r in body[1:])
                out.append(t + '</tbody></table></div>')
            continue
        if re.match(r'^\s*([-*]|\d+\.)\s+', ln):
            ordered = bool(re.match(r'^\s*\d+\.', ln))
            items = []
            while i < len(lines) and (re.match(r'^\s*([-*]|\d+\.)\s+', lines[i]) or (lines[i].startswith('  ') and lines[i].strip() and items)):
                if re.match(r'^\s*([-*]|\d+\.)\s+', lines[i]):
                    items.append(re.sub(r'^\s*([-*]|\d+\.)\s+', '', lines[i]))
                else:
                    items[-1] += ' ' + lines[i].strip()
                i += 1
            tag = 'ol' if ordered else 'ul'
            out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % inline(x) for x in items), tag))
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{1,4}\s|>|\s*\||\s*([-*]|\d+\.)\s+|\s*-{3,}\s*$)', lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append('<p>%s</p>' % inline(' '.join(buf)))
        else:
            i += 1
    return '\n'.join(out)


# ---------------------------------------------------------------- the parts of the book
def creation_part(rec):
    """The Telling of the Making (book/creation.md), set before the Six Books; None if it is missing."""
    p = os.path.join(HERE, 'book', 'creation.md')
    if not os.path.exists(p):
        return None
    return ('book-creation', None, rec.resolve(open(p, encoding='utf-8').read()))


def prose_parts(rec):
    parts = []
    for k in AGES:
        p = os.path.join(HERE, 'book', 'age_%s.md' % k)
        if os.path.exists(p):
            parts.append(('book-' + k, k, rec.resolve(open(p, encoding='utf-8').read())))
    return parts


def appendix_parts(rec):
    parts = []
    for p in sorted(glob.glob(os.path.join(HERE, 'appendices', '*.md'))):
        key = os.path.splitext(os.path.basename(p))[0]
        parts.append(('app-' + slug(key), None, rec.resolve(open(p, encoding='utf-8').read())))
    return parts


def houses_html(rec):
    if not rec.houses:
        return ''
    out = ['<h2 id="houses">The Houses of Rodos</h2>']
    for h in rec.houses:
        hid = 'house-' + slug(h.get('house', ''))
        out.append('<h3 id="%s">%s</h3>' % (hid, inline(h.get('house', ''))))
        if h.get('note'):
            out.append('<p>%s</p>' % inline(rec.resolve(h['note'])))
        kids = {}
        for pr in h.get('members', []):
            kids.setdefault(pr.get('parent'), []).append(pr)

        def tree(parent):
            rows = kids.get(parent, [])
            if not rows:
                return ''
            li = []
            for pr in rows:
                life = ' – '.join(x for x in (pr.get('born', '?') and ('b. ' + pr['born'] if pr.get('born') else ''),
                                              ('d. ' + pr['died']) if pr.get('died') else '') if x)
                bits = '<b>%s</b>' % inline(pr.get('name', ''))
                if pr.get('spouse'):
                    bits += ' = %s' % inline(pr['spouse'])
                if life:
                    bits += ' <span class="life">%s</span>' % life
                if pr.get('note'):
                    bits += '<br><span class="pn">%s</span>' % inline(rec.resolve(pr['note'], link=False))
                li.append('<li>%s%s</li>' % (bits, tree(pr.get('id'))))
            return '<ul class="tree">%s</ul>' % ''.join(li)
        out.append(tree(None))
    return '\n'.join(out)


def annals_html(rec, link_places=True):
    out = []
    for k in AGES:
        evs = [e for e in rec.events if e['age'] == k]
        if not evs:
            continue
        rn, en, cat = AGE_NAMES[k]
        out.append('<h3 id="annals-%s" class="agehd" style="color:var(--%s)">Age %s · %s <span>%s · %s, %s</span></h3>' % (
            k, cat, k, rn, en, reckoning.ERA[k][4], reckoning.display_span(k)))
        for e in evs:
            pl = ''
            if e.get('place'):
                pl = ' <a class="pl" data-ref="%s">%s</a>' % (e['place'], html.escape(rec.place_name(e['place']))) if link_places \
                    else ' <span class="plx">%s</span>' % html.escape(rec.place_name(e['place']))
            out.append('<div class="an%s" id="ev-%s"><div class="ad">%s%s</div><div class="at">%s</div><div class="ab">%s</div></div>' % (
                ' canon' if e.get('canon') else '', e['id'], e['date'], pl, inline(e['title']), inline(e['body'])))
    return '\n'.join(out)


def gazetteer_html(rec):
    out = []
    provs = {p['name']: p for p in rec.world['provinces']}
    byprov = {}
    for bid, b in sorted(rec.burg.items()):
        byprov.setdefault(b.get('province') or '—', []).append(bid)
    for pname in sorted(byprov, key=fold):
        pid = provs.get(pname, {}).get('id')
        out.append('<h3 id="gz-p-%s">%s</h3>' % (slug(pname), html.escape(provs.get(pname, {}).get('fullName', pname))))
        for bid in sorted(byprov[pname], key=lambda i: fold(rec.burg[i]['name'])):
            b, g = rec.burg[bid], rec.gaz.get(bid, {})
            facts = [b.get('group', ''), b.get('culture', ''), b.get('faith', ''), 'pop. %s' % format(b.get('population', 0), ',')]
            out.append('<div class="gz" id="gz-%d"><h4><a class="pl" data-ref="burg:%d">%s</a></h4><p class="gf">%s</p>' % (
                bid, bid, html.escape(b['name']), ' · '.join(html.escape(str(f)) for f in facts if f)))
            if g:
                out.append('<p class="gf">Founded %s%s. Known for %s.</p>' % (
                    g['founded']['date'], (' by ' + html.escape(g['founded_by'])) if g.get('founded_by') else '',
                    html.escape(g.get('known_for', '').rstrip('.'))))
                out.append('<p>%s</p>' % inline(g.get('history', '')))
            evs = rec.at.get('burg:%d' % bid, [])
            if evs:
                out.append('<ul class="gev">%s</ul>' % ''.join('<li><a href="#ev-%s">%s</a> — %s</li>' % (e['id'], e['date'], inline(e['title'])) for e in evs))
            out.append('</div>')
    return '\n'.join(out)


def compose(rec, link_places=True):
    """(toc, body html) of the whole record: prose, annals, appendices, houses, gazetteer."""
    toc, body = [], []
    making = creation_part(rec)
    if making:
        body.append('<section class="book prologue age-myth" id="%s">%s</section>' % (making[0], md_to_html(making[2], making[0], toc)))
    prose = prose_parts(rec)
    if prose:
        toc.append((1, 'part-tale', 'The Tale of the Six Ages'))
    for pid, k, md in prose:
        rn, en, cat = AGE_NAMES[k]
        body.append('<section class="book age-%s" id="%s">%s</section>' % (cat, pid, md_to_html(md, pid, toc)))
    toc.append((1, 'part-annals', 'The Annals of Rodos'))
    body.append('<section class="annals" id="part-annals"><h2>The Annals of Rodos</h2><p class="lede">Every remembered event of the six ages, '
                'in order, each on its day. %d events.</p>%s</section>' % (len(rec.events), annals_html(rec, link_places)))
    for k in AGES:
        toc.append((2, 'annals-' + k, 'Age %s · %s' % (k, AGE_NAMES[k][0])))
    apps = appendix_parts(rec)
    if apps or rec.houses:
        toc.append((1, 'part-app', 'Appendices'))
    for pid, _, md in apps:
        body.append('<section class="app" id="%s">%s</section>' % (pid, md_to_html(md, pid, toc)))
    if rec.houses:
        toc.append((2, 'houses', 'The Houses of Rodos'))
        body.append('<section class="app">%s</section>' % houses_html(rec))
    toc.append((1, 'part-gaz', 'Gazetteer'))
    body.append('<section class="gazetteer" id="part-gaz"><h2>A Gazetteer of Rodos</h2><p class="lede">Every town of the island, by '
                'shire: when and by whom it was founded, its history, and what the annals record there.</p>%s</section>' % gazetteer_html(rec))
    return toc, '\n'.join(body)


def toc_html(toc):
    rows = []
    for lvl, hid, txt in toc:
        if lvl > 2:
            continue
        cls = 'tp' if lvl == 1 else 'tc'
        target = hid
        rows.append('<a class="%s" href="#%s">%s</a>' % (cls, target, html.escape(txt)))
    return '\n'.join(rows)


BOOK_CSS = r"""
.bookwrap{display:flex; gap:48px; max-width:1120px; margin:0 auto; padding:0 24px;}
.btoc{flex:none; width:250px; position:sticky; top:52px; align-self:flex-start; max-height:calc(100vh - 60px); overflow:auto;
  padding:32px 16px 60px 0; border-right:1px solid var(--hair);}
.btoc a{display:block; text-decoration:none; color:var(--parchment-dim); font-size:14.5px; line-height:1.35; padding:3px 0;}
.btoc a.tp{font-family:'Cinzel',serif; font-size:12.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--parchment); margin-top:18px;}
.btoc a.tc{padding-left:10px;}
.btoc a:hover{color:var(--parchment);}
.btext{flex:1; min-width:0; max-width:720px; padding:32px 0 140px; font-size:19px; line-height:1.65;}
.btext > section{padding-top:8px;}
.btext > section + section{margin-top:56px; border-top:1px solid var(--hair);}
.btext h2{font-family:'Cinzel',serif; font-weight:600; font-size:31px; line-height:1.2; letter-spacing:.01em; margin:56px 0 18px; text-wrap:balance;}
.btext h3{font-family:'Cinzel',serif; font-weight:600; font-size:21px; line-height:1.3; letter-spacing:.02em; margin:44px 0 12px; text-wrap:balance;}
.btext h4{font-family:'Cormorant Garamond',serif; font-weight:600; font-style:italic; font-size:20px; line-height:1.3; margin:30px 0 8px;}
.btext h5,.btext h6{font-family:'Cinzel',serif; font-weight:600; font-size:13px; letter-spacing:.08em; text-transform:uppercase; color:var(--parchment-dim); margin:24px 0 6px;}
.btext h2 + p > em:only-child{display:block; font-size:18px; color:var(--parchment-dim); margin-top:-8px;}
.btext p{margin:0 0 16px;}
.btext ul,.btext ol{margin:0 0 16px; padding-left:24px;}
.btext li{margin:0 0 6px;}
.btext blockquote{margin:20px 0 28px; padding:6px 0 6px 22px; border-left:2px solid var(--myth); color:var(--parchment-dim); font-style:italic;}
.btext blockquote p{margin:0 0 6px;}
.btext hr{border:0; border-top:1px solid var(--hair); margin:40px auto; width:40%;}
.btext .tw{overflow-x:auto; margin:16px 0 24px;}
.btext table{border-collapse:collapse; width:100%; font-size:16px; line-height:1.45;}
.btext th,.btext td{border-bottom:1px solid var(--hair); padding:8px 14px 8px 0; text-align:left; vertical-align:top;}
.btext th{font-family:'Cinzel',serif; font-size:12px; letter-spacing:.07em; text-transform:uppercase; color:var(--parchment-dim); font-weight:600;}
.btext code{font-size:.9em;}
.btext .lede{color:var(--parchment-dim); font-size:18px; margin:-6px 0 24px;}
a.pl{color:inherit; text-decoration:underline; text-decoration-color:rgba(157,107,255,.55); text-underline-offset:3px; cursor:pointer;}
a.pl:hover{text-decoration-color:#9d6bff;}
.agehd{font-size:15px !important; letter-spacing:.1em !important; text-transform:uppercase; margin:52px 0 6px !important; padding-bottom:8px; border-bottom:1px solid var(--hair);}
.agehd span{display:block; text-transform:none; letter-spacing:0; font-family:'Cormorant Garamond',serif; font-style:italic; color:var(--parchment-dim); font-size:17px; margin-top:2px;}
.an{padding:12px 0; border-top:1px solid rgba(51,44,61,.6);}
.an:first-of-type{border-top:0;}
.an .ad{font-family:'Cinzel',serif; font-size:11.5px; letter-spacing:.05em; color:var(--parchment-dim);}
.an .at{font-weight:600; font-size:19px; line-height:1.35;}
.an .ab{font-size:17px; color:var(--parchment-dim); line-height:1.55;}
.an.canon .at::after{content:' ◆'; color:var(--holy); font-size:.7em; vertical-align:middle;}
.gazetteer h3{margin-top:48px; padding-bottom:8px; border-bottom:1px solid var(--hair);}
.gz{padding:14px 0 10px; border-top:1px solid rgba(51,44,61,.6);}
.gazetteer h3 + .gz{border-top:0;}
.gz h4{font-family:'Cormorant Garamond',serif; font-style:normal; font-size:21px; font-weight:600; margin:0 0 2px !important;}
.gz .gf{font-size:14.5px; line-height:1.45; color:var(--parchment-dim); margin:0 0 6px;}
.gz p{font-size:17px; line-height:1.6;}
.gev{font-size:15px; color:var(--parchment-dim); margin:0 0 8px; padding-left:18px;}
.gev a{color:var(--parchment-dim);}
ul.tree{list-style:none; padding-left:18px; border-left:1px solid var(--hair); margin:4px 0;}
ul.tree li{margin:6px 0;}
.tree .life{font-family:'Cinzel',serif; font-size:11.5px; color:var(--parchment-dim); letter-spacing:.03em;}
.tree .pn{font-size:16px; color:var(--parchment-dim);}
@media (max-width:860px){ .bookwrap{padding:0 16px;} .btoc{display:none;} .btext{padding:20px 0 100px; font-size:18px;}
  .btext h2{font-size:25px;} .btext h3{font-size:19px;} }
"""


def to_markdown(rec):
    out = ['# The Legendarium of Rodos', '']
    making = creation_part(rec)
    if making:
        out += [plain(making[2]), '']
    for _, k, md in prose_parts(rec):
        out += [plain(md), '']
    out += ['# The Annals of Rodos', '']
    for k in AGES:
        out += ['## Age %s · %s' % (k, AGE_NAMES[k][0]), '', '*%s · %s, %s*' % (AGE_NAMES[k][1][0].upper() + AGE_NAMES[k][1][1:],
                                                                         reckoning.ERA[k][4], reckoning.display_span(k)), '']
        for e in rec.events:
            if e['age'] == k:
                pl = ' (%s)' % rec.place_name(e['place']) if e.get('place') else ''
                out.append('- **%s** — *%s*%s. %s' % (e['date'], e['title'], pl, e['body']))
        out.append('')
    for _, _, md in appendix_parts(rec):
        out += [plain(md), '']
    out += ['# A Gazetteer of Rodos', '']
    letter = None
    for bid, b in sorted(rec.burg.items(), key=lambda kv: fold(kv[1]['name'])):
        g = rec.gaz.get(bid)
        if fold(b['name'])[:1].upper() != letter:
            letter = fold(b['name'])[:1].upper()
            out += ['#### ' + letter, '']
        out.append('**%s** (%s). ' % (b['name'], b.get('province', '')) + (
            'Founded %s%s. %s Known for %s.' % (g['founded']['date'], ' by ' + g['founded_by'] if g.get('founded_by') else '',
                                              g.get('history', ''), g.get('known_for', '').rstrip('.')) if g else ''))
        out.append('')
    return '\n'.join(out)


def main():
    rec = Record()
    open(os.path.join(HERE, 'LEGENDARIUM.md'), 'w', encoding='utf-8').write(to_markdown(rec))
    words = len(re.sub(r'<[^>]+>', ' ', compose(rec)[1]).split())
    print('LEGENDARIUM.md: %d events, %d gazetteer entries, %d houses, about %s words'
          % (len(rec.events), len(rec.gaz), len(rec.houses), format(words, ',')))
    if rec.missing:
        print('unresolved references:', sorted(set(rec.missing))[:40])
        sys.exit(1)


if __name__ == '__main__':
    main()
