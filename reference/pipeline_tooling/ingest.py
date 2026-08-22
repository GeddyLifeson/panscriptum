import json, re, sys

def slug(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+","-",s)
    return s.strip('-')[:60]

def ingest(output_path):
    d = json.load(open(output_path))
    result = d.get('result', d) if isinstance(d, dict) else d
    if not isinstance(result, list):
        result = [result]
    roll = json.load(open('/home/claude/panscriptum/sweep/SWEEP_ROLL.json'))
    by_name = {r['name']: r for r in roll}
    total = 0
    for src in result:
        if not src or 'source' not in src:
            continue
        name = src['source']
        fn = f"/home/claude/panscriptum/sweep/records/{slug(name)}.json"
        json.dump(src, open(fn,'w'), indent=2)
        n = len(src.get('entries',[]))
        total += n
        r = by_name.get(name)
        if r:
            r['status'] = src.get('status','catalogued')
            r['entry_count'] = n
            syn = src.get('synthesis',{}) or {}
            r['ceiling_entity'] = syn.get('ceiling_entity')
            r['provisional_magnitude'] = syn.get('provisional_magnitude')
        print(f"  {name}: {n} entries" + ("  [EMPTY/GAP]" if n==0 else ""))
    json.dump(roll, open('/home/claude/panscriptum/sweep/SWEEP_ROLL.json','w'), indent=2)
    done = sum(1 for r in roll if r['status'] not in ('pending',))
    print(f"  -> batch total {total} entries | ROLL PROGRESS {done}/{len(roll)}")

if __name__ == '__main__':
    for p in sys.argv[1:]:
        ingest(p)
