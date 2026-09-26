"""names_convert.py -- put the proper nouns of a volume in Dia-thìris (the owner's rule: every proper noun in Dia-thìris).

    python names_convert.py V --dry       # show what would change in Age V's writer files, change nothing
    python names_convert.py V             # convert, and write the log to quality/names_convert_V.log
    python names_convert.py all | master  # every age's writer files | the master record (legendarium/)

The English forms of eras/NAMES.json (en and its variants; not the "ambiguous" list, not humans' personal names)
and of eras/age_<K>/PLAN_names.json are replaced by their exact Dia-thìris form in the Books, the annals (title
and body), the gazetteer and the appendices. legendarium/glosses.py then footnotes the first mention with the
English gloss, so the English never needs to stand beside the name.

How a form is replaced:
  - "the"/"The" before the name is dropped: every Dia-thìris form is definite by itself (An t-Aiseag, A' Chompanaidh,
    Riaghaltas nan Coigreach); a sentence-initial dt that opens in lower case takes a capital.
  - possessives keep their 's: "the Company's agents" -> "A' Chompanaidh's agents".
  - plurals only where the registry has a plural form of its own (the Commissioners -> Na h-Àrd-mhaoir).
  - a one-word name used as an adjective takes the noun it qualifies: "the Company store" -> "A' Chompanaidh's store",
    "a Company clerk" -> "a clerk of A' Chompanaidh"; a title before a human name keeps the name:
    "Commissioner Crane" -> "Àrd-mhaor Crane".
  - an English appositive beside its own dt is dropped: "An Togail, the Levy," -> "An Togail,".
  - a one-word or lower-case form with no "the" before it (Abel Stone, a column of soldiers) is let stand, and so are
    the common nouns listed in COMMON (the crossing, the column, the fleet ... as ordinary words).
  - senses: "the Stone" is the order (Òrd na Cloiche) when its priests or its sending are spoken of, else the relic;
    "the Keeper" is the Hall's office (Coimheadaiche na Lasrach) beside the Hall or the flame, else the spirit.
Never touched: {{tokens}}, headings (their anchors are told_in targets), HTML tags and link targets, code, italic
Dia-thìris, a glossary's own definition (Appendix E's "**dt** · english" lines) and every human's name.
Every change is logged with its place and context; forms left because they are unclear are logged as LEFT.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

import qlib as q

HERE = os.path.dirname(os.path.abspath(__file__))

# lower-case or one-word English forms that are ordinary words in the prose far more often than the name: converted
# only in the longer forms that pin them (the column at Cnoc ghorm, the fleet of the Sundering ...), never bare
COMMON = {'the column', 'the crossing', 'the pillar', 'the obelisk', 'the fleet', 'the mist', 'the black coal',
          'the circus', 'the council', 'the law', 'the point', 'the board', 'the cup', 'the king\'s daughter',
          'the Point', 'the Board', 'the Cup',
          'the colour of the coal', 'the hunger', 'the war', 'the rising', 'the truce', 'the strike', 'the stoppage'}
# variants that would swallow a human's name or a place's qualifier, or name something else
BAD_VARIANTS = {'Clerk of the Company', 'the Keeper Raonaid Dhubh', 'the Keeper Calum Liath', 'the Red Hill list',
                'the Mission at Cathair', 'the Residency at Ros', 'the Moot at Caol', 'the council of custodians'}
# forms added for this volume's prose: the longer phrases that pin a common noun to the name
EXTRA = [('the column at Cnoc ghorm', 'Calbh Cnoc ghorm'), ('the column near Cnoc ghorm', 'Calbh Cnoc ghorm'),
         ('the pillar near Cnoc chiar', 'Colbh Cnoc chiar'), ('the obelisk near Cnoc bheag', 'Carragh Cnoc bheag'),
         ('the treaty in one tongue', 'Cùmhnant Cathair dhearg'), ('the fleet of An Aois Scaraidh', 'Cabhlach an Scaraidh'),
         ('the Council of Custodians', 'Comhairle a\' Chùraim'),
         ('the high custodian of the Council of Custodians', 'Ceann a\' Chùraim')]
TITLES = {'Commissioner'}
# offices and ranks used as common nouns ("a Commissioner who", "high custodian twenty years"): the bare dt noun
OFFICE = {'Commissioner': 'Àrd-mhaor', 'Commissioners': 'Àrd-mhaoir', 'high custodian': "Ceann a' Chùraim",
          'high custodian of the Council': "Ceann a' Chùraim", 'high custodian of the Council of Custodians': "Ceann a' Chùraim"}
POSSDET = {'its', 'their', 'his', 'her', 'your', 'our', 'Its', 'Their', 'His', 'Her', 'Your', 'Our'}             # a title before a human name: "Commissioner Crane" -> "Àrd-mhaor Crane"
DETS = {'a', 'an', 'A', 'An', 'one', 'no', 'No', 'every', 'Every', 'each', 'Each', 'any', 'another', 'two', 'three',
        'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'twelve', 'twenty', 'some', 'Some', 'this', 'that',
        'these', 'those', 'This', 'That', 'his', 'her', 'their', 'its', 'our', 'His', 'Her', 'Their', 'Its'}
ATTRIB = set('''clerk clerks ship ships store stores agent agents surveyor surveyors officer officers men man contract contracts carter carters guard guards chit chits uniform tenant-farmer surgeon steamship steamships pit pits mule mules ledger ledgers labourers labourer gunboat gunboats glazing engineer engineers coaster coasters brig brigs crier satchel pupil pupils primers primer kitchen cleric clerics hall halls school schools boat boats overseer overseers paymaster quay quays doctor doctors chaplain chaplains constable constables chapel chapels priest priests'''.split())
PERSONAL = {'person', 'human', 'human person', 'personal name', 'human name'}
SENT_END = re.compile(r'(?:^|[.!?:;]["”’)\]]?\s+|^\s*[-*]\s+|["“(]\s*|\*\*\s*|—\s*)$')


def fold(s):
    return q.B.build_book.fold(s)


def core_of(form):
    return re.sub(r'^(?i:the)\s+', '', form).strip()


def forms_for(k):
    """[(form, dt, entry)] longest first, from NAMES.json and the age's PLAN_names.json."""
    out, seen = [], set()

    def add(form, dt, e):
        form = re.sub(r'\s*\(.*?\)\s*', ' ', form).strip()
        form = re.sub(r"['’]s$", '', form)
        c = core_of(form)
        if (not form or form in BAD_VARIANTS or form in COMMON or len(c) < 3 or form == dt or c == dt
                or c.lower() == core_of(dt).lower() or (form, dt) in seen):
            return
        seen.add((form, dt))
        out.append((form, dt, e))
    later = set()
    if k in q.KEYS:                   # a name first attested after the age would be a forward reference: never written
        import future_check as FC
        ev = {e['id']: e for e in json.load(open(os.path.join(q.LEG, 'annals_dated.json'), encoding='utf-8'))}
        later = {e['dt'] for e in q.G.names() if (ev.get(e.get('first') or '') or {}).get('age') in q.KEYS
                 and FC.IDX[ev[e['first']]['age']] > FC.IDX[k]}
    for e in q.G.names():
        if str(e.get('kind', '')).lower() in PERSONAL or e['dt'] in later:
            continue
        for f in [e['en']] + [v for v in e.get('variants') or [] if isinstance(v, str)]:
            add(f, e['dt'], e)
    if k in q.KEYS:
        p = os.path.join(q.B.age_dir(k), 'PLAN_names.json')
        if os.path.exists(p):
            for e in json.load(open(p, encoding='utf-8')):
                if e.get('kind') == 'section-title' or str(e.get('kind', '')).lower() in PERSONAL:
                    continue
                add(e['en'], e['dt'], e)
    for f, dt in EXTRA:
        add(f, dt, {'dt': dt})
    # one English form, one Dia-thìris form: a form claimed by two entries is kept for the first (NAMES.json order)
    first = {}
    for f, dt, e in out:
        first.setdefault(f, (f, dt, e))
    return sorted(first.values(), key=lambda x: -len(core_of(x[0])))


def mask_spans(text, glossary=False):
    """Spans never touched: tokens, HTML tags, link targets, code, italics that are Dia-thìris (or, in a glossary,
    every italic), and a glossary line's definition."""
    spans = [m.span() for m in re.finditer(r'\{\{.*?\}\}|<[^>]+>|\]\([^)]*\)|`[^`]*`', text)]
    for m in re.finditer(r'(?<![*\w])\*([^*\n]+)\*(?!\*)', text):
        words = re.findall(r"[A-Za-z]+", m.group(1))
        eng = sum(1 for w in words if w.lower() in ('the', 'of', 'and', 'a', 'to', 'in', 'is', 'was', 'not', 'it', 'that'))
        if glossary or not words or eng / len(words) < 0.12:
            spans.append(m.span())
    if glossary:
        m = re.match(r'^\*\*.+?\*\*\s*·\s*[^.]*\.', text)
        if m:
            spans.append(m.span())
    return spans


def inside(i, spans):
    return any(a <= i < b for a, b in spans)


class Converter:
    def __init__(self, k):
        self.k = k
        self.forms = forms_for(k)
        self.by_core = {}
        for f, dt, e in self.forms:
            self.by_core.setdefault(core_of(f), []).append((f, dt, e))
        alts = '|'.join(re.escape(c) for c in sorted(self.by_core, key=len, reverse=True))
        self.rx = re.compile(r"(?<![\w'’-])(?P<art>(?:the|The)\s+)?(?P<core>%s)(?![\w-])(?P<pos>['’]s(?!\w))?" % alts)
        self.log, self.left = [], []
        dts = sorted({d for _, d, _ in self.forms}, key=len, reverse=True)
        self.dt_rx = re.compile(r"(?<![\w'’-])(?:%s)(?![\w-])" % '|'.join(re.escape(d) for d in dts)) if dts else None

    def sense(self, core, dt, text, s, e):
        """Choose among senses by the words around the name; None when unclear."""
        sent = text[max(0, s - 160):e + 160]
        if re.match(r'Appendix [A-Z]\b', core) or core.lower() in ('annals', 'appendices'):
            return None             # the volume's own appendices and chronicle, not the master's
        if 'high custodian' in core and self.k in ('VI', 'VII'):
            return 'Àrd-choimheadaiche'   # the Council of Custodians is gone by then; the Rite's office remains
        if core == 'Stone':
            if re.search(r'priest|order|was for|send|sent|men to|shut|town|city|temple|the Stone in the|Stone (?:and|or) ', sent):
                return 'Òrd na Cloiche'
            return dt
        if core == 'sacred forest' and re.search(r'Flidais|Muileann chiar', text[e:e + 60]):
            return None             # the forest of Flidais near Muileann chiar, which has no registry name
        if core == 'Keeper':
            if re.search(r'\bHall\b|flame|Flame|Lasair|Lasrach', sent):
                return 'Coimheadaiche na Lasrach'
            return 'Coimhdeach na Fine'
        return dt

    def convert(self, text, where, glossary=False):
        spans = mask_spans(text, glossary)
        spans += [m.span() for m in self.dt_rx.finditer(text)] if self.dt_rx else []
        out, last = [], 0
        for m in self.rx.finditer(text):
            s, e = m.span()
            if inside(s, spans) or s < last:
                continue
            core, art, pos = m.group('core'), m.group('art'), m.group('pos') or ''
            cands = self.by_core[core]
            form, dt, ent = next(((f, d, x) for f, d, x in cands if f.lower().startswith('the ')), cands[0])
            needs_art = form.lower().startswith('the ')
            dt = self.sense(core, dt, text, s, e)
            if dt is None:
                self.left.append((where, form, 'another thing of the same English name', text[max(0, s - 40):e + 40]))
                continue
            before = text[:s]
            prev = re.search(r"([\w'’-]+)\s*$", before)
            prevw = prev.group(1) if prev else ''
            after = text[e:]
            nxt = re.match(r"\s+([a-z][\w-]*)", after)
            nxtw = nxt.group(1) if nxt else ''
            nextcap = re.match(r"\s+([A-Z][\w'’-]+)", after)
            single = ' ' not in core
            new = None
            start = art and art[0] == 'T' or bool(SENT_END.search(before))
            if core in TITLES and not art and nextcap and not pos:
                new = re.sub(r"^(?:An t-|An |A' |Na h-|Na )", '', dt)
                s2 = s
            elif core in OFFICE and not art:
                off = 'Àrd-choimheadaiche' if 'high custodian' in core and self.k in ('VI', 'VII') else OFFICE[core]
                new, s2 = off + pos, s
                if prevw in ('a', 'A') and new[0] in 'AEIOUÀÈÌÒÙ':
                    s2 = prev.start(1)
                    new = prevw + 'n ' + new
            elif not art and prevw in POSSDET and single and core[0].isupper() and nxtw not in ATTRIB:
                s2 = prev.start(1)
                new = dt + pos
                start = start or bool(SENT_END.search(text[:s2]))
            elif single and nxtw in ATTRIB and not pos and core[0].isupper():
                # an adjective: "the Company store", "a Company clerk", "Company ships"
                noun_end = e + nxt.end()
                if art:
                    new_txt = "%s's %s" % (dt, nxtw)
                    s2 = s
                elif prevw in DETS or prevw.lower() in DETS:
                    det = prevw
                    if det.lower() in ('a', 'an'):
                        det = ('An' if det[0] == 'A' else 'an') if nxtw[0] in 'aeiou' else ('A' if det[0] == 'A' else 'a')
                    start = False
                    s2 = prev.start(1)
                    new_txt = '%s %s of %s' % (det, nxtw, dt)
                elif prevw and prevw[0].isupper() and not SENT_END.search(before) and prevw.lower() not in DETS:
                    self.left.append((where, form, 'after a capitalised word', text[max(0, s - 40):e + 40]))
                    continue
                else:
                    s2 = s
                    new_txt = "%s's %s" % (dt, nxtw)
                if start and new_txt[0].islower():
                    new_txt = new_txt[0].upper() + new_txt[1:]
                out.append(text[last:s2])
                out.append(new_txt)
                self.log.append((where, text[s2:noun_end], new_txt, text[max(0, s2 - 50):noun_end + 30]))
                last = noun_end
                continue
            elif art:
                new, s2 = dt + pos, s
            elif not single and re.search(r"['’]s\s+$", before):
                new, s2 = dt + pos, s
            elif not needs_art or (not single and core[0].isupper()):
                if single and prevw and prevw[0].isupper() and not SENT_END.search(before):
                    self.left.append((where, form, 'after a capitalised word (a human name?)', text[max(0, s - 40):e + 40]))
                    continue
                if prevw.lower() in ('a', 'an'):
                    self.left.append((where, form, 'after "a"', text[max(0, s - 40):e + 40]))
                    continue
                new, s2 = dt + pos, s
            else:
                if core[0].isupper() or core.lower() not in ('crossing',):
                    self.left.append((where, form, 'no "the" before it', text[max(0, s - 40):e + 40]))
                continue
            if new is None:
                continue
            if start and new[0].islower():
                new = new[0].upper() + new[1:]
            e2 = m.end()
            out.append(text[last:s2])
            out.append(new)
            self.log.append((where, text[s2:e2], new, text[max(0, s2 - 50):e2 + 30]))
            last = e2
        out.append(text[last:])
        res = ''.join(out)
        return self.dedupe(res, where)

    def dedupe(self, text, where):
        """"An Togail, An Togail," (an English appositive glossing its own dt) -> "An Togail,"."""
        for dt in {d for _, d, _ in self.forms}:
            if text.count(dt) < 2:
                continue
            d = re.escape(dt)
            new = re.sub(r'%s(?:,| —| \(|, or|, called| or) %s\)?' % (d, d), dt, text)
            new = re.sub(r'%s(?:,| —| \(|, or|, called| or) %s' % (d, d[0].lower() + d[1:] if d[0].isalpha() else d), dt, new)
            if new != text:
                self.log.append((where, '(appositive)', dt, 'dropped the English gloss beside ' + dt))
                text = new
        return text


def md_file(conv, path, dry):
    glossary = os.path.basename(path).startswith('E_')
    lines = open(path, encoding='utf-8').read().split('\n')
    fence, changed = False, False
    for i, ln in enumerate(lines):
        if ln.startswith('```'):
            fence = not fence
            continue
        if fence or ln.startswith('#') or not ln.strip():
            continue
        new = conv.convert(ln, '%s:%d' % (q.rel(path), i + 1), glossary)
        if new != ln:
            lines[i], changed = new, True
    if changed and not dry:
        open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    return changed


JSON_KEYS = {'title', 'body', 'history', 'known_for', 'founded_by', 'note', 'description', 'text'}


def json_file(conv, path, dry):
    data = json.load(open(path, encoding='utf-8'))
    changed = [False]

    def walk(x, tag):
        if isinstance(x, dict):
            t = x.get('id') if isinstance(x.get('id'), str) else tag
            for key, v in x.items():
                if isinstance(v, str) and key in JSON_KEYS:
                    new = conv.convert(v, '%s:%s.%s' % (q.rel(path), t, key))
                    if new != v:
                        x[key], changed[0] = new, True
                elif isinstance(v, (dict, list)):
                    walk(v, key if t == tag and not isinstance(x.get('id'), str) else t)
        elif isinstance(x, list):
            for v in x:
                walk(v, tag)
    walk(data, '$')
    if changed[0] and not dry:
        text = json.dumps(data, ensure_ascii=False, indent=1)
        open(path, 'w', encoding='utf-8').write(text + ('\n' if open(path, encoding='utf-8').read().endswith('\n') else ''))
    return changed[0]


def run(target, dry):
    keys = q.KEYS if target == 'all' else [target]
    logs = []
    for k in keys:
        conv = Converter(k)
        files = q.targets(k)
        for f in files:
            if os.path.basename(f) in ('places.json', 'front.json'):
                continue
            (json_file if f.endswith('.json') else md_file)(conv, f, dry)
        logs.append((k, conv))
    return logs


def main():
    ap = argparse.ArgumentParser(description='Put the English proper nouns of a volume in Dia-thìris.')
    ap.add_argument('target', help='I..VII | all | master')
    ap.add_argument('--dry', action='store_true', help='change nothing; print what would change')
    ap.add_argument('--show', type=int, default=30, help='changes shown (-1: all)')
    a = ap.parse_args()
    if a.target not in q.KEYS + ['all', 'master']:
        sys.exit('target: I..VII, all or master')
    for k, conv in run(a.target, a.dry):
        lines = ['CHANGE\t%s\t%s\t->\t%s\t|\t%s' % (w, old, new, ctx.replace('\n', ' ')) for w, old, new, ctx in conv.log]
        lines += ['LEFT\t%s\t%s\t(%s)\t|\t%s' % (w, f, why, ctx.replace('\n', ' ')) for w, f, why, ctx in conv.left]
        if not a.dry:
            with open(os.path.join(HERE, 'names_convert_%s.log' % k), 'a', encoding='utf-8') as fh:   # every run appended
                fh.write('# run %s: %d changes, %d left\n' % (time.strftime('%Y-%m-%d %H:%M'), len(conv.log), len(conv.left)))
                fh.write('\n'.join(lines) + '\n')
        print('%s: %d changes, %d left unclear%s' % (k, len(conv.log), len(conv.left), ' (dry run)' if a.dry else
                                                    ', log in quality/names_convert_%s.log' % k))
        for ln in (lines if a.show < 0 else lines[:a.show]):
            print(ln)


if __name__ == '__main__':
    main()
