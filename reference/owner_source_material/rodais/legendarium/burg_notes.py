"""
burg_notes.py -- give every burg of the Dia-thìr map (Rodos_finished.map, record 15) a note for a reader, from the
gazetteer (legendarium/gazetteer/out_*.json) and the master annals (legendarium/annals_dated.json).

A note is what Azgaar shows when the pointer rests on a town: its history as the gazetteer tells it, what it is known
for, its founding, and "Told of in:" with the annals events that happened there, by title and date ("The mason's fire
(VE 1)"). Proper nouns in the English are put in Dia-thìris by eras/quality/names_convert.py (humans' names as they
are); the gazetteer is already written so, and the pass only catches what slipped. No ids, no build terms.

finish_map.py calls apply(lines) last, after the reconcile; it touches only the burgs' "note" field.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGE_NAMES = {'I': 'An Aois Àrsaidh', 'II': 'An Aois Ailein', 'III': 'An Aois Naomh', 'IV': 'An Aois Scaraidh',
             'V': 'An Aois Choigreach', 'VI': 'An Aois Rìoghachd', 'VII': 'An Aois Dhubhain'}
MAX_TOLD = 6          # events named in a note; canon events first, then in the order of the annals


def gazetteer():
    out = {}
    d = os.path.join(HERE, 'gazetteer')
    for f in sorted(os.listdir(d)):
        if re.match(r'out_\d+\.json$', f):
            for k, v in json.load(open(os.path.join(d, f), encoding='utf-8')).items():
                out[int(k)] = v
    return out


def short_date(date):
    m = re.search(r'\b([A-Z]{2})\s+(-?[\d,]+)', date or '')
    return '%s %s' % (m.group(1), m.group(2)) if m else (date or '')


def sentence(text):
    text = re.sub(r'\s+', ' ', text or '').strip().rstrip(';,:')
    if not text:
        return ''
    if text[0].islower():
        text = text[0].upper() + text[1:]
    if not re.search(r'[.!?]["”’)]?$', text):
        text += '.'
    return text


def notes(burg_ids):
    """{burg id: note} for the burgs the gazetteer tells of."""
    sys.path.insert(0, os.path.join(ROOT, 'eras', 'quality'))
    import names_convert  # noqa: E402
    conv = names_convert.Converter('master')
    gaz = gazetteer()
    events = json.load(open(os.path.join(HERE, 'annals_dated.json'), encoding='utf-8'))
    at = {}
    for e in events:
        if (e.get('place') or '').startswith('burg:'):
            at.setdefault(int(e['place'][5:]), []).append(e)
    out = {}
    for i in burg_ids:
        g = gaz.get(i)
        if not g:
            continue
        parts = [conv.convert(g.get('history') or '', 'burg %d' % i)]
        if g.get('known_for'):
            parts.append('Known for ' + conv.convert(g['known_for'], 'burg %d' % i))
        age = AGE_NAMES.get(g.get('founded_age'))
        if age:
            by = conv.convert(g.get('founded_by') or '', 'burg %d' % i).strip()
            parts.append('Founded in %s%s' % (age, ' by ' + by if by else ''))
        evs = at.get(i, [])
        pick = [e for e in evs if e.get('canon')][:MAX_TOLD]
        pick += [e for e in evs if e not in pick][:MAX_TOLD - len(pick)]
        pick.sort(key=lambda e: evs.index(e))
        text = ' '.join(s for s in (sentence(p) for p in parts) if s)
        if pick:
            text += ' Told of in: ' + '; '.join('%s (%s)' % (e['title'].rstrip('.'), short_date(e['date'])) for e in pick) + '.'
        out[i] = text.strip()
    return out


def apply(lines, L_BURGS=15):
    """Write the notes into the burgs record of the map's lines (in place); returns how many burgs got one."""
    burgs = json.loads(lines[L_BURGS])
    ids = [b['i'] for b in burgs if isinstance(b, dict) and b.get('i') and not b.get('removed')]
    by = notes(ids)
    n = 0
    for b in burgs:
        if isinstance(b, dict) and b.get('i') in by:
            b['note'] = by[b['i']]
            n += 1
    text = json.dumps(burgs, ensure_ascii=False, separators=(',', ':'))
    lines[L_BURGS] = re.sub('[\ud800-\udfff]', lambda m: '\\u%04x' % ord(m.group()), text)
    return n
