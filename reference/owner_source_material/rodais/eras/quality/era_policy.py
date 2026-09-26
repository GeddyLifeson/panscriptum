"""era_policy.py -- one dashboard of every age: eras/quality/ERA_DASHBOARD.md.

    python era_policy.py            # all seven ages (those with eras/age_<K>/annals/)
    python era_policy.py IV V       # some ages;  --stdout prints instead of writing the file

Per age: check_era.check() status (its FAIL lines), entries against check_era.ENTRIES, words per section from
check_era.section_words() against check_era.TARGET, pages by check_era.DENSITY against check_era.PAGES, tells per 10k
words (tells_scan) and names_check findings in the writer files, and how many era events carry links, threads,
people, a category and a told_in.
"""
import argparse
import contextlib
import io
import os
import time

import names_check
import qlib as q
import tells_scan

C, B = q.C, q.B
OUT = os.path.join(q.Q, 'ERA_DASHBOARD.md')


def pct(n, d):
    return '%d/%d (%d%%)' % (n, d, round(100.0 * n / d)) if d else '0/0'


def age(k):
    row = {'age': k, 'title': B.english_name(k)}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fails = C.check(k)
    row['fails'] = fails
    row['notes'] = [ln[6:] for ln in buf.getvalue().splitlines() if ln.startswith('note  ')]
    try:
        events, _ = B.date_era(k)
        rec = B.EraRecord(k, events)
        words = C.section_words(k, rec, B.to_markdown(k, rec))
        row['entries'] = len(events)
        row['words'] = words
        row['pages'] = 10 + sum(words[s] / C.DENSITY[s] for s in C.DENSITY)
        row['nobooks'] = not os.listdir(os.path.join(B.age_dir(k), 'book')) if os.path.isdir(os.path.join(B.age_dir(k), 'book')) else True
    except (B.EraError, AssertionError) as e:
        events, row['error'] = [], str(e)
    era = [e for e in events if not e['master']]
    has = lambda f: sum(1 for e in era if e.get(f))  # noqa: E731
    row['era'] = len(era)
    row['cover'] = {f: pct(has(f), len(era)) for f in ('links', 'threads', 'people', 'category', 'told_in')}
    row['master_cat'] = pct(sum(1 for e in events if e['master'] and e.get('category')), sum(1 for e in events if e['master']))
    tt = tells_scan.total(tells_scan.scan_all(k))
    row['tells'] = tt
    nr = names_check.run(k)
    row['names'] = {c: sum(r['counts'].get(c, 0) for r in nr) for c in ('english', 'misspelt')}
    row['files'] = len(q.writer_files(k))
    return row


def band(v, lo_hi):
    lo, hi = lo_hi
    return '%s %s' % (format(int(v), ','), 'ok' if lo <= v and (hi is None or v <= hi) else ('low' if v < lo else 'HIGH'))


def markdown(rows):
    L = ['# Era dashboard', '', 'Written by `eras/quality/era_policy.py` on %s. Targets from `check_era.py`: entries %d-%d, '
         'pages %d-%s, words %s.' % (time.strftime('%Y-%m-%d %H:%M'), C.ENTRIES[0], C.ENTRIES[1], C.PAGES[0], C.PAGES[1] or '',
                                      ', '.join('%s %s-%s' % (s, format(a, ','), format(b, ',')) for s, (a, b) in C.TARGET.items())), '',
         '| Age | check_era | files | entries | pages | annals | books | gazetteer | appendices | tells /10k | English names | misspelt |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        w = r.get('words')
        L.append('| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %d | %d |' % (
            r['age'], 'HOLDS' if not r['fails'] else '%d FAIL' % len(r['fails']), r['files'],
            band(r['entries'], C.ENTRIES) if w else '-', band(r['pages'], C.PAGES) if w else '-',
            *([band(w[s], C.TARGET[s]) for s in ('annals', 'books', 'gazetteer', 'appendices')] if w else ['-'] * 4),
            '%.1f (%d in %s words)' % (r['tells']['per10k'], r['tells']['tells'], format(r['tells']['words'], ',')),
            r['names']['english'], r['names']['misspelt']))
    if any(r.get('nobooks') for r in rows):
        L += ['', 'Ages with no `book/` files yet (%s): `check_era.section_words()` then counts the annals a second time as '
              'books (its books slice opens at the first "# The " heading, which is "# The Annals of the Age"), so their books '
              'and pages figures are too high until a Book exists.' % ', '.join(r['age'] for r in rows if r.get('nobooks'))]
    L += ['', '## Coverage of era events', '', '| Age | era events | links | threads | people | category | told_in | master events with a category |',
          '|---|---|---|---|---|---|---|---|']
    for r in rows:
        c = r['cover']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s |' % (r['age'], r['era'], c['links'], c['threads'], c['people'],
                                                           c['category'], c['told_in'], r['master_cat']))
    L += ['', '## check_era failures and notes', '']
    for r in rows:
        L.append('**Age %s, %s**%s' % (r['age'], r['title'], (': ' + r['error']) if r.get('error') else ''))
        L += ['- FAIL %s' % f for f in r['fails']] + ['- note %s' % n for n in r['notes'][:8]]
        if len(r['notes']) > 8:
            L.append('- ... %d more notes (python check_era.py %s)' % (len(r['notes']) - 8, r['age']))
        L.append('')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser(description='Dashboard of every age.')
    ap.add_argument('ages', nargs='*')
    ap.add_argument('--stdout', action='store_true')
    a = ap.parse_args()
    keys = a.ages or [k for k in q.KEYS if os.path.isdir(os.path.join(B.age_dir(k), 'annals'))]
    md = markdown([age(k) for k in keys])
    if a.stdout:
        print(md)
    else:
        open(OUT, 'w', encoding='utf-8').write(md + '\n')
        print('wrote %s' % q.rel(OUT))


if __name__ == '__main__':
    main()
