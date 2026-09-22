"""
check_rodais.py -- verify everything in this folder in one run.

  1. the engine's self-test (rodais_engine.py)
  2. LEXICON.json: every entry complete, every Ròdais field already in Ròdais
     spelling, and a caol-le-caol report (real exceptions are exempt in the
     engine; what remains is loanwords, names and unhyphenated compounds,
     listed, not failed)
  3. TEXTS.json: every line paired with its translation, Ròdais spelling
  4. Rodos_finished.map: the rewritten sections parse, no pre-Ròdais name
     survives, every saved burg label matches its burg

Exit status 0 only when every check holds.  python check_rodais.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rodais_engine as R  # noqa: E402

fails = []


def check(ok, what):
    print(('ok    ' if ok else 'FAIL  ') + what)
    if not ok:
        fails.append(what)


def words(text):
    return [w for w in re.split(r"[\s,.?!;:()\"“”—–…/]+|'(?=\s)|(?<=\s)'", text) if w and w != "'"]


# 1. engine
check(R._selftest(), 'engine self-test')

# 2. lexicon
lex = json.load(open(os.path.join(HERE, 'LEXICON.json'), encoding='utf-8'))['entries']
check(len(lex) == 5005 and len({e['id'] for e in lex}) == 5005, 'lexicon: 5,005 distinct entries (%d)' % len(lex))
check(all(e.get('rod') and e.get('pos') and e.get('en') for e in lex), 'lexicon: every entry has headword, part of speech, English')
check(all(e.get('g') in ('m', 'f') for e in lex if e['pos'] == 'n'), 'lexicon: every noun has a gender')
check(all(e.get('root') for e in lex if e['pos'] == 'v'), 'lexicon: every verb has a root')
ken = [e for e in lex if e.get('kenning')]
check(all(e.get('lit') and e.get('scots') for e in ken), 'lexicon: every old-root compound has its literal sense and the word it replaces (%d)' % len(ken))
check(len({e['rod'].lower() for e in ken}) == len(ken), 'lexicon: no two old-root compounds share a headword')
check(not [e for e in ken if R.check_agreement(e['rod'].strip('?!.'))], 'lexicon: every old-root compound obeys caol le caol')
fields = [(e['id'], e[k]) for e in lex for k in ('rod', 'pl', 'root') if e.get(k)]
check(all(R.normalize(v) == v for _, v in fields), 'lexicon: every Ròdais field is in Ròdais spelling (no acute, no sg)')
flag = sorted({w for _, v in fields for w in words(v) if R.check_agreement(w)}, key=str.lower)
print('      caol le caol: %d words left outside the rule (loanwords, names, unhyphenated compounds): %s' % (len(flag), ', '.join(flag)))

# 3. texts
texts = json.load(open(os.path.join(HERE, 'TEXTS.json'), encoding='utf-8'))['texts']
check(all(len(t['paras']) == len(t['paras_en']) for t in texts), 'texts: every line paired with its English (%d texts)' % len(texts))
check(all(R.normalize(p) == p for t in texts for p in t['paras'] + [t['title']]), 'texts: Ròdais spelling throughout')
tflag = sorted({w for t in texts for p in t['paras'] for w in words(p) if R.check_agreement(w)}, key=str.lower)
print('      caol le caol in texts: %s' % (', '.join(tflag) or 'none'))

# 4. map
lines = open(os.path.join(HERE, 'Rodos_finished.map'), encoding='utf-8').read().split('\n')
parsed = {}
for n in (137, 139, 140, 154, 155, 157, 160, 162, 163, 177):
    try:
        parsed[n] = json.loads(lines[n])
    except Exception as e:  # noqa: BLE001
        parsed[n] = None
        check(False, 'map: section at line %d parses (%s)' % (n, e))
check(all(v is not None for v in parsed.values()), 'map: every rewritten section parses')
OLD = ['Luteley', 'Grantesham', 'Kiverton', 'Marltash', 'Albridge', 'Penrith', 'Towbigham', 'Hatlexe', 'Uxblean',
       'Tuton', 'Clitle', 'Shkell', 'Seann Dhunn', 'Seann Tharr', 'Seann Tholl', 'City-State Rodos', 'Wincland']
left = [w for w in OLD if any(w in lines[n] for n in list(parsed) + [126])]
check(not left, 'map: no pre-Ròdais name left (%s)' % (', '.join(left) or 'none'))
burgs = {b['i']: b['name'] for b in parsed[140] if isinstance(b, dict) and b.get('name')}
labels = re.findall(r'<text id="burgLabel\d+" data-label-type="burg" data-id="(\d+)"[^>]*>([^<]*)</text>', lines[126])
check(labels and all(burgs.get(int(i)) == t for i, t in labels), 'map: all %d saved burg labels match their burgs' % len(labels))
names = [o['name'] for n in (137, 140, 154, 155, 157, 160, 162, 163) for o in parsed[n] if isinstance(o, dict) and o.get('name')]
check(all(R.normalize(x) == x for x in names), 'map: every name in Ròdais spelling (%d names)' % len(names))
mflag = sorted({w for x in names for w in words(x) if R.check_agreement(w)})
check(not mflag, 'map: every name obeys caol le caol (%s)' % (', '.join(mflag) or 'no exceptions'))

print('\n%s' % ('ALL CHECKS HOLD' if not fails else '%d CHECK(S) FAILED' % len(fails)))
sys.exit(1 if fails else 0)
