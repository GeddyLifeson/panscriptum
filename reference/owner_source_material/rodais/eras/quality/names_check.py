"""names_check.py -- proper nouns against eras/NAMES.json.

    python names_check.py IV            # Age IV's writer files;  also: master, eras, a file or a directory
    python names_check.py master --hits 0 --json

Three findings:
  english    an English name (or listed variant) still standing where NAMES.json gives a Dia-thìris form
             (glosses.english_left, so humans' personal names are let stand as the build lets them)
  misspelt   a Dia-thìris form written with the wrong case or accents ("Baile Chrom" for "Baile chrom",
             "Aois Arsaidh"), or with an English article before a name that carries its own ("the An Aois Naomh")
  registry   a dt in NAMES.json or THREADS.json that rodais_engine.normalize() would change

For an age (I..VII) the age's PLAN_names.json forms count as well. An English form standing inside a Dia-thìris name
(Diosal in "An Diosal", Sloc in "Là Stad nan Sloc") is not a hit. Hits the owner lets stand (a human's name, a common
noun, a heading that is not the name, a glossary's own definition) are listed with their reason in
quality/names_allow.json: {"allow": [{"files": glob, "en": english form, "near": regex, "reason": ...}]}; a hit is
allowed when its file matches "files", its form is "en" (or, for a misspelt hit, its registry form is "dt") and "near" is found in the text around it, where the hit
itself is written as § (so "Abel §" or "(?<![Tt]he )§"). Allowed hits are counted apart and never fail.
"""
import argparse
import bisect
import collections
import json
import re
import unicodedata

import fnmatch
import os

import qlib as q

ART = re.compile(r"^(?:An t-|Na h-|An |Am |Na |A' |an t-|na h-|an |am |na |a' )")


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def plan_names(k):
    """The age's PLAN_names.json entries (English forms without their bracketed notes)."""
    p = os.path.join(q.B.age_dir(k), 'PLAN_names.json') if k in q.KEYS else ''
    if not p or not os.path.exists(p):
        return []
    out = []
    for e in json.load(open(p, encoding='utf-8')):
        if e.get('dt') and e.get('en') and e.get('kind') != 'section-title':
            out.append(dict(e, en=re.sub(r'\s*\(.*?\)\s*', ' ', e['en']).strip()))
    return out


def allow_rules():
    p = os.path.join(q.Q, 'names_allow.json')
    if not os.path.exists(p):
        return []
    return [dict(r, rx=re.compile(r['near'])) for r in json.load(open(p, encoding='utf-8')).get('allow', [])]


def entries(k=None):
    """NAMES entries (and the age's PLAN_names), each variant as another English form."""
    out = []
    for e in q.G.names() + plan_names(k):
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


def check(path, ents, pats, rules=(), dts=None):
    """Search the whole file once per name, then place each hit in its unit."""
    units = q.prose(path)
    starts, pos = [], 0
    for _, t in units:
        starts.append(pos)
        pos += len(t) + 1
    text = '\n'.join(t for _, t in units)
    where = lambda i: units[bisect.bisect_right(starts, i) - 1][0]  # noqa: E731
    hits, seen = [], set()
    if dts:
        for m in dts.finditer(text):
            seen.update(range(m.start(), m.end()))
    rel = q.rel(path)
    allowed = 0
    for en, dt in sorted(q.G.english_left(text, ents), key=lambda x: -len(x[0])):
        core = re.sub(r'^(?i:the)\s+', '', en)
        for m in re.finditer(r'(?<![\w\-])%s(?![\w\-])' % re.escape(core), text):
            if m.start() in seen:
                continue
            seen.update(range(m.start(), m.end()))
            around = text[max(0, m.start() - 80):m.start()] + '§' + text[m.end():m.end() + 80]
            if any(r.get('en') in (en, '*') and fnmatch.fnmatch(rel, r.get('files', '*')) and r['rx'].search(around) for r in rules):
                allowed += 1
                continue
            hits.append((where(m.start()), 'english', '%s -> %s' % (en, dt)))
    ftext = fold(text)
    for dt, core, fcore, rx in pats:
        for m in (rx.finditer(text) if fcore in ftext else ()):
            got = m.group(2)
            around = text[max(0, m.start(2) - 80):m.start(2)] + '§' + text[m.end(2):m.end(2) + 80]
            if any(r.get('dt') == dt and fnmatch.fnmatch(rel, r.get('files', '*')) and r['rx'].search(around) for r in rules):
                allowed += 1
                continue
            if got != core and not (got[1:] == core[1:] and got[0] == core[0].upper()):
                hits.append((where(m.start(2)), 'misspelt', '%s (write %s)' % (got, core)))
            elif m.group(1) and core != dt:
                hits.append((where(m.start()), 'misspelt', '%s%s (the name has its article: %s)' % (m.group(1), got, dt)))
    counts = dict(collections.Counter(h[1] for h in hits))
    counts['allowed'] = allowed
    return {'file': rel, 'counts': counts, 'total': len(hits), 'hits': hits}


def run(target):
    ents, pats, rules = entries(target), dt_patterns(), allow_rules()
    forms = sorted({e['dt'] for e in ents}, key=len, reverse=True)
    dts = re.compile(r"(?<![\w'’-])(?:%s)(?![\w-])" % '|'.join(re.escape(d) for d in forms)) if forms else None
    return [check(f, ents, pats, rules, dts) for f in q.targets(target)]


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
        print('%-44s english %4d  misspelt %4d  allowed %4d' % (r['file'][-44:], r['counts'].get('english', 0),
                                                              r['counts'].get('misspelt', 0), r['counts'].get('allowed', 0)))
    print('TOTAL english %d, misspelt %d, registry dt failing normalize() %d (allowed by quality/names_allow.json: %d)' % (
        sum(r['counts'].get('english', 0) for r in res), sum(r['counts'].get('misspelt', 0) for r in res), len(reg),
        sum(r['counts'].get('allowed', 0) for r in res)))
    for src, dt, n in reg:
        print('registry: %s dt "%s" normalizes to "%s"' % (src, dt, n))
    if a.hits:
        for r in res:
            for h in (r['hits'] if a.hits < 0 else r['hits'][:a.hits]):
                print('%s:%s: %s: %s' % ((r['file'],) + h))


if __name__ == '__main__':
    main()
