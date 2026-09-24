"""
build_language.py -- assemble the Dia-thìris language book: one page with the whole language.

    pip install markdown
    python build_language.py            (from this folder; writes DIATHIRIS.html)

The book has two parts:

    Book         the sounds (PHONOLOGY.md), the grammar in brief (GRAMMAR.md), word forms
                 (GRAMMAR_MORPHOLOGY.md), sentences (GRAMMAR_SYNTAX.md), names (NAMING_LAYER.md)
                 and the texts (TEXTS.md), with a contents list
    Dictionary   every entry of LEXICON.json, searchable in both directions (Dia-thìris and English), with
                 gender, genitive, plural, verbal noun, pronunciation, and for a kenning its literal sense

The book is written from inside the world: the build stops if a chapter still names a file.

The page needs no server: open DIATHIRIS.html in a browser. Rebuild it after changing any of the files above.
"""
import html
import json
import os
import re
import unicodedata

import markdown

import rodais_engine as R

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'DIATHIRIS.html')

CHAPTERS = [  # (id, tab label, file, title shown)
    ('sounds', 'Sounds', 'PHONOLOGY.md', 'The sounds'),
    ('grammar', 'Grammar in brief', 'GRAMMAR.md', 'The grammar in brief'),
    ('forms', 'Word forms', 'GRAMMAR_MORPHOLOGY.md', 'Word forms'),
    ('sentences', 'Sentences', 'GRAMMAR_SYNTAX.md', 'Sentences'),
    ('naming', 'Names', 'NAMING_LAYER.md', 'Names'),
    ('texts', 'Texts', 'TEXTS.md', 'Texts'),
]
FILE_LINK = {c[2]: ('#ch-' + c[0], c[3]) for c in CHAPTERS}   # a stray file name in the text becomes its chapter
FILE_LINK.update({f: ('#dictionary', 'the Dictionary') for f in ('LEXICON.json', 'LEXICON.md', 'LEXICON_EN.md')})
SAMPLE = ('Thug am bàrd am bradan do Fhionn.', 'The poet gave the salmon to Fionn.')
POS = {'n': 'noun', 'v': 'verb', 'adj': 'adjective', 'adv': 'adverb', 'prep': 'preposition', 'conj': 'conjunction',
       'pron': 'pronoun', 'num': 'numeral', 'interj': 'interjection', 'det': 'determiner', 'part': 'particle',
       'phrase': 'phrase'}


def slug(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def chapter_html(cid, path):
    text = open(os.path.join(HERE, path), encoding='utf-8').read()
    text = re.sub(r'^# .*\n', '', text, count=1)  # the chapter supplies its own title
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
                           extension_configs={'toc': {'toc_depth': '2-2',
                                                      'slugify': lambda v, sep: cid + '-' + slug(v)}})
    body = md.convert(text)
    body = body.replace('<table>', '<div class="tw"><table>').replace('</table>', '</table></div>')
    body = re.sub(r'(?:<code>)?([A-Z_]+\.(?:md|json))(?:</code>)?',
                  lambda m: '<a href="%s"><i>%s</i></a>' % FILE_LINK[m.group(1)] if m.group(1) in FILE_LINK else m.group(0), body)
    left = re.findall(r'[\w-]+\.(?:md|json|py)\b', re.sub(r'<[^>]+>', ' ', body))
    if left:
        raise SystemExit('%s still names files: %s' % (path, sorted(set(left))[:10]))
    toc = [(t['id'], html.unescape(re.sub(r'<[^>]+>', '', t['name']))) for t in md.toc_tokens]
    return body, toc


SENSE_FIX = [(re.compile(r'\((?:a )?post-1800 loan\)|\(a loan of the 1800s\)|\(a loan of the machine age\)'), "(from the humans' tongue)"),
             (re.compile(r'\(old Scots loan\)'), '(an old loan)')]   # older LEXICON.json files; merge_lexicon now writes these in-world


def sense(s):
    for pat, rep in SENSE_FIX:
        s = pat.sub(rep, s)
    return s


def dictionary_data():
    lex = json.load(open(os.environ.get('RODAIS_LEXICON', os.path.join(HERE, 'LEXICON.json')), encoding='utf-8'))['entries']
    rows = []
    for e in lex:
        rows.append([e.get('rod', ''), e.get('pos', ''), e.get('g', ''), e.get('gen', ''), e.get('pl', ''),
                     e.get('vn', '') if e.get('vn') != e.get('rod') else '', e.get('en', ''), sense(e.get('sense', '')),
                     e.get('lit', ''), '', 1 if e.get('kenning') else 0,
                     e.get('ipa', ''), e.get('level', '')])
    stats = {'entries': len(rows), 'english': len({r[6].lower() for r in rows}),
             'kennings': sum(r[10] for r in rows)}
    return rows, stats


def main():
    chapters, nav = [], []
    for cid, label, path, title in CHAPTERS:
        body, toc = chapter_html(cid, path)
        chapters.append('<section class="chapter" id="ch-%s"><h1>%s</h1>%s</section>' % (cid, html.escape(title), body))
        nav.append('<li><a class="ch" href="#ch-%s">%s</a><ol>%s</ol></li>' % (
            cid, html.escape(label), ''.join('<li><a href="#%s">%s</a></li>' % (i, html.escape(n)) for i, n in toc)))
    rows, stats = dictionary_data()
    page = open(os.path.join(HERE, 'language_template.html'), encoding='utf-8').read()
    page = (page.replace('{{NAV}}', ''.join(nav))
                .replace('{{CHAPTERS}}', '\n'.join(chapters))
                .replace('{{SAMPLE_RO}}', html.escape(SAMPLE[0]))
                .replace('{{SAMPLE_IPA}}', html.escape(R.pronounce(SAMPLE[0].rstrip('.'))))
                .replace('{{SAMPLE_EN}}', html.escape(SAMPLE[1]))
                .replace('{{POS}}', json.dumps(POS))
                .replace('{{STATS}}', '%s entries · %s English words · %s kennings' % (
                    format(stats['entries'], ','), format(stats['english'], ','), format(stats['kennings'], ',')))
                .replace('{{DATA}}', json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')))
    open(OUT, 'w', encoding='utf-8').write(page)
    print('wrote %s (%.1f MB): %d chapters, %s' % (os.path.basename(OUT), os.path.getsize(OUT) / 1e6, len(chapters), stats))


if __name__ == '__main__':
    main()
