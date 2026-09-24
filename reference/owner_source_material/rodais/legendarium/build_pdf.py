"""
build_pdf.py -- typeset the legendarium as a book: The_Diathir_Legendarium.pdf

    python3 build_pdf.py [fonts-dir] [out.pdf]

Reads LEGENDARIUM.md (run build_book.py first) and lays it out with WeasyPrint (pip install weasyprint
markdown) as a printed book: half-title, title page, contents with page numbers, the Telling of the Making
(the prologue, opening like a book), the Seven Books (each opening
on a right-hand page with its epigraph and a drop capital), the Annals, the Appendices and the Gazetteer, with
running heads and folios. fonts-dir holds EB Garamond (EBGaramond[wght].ttf, EBGaramond-Italic[wght].ttf),
Cinzel[wght].ttf and UncialAntiqua-Regular.ttf from github.com/google/fonts (OFL); without them the book
falls back to the system serif.
"""
import html
import os
import re
import sys

import markdown

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(HERE, 'fonts')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(HERE), 'The_Diathir_Legendarium.pdf')

PROLOGUE = 'The Prologue'     # the label over the Telling of the Making, which stands before the Seven Books
ORD = {'First': 'The First Book', 'Second': 'The Second Book', 'Third': 'The Third Book',
       'Fourth': 'The Fourth Book', 'Fifth': 'The Fifth Book', 'Sixth': 'The Sixth Book', 'Seventh': 'The Seventh Book'}


def md(text):
    return markdown.markdown(text, extensions=['tables', 'sane_lists'])


def slug(s, seen):
    base = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60] or 'x'
    s, n = base, 2
    while s in seen:
        s, n = '%s-%d' % (base, n), n + 1
    seen.add(s)
    return s


def split_parts(lines):
    """-> list of (kind, heading, body-lines): prologue / book / annals / appendix / gazetteer."""
    parts, cur = [], None
    for ln in lines:
        m_book = re.match(r'^# (The \w+ Book): (.*)$', ln)
        m_pro = re.match(r"^# (Aithris a' Chruthachaidh: .*)$", ln)
        m_app = re.match(r'^#{1,2} (Appendix [A-Z]) — (.*)$', ln)
        if m_book:
            cur = ['book', (m_book.group(1), m_book.group(2)), []]
        elif m_pro:
            # the Telling of the Making: laid out as a book, under its own label
            cur = ['prologue', (PROLOGUE, m_pro.group(1).replace(': ', ', ', 1)), []]
        elif ln.startswith('# The Annals of Dia-thìr'):
            cur = ['annals', ('The Annals of Dia-thìr', ''), []]
        elif m_app:
            cur = ['appendix', (m_app.group(1), m_app.group(2)), []]
        elif ln.startswith('# A Gazetteer of Dia-thìr'):
            cur = ['gazetteer', ('A Gazetteer of Dia-thìr', ''), []]
        elif ln.startswith('# The Legendarium of Dia-thìr'):
            continue
        else:
            if cur is not None:
                cur[2].append(ln)
            continue
        parts.append(cur)
    return parts


def body_html(lines, level_map, seen, toc, toc_depth_tag):
    """Markdown -> HTML with headings re-levelled; ## headings get ids and go into the contents."""
    out, buf = [], []

    def flush():
        if buf:
            out.append(md('\n'.join(buf)))
            buf.clear()
    for ln in lines:
        m = re.match(r'^(#{2,4}) (.*)$', ln)
        if m:
            flush()
            lvl, txt = len(m.group(1)), m.group(2).strip()
            tag = level_map.get(lvl, 'h5')
            inner = md(txt)[3:-4]          # inline markdown, strip <p>
            if lvl == 2:
                hid = slug(txt, seen)
                num = re.match(r'^([IVXLC]+)\. (.*)$', txt)
                if num:
                    out.append('<%s id="%s" class="sec" data-title="%s"><span class="num">%s</span>%s</%s>'
                               % (tag, hid, html.escape(num.group(2), quote=True), num.group(1), md(num.group(2))[3:-4], tag))
                    toc.append((toc_depth_tag, hid, num.group(1) + '. ' + num.group(2)))
                else:
                    out.append('<%s id="%s" class="sec" data-title="%s">%s</%s>'
                               % (tag, hid, html.escape(re.sub(r'[*_]', '', txt), quote=True), inner, tag))
                    toc.append((toc_depth_tag, hid, re.sub(r'[*_]', '', txt)))
            else:
                out.append('<%s>%s</%s>' % (tag, inner, tag))
        else:
            buf.append(ln)
    flush()
    return '\n'.join(out)


def dropcaps(h):
    """A drop capital on the first letter of each section of the books."""
    return re.sub(r'(</h2>\s*<p>)([\u201c\u2018"\']?[^\W\d_])', r'\1<span class="dc">\2</span>', h)


def build():
    lines = open(os.path.join(HERE, 'LEGENDARIUM.md'), encoding='utf-8').read().split('\n')
    parts = split_parts(lines)
    seen, toc, chunks = set(), [], []
    first_app = True
    for kind, (label, title), body in parts:
        cid = slug(label, seen)
        if kind in ('book', 'prologue'):
            # the date line and the epigraph come first in the body
            head, i = [], 0
            while i < len(body) and not body[i].startswith('## '):
                head.append(body[i]); i += 1
            sub = title.split(', ', 1)
            toc.append((kind, cid, '%s: %s' % (label, title)))
            chunks.append(
                '<section class="book" id="%s"><div class="opener">'
                '<p class="booklabel">%s</p><h1 data-run="%s">%s</h1>%s'
                '<div class="front">%s</div></div>%s</section>'
                % (cid, label, html.escape(label + ': ' + sub[0], quote=True), sub[0],
                   '<p class="booksub">%s</p>' % sub[1] if len(sub) > 1 else '',
                   md('\n'.join(head)), dropcaps(body_html(body[i:], {2: 'h2', 3: 'h3', 4: 'h4'}, seen, toc, 'sec'))))
        elif kind == 'annals':
            toc.append(('part', cid, 'The Annals of Dia-thìr'))
            chunks.append('<section class="part annals" id="%s"><div class="partpage"><p class="booklabel">Part Two</p>'
                          '<h1 data-run="The Annals of Dia-thìr">The Annals of Dia-thìr</h1></div>%s</section>'
                          % (cid, body_html(body, {2: 'h2', 3: 'h3', 4: 'h4'}, seen, toc, 'sec')))
        elif kind == 'appendix':
            if first_app:
                toc.append(('part', 'appendices', 'The Appendices'))
                chunks.append('<section class="part" id="appendices"><div class="partpage"><p class="booklabel">Part Three</p>'
                              '<h1 class="parttitle" data-run="The Appendices">The Appendices</h1></div></section>')
                first_app = False
            toc.append(('app', cid, '%s. %s' % (label, title)))
            chunks.append('<section class="appendix" id="%s"><p class="booklabel">%s</p><h1 data-run="%s" data-sec="%s">%s</h1>%s</section>'
                          % (cid, label, html.escape(label + ': ' + title, quote=True), html.escape(title, quote=True), title,
                             body_html(body, {2: 'h2', 3: 'h2', 4: 'h3'}, seen, toc, 'appsec')))
        else:
            toc.append(('part', cid, 'A Gazetteer of Dia-thìr'))
            chunks.append('<section class="part gazetteer" id="%s"><div class="partpage"><p class="booklabel">Part Four</p>'
                          '<h1 data-run="A Gazetteer of Dia-thìr">A Gazetteer of Dia-thìr</h1></div><div class="cols">%s</div></section>'
                          % (cid, md('\n'.join(body))))

    # contents: books with their sections; the annals' ages; each appendix; the gazetteer
    rows, part_one = [], False
    for kind, hid, text in toc:
        if kind == 'book' and not part_one:
            rows.append('<p class="toc-part">Part One · The Seven Books</p>')
            part_one = True
        if kind == 'prologue':
            rows.append('<a class="toc-book toc-prologue" href="#%s">%s</a>' % (hid, html.escape(text)))
        elif kind == 'book':
            rows.append('<a class="toc-book" href="#%s">%s</a>' % (hid, html.escape(text)))
        elif kind == 'sec':
            rows.append('<a class="toc-sec" href="#%s">%s</a>' % (hid, html.escape(text)))
        elif kind == 'part':
            rows.append('<a class="toc-partline" href="#%s">%s</a>' % (hid, html.escape(text)))
        elif kind == 'app':
            rows.append('<a class="toc-book" href="#%s">%s</a>' % (hid, html.escape(text)))
    # sections of the appendices are too many for the contents; keep books, ages and appendices only
    toc_html = '\n'.join(rows)
    doc = TEMPLATE.replace('%FONTS%', 'file://' + FONTS).replace('%TOC%', toc_html).replace('%BODY%', '\n'.join(chunks))
    from weasyprint import HTML
    HTML(string=doc, base_url=HERE).write_pdf(OUT)
    print('wrote', OUT)


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>The Legendarium of Dia-thìr</title>
<style>
@font-face{font-family:'EBG';src:url('%FONTS%/EBGaramond[wght].ttf');font-weight:400 800;font-style:normal}
@font-face{font-family:'EBG';src:url('%FONTS%/EBGaramond-Italic[wght].ttf');font-weight:400 800;font-style:italic}
@font-face{font-family:'Cinzel';src:url('%FONTS%/Cinzel[wght].ttf');font-weight:400 900}
@font-face{font-family:'Uncial';src:url('%FONTS%/UncialAntiqua-Regular.ttf')}

@page{size:156mm 234mm; margin:20mm 16mm 22mm 20mm;
  @bottom-center{content:counter(page); font:9.5pt 'EBG',serif; color:#444}}
@page :left{margin:20mm 20mm 22mm 16mm;
  @top-left{content:string(bookrun); font:7.5pt 'Cinzel',serif; letter-spacing:.12em; color:#555; text-transform:uppercase}}
@page :right{@top-right{content:string(secrun); font:italic 9pt 'EBG',serif; color:#555}}
@page front{@bottom-center{content:none} @top-left{content:none} @top-right{content:none}}
@page blank{@bottom-center{content:none} @top-left{content:none} @top-right{content:none}}
@page opener{@top-left{content:none} @top-right{content:none}}
@page :blank{@bottom-center{content:none} @top-left{content:none} @top-right{content:none}}

html{font-family:'EBG','Georgia',serif; font-size:10.6pt; line-height:1.42; color:#1a1612; hyphens:auto;
  font-variant-numeric:oldstyle-nums proportional-nums; font-kerning:normal}
p{margin:0; text-align:justify; orphans:2; widows:2}
p + p{text-indent:1.3em}
em{font-style:italic}
a{color:inherit; text-decoration:none}
blockquote{margin:.9em 1.6em; font-size:.97em}
blockquote p{text-indent:0!important; text-align:left}

/* front matter */
.front-matter{page:front}
.halftitle{page:blank; break-after:page; text-align:center; padding-top:62mm}
.halftitle h1{font-family:'Uncial',serif; font-weight:400; font-size:24pt; color:#6d1f14; margin:0}
.titlepage{page:blank; break-before:right; break-after:page; text-align:center; padding-top:34mm}
.titlepage .t1{font-family:'Cinzel',serif; font-size:11pt; letter-spacing:.35em; text-transform:uppercase; margin:0 0 6mm}
.titlepage h1{font-family:'Uncial',serif; font-weight:400; font-size:38pt; line-height:1.05; color:#6d1f14; margin:0 0 7mm}
.titlepage .t2{font-style:italic; font-size:13pt; margin:0 0 3mm; text-align:center}
.titlepage .rule{width:28mm; border-top:1px solid #6d1f14; margin:9mm auto}
.titlepage .t3{font-size:10.5pt; text-align:center; line-height:1.6}
.titlepage .t4{position:absolute; bottom:0; left:0; right:0; font-family:'Cinzel',serif; font-size:8.5pt; letter-spacing:.2em; text-transform:uppercase; text-align:center}
.epipage{page:blank; break-before:page; break-after:page; padding-top:70mm; text-align:center}
.epipage p{text-align:center; text-indent:0!important}
.epipage .ro{font-style:italic; font-size:13pt}
.epipage .en{margin-top:2mm}
.epipage .src{margin-top:4mm; font-size:9pt; color:#555}
.toc{page:front; break-before:right}
.toc h1{font-family:'Cinzel',serif; font-weight:500; font-size:15pt; letter-spacing:.2em; text-transform:uppercase; text-align:center; margin:4mm 0 9mm; color:#6d1f14}
.toc a{display:block; text-indent:0}
.toc a::after{content:leader('.') target-counter(attr(href url), page)}
.toc-part{font-family:'Cinzel',serif; font-size:8.5pt; letter-spacing:.18em; text-transform:uppercase; color:#6d1f14; margin:5mm 0 1.5mm; text-align:left}
.toc-book{font-weight:600; margin-top:2.6mm}
.toc-prologue{margin-top:5mm}
.toc-sec{font-size:9.4pt; padding-left:5mm; line-height:1.35}
.toc-partline{font-family:'Cinzel',serif; font-size:9pt; letter-spacing:.14em; text-transform:uppercase; color:#6d1f14; margin-top:6mm}

/* the books */
.opener{page:opener; break-before:right; padding-top:30mm; margin-bottom:9mm; text-align:center}
.booklabel{font-family:'Cinzel',serif; font-size:9pt; letter-spacing:.3em; text-transform:uppercase; color:#6d1f14; text-align:center; margin:0 0 4mm}
.book h1{font-family:'Uncial',serif; font-weight:400; font-size:25pt; line-height:1.1; margin:0; color:#1a1612; string-set:bookrun attr(data-run)}
.booksub{font-style:italic; font-size:13pt; text-align:center; margin:2.5mm 0 0}
.front{margin:8mm auto 0; max-width:92mm}
.front p{text-align:center; text-indent:0!important}
.front > p:first-child{font-family:'Cinzel',serif; font-size:8.5pt; letter-spacing:.14em; color:#555; margin-bottom:6mm}
.front blockquote{margin:0; font-size:10pt}
.front blockquote p{text-align:center}
h2.sec{font-family:'EBG',serif; font-weight:500; font-size:13.5pt; text-align:center; margin:11mm 0 5mm; line-height:1.2;
  break-after:avoid; string-set:secrun attr(data-title)}
h2.sec .num{display:block; font-family:'Cinzel',serif; font-size:9pt; letter-spacing:.25em; color:#6d1f14; margin-bottom:1.5mm}
.book h2.sec + p{text-indent:0}
.book .dc{font-family:'Uncial',serif; float:left; font-size:3.05em; line-height:.9; padding:1.2mm 1.6mm 0 0; color:#6d1f14}
.book .opener + h2.sec{margin-top:0}
h3{font-family:'Cinzel',serif; font-weight:500; font-size:9.5pt; letter-spacing:.12em; text-transform:uppercase; margin:6mm 0 2.5mm; break-after:avoid; text-align:left}
h4{font-style:italic; font-weight:600; font-size:10.5pt; margin:4mm 0 1.5mm; break-after:avoid}
h3 + p, h4 + p, blockquote + p, ul + p, table + p, .tw + p{text-indent:0}
hr{border:0; text-align:center; margin:5mm 0}
hr::before{content:'❦'; color:#6d1f14}

/* part pages */
.partpage{page:opener; break-before:right; break-after:page; padding-top:70mm; text-align:center}
.partpage h1, .parttitle{font-family:'Uncial',serif; font-weight:400; font-size:26pt; color:#6d1f14; margin:0; string-set:bookrun attr(data-run), secrun attr(data-run)}

/* annals */
.annals h2.sec{font-family:'Cinzel',serif; font-size:11pt; letter-spacing:.14em; text-transform:uppercase; break-before:page; margin-top:0}
.annals ul{list-style:none; margin:0; padding:0}
.annals li{font-size:9.2pt; line-height:1.36; margin:0 0 1.6mm; text-align:justify; padding-left:3mm; text-indent:-3mm; break-inside:avoid-page}
.annals li strong{font-weight:600; font-variant:small-caps; letter-spacing:.02em}
.annals li p{text-indent:-3mm}

/* appendices */
.appendix{break-before:right; padding-top:14mm}
.appendix h1{font-family:'Uncial',serif; font-weight:400; font-size:19pt; text-align:center; margin:0 0 9mm; line-height:1.15; string-set:bookrun attr(data-run), secrun attr(data-sec)}
.appendix h2.sec{font-size:12pt; text-align:left; margin:8mm 0 3mm}
.appendix p{font-size:10pt}
table{border-collapse:collapse; width:100%; font-size:7.6pt; line-height:1.28; margin:3mm 0 4mm; font-variant-numeric:lining-nums tabular-nums}
th{font-family:'Cinzel',serif; font-weight:600; font-size:6.6pt; letter-spacing:.06em; text-transform:uppercase; text-align:left; border-bottom:.6pt solid #6d1f14; padding:1.2mm 1.4mm}
td{border-bottom:.3pt solid #cbbfa9; padding:1mm 1.4mm; vertical-align:top; text-align:left}
tr{break-inside:avoid}
.appendix ul, .appendix ol{padding-left:5mm; margin:1.5mm 0 3mm}
.appendix li{font-size:10pt; margin-bottom:1mm}

/* gazetteer */
.gazetteer .cols{column-count:2; column-gap:6mm; column-fill:auto}
.gazetteer p{font-size:8.6pt; line-height:1.33; text-indent:0!important; margin:0 0 1.6mm; text-align:justify; break-inside:avoid-column}
.gazetteer h2, .gazetteer h3, .gazetteer h4{font-family:'Uncial',serif; font-weight:400; font-size:17pt; color:#6d1f14; margin:3mm 0 2mm; break-after:avoid}
</style></head><body>
<div class="halftitle"><h1>The Legendarium of Dia-thìr</h1></div>
<div class="titlepage">
  <p class="t1">Leabhar nan Aoisean</p>
  <h1>The Legendarium<br>of Dia-thìr</h1>
  <p class="t2">being the Telling of the Making, the Seven Books of the island,<br>the Annals of its years, the Appendices, and a Gazetteer of its towns</p>
  <div class="rule"></div>
  <p class="t3">as they are kept in the Library at Muileann chaol<br>and told at the hearths of the island</p>
</div>
<div class="epipage">
  <p class="ro">Cha do thàinig sinn; bha sinn ann.</p>
  <p class="en">We did not come; we were here.</p>
  <p class="src">cut on the column at Cnoc ghorm</p>
</div>
<nav class="toc"><h1>Contents</h1>
%TOC%
</nav>
%BODY%
</body></html>
"""

if __name__ == '__main__':
    build()
