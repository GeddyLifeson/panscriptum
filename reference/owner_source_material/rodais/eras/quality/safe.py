"""safe.py -- snapshot an age's writer files before a bulk edit, and put them back.

    python safe.py snap IV [--note "before the dash sweep"]   # eras/quality/snapshots/age_IV_<stamp>.tar.gz
    python safe.py list [IV]
    python safe.py restore age_IV_20260925-101500.tar.gz [--dry]

Writer files are eras/age_<K>/ annals (not the master seed), book/, gazetteer/, appendices/, places.json, front.json.
The last KEEP snapshots of each age are kept. A restore first snapshots the files as they stand (note "pre-restore"),
then writes back every file of the snapshot; files made since the snapshot are listed and left alone.
"""
import argparse
import glob
import io
import os
import sys
import tarfile
import time

import qlib as q

SNAPS = os.path.join(q.Q, 'snapshots')
KEEP = 20


def snaps(k=None):
    return sorted(glob.glob(os.path.join(SNAPS, 'age_%s_*.tar.gz' % (k or '*'))), key=os.path.getmtime)


def snap(k, note=''):
    os.makedirs(SNAPS, exist_ok=True)
    d = q.B.age_dir(k)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    path = os.path.join(SNAPS, 'age_%s_%s.tar.gz' % (k, stamp))
    n = 1
    while os.path.exists(path):
        path = os.path.join(SNAPS, 'age_%s_%s-%d.tar.gz' % (k, stamp, n))
        n += 1
    files = q.writer_files(k)
    with tarfile.open(path, 'w:gz') as tar:
        for f in files:
            tar.add(f, arcname=os.path.relpath(f, d))
        if note:
            info = tarfile.TarInfo('.note')
            data = note.encode('utf-8')
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    for old in snaps(k)[:-KEEP]:
        os.remove(old)
    print('snapshot %s: %d files%s' % (q.rel(path), len(files), ' (%s)' % note if note else ''))
    return path


def note_of(path):
    with tarfile.open(path) as tar:
        try:
            return tar.extractfile('.note').read().decode('utf-8')
        except KeyError:
            return ''


def restore(name, dry=False):
    path = name if os.path.exists(name) else os.path.join(SNAPS, os.path.basename(name))
    if not os.path.exists(path):
        sys.exit('no snapshot %s (see: safe.py list)' % name)
    k = os.path.basename(path).split('_')[1]
    d = q.B.age_dir(k)
    with tarfile.open(path) as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name != '.note']
        bad = [m.name for m in members if m.name.startswith('/') or '..' in m.name.split('/')]
        if bad:
            sys.exit('refusing unsafe paths: %s' % ', '.join(bad))
        names = {m.name for m in members}
        new = sorted(os.path.relpath(f, d) for f in q.writer_files(k) if os.path.relpath(f, d) not in names)
        if dry:
            print('would restore %d files into %s' % (len(members), q.rel(d)))
        else:
            snap(k, 'pre-restore of %s' % os.path.basename(path))
            for m in members:
                tar.extract(m, d)
            print('restored %d files into %s' % (len(members), q.rel(d)))
        for f in new:
            print('  not in the snapshot, left as it is: %s' % f)


def main():
    ap = argparse.ArgumentParser(description="Snapshot and restore an age's writer files.")
    ap.add_argument('cmd', choices=['snap', 'list', 'restore'])
    ap.add_argument('arg', nargs='?', help='age (snap, list) or snapshot file (restore)')
    ap.add_argument('--note', default='')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'snap':
        if a.arg not in q.KEYS:
            sys.exit('snap needs an age: %s' % ', '.join(q.KEYS))
        snap(a.arg, a.note)
    elif a.cmd == 'list':
        for p in snaps(a.arg):
            print('%s  %s  %s' % (os.path.basename(p), time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(p))), note_of(p)))
    else:
        restore(a.arg, a.dry)


if __name__ == '__main__':
    main()
