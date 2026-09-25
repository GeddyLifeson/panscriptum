"""
event_links.py -- typed links between annals events, both ways, and the events' categories.

Any annals event, master or era, may carry
    "category": one of CATEGORIES
    "links": [{"to": "<event id>", "type": one of TYPES, "note": "a few words (optional)"}, ...]
The reverse link is added to the target automatically, with the type's incoming label. The types and their
labels follow the Atlas timeline (ERA_PLAN.md, modelled on the Middle-earth interactive map's timeline):

    type      arrow  outgoing          incoming
    cause     →      Leads to          Caused by
    sequel    ←      Follows from      Leads to
    parallel  ⇄      At the same time  At the same time
    legacy    ⇝      Legacy            Legacy of
    location  ○      Same place        Same place
    person    ◇      Same person       Same person
    fulfils   ✦      Fulfils           Fulfilled by
    answers   ↩      Answers           Answered by

resolve(universe) takes every event that can be linked ({id: event}, each with age, date, title and 'master'
for a master event) and returns {id: [link, ...]} with both directions, each
    {"to", "type", "dir": "out" | "in", "arrow", "label", "note"?, "age", "era", "date", "year", "title", "master"}
footnote_html() prints one entry's links for the PDFs. build_book.py (the master) and ../eras/build_era.py (the
era legendaria and the Atlas data) both use this module.
"""
import html
import re

TYPES = {
    'cause': ('→', 'Leads to', 'Caused by'),
    'sequel': ('←', 'Follows from', 'Leads to'),
    'parallel': ('⇄', 'At the same time', 'At the same time'),
    'legacy': ('⇝', 'Legacy', 'Legacy of'),
    'location': ('○', 'Same place', 'Same place'),
    'person': ('◇', 'Same person', 'Same person'),
    'fulfils': ('✦', 'Fulfils', 'Fulfilled by'),
    'answers': ('↩', 'Answers', 'Answered by'),
}
CATEGORIES = {
    'rulers': 'rulers and houses',
    'war': 'war',
    'faith': 'faith and myth',
    'coal': 'coal and the vein',
    'trade': 'trade and work',
    'land': 'land and sea',
    'law': 'law and learning',
    'humans': 'the humans',
    'coalblood': 'the coal-blood',
}


def problems(ev):
    """What is wrong with one event's category and links, as written (targets are checked by the caller)."""
    out = []
    i = ev.get('id')
    if 'category' in ev and ev['category'] not in CATEGORIES:
        out.append('%s: category "%s" is not one of %s' % (i, ev['category'], ', '.join(CATEGORIES)))
    links = ev.get('links')
    if links is None:
        return out
    if not isinstance(links, list):
        return out + ['%s: "links" is a list of {"to": id, "type": T}' % i]
    for ln in links:
        if not isinstance(ln, dict) or not ln.get('to') or set(ln) - {'to', 'type', 'note'}:
            out.append('%s: a link is {"to": id, "type": T, "note": optional words}: %s' % (i, ln))
        elif ln.get('type') not in TYPES:
            out.append('%s: link to %s has type "%s", not one of %s' % (i, ln['to'], ln.get('type'), ', '.join(TYPES)))
        elif ln['to'] == i:
            out.append('%s: links to itself' % i)
    return out


def resolve(universe, display_year=None):
    """-> {id: [resolved link, ...]} for every event with a link either way. A link whose target is not in the
    universe, or whose type is unknown, is left out here (the validators report it)."""
    def card(t, typ, d, note):
        e = universe[t]
        arrow, out_l, in_l = TYPES[typ]
        c = {'to': t, 'type': typ, 'dir': d, 'arrow': arrow, 'label': out_l if d == 'out' else in_l,
             'age': e.get('age'), 'era': e.get('era'), 'date': e.get('date'), 'title': e.get('title'),
             'master': bool(e.get('master', True))}
        if note:
            c['note'] = note
        if display_year and e.get('y') is not None:
            c['year'] = display_year(e)
        return c

    def good(i, ln):
        return isinstance(ln, dict) and ln.get('to') in universe and ln['to'] != i and ln.get('type') in TYPES
    stated = {(i, ln['to'], ln['type']) for i, e in universe.items() for ln in e.get('links') or [] if good(i, ln)}
    out = {}
    for i, e in universe.items():
        for ln in e.get('links') or []:
            if not good(i, ln):
                continue
            t, typ = ln['to'], ln['type']
            out.setdefault(i, []).append(card(t, typ, 'out', ln.get('note')))
            if (t, i, typ) not in stated:            # the target names the same link itself: no second copy
                out.setdefault(t, []).append(card(i, typ, 'in', ln.get('note')))
    return out


def anchor(eid):
    return 'ev-' + re.sub(r'[^A-Za-z0-9_-]', '-', eid)


def footnote_html(links, here_age=None, other_book=None, age_name=None):
    """One annals entry's links as a PDF footnote (<span class="fn">, which build_pdf.py floats to the page foot).
    A link into this book (here_age None: the master, where every master event stands; else the same age) jumps to
    the entry; a link into another age prints '→ <age in Dia-thìris>, <year>' and opens that age's own book:
    other_book(age) gives the href (build_era.py makes it a relative GoToR link)."""
    rows = []
    for ln in links:
        title = html.escape(ln.get('title') or ln['to'], quote=False)
        note = ' (%s)' % html.escape(ln['note'], quote=False) if ln.get('note') else ''
        head = '%s %s' % (ln['arrow'], ln['label'])
        if here_age is None or ln['age'] == here_age:
            rows.append('%s <a href="#%s"><em>%s</em>, %s</a>%s' % (head, anchor(ln['to']), title, ln.get('date') or '', note))
        elif other_book:
            where = '%s, %s' % (age_name(ln['age']) if age_name else ln['age'], ln.get('year') or '')
            rows.append('%s <em>%s</em> <a href="%s#%s">→ %s</a>%s' % (head, title, other_book(ln['age']), anchor(ln['to']),
                                                                       html.escape(where.rstrip(', '), quote=False), note))
    return '<span class="fn fl">%s.</span>' % '; '.join(rows) if rows else ''
