"""
validate_batch.py -- check one translated lexicon batch before it is merged into LEXICON.json.

    python validate_batch.py out_07.json      (run from this folder)

Checks every entry: schema, part of speech, noun gender/plural, verb root/verbal noun, that the Ròdais
is already in Ròdais spelling (normalize() leaves it unchanged: grave accents only, sc not sg), and
caol le caol inside each word (check_agreement(), reported as warnings: some real words break it).
Also checks the batch covers every word of its in_NN.json. Exits non-zero on any error.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import rodais_engine as R  # noqa: E402

POS = {'n', 'v', 'adj', 'adv', 'prep', 'conj', 'pron', 'num', 'interj', 'det', 'phrase', 'part'}


def main(path):
    out = json.load(open(path, encoding='utf-8'))
    src = json.load(open(re.sub(r'out_(\d+)\.json$', r'in_\1.json', path), encoding='utf-8'))
    errors, warnings = [], []
    done = {}
    for e in out:
        en = e.get('en')
        done.setdefault(en, []).append(e)
        if e.get('skip'):
            continue
        where = '%s (%s)' % (en, e.get('pos'))
        for k in ('id', 'en', 'rank', 'rod', 'pos', 'sense'):
            if not e.get(k):
                errors.append('%s: missing %s' % (where, k))
        if e.get('pos') not in POS:
            errors.append('%s: pos must be one of %s' % (where, sorted(POS)))
        if e.get('pos') == 'n':
            if e.get('g') not in ('m', 'f'):
                errors.append('%s: noun needs g = m or f' % where)
            if not e.get('pl'):
                warnings.append('%s: noun without a plural (fine only for mass/abstract nouns)' % where)
        if e.get('pos') == 'v' and not (e.get('root') and e.get('vn')):
            errors.append('%s: verb needs root and vn (verbal noun)' % where)
        if e.get('kenning') and not (e.get('lit') and e.get('scots')):
            errors.append('%s: a kenning needs lit and scots' % where)
        for f in ('rod', 'pl', 'gen', 'root', 'vn'):
            v = e.get(f)
            if not v:
                continue
            if R.normalize(v) != v:
                errors.append('%s: %s %r is not in Ròdais spelling (normalize gives %r)' % (where, f, v, R.normalize(v)))
            if re.search('[áéíóú]', v):
                errors.append('%s: %s %r has an acute accent' % (where, f, v))
            for w in re.findall(r"[^\s\-'’,.!?;:()]+", v):
                if R.check_agreement(w):
                    warnings.append('%s: %s %r breaks caol le caol' % (where, f, w))
    missing = [s['en'] for s in src if s['en'] not in done]
    if missing:
        errors.append('%d words of the batch have no entry and no skip: %s' % (len(missing), ', '.join(missing[:30])))
    ids = [e.get('id') for e in out if not e.get('skip')]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        errors.append('duplicate ids: %s' % ', '.join(dup[:20]))
    kept = sum(1 for e in out if not e.get('skip'))
    skipped = sum(1 for e in out if e.get('skip'))
    print('%s: %d entries, %d skipped, %d errors, %d warnings' % (os.path.basename(path), kept, skipped, len(errors), len(warnings)))
    for m in errors[:60]:
        print('ERROR  ', m)
    for m in warnings[:40]:
        print('warning', m)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main(sys.argv[1])
