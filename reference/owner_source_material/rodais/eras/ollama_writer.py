#!/usr/bin/env python3
"""Write the missing era chapters with a local Ollama model.

Run from the rodais folder on a machine with Ollama:
    python3 eras/ollama_writer.py --model qwen2.5:32b            # every missing chapter, all ages
    python3 eras/ollama_writer.py --model qwen2.5:32b --age VII  # one age
    python3 eras/ollama_writer.py --list                         # show what is missing

For each chapter NN of age K that has no book/NN_*.md with a matching events/NN.json, it:
  1. reads the chapter's block in eras/age_<K>/PLAN.md, the neighbours' synopses, the end of the previous
     chapter if it exists, a voice sample from the master Book of the age, and the writers' rules;
  2. asks the model for a scene plan, then writes the chapter scene by scene (local models write better
     in ~1,000-word pieces), carrying the tail of each scene into the next;
  3. asks for the events sidecar as JSON and validates it;
  4. runs quality/tells_scan.py and quality/future_check.py and does one repair pass if they complain;
  5. writes book/NN_<slug>.md and events/NN.json. Existing chapters are never touched.
Resumable: rerun and it continues with what is still missing. Uses only the standard library.
"""
import argparse, unicodedata, json, os, re, subprocess, sys, textwrap, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGES = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
CH = re.compile(r'^\*\*(?:Ch\.? ?)?(\d{1,2})\.\s+(.*)$')
HOST = os.environ.get('OLLAMA_HOST', 'http://127.0.0.1:11434')


def read(p, n=None):
    try:
        t = open(p, encoding='utf-8').read()
    except OSError:
        return ''
    return t if n is None else t[:n]


def plan_chapters(k):
    """{NN: (title_line, block_text)} from the age's PLAN.md."""
    lines = read(os.path.join(HERE, f'age_{k}', 'PLAN.md')).splitlines()
    out, cur, buf = {}, None, []
    for ln in lines:
        m = CH.match(ln)
        if m or (cur and ln.startswith('#')):
            if cur:
                out[cur[0]] = (cur[1], '\n'.join(buf).strip())
            cur, buf = ((int(m.group(1)), m.group(2)) if m else None), []
            if m:
                buf.append(ln)
            continue
        if cur:
            buf.append(ln)
    if cur:
        out[cur[0]] = (cur[1], '\n'.join(buf).strip())
    return out


def done(k):
    d = os.path.join(HERE, f'age_{k}')
    book = {int(f[:2]): f for f in os.listdir(os.path.join(d, 'book')) if f[:2].isdigit()} if os.path.isdir(os.path.join(d, 'book')) else {}
    ev = {int(f[:2]) for f in os.listdir(os.path.join(d, 'events')) if f[:2].isdigit()} if os.path.isdir(os.path.join(d, 'events')) else set()
    return book, ev


def missing(k):
    book, ev = done(k)
    return [n for n in sorted(plan_chapters(k)) if not (n in book and n in ev)]


def ollama(model, prompt, system, num_predict=2400, temperature=0.8, fmt=None):
    body = {'model': model, 'prompt': prompt, 'system': system, 'stream': False,
            'options': {'num_predict': num_predict, 'temperature': temperature, 'num_ctx': 16384}}
    if fmt:
        body['format'] = fmt
    req = urllib.request.Request(HOST + '/api/generate', json.dumps(body).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=3600) as r:
        return json.loads(r.read())['response'].strip()


def clean_title(title):
    t = title.split('**')[0].split('·')[0].split('—')[0].split('[')[0].split('(')[0]
    return re.sub(r'[*_]', '', t).strip().rstrip('.')


def slug(title):
    t = unicodedata.normalize('NFKD', clean_title(title))
    t = re.sub(r'^Of the |^Of ', '', t)
    s = re.sub(r'[^a-z0-9]+', '_', t.lower().encode('ascii', 'ignore').decode()).strip('_')
    return s[:60] or 'chapter'


def run(cmd):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)[-3000:]


def rules():
    g = read(os.path.join(HERE, 'WRITERS_GUIDE.md'))
    keep = []
    for sec in ('## 0.', '## 8.', '## 13.'):
        i = g.find(sec)
        if i >= 0:
            j = g.find('\n## ', i + 5)
            keep.append(g[i:j if j > 0 else None])
    tells = read(os.path.join(HERE, 'quality', 'TELLS_FOR_WRITERS.md'), 4000)
    return '\n\n'.join(keep)[:9000] + '\n\n' + tells


SYSTEM = """You are writing one chapter of a long historical novel about the island of Dia-thìr, in the high,
plain recollection voice of an old chronicle retold as a story (think Tolkien's Silmarillion tales told at
novel length): concrete scenes, speech, weather, work, people, consequence. No modern words, no meta
commentary, no talk of "the record" or "sources", no summaries of themes, no foreshadowing of anything after
this chapter's dates. Proper nouns in Dia-thìris exactly as given; human names as given. Never use the word
obsidian. Output only the prose asked for."""


def write_chapter(k, n, model, verbose=True):
    chs = plan_chapters(k)
    title, block = chs[n]
    prev_syn = chs.get(n - 1, ('', ''))[1][:1500]
    next_syn = chs.get(n + 1, ('', ''))[1][:1000]
    book, _ = done(k)
    prev_tail = read(os.path.join(HERE, f'age_{k}', 'book', book[n - 1]))[-2500:] if n - 1 in book else ''
    voice = read(os.path.join(ROOT, 'legendarium', 'book', f'age_{k}.md'), 5000)
    names = read(os.path.join(HERE, f'age_{k}', 'PLAN_names.json'), 3000)
    people = read(os.path.join(HERE, f'age_{k}', 'PLAN_people.json'), 5000)
    ctx = textwrap.dedent(f"""
    RULES:
    {rules()}

    VOICE SAMPLE (match this voice, do not copy it):
    {voice}

    NAMES FOR THIS AGE (use exactly): {names}
    PEOPLE (ages and dates must agree): {people}

    PREVIOUS CHAPTER'S PLAN: {prev_syn}
    END OF THE PREVIOUS CHAPTER AS WRITTEN: {prev_tail}
    NEXT CHAPTER'S PLAN (do not write it; end where it begins): {next_syn}

    THIS CHAPTER'S PLAN:
    {block}
    """)
    say = print if verbose else (lambda *a: None)
    say(f'[{k} {n:02d}] planning: {title[:70]}')
    scenes = ollama(model, ctx + '\n\nList 5 to 7 scenes for this chapter, one per line, numbered, each a single '
                    'sentence saying what happens and whose eyes we are behind. Together they must carry every event '
                    'in the plan, in date order, and end exactly where the plan says.', SYSTEM, 600, 0.6)
    scene_lines = [s for s in scenes.splitlines() if re.match(r'^\s*\d', s)][:7] or [scenes]
    parts, tail = [], prev_tail[-1200:]
    for i, sc in enumerate(scene_lines, 1):
        say(f'[{k} {n:02d}] scene {i}/{len(scene_lines)}')
        txt = ollama(model, ctx + f'\n\nSCENE LIST:\n{scenes}\n\nTHE STORY SO FAR ENDS:\n{tail}\n\n'
                     f'Write scene {i} in full, about 900 words of finished prose, beginning with the heading '
                     f'"## {roman(i)}." on its own line. Scene {i}: {sc}', SYSTEM, 2000)
        if not txt.lstrip().startswith('## '):
            txt = f'## {roman(i)}.\n\n' + txt
        parts.append(txt.strip())
        tail = txt[-1200:]
    heading = '# ' + clean_title(title) + '\n\n'
    prose = heading + '\n\n'.join(parts) + '\n'
    fn = os.path.join(HERE, f'age_{k}', 'book', f'{n:02d}_{slug(title)}.md')
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    open(fn, 'w', encoding='utf-8').write(prose)
    # checks and one repair pass
    for tool in ('tells_scan.py', 'future_check.py'):
        args = [sys.executable, f'eras/quality/{tool}', os.path.relpath(fn, ROOT)] + ([k] if tool == 'future_check.py' else [])
        rc, out = run(args)
        if rc != 0 or re.search(r'\b[1-9]\d* (hits?|forward|tells?)\b', out):
            say(f'[{k} {n:02d}] repairing after {tool}')
            fixed = ollama(model, f'Here is a chapter and a checker report. Rewrite only the flagged sentences, '
                           f'keep everything else word for word, and return the whole chapter.\n\nREPORT:\n{out}\n\n'
                           f'CHAPTER:\n{read(fn)}', SYSTEM, 9000, 0.4)
            if len(fixed.split()) > 0.8 * len(prose.split()):
                open(fn, 'w', encoding='utf-8').write(fixed if fixed.startswith('# ') else heading + fixed)
    # events sidecar
    say(f'[{k} {n:02d}] events')
    evs = None
    for _ in range(3):
        raw = ollama(model, 'From this chapter, list the new events it introduces as a JSON array. Each item: '
                     '{"title": str, "era_year": int, "summary": str (40-80 words, chronicle voice, no foreshadowing), '
                     '"category": one of rulers|war|faith|coal|trade|land|law|humans|coalblood, "people": [str], '
                     '"places": [str], "threads": [str], "master_links": [master event ids from the plan]}. '
                     f'8 to 16 items. Output only JSON.\n\nPLAN:\n{block}\n\nCHAPTER:\n{read(fn)[:24000]}',
                     SYSTEM, 3000, 0.3, fmt='json')
        try:
            v = json.loads(raw)
            v = v if isinstance(v, list) else next((x for x in v.values() if isinstance(x, list)), None)
            if v and all(isinstance(e, dict) and 'title' in e and 'summary' in e for e in v):
                evs = v
                break
        except (ValueError, StopIteration):
            pass
    if evs is None:
        say(f'[{k} {n:02d}] events failed; chapter kept, rerun to retry events')
        return False
    ef = os.path.join(HERE, f'age_{k}', 'events', f'{n:02d}.json')
    os.makedirs(os.path.dirname(ef), exist_ok=True)
    json.dump(evs, open(ef, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    say(f'[{k} {n:02d}] done: {len(read(fn).split())} words, {len(evs)} events')
    return True


def roman(i):
    return ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX'][i - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default=os.environ.get('OLLAMA_MODEL', 'qwen2.5:32b'))
    ap.add_argument('--age', action='append', choices=AGES)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='stop after this many chapters')
    a = ap.parse_args()
    ages = a.age or AGES
    todo = [(k, n) for k in ages for n in missing(k)]
    if a.list:
        for k in ages:
            print(k, missing(k))
        print(len(todo), 'chapters missing')
        return
    # a chapter whose book file exists without events is half-written: rewrite it from scratch
    for k, n in todo:
        book, _ = done(k)
        if n in book:
            os.remove(os.path.join(HERE, f'age_{k}', 'book', book[n]))
    ok = 0
    for i, (k, n) in enumerate(todo):
        if a.limit and i >= a.limit:
            break
        try:
            ok += bool(write_chapter(k, n, a.model))
        except Exception as e:  # keep going; rerun picks it up
            print(f'[{k} {n:02d}] error: {e}', file=sys.stderr)
    print(f'{ok} chapters written; {len(todo) - ok} left (rerun to continue)')


if __name__ == '__main__':
    main()
