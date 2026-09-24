"""
merge_lexicon.py -- fold the translated batches into the Dia-thìris dictionary.

    python merge_lexicon.py            (from this folder)
    python merge_lexicon.py /tmp/x     (dry run: write the outputs to /tmp/x instead)

Reads LEXICON_5005.json (the original 5,005 entries, kept as they were before the merge) and every out_NN.json here, and writes:

    ../LEXICON.json      all entries, keyed by English; new entries carry their frequency rank and
                         band ("F1" = the 1,000 most common English words ... "F16"), and every entry
                         gets "ipa" from rodais_engine.pronounce() when the engine has it; the "scots"
                         field of the batches (the outside word a kenning stands for) is dropped
    ../LEXICON.md        Dia-thìris - English, sorted by Dia-thìris headword
    ../LEXICON_EN.md     English - Dia-thìris, sorted by English headword
    coverage.txt         how many of the most common English words the dictionary now covers

After loading, audit_patch.json (written by audit.py: case, verb form, peoples, conflicts, loans vs
kennings, old native words, missing main senses) is applied to the original and the new entries alike:
its edits by id, its drops, its additions. A new entry is then added only if no entry already has the
same English, the same Dia-thìris form and the same part of speech (so a demonym keeps both its noun and its
adjective).
"""
import glob
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else ROOT  # a scratch folder for a dry run
import rodais_engine as R  # noqa: E402

POS_ABBR = {'n': 'n.', 'v': 'v.', 'adj': 'adj.', 'adv': 'adv.', 'prep': 'prep.', 'conj': 'conj.', 'pron': 'pron.',
            'num': 'num.', 'interj': 'interj.', 'det': 'det.', 'part': 'part.', 'phrase': 'phr.'}


def key(s):
    """Sort key: ignore a leading article or apostrophe, accents and case."""
    s = re.sub(r"^(an t-|an |am |a' |na h-|na |'s |')", '', s.lower())
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode()


PATCH = os.path.join(HERE, 'audit_patch.json')


def apply_patch(orig, batch, path=PATCH):
    """Apply audit_patch.json to the loaded entries: edits by id ("set" / "unset"), drops, additions.
    An edit whose "old" values no longer match the data is still applied, with a warning (the data
    changed after audit.py was run: re-run it)."""
    if not os.path.exists(path):
        print('no %s: merging without the audit' % os.path.basename(path))
        return orig, batch
    patch = json.load(open(path, encoding='utf-8'))
    edits = {ed['id']: ed for ed in patch.get('edit', [])}
    drops = {d['id'] for d in patch.get('drop', [])}
    stale, used = [], set()

    def fix(e):
        ed = edits.get(e.get('id'))
        if not ed:
            return e
        used.add(ed['id'])
        e = dict(e)
        stale.extend((e['id'], k) for k, v in ed.get('old', {}).items() if e.get(k) != v)
        for k in ed.get('unset', []):
            e.pop(k, None)
        e.update(ed.get('set', {}))
        return e

    orig = [fix(e) for e in orig if e.get('id') not in drops]
    batch = [fix(e) for e in batch if e.get('id') not in drops]
    batch += [{k: v for k, v in a.items() if k != 'why'} for a in patch.get('add', [])]
    missing = sorted(set(edits) - used)
    print('audit patch: %d edits, %d drops, %d additions' % (len(edits), len(drops), len(patch.get('add', []))))
    if stale:
        print('WARNING: %d patched fields changed since audit.py ran (re-run it): %s'
              % (len(stale), ', '.join('%s.%s' % x for x in stale[:10])))
    if missing:
        print('WARNING: %d patch edits name no entry: %s' % (len(missing), ', '.join(missing[:10])))
    return orig, batch


def main():
    base = json.load(open(os.path.join(HERE, 'LEXICON_5005.json'), encoding='utf-8'))  # the original lexicon, before the merge
    orig = [e for e in base['entries'] if not str(e.get('id', '')).startswith('f-')]
    batch, skipped = [], []
    for f in sorted(glob.glob(os.path.join(HERE, 'out_*.json'))):
        for e in json.load(open(f, encoding='utf-8')):
            (skipped if e.get('skip') else batch).append(e)
    orig, batch = apply_patch(orig, batch)
    seen = {(e['en'].lower(), e['rod'].lower(), e.get('pos')) for e in orig}
    new = []
    for e in batch:
        k = (e['en'].lower(), e['rod'].lower(), e.get('pos'))
        if k in seen:
            continue
        seen.add(k)
        e = dict(e)
        e['level'] = 'F%d' % min(16, (int(e.get('rank', 16000)) - 1) // 1000 + 1)
        e.setdefault('topic', '')
        new.append(e)
    entries = orig + new
    lit = {}  # a kenning used for several English words keeps one literal sense: the first one given
    for e in entries:
        if e.get('kenning') and e.get('lit'):
            e['lit'] = lit.setdefault(e['rod'].lower(), e['lit'])
    pron = getattr(R, 'pronounce', None)
    if pron:
        for e in entries:
            try:
                e['ipa'] = pron(e['rod'])
            except Exception:  # noqa: BLE001 -- a pronunciation failure must not stop the merge
                pass
    for e in entries:   # the dictionary is written from inside the island: no outside word stands beside a kenning
        e.pop('scots', None)
    base['entries'] = entries
    base['source'] = ('The word-hoard of the Dia-thìris tongue, set down at the Library at Muileann chaol: English headwords '
                      'with their Dia-thìris, the first 5,005 graded by level (A1-C2) and the rest by how often the English '
                      'word is used (levels F1-F16, bands of 1,000 words). An entry marked "kenning" is a word the island '
                      'built from old roots for a thing that came with the humans or after them; "lit" gives its literal sense.')
    json.dump(base, open(os.path.join(OUT, 'LEXICON.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # coverage of the frequency list
    ranked = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'in_*.json'))):
        for w in json.load(open(f, encoding='utf-8')):
            ranked[w['en']] = w['rank']
    covered_en = {e['en'].lower() for e in entries}
    covered_en |= {re.sub(r'\s*\(.*?\)', '', re.sub(r'^to ', '', w)).strip() for w in covered_en}   # "spend (money)", "to wear"
    skip_en = {e['en'] for e in skipped} - covered_en   # a skip the audit turned into an entry is covered
    real = sorted((r, w) for w, r in ranked.items() if w not in skip_en)
    have_orig = len({re.sub(r'^(to|a|an|the) ', '', e['en'].lower()) for e in orig})
    lines = ['entries: %d (original %d, new %d)' % (len(entries), len(orig), len(new)),
             'distinct English headwords: %d' % len(covered_en),
             'frequency-list words translated: %d; skipped as names/junk: %d' % (sum(1 for _, w in real if w in covered_en), len(skip_en)),
             'original lexicon headwords: %d' % have_orig]
    open(os.path.join(HERE if OUT == ROOT else OUT, 'coverage.txt'), 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

    # Dia-thìris - English
    def gloss(e):
        bits = []
        if e.get('pos') == 'n' and e.get('g'):
            bits.append(e['g'] + '.')
            if e.get('gen'):
                bits.append('gen. *%s*' % e['gen'])
            if e.get('pl'):
                bits.append('pl. *%s*' % e['pl'])
        if e.get('pos') == 'v' and e.get('vn') and e.get('vn') != e.get('rod'):
            bits.append('vn. *%s*' % e['vn'])
        return ', '.join(bits)

    out = ['# Dia-thìris – English dictionary', '',
           'Here are %d words of the Dia-thìris tongue, in the order of their headwords; a leading article is passed '
           'over in the ordering. A noun is given with its gender, its genitive and its plural, a verb with its '
           'verbal noun, and every word with its sound between slashes. The mark ✦ follows a word that the '
           'island built from its own old roots when a new thing came to it with the humans or after them '
           '(GRAMMAR.md §13); the literal sense of such a word is set after it, as *suathaiche-nèimh* '
           '"heaven-grazer" for a tower of many floors. The other road, from English into Dia-thìris, is `LEXICON_EN.md`.'
           % len(entries), '']
    letter = None
    for e in sorted(entries, key=lambda e: (key(e['rod']), e['en'].lower())):
        k = key(e['rod'])[:1].upper() or "'"
        if k != letter:
            letter = k
            out += ['', '## ' + k, '']
        extra = []
        if e.get('ipa'):
            extra.append('/%s/' % e['ipa'])
        g = gloss(e)
        s = '- **%s**%s %s%s — %s' % (e['rod'], ' ✦' if e.get('kenning') else '', POS_ABBR.get(e.get('pos'), ''),
                                     (' (' + g + ')') if g else '', e['en'])
        if e.get('sense'):
            s += ' (%s)' % e['sense']
        if e.get('lit'):
            s += '; lit. "%s"' % e['lit']
        if extra:
            s += ' ' + ' '.join(extra)
        s += ' `%s`' % e.get('level', '')
        out.append(s)
    open(os.path.join(OUT, 'LEXICON.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')

    # English - Dia-thìris
    out = ['# English – Dia-thìris dictionary', '', 'The same %d words, in the order of their English headwords. The full '
           'entries, with sound and literal sense, stand in `LEXICON.md`.' % len(entries), '']
    letter = None
    for e in sorted(entries, key=lambda e: (key(e['en']), e['rod'].lower())):
        k = key(e['en'])[:1].upper() or '?'
        if k != letter:
            letter = k
            out += ['', '## ' + k, '']
        s = '- **%s**%s — *%s*%s' % (e['en'], (' (%s)' % e['sense']) if e.get('sense') else '', e['rod'],
                                     ' ✦' if e.get('kenning') else '')
        g = gloss(e)
        if g:
            s += ' ' + POS_ABBR.get(e.get('pos'), '') + ' ' + g
        out.append(s)
    open(os.path.join(OUT, 'LEXICON_EN.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    main()
