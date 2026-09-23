"""
aggregate_top100.py -- our own top 100 rock and metal artists, from the published rankings in rock_lists_*.json.

    python aggregate_top100.py          (from this folder; writes top100_rock_metal.json)

Method (a normalized Borda count):
- A list counts only if at least 30 of its places were confirmed from the published page (partial transcriptions
  would otherwise over-weight the few names found).
- On a list of N places, the artist at place r scores (N - r + 1) / N: 1.0 for first, 1/N for last. So every list
  is worth the same, whatever its length.
- General "greatest artists" lists (Rolling Stone, VH1) count only their rock and metal artists (the
  rock_or_metal flag); their places are kept as published.
- An artist's score is the sum over lists. Ties are broken by the number of lists naming the artist, then by the
  best single place.
"""
import glob
import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_CONFIRMED = 30
ALIASES = {'guns n roses': "Guns N' Roses", 'guns and roses': "Guns N' Roses", 'acdc': 'AC/DC', 'ac dc': 'AC/DC',
           'jimi hendrix experience': 'Jimi Hendrix', 'the jimi hendrix experience': 'Jimi Hendrix',
           'motorhead': 'Motörhead', 'blue oyster cult': 'Blue Öyster Cult', 'kiss': 'Kiss',
           'bruce springsteen and the e street band': 'Bruce Springsteen', 'tom petty and the heartbreakers': 'Tom Petty',
           'creedence clearwater revival': 'Creedence Clearwater Revival', 'ccr': 'Creedence Clearwater Revival',
           'ozzy': 'Ozzy Osbourne', 'the police': 'The Police', 'rage against the machine': 'Rage Against the Machine',
           'red hot chili peppers': 'Red Hot Chili Peppers', 'the red hot chili peppers': 'Red Hot Chili Peppers',
           'emerson lake and palmer': 'Emerson, Lake & Palmer', 'crosby stills nash and young': 'Crosby, Stills, Nash & Young',
           'crosby stills and nash': 'Crosby, Stills, Nash & Young', 'parliament funkadelic': 'Parliament-Funkadelic',
           'deep purple': 'Deep Purple', 'dio': 'Dio', 'ronnie james dio': 'Dio', 'queensryche': 'Queensrÿche'}


def norm(a):
    s = unicodedata.normalize('NFD', a).encode('ascii', 'ignore').decode().lower()
    s = s.replace('&', 'and')
    s = re.sub(r"[^a-z0-9 ]", ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'^the ', '', s)
    return s


def main():
    lists = []
    for f in sorted(glob.glob(os.path.join(HERE, 'rock_lists_*.json'))):
        lists += json.load(open(f, encoding='utf-8'))
    used, dropped = [], []
    score, names, count, best, where = {}, {}, {}, {}, {}
    for L in lists:
        es = [e for e in L['entries'] if e.get('artist') and e.get('rank')]
        if len(es) < MIN_CONFIRMED:
            dropped.append('%s (%s %s): %d confirmed places' % (L['list'], L.get('publisher'), L.get('year'), len(es)))
            continue
        n = max(e['rank'] for e in L['entries'] if e.get('rank'))
        used.append('%s (%s %s), %d places' % (L['list'], L.get('publisher'), L.get('year'), n))
        for e in es:
            if e.get('rock_or_metal') is False:
                continue
            k = norm(e['artist'])
            k = norm(ALIASES.get(k, ALIASES.get('the ' + k, e['artist'])))
            names.setdefault(k, ALIASES.get(norm(e['artist']), e['artist']))
            score[k] = score.get(k, 0) + (n - e['rank'] + 1) / n
            count[k] = count.get(k, 0) + 1
            best[k] = min(best.get(k, 999), e['rank'])
            where.setdefault(k, []).append('%s %s #%d' % (L.get('publisher'), L.get('year'), e['rank']))
    order = sorted(score, key=lambda k: (-score[k], -count[k], best[k]))
    top = [{'rank': i + 1, 'artist': names[k], 'score': round(score[k], 3), 'lists': count[k], 'places': where[k]}
           for i, k in enumerate(order[:100])]
    out = {'method': __doc__.strip().split('\n\n', 1)[1], 'lists_used': used, 'lists_dropped': dropped,
           'top100': top, 'next_10': [names[k] for k in order[100:110]]}
    json.dump(out, open(os.path.join(HERE, 'top100_rock_metal.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('used:', *used, sep='\n  ')
    print('dropped:', *dropped, sep='\n  ')
    for t in top:
        print('%3d %-32s %.2f %d' % (t['rank'], t['artist'], t['score'], t['lists']))


if __name__ == '__main__':
    main()
