"""
build_pool.py -- assemble ../albums.json, the pool of release dates the reckoning draws on.

    python build_pool.py          (from this folder)

Two lists of artists, every date looked up on the web with its source:

    the owner's own list     g1-g5.json, c1-c6.json  (Rush, Van Halen, Savatage ... Sinatra, the Treyarch
                             composers, Panda Eyes, LudoWic)
    our top 100 rock and     r1-r9.json, for the artists of top100_rock_metal.json (aggregate_top100.py)
    metal artists            not already on the owner's list
    the overlap, re-checked  verify_overlap.json: the 13 artists on both lists, every date searched again;
                             its corrections and additions win

A record listed twice (same artist and title, ignoring case and punctuation) is kept once, with its most
precise date; where two sources give different days, the overlap check wins, then the earlier file.
Which album makes which date of the annals is not recorded anywhere (the owner's rule).
"""
import glob
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = ['verify_overlap'] + ['g%d' % i for i in range(1, 6)] + ['c%d' % i for i in range(1, 7)] + ['r%d' % i for i in range(1, 10)]


def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).replace(' and ', ' ').strip()


def main():
    pool, where = {}, {}
    for name in ORDER:
        for e in json.load(open(os.path.join(HERE, name + '.json'), encoding='utf-8')):
            d = str(e.get('date') or '')
            if not re.match(r'^\d{4}(-\d{2}(-\d{2})?)?$', d):
                continue
            k = (norm(e['artist']).replace('the ', ''), norm(e['album']))
            rec = {'artist': e['artist'], 'album': e['album'], 'date': d, 'kind': e.get('kind', ''), 'source': e.get('source', '')}
            if k not in pool or len(d) > len(pool[k]['date']) and d.startswith(pool[k]['date']):
                pool[k] = rec
                where[k] = name
    out = sorted(pool.values(), key=lambda r: (r['date'], r['artist'], r['album']))
    json.dump(out, open(os.path.join(os.path.dirname(HERE), 'albums.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    day = sum(1 for r in out if len(r['date']) == 10)
    print('albums.json: %d records by %d artists, %d dated to the day, years %s-%s'
          % (len(out), len({r['artist'] for r in out}), day, out[0]['date'][:4], out[-1]['date'][:4]))


if __name__ == '__main__':
    main()
