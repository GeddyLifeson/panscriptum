#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spoken pronunciations of the Dia-thìris proper nouns, for the Atlas glossary.

  python3 tools/gen_name_audio.py                  # record everything still missing (resumable)
  python3 tools/gen_name_audio.py --list           # print the list (NAMES.json first, then by mentions) and stop
  python3 tools/gen_name_audio.py --limit 150      # record at most 150 new clips this run
  python3 tools/gen_name_audio.py --manifest-only  # rebuild manifest.json from the files on disk

What is recorded (deduped on the exact dt spelling):
  1. every `dt` in eras/NAMES.json "names"
  2. every town (burg) in the gazetteer (legendarium/world.json burgs with a legendarium/gazetteer/out_*.json entry)
  3. every person in eras/PEOPLE.json whose name is Dia-thìris: "(glosses)" are dropped, "A, B" gives two names,
     and a name with any English word (human names such as "Edmund Harrow", "the fosterling") is skipped.
  NAMES.json entries come first, then the rest by how often they are mentioned in the annals.

Voice: the same as the Polyglot Voyager Dia-thìris (gr) clips: OmniVoice (k2-fsa/OmniVoice) with its Irish model
(language "ga"), grave accents rewritten as Irish acutes, one speaker cloned from omni_gr_man.wav, 16 diffusion steps,
peak-normalised, silence trimmed. Needs the model already in the Hugging Face cache (nothing is downloaded) and ffmpeg.

Output: Diathir_Atlas/audio/names/<slug>.mp3 (mono, 24 kHz, 32 kb/s) and Diathir_Atlas/audio/names/manifest.json
{dt: "<slug>.mp3"}. A clip already on disk is never re-recorded; the manifest is rewritten every 25 clips.
"""
import os, sys, re, json, glob, time, argparse, unicodedata, subprocess, collections, warnings
warnings.filterwarnings('ignore')
os.environ.setdefault('HF_HUB_OFFLINE', '1')

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # RODAIS
PG = '/home/user/Polyglot-Game'
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=os.path.join(HERE, 'Diathir_Atlas', 'audio', 'names'))
ap.add_argument('--ref', default=os.path.join(PG, 'tools', 'voices', 'omni_gr_man.wav'))
ap.add_argument('--ref-text', default=os.path.join(PG, 'tools', 'voices', 'omni_gr_man.txt'))
ap.add_argument('--steps', type=int, default=16)
ap.add_argument('--bitrate', default='32k')
ap.add_argument('--limit', type=int, default=0, help='record at most this many new clips (0 = all)')
ap.add_argument('--only', default='', help='comma-separated dt forms to (re-)record')
ap.add_argument('--list', action='store_true')
ap.add_argument('--manifest-only', action='store_true')
args = ap.parse_args()

# ---------------------------------------------------------------- the list
def load(p): return json.load(open(os.path.join(HERE, p), encoding='utf-8'))
def nfc(s): return unicodedata.normalize('NFC', s).strip()

ENGLISH = set('''the of son girl lad eastern fosterling fourth name red hill knapper's king grandfather great-grandfather
 abel agnes alice amos anne annie arthur charles christina clara colin daniel david dodds edgar edmund edward edwin ellen
 enoch ferguson fraser george hannah harry henry hugh james jenny joe jonas joseph josiah lionel margaret marion martha
 mary matthew meikle nathan nathaniel ned nell obadiah oliver oscar osgood oswin owen peg peggy peter robert ruth sam
 samuel sarah silas thomas tom walter will william hale ashe'''.split())

def is_dt_person(n):
    toks = n.split()
    return toks and not any(t.lower().strip(".,'") in ENGLISH or t.endswith("'s") for t in toks)

def collect():
    names = [nfc(n['dt']) for n in load('eras/NAMES.json')['names'] if n.get('dt')]
    w = load('legendarium/world.json')
    gaz = set()
    for f in glob.glob(os.path.join(HERE, 'legendarium', 'gazetteer', 'out_*.json')):
        gaz |= set(json.load(open(f, encoding='utf-8')))
    towns = [nfc(b['name']) for b in w['burgs'] if str(b['id']) in gaz and b.get('name')]
    people = []
    for p in load('eras/PEOPLE.json')['people']:
        for part in re.sub(r'\([^)]*\)', '', p['name']).split(','):
            part = nfc(re.sub(r'\s+', ' ', part))
            if part and is_dt_person(part): people.append(part)
    # mentions across the annals (every age's text)
    corpus = []
    for f in [os.path.join(HERE, 'legendarium', 'annals_dated.json')] + sorted(glob.glob(os.path.join(HERE, 'eras', 'age_*', 'annals_dated.json'))):
        for e in json.load(open(f, encoding='utf-8')):
            corpus.append(' '.join(str(e.get(k, '')) for k in ('title', 'body')))
    corpus = nfc('\n'.join(corpus))
    def mentions(s): return len(re.findall(r'(?<!\w)' + re.escape(s) + r'(?!\w)', corpus))
    seen, first = set(), []
    for n in names:
        if n not in seen: seen.add(n); first.append(n)
    rest = []
    for n in towns + people:
        if n not in seen: seen.add(n); rest.append(n)
    rest.sort(key=lambda n: -mentions(n))
    return first, rest

def slug(s, taken):
    a = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    a = re.sub(r'[^a-z0-9]+', '-', a).strip('-') or 'name'
    b, i = a, 2
    while b in taken and taken[b] != s:
        b = '%s-%d' % (a, i); i += 1
    taken[b] = s
    return b

first, rest = collect()
order = first + rest
os.makedirs(args.out, exist_ok=True)
man_path = os.path.join(args.out, 'manifest.json')
# keep the slugs of anything already recorded, so reruns never rename files
taken, files = {}, {}
if os.path.exists(man_path):
    for dt, f in json.load(open(man_path, encoding='utf-8')).items():
        taken[f[:-4]] = dt; files[dt] = f
for n in order:
    if n not in files: files[n] = slug(n, taken) + '.mp3'

def write_manifest():
    m = {n: files[n] for n in order if os.path.exists(os.path.join(args.out, files[n]))}
    json.dump(m, open(man_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    return m

if args.list:
    for i, n in enumerate(order):
        print('%4d %s %s -> %s' % (i + 1, 'N' if i < len(first) else ' ', n, files[n]))
    print(len(first), 'NAMES.json +', len(rest), 'places/people =', len(order))
    sys.exit()
if args.manifest_only:
    print(len(write_manifest()), 'clips in manifest'); sys.exit()

only = set(nfc(x) for x in args.only.split(',') if x.strip())
todo = [n for n in order if n in only] if only else [n for n in order if not os.path.exists(os.path.join(args.out, files[n]))]
if args.limit: todo = todo[:args.limit]
print(len(order), 'names;', len(todo), 'to record', flush=True)
if not todo: print(len(write_manifest()), 'clips in manifest'); sys.exit()

# ---------------------------------------------------------------- the voice (as Polyglot-Game tools/gen_audio.py --backend omnivoice)
import numpy as np, soundfile as sf, torch
from omnivoice import OmniVoice
from omnivoice.models.omnivoice import OmniVoiceGenerationConfig
torch.set_num_threads(os.cpu_count() or 4)
dev = 'cuda:0' if torch.cuda.is_available() else 'cpu'
model = OmniVoice.from_pretrained('k2-fsa/OmniVoice', device_map=dev, dtype=torch.float16 if dev != 'cpu' else torch.float32)
prompt = model.create_voice_clone_prompt(ref_audio=args.ref, ref_text=open(args.ref_text, encoding='utf-8').read().strip())
cfg = OmniVoiceGenerationConfig(num_step=args.steps, postprocess_output=False)
SR = 24000

def acute(t):   # Dia-thìris is read by the Irish model: grave accents -> acutes
    return unicodedata.normalize('NFC', unicodedata.normalize('NFD', t).replace('̀', '́'))

def say(text):
    a = model.generate(text=acute(text) + '.', language='ga', voice_clone_prompt=prompt, generation_config=cfg)[0]
    a = np.asarray(a, dtype=np.float32)
    if not len(a): raise RuntimeError('empty audio')
    a = a / (np.abs(a).max() + 1e-9) * 0.9
    idx = np.where(np.abs(a) > 0.01)[0]
    if len(idx): a = a[max(0, idx[0] - 1200): min(len(a), idx[-1] + 2400)]
    return a

t0 = time.time()
tmp = os.path.join(args.out, '_tmp.wav')
for i, n in enumerate(todo):
    mp3 = os.path.join(args.out, files[n])
    try:
        sf.write(tmp, say(n), SR)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-ac', '1', '-ar', str(SR), '-c:a', 'libmp3lame',
                        '-b:a', args.bitrate, mp3 + '.part.mp3'], check=True)
        os.replace(mp3 + '.part.mp3', mp3)
    except Exception as e:
        print('FAIL', n, repr(e)[:100], flush=True)
    if i % 25 == 24 or i == len(todo) - 1:
        write_manifest()
        el = time.time() - t0
        print('  %d/%d  %ds  (%.1fs a clip)' % (i + 1, len(todo), el, el / (i + 1)), flush=True)
if os.path.exists(tmp): os.remove(tmp)
print('DONE -', len(write_manifest()), 'clips in manifest')
