"""
glosses.py -- the English gloss of a Dia-thìris proper noun, added by the build on its first mention.

Writers write the Dia-thìris name only. The build finds the names of ../eras/NAMES.json (a list of
{en, dt, gloss, kind, first, status}) in the finished HTML and, on the first mention in each scope,
    PDF  (mode 'footnote'): puts the gloss in a footnote, <span class="fn">gloss</span>, which the book's CSS
                            floats to the foot of the page with a superscript number (WeasyPrint float: footnote);
    HTML (mode 'tooltip'):  wraps the name in <span class="gl" title="gloss">, a dotted underline and a hover gloss.
A scope is a chapter or section of a book, an annals entry, a gazetteer entry, a section of an appendix: the caller
says where scopes open with a regex on the opening tags. Nothing is glossed inside headings, links, tables,
block quotations (Dia-thìris quotations stand as they are), code, or a gloss already made.

With no NAMES.json, or with the environment variable RODAIS_NO_GLOSSES=1, every function here returns its input
unchanged, so the books are exactly what they were before glosses existed. RODAIS_NAMES=<path> reads another
names file (for trials).
"""
import html as _html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(os.path.dirname(HERE), 'eras', 'NAMES.json')
SKIP_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'table', 'blockquote', 'code', 'script', 'style', 'sup', 'title'}
VOID = {'br', 'hr', 'img', 'meta', 'link', 'input', 'wbr', 'col', 'source'}
DEAD = {'rejected', 'retired', 'withdrawn', 'dropped'}
PERSONAL = {'person', 'human', 'human person', 'personal name', 'human name'}

_cache = {}


def names(path=None):
    """The usable entries of NAMES.json: [{en, dt, gloss, kind, ...}], [] when there is none or glosses are off."""
    if os.environ.get('RODAIS_NO_GLOSSES') == '1':
        return []
    path = path or os.environ.get('RODAIS_NAMES') or DEFAULT
    if path not in _cache:
        data = []
        if os.path.exists(path):
            raw = json.load(open(path, encoding='utf-8'))
            if isinstance(raw, dict):
                raw = raw.get('names') or raw.get('entries') or []
            data = [e for e in raw if isinstance(e, dict) and e.get('dt') and e.get('gloss')
                    and str(e.get('status', '')).lower() not in DEAD]
        _cache[path] = data
    return _cache[path]


def _matcher(entries):
    forms = sorted({e['dt'] for e in entries}, key=len, reverse=True)       # longest first
    if not forms:
        return None, {}
    gl = {}
    for e in entries:
        gl.setdefault(e['dt'], e['gloss'])
    rx = re.compile(r'(?<![\w\-\'])(%s)(?![\w\-])' % '|'.join(re.escape(_html.escape(f, quote=False)) for f in forms))
    return rx, {_html.escape(k, quote=False): v for k, v in gl.items()}


def gloss_html(doc, scope=r'<(?:h2|li|p)\b', mode='footnote', entries=None):
    """Add the gloss of each Dia-thìris name on its first mention in every scope of doc (an HTML string).
    scope: a regex matched against each opening tag; a match opens a new scope."""
    entries = names() if entries is None else entries
    if not entries:
        return doc
    rx, gl = _matcher(entries)
    scope_rx = re.compile(scope)
    out, seen, skip = [], set(), []
    for piece in re.split(r'(<[^>]+>)', doc):
        if piece.startswith('<'):
            m = re.match(r'<(/?)([a-zA-Z0-9]+)([^>]*)>', piece)
            if m:
                closing, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
                special = tag in SKIP_TAGS or (tag == 'span' and re.search(r'class="(?:fn|gl)\b', attrs))
                if not closing and scope_rx.match(piece):
                    seen = set()
                if not closing and tag not in VOID and not attrs.rstrip().endswith('/'):
                    skip.append(bool(special))
                elif closing and skip:
                    skip.pop()
            out.append(piece)
            continue
        if any(skip) or not piece:
            out.append(piece)
            continue

        def sub(m):
            name = m.group(1)
            if name in seen:
                return name
            seen.add(name)
            g = _html.escape(gl[name], quote=True)
            if mode == 'tooltip':
                return '<span class="gl" title="%s">%s</span>' % (g, name)
            return '%s<span class="fn">%s</span>' % (name, g)
        out.append(rx.sub(sub, piece))
    return ''.join(out)


def english_left(text, entries=None):
    """English names from NAMES.json still standing in text where the Dia-thìris form belongs (human personal
    names excepted). -> sorted list of (english, dia-thìris)."""
    entries = names() if entries is None else entries
    hits = set()
    for e in entries:
        en = (e.get('en') or '').strip()
        if not en or str(e.get('kind', '')).lower() in PERSONAL or en == e['dt']:
            continue
        core = re.sub(r'^(?i:the)\s+', '', en)
        if len(core) < 3:
            continue
        if re.search(r'(?<![\w\-])%s(?![\w\-])' % re.escape(core), text):
            hits.add((en, e['dt']))
    return sorted(hits)


# the book's footnotes (build_pdf.py adds this to its stylesheet when a book has any footnote); the Atlas's
# hover glosses are styled by .gl in build_book.BOOK_CSS
FOOTNOTE_CSS = """
.fn{float:footnote; font-size:8pt; line-height:1.3; font-style:normal; font-weight:400; text-indent:0; text-align:left;
  font-variant:normal; letter-spacing:0; text-transform:none; color:#1a1612}
.fn::footnote-call{content:counter(footnote); vertical-align:super; font-size:.62em; line-height:0; color:#6d1f14}
.fn::footnote-marker{content:counter(footnote) '. '; color:#6d1f14}
.book h2.sec, .appendix, .annals h2.sec, .gazetteer h4{counter-reset:footnote}
@page{@footnote{border-top:.4pt solid #cbbfa9; padding-top:1.2mm; margin-top:2.5mm}}
"""
