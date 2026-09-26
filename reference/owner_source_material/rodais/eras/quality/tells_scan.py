"""tells_scan.py -- find machine-sounding prose (TOLKIEN_BRIEF "What counts as machine-sounding", BOOK_STYLE_BRIEF).

    python tells_scan.py master            # the master legendarium
    python tells_scan.py IV                # Age IV's writer files (eras/age_IV/, not the master seed)
    python tells_scan.py path/to/file.md   # a file or a directory
    python tells_scan.py IV --hits 0       # counts only;  --json for machine output

Per file: words, hits of each tell, tells per 10k words, em-dashes per 1k words, watch-words used over OVERUSE
per 10k words; then each hit as file:where: tell: snippet. The writers' short list is TELLS_FOR_WRITERS.md.
"""
import argparse
import collections
import json
import re

import qlib as q

I = re.I
MODERN = (r'framework|process(?:es)?|crucial(?:ly)?|significant(?:ly)?|significance|notably|ensur(?:e|es|ed|ing)|landscape|'
          r'navigat(?:e|es|ed|ing)|delv(?:e|es|ed|ing)|tapestry|testament|pivotal|underscor(?:e|es|ed|ing)|robust|'
          r'arguably|essentially|ultimately|interestingly|seamless(?:ly)?|leverag(?:e|es|ed|ing)|'
          r'multifaceted|nuanced?|intricate|showcas(?:e|es|ed|ing)|resonat(?:e|es|ed|ing)|vibrant|bustling')
TELLS = [
    ('not-X-but-Y', re.compile(r"\bnot\b(?! only)[^.;:!?\n]{1,60}?,? but\b|\b(?:was|is|were|are|did|does)(?:n['’]t| not)\b[^.;!?\n]{1,50}[;:.—–]\s*(?:it|this|that|they|he|she) (?:was|is|were|are|did)\b", I)),
    ('summing-up', re.compile(r'\bwhich is to say\b|\bin other words\b|\bthis matters because\b|\bit is a fair summary\b|'
                              r"\bit['’]?s worth noting\b|\bit is worth noting\b|\bin short,|\bin essence\b|\bto put it (?:simply|plainly)\b", I)),
    ('record-hedging', re.compile(r"\b(?:the|no) (?:records?|chronicles?|annals?|sources?|histor(?:y|ies)|chroniclers?)\b[^.;\n]{0,25}?"
                                  r"\b(?:does not|do not|did not|doesn['’]t|don['’]t|never|cannot|can not|could not|is silent|are silent|"
                                  r"says? nothing|tells? nothing|knows? (?:it|him|her|them) as)\b|"
                                  r"\bit is not (?:recorded|known|told) (?:why|whether|how|who|what|where)\b|"
                                  r"\b(?:is|are|was|were) not recorded\b|\bnothing is (?:recorded|told|known)\b", I)),
    ('modern-word', re.compile(r'\b(?:%s)\b|\ba sense of\b|\bserv(?:e|es|ed|ing) as\b|\bplay(?:s|ed|ing)? an? (?:\w+ )?role\b|'
                               r'\bin terms of\b|\bthe realm of\b|\bkey (?:role|part|figure|moment|factor|point|step|element)\b|'
                               r'\b(?:is|was|are|were) key\b' % MODERN, I)),
    ('participle-tail', re.compile(r',\s+(?:thus\s+|thereby\s+)?(?:marking|reflecting|highlighting|underscoring|signall?ing|symboli[sz]ing|'
                                   r'cementing|ensuring|showcasing|emphasi[sz]ing|illustrating|demonstrating|paving|solidifying|'
                                   r'foreshadowing|embodying|heralding|signifying|capturing|encapsulating)\b', I)),
    ('dash-and', re.compile(r'\s[—–]\s*and\b|—and\b')),
]
OVERUSE = ('quiet', 'quietly', 'simply', 'merely', 'indeed', 'truly', 'deeply', 'utterly', 'entirely', 'perhaps',
           'faint', 'faintly', 'softly', 'stillness', 'echo', 'echoes', 'echoed', 'weight', 'somehow', 'itself',
           'very', 'something', 'moment', 'certain', 'thread', 'threads', 'shape', 'shaped')
LIMIT = 6.0          # watch-word uses per 10k words before it counts as over-used
RUN = 3              # the same sentence opener this many times in a row
SENT = re.compile(r'(?<=[.!?])["”’)]*\s+(?=["“(]?[A-ZÀ-Ù{])')


def opener(s):
    w = [x.lower() for x in q.C.WORD.findall(s)[:2]]
    return ' '.join(w) if w and w[0] in ('the', 'a', 'an') else (w[0] if w else '')


def scan(path):
    units = q.prose(path)
    hits, n_words, dashes, vocab = [], 0, 0, collections.Counter()
    prev, run = None, []
    for where, text in units:
        n_words += q.words(text)
        if not text.lstrip().startswith('|'):
            dashes += text.count('—') + text.count(' – ')
        vocab.update(w.lower() for w in q.C.WORD.findall(text))
        clean = re.sub(r'\{\{[^}]*\}\}', 'X', text)
        for name, rx in TELLS:
            for m in rx.finditer(clean):
                hits.append((where, name, clean[max(0, m.start() - 30):m.end() + 30].replace('\n', ' ')))
        if text.lstrip().startswith(('#', '|', '>')):
            continue
        for s in SENT.split(clean):
            o = opener(s)
            run = run + [(where, s)] if o and o == prev else [(where, s)]
            prev = o
            if len(run) == RUN:
                hits.append((run[0][0], 'repeated-opener', '"%s" x%d: %s' % (o, RUN, s[:60])))
    per10k = lambda c: 10000.0 * c / max(n_words, 1)  # noqa: E731
    over = {w: round(per10k(vocab[w]), 1) for w in OVERUSE if vocab[w] >= 5 and per10k(vocab[w]) > LIMIT}
    counts = collections.Counter(h[1] for h in hits)
    return {'file': q.rel(path), 'words': n_words, 'counts': dict(counts), 'tells': len(hits),
            'per10k': round(per10k(len(hits)), 1), 'dashes_per1k': round(1000.0 * dashes / max(n_words, 1), 1),
            'overused': over, 'hits': hits}


def scan_all(target):
    return [scan(f) for f in q.targets(target)]


def total(results):
    w = sum(r['words'] for r in results)
    t = sum(r['tells'] for r in results)
    return {'files': len(results), 'words': w, 'tells': t, 'per10k': round(10000.0 * t / max(w, 1), 1),
            'counts': dict(sum((collections.Counter(r['counts']) for r in results), collections.Counter()))}


def main():
    ap = argparse.ArgumentParser(description='Find machine-sounding prose.')
    ap.add_argument('target', nargs='+', help='file | dir | I..VII | eras | master')
    ap.add_argument('--hits', type=int, default=20, metavar='N', help='line hits shown per file (0: none, -1: all)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    res = [r for t in a.target for r in scan_all(t)]
    if a.json:
        print(json.dumps({'files': res, 'total': total(res)}, ensure_ascii=False, indent=1))
        return
    names = [n for n, _ in TELLS] + ['repeated-opener']
    print('%-44s %7s %6s  %s  dash/1k' % ('file', 'words', '/10k', ' '.join(n[:8].rjust(8) for n in names)))
    for r in res:
        print('%-44s %7d %6.1f  %s  %5.1f' % (r['file'][-44:], r['words'], r['per10k'],
              ' '.join(str(r['counts'].get(n, 0)).rjust(8) for n in names), r['dashes_per1k']))
        if r['overused']:
            print('    over-used (per 10k): ' + ', '.join('%s %s' % kv for kv in sorted(r['overused'].items(), key=lambda x: -x[1])))
    tt = total(res)
    print('TOTAL %d files, %d words, %d tells, %.1f per 10k: %s' % (tt['files'], tt['words'], tt['tells'], tt['per10k'],
          ', '.join('%s %d' % kv for kv in sorted(tt['counts'].items()))))
    if a.hits:
        for r in res:
            for where, name, snip in (r['hits'] if a.hits < 0 else r['hits'][:a.hits]):
                print('%s:%s: %s: %s' % (r['file'], where, name, snip))


if __name__ == '__main__':
    main()
