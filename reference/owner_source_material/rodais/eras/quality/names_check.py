"""names_check.py -- proper nouns against eras/NAMES.json.

    python names_check.py IV            # Age IV's writer files;  also: master, eras, a file or a directory
    python names_check.py master --hits 0 --json

Three findings:
  english    an English name (or listed variant) still standing where NAMES.json gives a Dia-thìris form
             (glosses.english_left, so humans' personal names are let stand as the build lets them)
  misspelt   a Dia-thìris form written with the wrong case or accents ("Baile Chrom" for "Baile chrom",
             "Aois Arsaidh"), or with an English article before a name that carries its own ("the An Aois Naomh")
  registry   a dt in NAMES.json or THREADS.json that rodais_engine.normalize() would change
"""
import argparse
import bisect
import collections
import json
import re
import unicodedata

import qlib as q

ART = re.compile(r"^(?:An t-|Na h-|An |Am |Na |A' |an t-|na h-|an |am |na |a' )")


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def entries():
    """NAMES entries, each variant as another English form."""
    out = []
    for e in q.G.names():
        out.append(e)
        out += [dict(e, en=v) for v in e.get('variants') or [] if isinstance(v, str)]
    return out


def dt_patterns():
    """[(dt, core, regex)]: the core (dt without its article) matched whatever its case and accents."""
    pats, seen = [], set()
    for e in q.G.names():
        dt = e['dt']
        core = ART.sub('', dt)
        if dt in seen or len(core) < 4:
            continue
        seen.add(dt)
        chars = ''.join('[%s]' % re.escape(''.join({c, c.upper(), c.lower(), fold(c), fold(c).upper()})) if c.isalpha() else re.escape(c)
                        for c in core)
        pats.append((dt, core, fold(core), re.compile(r"(?<![\w'-])(the |The )?(%s)(?![\w-])" % chars)))
    return pats


def registry():
    bad = [('NAMES', e['dt'], q.R.normalize(e['dt'])) for e in q.G.names() if q.R.normalize(e['dt']) != e['dt']]
    th = json.load(open(q.os.path.join(q.ERAS, 'THREADS.json'), encoding='utf-8')).get('threads', [])
    bad += [('THREADS', t['dt'], q.R.normalize(t['dt'])) for t in th if t.get('dt') and q.R.normalize(t['dt']) != t['dt']]
    return bad


def check(path, ents, pats):
    """Search the whole file once per name, then place each hit in its unit."""
    units = q.prose(path)
    starts, pos = [], 0
    for _, t in units:
        starts.append(pos)
        pos += len(t) + 1
    text = '\n'.join(t for _, t in units)
    where = lambda i: units[bisect.bisect_right(starts, i) - 1][0]  # noqa: E731
    hits, seen = [], set()
    for en, dt in sorted(q.G.english_left(text, ents), key=lambda x: -len(x[0])):
        core = re.sub(r'^(?i:the)\s+', '', en)
        for m in re.finditer(r'(?<![\w\-])%s(?![\w\-])' % re.escape(core), text):
            if m.start() in seen:
                continue
            seen.update(range(m.start(), m.end()))
            hits.append((where(m.start()), 'english', '%s -> %s' % (en, dt)))
    ftext = fold(text)
    for dt, core, fcore, rx in pats:
        for m in (rx.finditer(text) if fcore in ftext else ()):
            got = m.group(2)
            if got != core and not (got[1:] == core[1:] and got[0] == core[0].upper()):
                hits.append((where(m.start(2)), 'misspelt', '%s (write %s)' % (got, core)))
            elif m.group(1) and core != dt:
                hits.append((where(m.start()), 'misspelt', '%s%s (the name has its article: %s)' % (m.group(1), got, dt)))
    return {'file': q.rel(path), 'counts': dict(collections.Counter(h[1] for h in hits)), 'total': len(hits), 'hits': hits}


def run(target):
    ents, pats = entries(), dt_patterns()
    return [check(f, ents, pats) for f in q.targets(target)]


def main():
    ap = argparse.ArgumentParser(description='Check proper nouns against eras/NAMES.json.')
    ap.add_argument('target', nargs='+', help='file | dir | I..VII | eras | master')
    ap.add_argument('--hits', type=int, default=20, metavar='N', help='hits shown per file (0: none, -1: all)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    res = [r for t in a.target for r in run(t)]
    reg = registry()
    if a.json:
        print(json.dumps({'files': res, 'registry': reg}, ensure_ascii=False, indent=1))
        return
    for r in res:
        print('%-44s english %4d  misspelt %4d' % (r['file'][-44:], r['counts'].get('english', 0), r['counts'].get('misspelt', 0)))
    print('TOTAL english %d, misspelt %d, registry dt failing normalize() %d' % (
        sum(r['counts'].get('english', 0) for r in res), sum(r['counts'].get('misspelt', 0) for r in res), len(reg)))
    for src, dt, n in reg:
        print('registry: %s dt "%s" normalizes to "%s"' % (src, dt, n))
    if a.hits:
        for r in res:
            for h in (r['hits'] if a.hits < 0 else r['hits'][:a.hits]):
                print('%s:%s: %s: %s' % ((r['file'],) + h))


if __name__ == '__main__':
    main()
