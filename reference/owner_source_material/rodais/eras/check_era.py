"""
check_era.py -- validate one age's era legendarium before it is built or handed on.

    python check_era.py IV             # every check for the Age of Sundering
    python check_era.py all            # every age that has eras/age_<K>/annals/
    python check_era.py IV --final     # also fail when a section is outside its size target
    python check_era.py IV --fuzz 200  # also throw 200 random era events into every gap and prove no master moves

Checks (FAIL stops the exit status at 1; "note" lines are information):
  1. the seed file holds exactly the master events of the age (legendarium/annals/age_<K>.json)
  2. the era annals date: every master event present, in order, on exactly its master date; the annals never
     run backwards and never leave the age's era (build_era.date_era, verified again here)
  3. ids: every era id is E<K>-nnnn, unique across the files and the whole master record, and inside its
     writer's block (writer N owns E<K>-N000 .. E<K>-N999)
  4. every era event has a category of the nine, and "links", "threads" and "people" lists; every link is of the
     eight types and its target exists (this era, another era, or the master); every thread is in THREADS.json,
     every person in PEOPLE.json, and every "told_in" names a book file and one of its headings
  4b. every {{date:}}, {{year:}}, {{reckon:}} and {{place:}} token resolves, and no other {{...}} is left
  5. every event place and every gazetteer burg is on the master map or declared in places.json
  6. the gazetteer: a master town keeps its master founding age, and every town was founded by the end of the age
  7. Dia-thìris spelling: every Dia-thìris form (a word with a long vowel, a word opening in bh/dh/fh/mh, every
     word of a declared name) passes rodais_engine.normalize() unchanged, and check_agreement() unless the master
     record already uses that very word (the names and loanwords check_rodais.py lets stand)
  8. no "obsidian", no Rodos / Ròdais / Ròdaich, no glacier or ice cap, no date in the old continuous count;
     a note for every English form of a NAMES.json proper noun left in the text (humans' personal names excepted)
  8b. future: nothing ahead of the age (quality/future_check.py): no token, era, name or town of a later age, no
     foreshadowing phrase; an era annals entry looks no further than its own day
  8c. ages (quality/ages_check.py, the owner's rule): the rulers who lived in the age keep eras/RULERS.json's rule (no
     one born in FE 1,200 or later, or outside the king's kin, lives past 95; the long years fade generation by
     generation), and eras/age_<K>/PLAN_people.json keeps the rule and the rulers' years of RULERS.json
  9. size: words per section and an estimated page count against the 500-600 page target
"""
import argparse
import glob
import json
import os
import random
import re
import sys

ERAS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ERAS)
sys.path.insert(0, ERAS)
sys.path.insert(0, ROOT)
import build_era as B  # noqa: E402
import rodais_engine as R  # noqa: E402
import event_links as EL  # noqa: E402
import glosses as G  # noqa: E402
sys.path.insert(0, os.path.join(ERAS, 'quality'))
import future_check as FC  # noqa: E402
import ages_check as AC  # noqa: E402

LEG = B.LEG
RK = B.reckoning

# words per printed page in the house design, measured on the master PDF (596 pages): the books ~405, the annals
# ~540, the appendices ~445 (tables), the gazetteer ~620 (two columns), each counting its own opener and part pages;
# plus ~10 pages of front matter and contents. On the master this estimate gives 596 pages, as built.
DENSITY = {'books': 405, 'annals': 540, 'appendices': 445, 'gazetteer': 620}
TARGET = {'annals': (30000, 45000), 'books': (170000, 200000), 'gazetteer': (10000, 15000), 'appendices': (10000, 20000)}
ENTRIES = (500, 800)
PAGES = (500, 600)

WORD = re.compile(r"[^\W\d_](?:[^\W\d_]|['’-](?=[^\W\d_]))*")
LONG = re.compile('[àèìòùÀÈÌÒÙáéíóúÁÉÍÓÚ]')
LENITED = re.compile(r'^[BbDdFfMm]h[aeiouàèìòùAEIOU]')
BANNED = [(re.compile(r'(?i)obsidian'), 'obsidian'),
          (re.compile(r'\bR[oò]d(?:os|ais|aich)\b'), 'Rodos/Ròdais/Ròdaich'),
          (re.compile(r'(?i)\bglacier|\bice[ -]?caps?\b|\biceberg|\bdrift[ -]ice\b'), 'glacier/ice'),
          (re.compile(r'\d[\d,]*\s+B?DE\b|\bBDE\b|Diosal (?:Era|Age)|\bNew Age\b'), 'old continuous count')]


class Report:
    def __init__(self):
        self.fails = []

    def check(self, ok, what):
        print(('ok    ' if ok else 'FAIL  ') + what)
        if not ok:
            self.fails.append(what)

    @staticmethod
    def note(what):
        print('note  ' + what)


def known_words():
    """Every word the master record and the language already use: what check_rodais.py lets stand."""
    texts = []
    lex = json.load(open(os.path.join(ROOT, 'LEXICON.json'), encoding='utf-8'))['entries']
    texts += [e[k] for e in lex for k in ('rod', 'pl', 'root') if e.get(k)]
    for t in json.load(open(os.path.join(ROOT, 'TEXTS.json'), encoding='utf-8'))['texts']:
        texts += t['paras'] + [t['title']]
    texts.append(open(os.path.join(LEG, 'world.json'), encoding='utf-8').read())
    for pat in ('annals/*.json', 'book/*.md', 'appendices/*.md', 'appendices/houses.json', 'gazetteer/out_*.json'):
        texts += [open(f, encoding='utf-8').read() for f in glob.glob(os.path.join(LEG, pat))]
    return {w for t in texts for w in WORD.findall(t)}


def english_possessive(w):
    return re.sub(r"['’]s$", '', w)


def spelling(texts, names, report):
    """texts: [(where, text)]; names: declared Dia-thìris names (every word of them is a form to check)."""
    known = known_words()
    bad_norm, bad_agree = {}, {}
    forms = set()
    for where, t in texts + [('name', n) for n in names]:
        for w in WORD.findall(t):
            w = english_possessive(w)
            if not (LONG.search(w) or LENITED.match(w) or where == 'name'):
                continue
            forms.add(w)
            if R.normalize(w) != w:
                bad_norm.setdefault(w, where)
            elif R.check_agreement(w) and w not in known and w.lower() not in known:
                bad_agree.setdefault(w, where)
    report.check(not bad_norm, 'spelling: %d Dia-thìris forms pass normalize() unchanged (%s)' % (
        len(forms), ', '.join('%s in %s' % kv for kv in list(bad_norm.items())[:10]) or 'all'))
    report.check(not bad_agree, 'spelling: caol le caol holds in every new Dia-thìris form (%s)' % (
        ', '.join('%s in %s' % kv for kv in list(bad_agree.items())[:10]) or 'all'))


def section_words(k, rec, md):
    """Words per section of the built markdown."""
    def between(a, b):
        i = md.find(a)
        if i < 0:
            return ''
        j = md.find(b, i + 1) if b else -1
        return md[i:j if j >= 0 else len(md)]
    b0 = md.find('\n# ')          # the first heading after the title: a Part, a Chapter or a Book, else the annals
    books = '' if b0 < 0 or md.startswith('\n# The Annals of the Age', b0) else md[b0:md.find('\n# The Annals of the Age')]
    annals = between('\n# The Annals of the Age', '\n# A Gazetteer of the Age' if '\n# A Gazetteer of the Age' in md else '\n# Appendix')
    gaz = between('\n# A Gazetteer of the Age', '\n# Appendix')
    i = md.find('\n# Appendix')
    apps = md[i:] if i >= 0 else ''
    return {'books': len(books.split()), 'annals': len(annals.split()), 'gazetteer': len(gaz.split()), 'appendices': len(apps.split())}


def fuzz(k, n, report):
    """Throw n random era events into random gaps, with random windows, exact days, eves and same-days,
    and check every master event keeps its day. A bad "on" day must be refused, never obeyed."""
    rng = random.Random(1)
    masters = B.master_events(k)
    ids = [m['id'] for m in masters]
    orig_load = B.load_sources
    seed, writers = orig_load(k)
    moved, refused, runs = 0, 0, 0
    last_ey = RK.era_year(RK.ERA[k][2], k)
    for run in range(5):
        evs, on_gaps = [], set()
        for i in range(n):
            e = {'id': 'E%s-9%03d' % (k, i), 'title': 't', 'body': 'b'}
            r = rng.random()
            if r < .3:
                a = rng.randint(1, last_ey)
                e['era_between'] = [a, min(last_ey, a + rng.randint(0, 50))]
            elif r < .4:
                e['between'] = [rng.randint(-20000, 3000), rng.randint(-20000, 3000)]
            elif r < .5:
                e['eve'] = rng.choice([True, rng.randint(1, 400)])
            elif r < .6:
                e['same_day'] = True
            elif r < .7:
                e['within'] = [rng.choice(ids), rng.randint(0, 30), rng.randint(0, 5)]
            g = rng.randrange(len(ids))
            if r > .9 and g not in on_gaps:              # one exact day inside the gap
                L = (masters[g]['y'], masters[g]['m'], masters[g]['d'])
                Rb = (masters[g + 1]['y'], masters[g + 1]['m'], masters[g + 1]['d']) if g + 1 < len(masters) else B.bounds(k, masters)
                y = rng.randint(L[0], Rb[0])
                day = (y, rng.randint(1, 12), rng.randint(1, 28))
                if L <= day <= Rb:
                    on_gaps.add(g)
                    e['on'] = [RK.era_year(y, k), day[1], day[2]]
            evs.append((g, e))
        evs.sort(key=lambda x: x[0])
        body = []
        for g, e in evs:
            body += [{'after': ids[g]}, e]
        w = {'writer': 9, 'span': [ids[0], 'end'], 'events': body, 'file': 'fuzz.json'}
        B.load_sources = lambda _k, s=seed, w=w: (s, [w])
        runs += 1
        try:
            out, _ = B.date_era(k)
            by = {e['id']: e for e in out}
            moved += sum(1 for m in masters if (by[m['id']]['y'], by[m['id']]['m'], by[m['id']]['d']) != (m['y'], m['m'], m['d']))
        except B.EraError:
            refused += 1                                 # an "on" day outside its gap: refused, as it must be
        except AssertionError:
            moved += 1
        finally:
            B.load_sources = orig_load
    # an exact day outside its gap is refused, never obeyed
    first, second = ids[0], ids[1]
    bad = {'id': 'E%s-9999' % k, 'title': 't', 'body': 'b', 'on': [last_ey, 12, 28]}
    B.load_sources = lambda _k: (seed, [{'writer': 9, 'span': [first, second], 'events': [bad], 'file': 'fuzz.json'}])
    try:
        B.date_era(k)
        bad_refused = False
    except B.EraError:
        bad_refused = True
    finally:
        B.load_sources = orig_load
    report.check(moved == 0 and refused == 0 and bad_refused,
                 'fuzz: %d runs of %d random era events in random gaps (windows anywhere, eves, same days, "within", '
                 'exact days): no master event moved; an exact day outside its gap is refused' % (runs, n))


def check(k, final=False, n_fuzz=0):
    report = Report()
    print('== Age %s: %s' % (k, B.full_title(k)))
    d = B.age_dir(k)
    seed_p = os.path.join(d, 'annals', 'age_%s_master.json' % k)
    seed_ok = os.path.exists(seed_p) and json.load(open(seed_p, encoding='utf-8')) == B.master_source(k)
    report.check(seed_ok, 'seed: annals/age_%s_master.json is exactly legendarium/annals/age_%s.json' % (k, k))
    try:
        events, warn = B.date_era(k)
    except (B.EraError, AssertionError) as e:
        report.check(False, 'annals: the era annals date (%s)' % e)
        return report.fails
    for w in warn:
        report.note(w)
    masters = B.master_events(k)
    by = {e['id']: e for e in events}
    missing = [m['id'] for m in masters if m['id'] not in by]
    moved = [m['id'] for m in masters if m['id'] in by and (by[m['id']]['y'], by[m['id']]['m'], by[m['id']]['d'], by[m['id']]['date'])
             != (m['y'], m['m'], m['d'], m['date'])]
    report.check(not missing and not moved, 'annals: all %d master events present with their master dates (missing %s, moved %s)'
                 % (len(masters), ', '.join(missing[:6]) or 'none', ', '.join(moved[:6]) or 'none'))
    order = [(e['y'], e['m'], e['d']) for e in events]
    report.check(order == sorted(order) and all(RK.era_of(*o) == k for o in order),
                 'annals: %d events in order of date, all inside the era of Age %s' % (len(events), k))
    built = os.path.join(d, 'annals_dated.json')
    if os.path.exists(built):
        stale = json.load(open(built, encoding='utf-8')) != json.loads(json.dumps(events, ensure_ascii=False))
        if stale:
            report.note('annals_dated.json is older than the sources: run build_era.py %s' % k)
    era = [e for e in events if not e['master']]
    all_master = {e['id'] for e in json.load(open(os.path.join(LEG, 'annals_dated.json'), encoding='utf-8'))}
    ids = [e['id'] for e in events]
    report.check(len(ids) == len(set(ids)) and not [i for i in ids if i in all_master and not by[i]['master']],
                 'ids: %d ids unique across the files and the master record' % len(ids))
    writer = {}
    blocks = []
    for e in era:
        if e['src'] not in writer:
            writer[e['src']] = json.load(open(os.path.join(d, 'annals', e['src']), encoding='utf-8')).get('writer')
        w = writer[e['src']]
        num = int(B.ERA_ID.match(e['id']).group(2))
        if not isinstance(w, int) or num // 1000 != w:
            blocks.append('%s in %s (writer %s)' % (e['id'], e['src'], w))
    report.check(not blocks, 'ids: every era id inside its writer\'s block, E%s-N000..N999 for writer N (%s)'
                 % (k, ', '.join(blocks[:6]) or 'all %d' % len(era)))
    # categories and links
    shape = [p for e in events for p in EL.problems(e)]
    nocat = [e['id'] for e in era if not e.get('category')]
    report.check(not shape and not nocat, 'links and categories: every link is {to, type, note?} of the eight types, '
                 'every category one of the nine, every era event has one (%s)' % ('; '.join(shape[:5] + ['no category: ' + ', '.join(nocat[:8])] if nocat else shape[:5]) or 'all'))
    uni, undated = B.link_universe(k, events)
    for o in undated:
        report.note('Age %s does not date yet; its ids are still known as link targets' % o)
    dangling = ['%s -> %s' % (e['id'], ln.get('to')) for e in events for ln in e.get('links') or []
                if isinstance(ln, dict) and ln.get('to') not in uni]
    n_links = sum(len(e.get('links') or []) for e in events)
    report.check(not dangling, 'links: all %d link targets exist, in this era, another era or the master (%s)'
                 % (n_links, ', '.join(dangling[:8]) or 'all'))
    # threads, people, the telling (eras/THREADS.json, eras/PEOPLE.json, "told_in": "book/<file>.md#<anchor>")
    TH, PP = B.threads(), B.people()
    lacking = ['%s (%s)' % (e['id'], ', '.join(f for f in ('links', 'threads', 'people') if not isinstance(e.get(f), list)))
               for e in era if not all(isinstance(e.get(f), list) for f in ('links', 'threads', 'people'))]
    report.check(not lacking, 'fields: every era event fills "links", "threads" and "people" (an empty list when there '
                 'is truly none) (%s)' % (', '.join(lacking[:6]) or 'all %d' % len(era)))
    badt = ['%s: %s' % (e['id'], t) for e in events for t in e.get('threads') or [] if t not in TH]
    report.check(not badt, 'threads: every thread id is in eras/THREADS.json (%s)' % (', '.join(badt[:8]) or 'all'))
    badp = ['%s: %s' % (e['id'], q) for e in events for q in e.get('people') or [] if q not in PP]
    report.check(not badp, 'people: every person id is in eras/PEOPLE.json (%s)' % (', '.join(badp[:8]) or 'all'))
    badr = ['%s: %s' % (e['id'], e['told_in']) for e in events if e.get('told_in') and not B.told_in(k, e['told_in'])]
    report.check(not badr, 'told_in: every "book/<file>.md#<anchor>" names a book file and one of its headings (%s)'
                 % (', '.join(badr[:6]) or 'all %d' % sum(1 for e in events if e.get('told_in'))))
    nomcat = sum(1 for e in events if e['master'] and not e.get('category'))
    if nomcat:
        report.note('%d master events have no category yet (the master pass gives them one)' % nomcat)
    # the record, tokens and places
    rec = B.EraRecord(k, events)
    try:
        md = B.to_markdown(k, rec)
    except B.EraError as e:
        report.check(False, 'sources: %s' % e)
        return report.fails
    left = sorted(set(re.findall(r'\{\{[^}]*\}\}', md)))
    report.check(not rec.missing and not left, 'tokens: every {{date}}, {{year}}, {{reckon}} and {{place}} resolves (%s)'
                 % (', '.join(sorted(set(rec.missing))[:8] + left[:4]) or 'all'))
    master_burgs = {str(b['id']) for b in rec.world['burgs']}
    declared = {ref.split(':', 1)[1] for ref in rec.places if ref.startswith('burg:')}
    clash = sorted(declared & master_burgs)
    report.check(not clash, 'places: no declared era burg reuses a master burg id (%s)' % (', '.join(clash) or 'none'))
    badpl = [e['id'] for e in events if e.get('place') and e['place'] not in rec.names]
    report.check(not badpl, 'places: every event place is on the master map or in places.json (%s)' % (', '.join(badpl[:8]) or 'all'))
    badg = [bid for bid in rec.era_gaz if bid not in master_burgs and bid not in declared]
    report.check(not badg, 'gazetteer: %d entries, every burg id on the master map or a declared era burg (%s)'
                 % (len(rec.era_gaz), ', '.join(badg[:8]) or 'all'))
    contra, late = [], []
    end = B.bounds(k, masters)
    for bid, g in rec.era_gaz.items():
        mg = rec.gaz.get(int(bid)) if bid.isdigit() else None
        if mg and g.get('founded_age') and g['founded_age'] != mg.get('founded_age'):
            contra.append('%s (%s, master %s)' % (bid, g['founded_age'], mg.get('founded_age')))
        f = g['founded']
        if (f['y'], f['m'], f['d']) > end:
            late.append('%s (%s)' % (bid, f['date']))
    report.check(not contra, 'gazetteer: master towns keep their master founding age (%s)' % (', '.join(contra[:6]) or 'all'))
    report.check(not late, 'gazetteer: every town stands by the end of the age (%s)' % (', '.join(late[:6]) or 'all'))
    # spelling and banned words: the era's own words (not the master events, already checked by check_rodais.py)
    srcs = []
    for pat in ('book/*.md', 'appendices/*.md', 'gazetteer/*.json', 'places.json', 'front.json'):
        for f in sorted(glob.glob(os.path.join(d, pat))):
            srcs.append((os.path.relpath(f, d), open(f, encoding='utf-8').read()))
    srcs += [(e['id'], '%s %s' % (e['title'], e['body'])) for e in era]
    names = [p['name'] for p in rec.places.values() if p.get('name')] + [g['name'] for g in rec.era_gaz.values() if g.get('name')]
    spelling(srcs, names, report)
    eng = sorted({'%s (write %s) in %s' % (en, dt, where) for where, t in srcs for en, dt in G.english_left(t)})
    for x in eng[:40]:
        report.note('proper noun in English: %s' % x)
    if not G.names():
        report.note('no eras/NAMES.json yet: English proper nouns are not looked for')
    hits = sorted({'%s in %s' % (label, where) for where, t in srcs for rx, label in BANNED if rx.search(t)})
    report.check(not hits, 'words: no obsidian, no Rodos/Ròdais/Ròdaich, no glacier or ice, no old continuous count (%s)'
                 % (', '.join(hits[:8]) or 'none'))
    # the owner's rule: a volume speaks only of its own age and what came before (quality/future_check.py)
    ahead = FC.check_era(k)
    for where, rule, matched, why, snip in ahead[:20]:
        report.note('forward reference: %s: %s "%s" (%s)' % (where, rule, matched, why))
    report.check(not ahead, 'future: the book, annals, gazetteer and appendices speak only of Age %s and before, no later '
                 'event, era, name, town or foreshadowing (%s)' % (k, '%d hit(s), quality/future_check.py %s' % (len(ahead), k)
                                                                    if ahead else 'none'))
    # the owner's rule: rulers' ages stated, and ages back to normal by the Holy Age (quality/ages_check.py, eras/RULERS.json)
    ares, adoc = AC.check_age(k)
    for what, pr in ares:
        for x in pr[:10]:
            report.note('ages: %s: %s' % (what, x))
    report.check(not any(pr for _, pr in ares), 'ages: the %d rulers who lived in Age %s and the plan keep RULERS.json (no one born in '
                 'FE 1,200 or later, or outside the king\'s kin, past 95; the long years fading generation by generation; '
                 'planned rulers\' years as RULERS.json gives them) (%s)' % (len(adoc['rulers']), k,
                 '; '.join('%s %d' % (w, len(pr)) for w, pr in ares if pr) or 'all'))
    # size
    words = section_words(k, rec, md)
    pages = 10 + sum(words[s] / DENSITY[s] for s in DENSITY)        # the densities include the openers
    total = sum(words.values())
    print('size  %-11s %8s words   target %s' % ('annals', format(words['annals'], ','), '%s-%s words, %s-%s entries (%d now)'
          % (format(TARGET['annals'][0], ','), format(TARGET['annals'][1], ','), format(ENTRIES[0], ','), format(ENTRIES[1], ','), len(events))))
    for s in ('books', 'gazetteer', 'appendices'):
        print('size  %-11s %8s words   target %s-%s' % (s, format(words[s], ','), format(TARGET[s][0], ','), format(TARGET[s][1], ',')))
    print('size  %-11s %8s words   about %d pages (target %d-%d)' % ('total', format(total, ','), pages, PAGES[0], PAGES[1]))
    if final:
        out = [s for s in TARGET if not TARGET[s][0] <= words[s] <= TARGET[s][1]]
        if not ENTRIES[0] <= len(events) <= ENTRIES[1]:
            out.append('annals entries')
        if not PAGES[0] <= pages <= PAGES[1]:
            out.append('pages')
        report.check(not out, 'size: every section, the annals entries and the page estimate inside their targets (outside: %s)'
                     % (', '.join(out) or 'none'))
    if n_fuzz:
        fuzz(k, n_fuzz, report)
    return report.fails


def main():
    ap = argparse.ArgumentParser(description='Validate an age\'s era legendarium.')
    ap.add_argument('age', help='I..VII or all')
    ap.add_argument('--final', action='store_true', help='fail when a section is outside its size target')
    ap.add_argument('--fuzz', type=int, default=0, metavar='N', help='prove with N random era events that no master moves')
    a = ap.parse_args()
    keys = [k for k in B.KEYS if os.path.isdir(os.path.join(B.age_dir(k), 'annals'))] if a.age == 'all' else [a.age]
    if any(k not in B.KEYS for k in keys):
        sys.exit('age must be one of %s or all' % ', '.join(B.KEYS))
    fails = []
    for k in keys:
        fails += ['Age %s: %s' % (k, f) for f in check(k, a.final, a.fuzz)]
        print()
    print('ALL CHECKS HOLD' if not fails else '%d CHECK(S) FAILED' % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
