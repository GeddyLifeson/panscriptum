"""qlib.py -- what the quality tools share: RODAIS paths, the check_era modules, targets and prose units.

A target is a file, a directory, an age key (I..VII: that age's writer files), 'eras' (every age's writer files)
or 'master' (legendarium/ annals, books, appendices, gazetteer). prose(path) splits a file into (where, text) units:
a line of Markdown (where = line number), or a prose string of JSON (where = event id / burg id + key).
"""
import glob
import json
import os
import sys

Q = os.path.dirname(os.path.abspath(__file__))
ERAS = os.path.dirname(Q)
ROOT = os.path.dirname(ERAS)
sys.path.insert(0, ERAS)
sys.path.insert(0, ROOT)
import check_era as C  # noqa: E402  (brings build_era as C.B, glosses as C.G, rodais_engine as C.R, event_links as C.EL)

B, G, R, EL = C.B, C.G, C.R, C.EL
LEG = B.LEG
KEYS = B.KEYS
MASTER_PATS = ('annals/age_*.json', 'book/*.md', 'appendices/*.md', 'gazetteer/out_*.json')
WRITER_PATS = ('annals/*.json', 'book/*.md', 'gazetteer/*.json', 'appendices/*.md', 'places.json', 'front.json')
PROSE_KEYS = {'title', 'body', 'history', 'known_for', 'note', 'description', 'founded_by', 'en', 'text', 'gloss'}
SKIP_KEYS = {'id', 'to', 'type', 'place', 'kind', 'category', 'dt', 'ro', 'src', 'told_in', 'status', 'colour'}


def writer_files(k):
    d = B.age_dir(k)
    out = []
    for pat in WRITER_PATS:
        out += [f for f in sorted(glob.glob(os.path.join(d, pat))) if not f.endswith('_master.json')]
    return out


def targets(arg):
    if arg == 'master':
        return [f for pat in MASTER_PATS for f in sorted(glob.glob(os.path.join(LEG, pat)))]
    if arg == 'eras':
        return [f for k in KEYS for f in writer_files(k)]
    if arg in KEYS:
        return writer_files(arg)
    if os.path.isdir(arg):
        return sorted(os.path.join(dp, f) for dp, _, fs in os.walk(arg) for f in fs if f.endswith(('.md', '.json')))
    if os.path.isfile(arg):
        return [arg]
    sys.exit('no such target: %s (a file, a directory, I..VII, eras or master)' % arg)


def _walk(x, path, out):
    if isinstance(x, dict):
        tag = x.get('id') if isinstance(x.get('id'), str) else path
        for k, v in x.items():
            if k in SKIP_KEYS:
                continue
            if isinstance(v, str):
                if k in PROSE_KEYS or len(v.split()) >= 5:
                    out.append(('%s.%s' % (tag, k), v))
            else:
                _walk(v, '%s.%s' % (tag, k) if tag == path else tag, out)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            if isinstance(v, str) and len(v.split()) >= 5:
                out.append(('%s[%d]' % (path, i), v))
            else:
                _walk(v, '%s[%d]' % (path, i), out)


def prose(path):
    """[(where, text)] of one file."""
    if path.endswith('.json'):
        out = []
        _walk(json.load(open(path, encoding='utf-8')), '$', out)
        return [(w.lstrip('$.'), t) for w, t in out]
    fence, out = False, []
    for i, line in enumerate(open(path, encoding='utf-8'), 1):
        if line.startswith('```'):
            fence = not fence
        elif not fence and line.strip():
            out.append((str(i), line.rstrip('\n')))
    return out


def words(text):
    return len(C.WORD.findall(text))


def rel(path):
    return os.path.relpath(path, ROOT)
