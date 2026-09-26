"""ask.py -- full-text search over the whole record: eras/quality/rodos.sqlite (SQLite FTS5).

    python ask.py "coal-blood Muileann"        # top 10 hits, each with its id
    python ask.py "Aois Arsaidh" -n 25 --kind annal
    python ask.py --rebuild                    # rebuild the index (also done when it is missing)

Indexed: master annals_dated.json, every age's era annals (dated when the age dates, as written when not), master and
era books and appendices (one row per ## / ### section, id "book/<file>#<anchor>"), houses.json, the master and era
gazetteers (id "burg:N"), NAMES, PEOPLE and THREADS. Accents are ignored in matching ("Arsaidh" finds "Àrsaidh").
Query syntax is FTS5 (AND, OR, NOT, "a phrase", prefix*); a query FTS5 cannot parse is searched word by word.
"""
import argparse
import glob
import json
import os
import re
import sqlite3

import qlib as q

DB = os.path.join(q.Q, 'rodos.sqlite')


def sections(path, src):
    """Split a Markdown file at its #/##/### headings."""
    out, head, buf = [], os.path.basename(path), []
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^#{1,3} (.+)$', line)
        if m:
            if ''.join(buf).strip():
                out.append((head, buf))
            head, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    out.append((head, buf))
    return [('%s/%s#%s' % (src, os.path.basename(path), q.B.heading_anchor(h)), h, ''.join(b)) for h, b in out if ''.join(b).strip()]


def annal_rows(events, kind):
    return [(e['id'], kind, e.get('age', ''), e.get('title', ''), '%s %s %s' % (e.get('date', ''), e.get('body', ''), e.get('kind', '')))
            for e in events]


def gazetteer_rows(files, names, kind):
    rows = []
    for f in files:
        for bid, g in json.load(open(f, encoding='utf-8')).items():
            txt = ' '.join(str(g.get(k, '')) for k in ('name', 'founded_by', 'history', 'known_for'))
            rows.append(('burg:%s' % bid, kind, q.rel(f), g.get('name') or names.get(str(bid), ''), txt))
    return rows


def rows():
    out = annal_rows(json.load(open(os.path.join(q.LEG, 'annals_dated.json'), encoding='utf-8')), 'annal')
    for k in q.KEYS:
        d = q.B.age_dir(k)
        if not os.path.isdir(os.path.join(d, 'annals')):
            continue
        try:
            evs = [e for e in q.B.date_era(k)[0] if not e['master']]
        except (q.B.EraError, AssertionError):
            evs = q.B.raw_era_events(k)
        out += annal_rows(evs, 'era-annal')
        for sub, kind in (('book', 'era-book'), ('appendices', 'era-appendix')):
            for f in sorted(glob.glob(os.path.join(d, sub, '*.md'))):
                out += [(i, kind, k, h, b) for i, h, b in sections(f, 'age_%s/%s' % (k, sub))]
        out += gazetteer_rows(sorted(glob.glob(os.path.join(d, 'gazetteer', '*.json'))), {}, 'era-gazetteer')
    for sub, kind in (('book', 'book'), ('appendices', 'appendix')):
        for f in sorted(glob.glob(os.path.join(q.LEG, sub, '*.md'))):
            out += [(i, kind, '', h, b) for i, h, b in sections(f, sub)]
    for h in json.load(open(os.path.join(q.LEG, 'appendices', 'houses.json'), encoding='utf-8')):
        out.append(('house:' + h.get('house', ''), 'house', '', h.get('house', ''), json.dumps(h, ensure_ascii=False)))
    world = json.load(open(os.path.join(q.LEG, 'world.json'), encoding='utf-8'))
    names = {str(b['id']): b.get('name', '') for b in world['burgs'] if isinstance(b, dict)}
    out += gazetteer_rows(sorted(glob.glob(os.path.join(q.LEG, 'gazetteer', 'out_*.json'))), names, 'gazetteer')
    reg = lambda f, key: json.load(open(os.path.join(q.ERAS, f), encoding='utf-8')).get(key, [])  # noqa: E731
    for e in reg('NAMES.json', 'names') + reg('NAMES.json', 'ambiguous'):
        out.append(('name:' + e.get('dt', ''), 'name', e.get('kind', ''), '%s = %s' % (e.get('dt', ''), e.get('en', '')),
                    ' '.join(str(e.get(k, '')) for k in ('gloss', 'first', 'status', 'note')) + ' ' + ' '.join(e.get('variants') or [])))
    for p in reg('PEOPLE.json', 'people'):
        out.append(('person:' + p.get('id', ''), 'person', '', p.get('name', ''), json.dumps(p, ensure_ascii=False)))
    for t in reg('THREADS.json', 'threads'):
        out.append(('thread:' + t.get('id', ''), 'thread', '', '%s = %s' % (t.get('dt', ''), t.get('gloss', '')), t.get('description', '')))
    return out


def build():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE VIRTUAL TABLE docs USING fts5(id UNINDEXED, kind UNINDEXED, src UNINDEXED, title, body, "
                "tokenize='unicode61 remove_diacritics 2')")
    rs = rows()
    con.executemany('INSERT INTO docs VALUES (?,?,?,?,?)', rs)
    con.commit()
    return len(rs)


def ask(query, n=10, kind=None):
    con = sqlite3.connect(DB)
    sql = ("SELECT id, kind, src, title, snippet(docs, 4, '[', ']', ' … ', 18) FROM docs WHERE docs MATCH ?%s "
           "ORDER BY bm25(docs, 5.0, 1.0) LIMIT ?" % (' AND kind = ?' if kind else ''))
    args = lambda qq: [qq] + ([kind] if kind else []) + [n]  # noqa: E731
    try:
        return con.execute(sql, args(query)).fetchall()
    except sqlite3.OperationalError:
        return con.execute(sql, args(' '.join('"%s"' % w.replace('"', '') for w in query.split()))).fetchall()


def main():
    ap = argparse.ArgumentParser(description='Search the whole record.')
    ap.add_argument('query', nargs='?')
    ap.add_argument('-n', type=int, default=10)
    ap.add_argument('--kind', help='annal, era-annal, book, era-book, appendix, era-appendix, gazetteer, era-gazetteer, '
                                   'house, name, person, thread')
    ap.add_argument('--rebuild', action='store_true')
    a = ap.parse_args()
    if a.rebuild or not os.path.exists(DB):
        print('indexed %d rows into %s' % (build(), q.rel(DB)))
    if a.query:
        for i, kind, src, title, snip in ask(a.query, a.n, a.kind):
            print('%-28s %-13s %s\n    %s\n    %s' % (i, kind, src, title, re.sub(r'\s+', ' ', snip)))


if __name__ == '__main__':
    main()
