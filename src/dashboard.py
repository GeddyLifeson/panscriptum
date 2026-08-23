#!/usr/bin/env python3
"""
DASHBOARD — what every meter in this project reads, on one page, without asking anybody.

WHY
---
Everything this library does is metered somewhere, and until now every meter was in a different
place and most of them were in my head: the corpus reader's progress line in one log, the page
roll's in another, the free-tier quotas inside Cascade's router, the watcher's findings in a
JSON ledger, coverage in a third file. The owner's only way to see where things stood was to ask
and wait for someone to go and look.

That is a bad arrangement for a project whose entire recurring defect is a number nobody was
looking at. A quota exhausted at two in the afternoon should be visible at two in the afternoon.

WHAT IT SERVES
--------------
    /            the page. Auto-refreshes; no build step, no dependencies, one file.
    /api/state   the same numbers as JSON, for anything else that wants them.

Nothing here computes anything of its own. It reads what the pipeline already writes -- logs,
ledgers, the router's own accounting -- so the dashboard can never disagree with the system it
is reporting on. If a number is wrong here it is wrong there, which is the property you want in
an instrument.

THE QUOTA PANEL IS THE POINT
----------------------------
Free tiers meter four different ways at once -- requests per minute, requests per day, tokens
per minute, tokens per day -- and a bucket is exhausted the moment ANY of the four hits zero.
Today Mistral's daily 2,000 requests were spent by mid-afternoon while its per-minute window sat
wide open, and the corpus read slowed by a factor of ten with nothing in any log to say why. The
panel shows every window for every bucket, and the TIGHTEST one is what actually binds.
"""
import argparse
import glob
import http.server
import json
import os
import re
import socketserver
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "src")
sys.path.insert(0, SRC)
import silence                                                          # noqa: E402

_BAD_CHARS = (chr(8), chr(11), chr(12), chr(7))
if any(c in open(os.path.abspath(__file__), encoding="utf-8").read() for c in _BAD_CHARS):
    raise SystemExit(__file__ + ": a regex escape was eaten in transit.")

STATE = os.path.join(HERE, "state")
DATA = os.path.join(HERE, "data")

# The reader's progress line. Built from the same format string read.py prints, so if that line
# changes this stops matching rather than silently reporting stale numbers.
RE_READ = re.compile(
    r"(?P<done>[\d,]+)/(?P<total>[\d,]+)\s+(?P<rate>[\d.]+)\s+chunks/s\s+"
    r"feats\s+(?P<feats>[\d,]+)\s+dropped\s+(?P<dropped>[\d,]+)\s+"
    r"chunks\s+(?P<chunks>[\d,]+)/(?P<budget>[\d,]+).*?"
    r"(?P<gpu>\d+)\s+to\s+GPU,\s+(?P<unans>\d+)\s+UNANSWERED.*?eta\s+(?P<eta>[\d.]+)h")

RE_ROLL = re.compile(
    r"(?P<done>[\d,]+)/(?P<total>[\d,]+)\s+(?P<rate>[\d.]+)/s\s+"
    r"feats\s+(?P<feats>[\d,]+)\s+quantities\s+(?P<q>[\d,]+)\s+"
    r"pages\s+(?P<pages>[\d,]+)\s+(?P<chars>[\d.]+)M\s+chars\s+eta\s+(?P<eta>[\d.]+)h")


def _num(s):
    try:
        return int(str(s).replace(",", ""))
    except Exception:
        return 0


def _tail_match(path, rx, keep=400):
    """The most recent line in a log that matches. Reads the tail, not the file.

    These logs reach tens of megabytes over a long run and the dashboard polls every few
    seconds; reading them whole would make the instrument the heaviest thing on the machine.
    """
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 60000))
            body = f.read().decode("utf-8", "replace")
    except Exception:
        silence.note("dashboard.py:tail")
        return None
    for line in reversed(body.splitlines()[-keep:]):
        m = rx.search(line)
        if m:
            return m.groupdict()
    return None


# --------------------------------------------------------------------------- the panels

def quotas():
    """Every window on every bucket, and which one is actually binding.

    A bucket is exhausted when ANY of its four meters hits zero, so reporting only requests-per-
    day would have shown Mistral as healthy at the exact moment its per-minute window was the
    thing stopping the run -- and reporting only per-minute would have missed the opposite.
    """
    out = []
    try:
        import cascade_bridge as CB
        if not CB.engine():
            return [{"bucket": "cascade unavailable", "windows": [], "worst": 0.0}]
        router = CB._ROUTER
        seen = {}
        for m in router.models:
            if m.bucket.startswith("ollama:"):
                continue
            if m.bucket in seen:
                continue
            seen[m.bucket] = m
        for bucket, m in sorted(seen.items()):
            try:
                st = router.model_status(m)
            except Exception:
                silence.note("dashboard.py:model_status")
                continue
            if st.get("unlimited"):
                out.append({"bucket": bucket, "model": m.id, "unlimited": True,
                            "windows": [], "worst": 1.0})
                continue
            windows, worst = [], 1.0
            for name, v in (st.get("remaining") or {}).items():
                if not isinstance(v, dict) or not v.get("cap"):
                    continue
                left, cap = max(0, v.get("left", 0)), v["cap"]
                frac = left / cap if cap else 0.0
                worst = min(worst, frac)
                windows.append({"name": name, "left": left, "cap": cap,
                                "frac": round(frac, 4)})
            out.append({"bucket": bucket, "model": m.id, "unlimited": False,
                        "windows": sorted(windows, key=lambda w: w["frac"]),
                        "worst": round(worst, 4)})
    except Exception as e:
        silence.note("dashboard.py:quotas")
        out.append({"bucket": f"quota read failed: {type(e).__name__}", "windows": [],
                    "worst": 0.0})
    return out


def throughput(minutes=15):
    """Calls actually made in the recent past, per bucket. The quota panel says what is LEFT;
    this says what is being SPENT, and the two together are the whole picture."""
    import sqlite3
    path = os.path.join(STATE, "cascade_scratch.db")
    out = {"window_min": minutes, "calls": 0, "per_hour": 0, "buckets": []}
    try:
        c = sqlite3.connect(path)
        since = time.time() - minutes * 60
        rows = list(c.execute(
            "select bucket, count(*), sum(outcome='ok') from usage where ts > ? "
            "group by bucket order by 2 desc", (since,)))
        total = sum(r[1] for r in rows)
        out["calls"] = total
        out["per_hour"] = int(total * 60 / minutes) if minutes else 0
        out["buckets"] = [{"bucket": b, "calls": n, "ok": int(ok or 0)} for b, n, ok in rows]
    except Exception:
        silence.note("dashboard.py:throughput")
    return out


def jobs():
    """The long-running work, each as a fraction of its own honest denominator."""
    out = []
    import lognames as LN
    r = _tail_match(os.path.join(STATE, LN.READ), RE_READ)
    if r:
        out.append({
            "name": "corpus read", "unit": "chunks",
            "done": _num(r["chunks"]), "total": _num(r["budget"]),
            "detail": (f"{_num(r['done']):,}/{_num(r['total']):,} entities  ·  "
                       f"{_num(r['feats']):,} feats  ·  {r['rate']} chunks/s"),
            "warn": (f"{_num(r['unans'])} unanswered" if _num(r["unans"]) else ""),
            "eta_h": float(r["eta"])})
    roll = _tail_match(os.path.join(STATE, LN.ROLL), RE_ROLL)
    if roll:
        out.append({
            "name": "page roll", "unit": "entities",
            "done": _num(roll["done"]), "total": _num(roll["total"]),
            "detail": (f"{_num(roll['pages']):,} pages  ·  {roll['chars']}M characters  ·  "
                       f"{roll['rate']}/s"),
            "warn": "", "eta_h": float(roll["eta"])})
    return out


def library():
    """What the library actually holds: hosts, coverage, and the phases that exist."""
    out = {}
    try:
        import weave_index as WI
        import feats as F
        hosts = json.load(open(F.HOSTS, encoding="utf-8"))
        recs = {r["source"]: r for r in WI.load_records()}
        with_host = [s for s in recs if hosts.get(s)]
        without = [s for s in recs if not hosts.get(s)]
        out["sources"] = {"total": len(recs), "with_host": len(with_host),
                          "without_host": len(without),
                          "entries_with_host": sum(len(recs[s]["entries"]) for s in with_host),
                          "entries_without_host": sum(len(recs[s]["entries"]) for s in without)}
    except Exception:
        silence.note("dashboard.py:library-hosts")
    try:
        rows = json.load(open(os.path.join(DATA, "COVERAGE.json"), encoding="utf-8"))
        n = sum(r["entries"] for r in rows)
        cited = sum(r["cited"] for r in rows)
        read = sum(r["read"] for r in rows)
        out["coverage"] = {"entries": n, "cited": cited, "read": read,
                           "settled": cited + read, "feats": sum(r["feats"] for r in rows),
                           "age_h": round((time.time() - os.path.getmtime(
                               os.path.join(DATA, "COVERAGE.json"))) / 3600, 1)}
    except Exception:
        silence.note("dashboard.py:library-coverage")
    try:
        import pipeline as P
        out["phases"] = [{"name": n, "built": hasattr(P, "phase_" + n)} for n in P.PHASES]
    except Exception:
        silence.note("dashboard.py:library-phases")
    try:
        readfeats = len(glob.glob(os.path.join(DATA, "readfeats", "**", "*.json"),
                                  recursive=True))
        out["readfeats"] = readfeats
    except Exception:
        silence.note("dashboard.py:library-readfeats")
    return out


def watch():
    """The standing sweep's verdict, so the dashboard says when the code itself is suspect."""
    out = {"open": 0, "high": 0, "rounds": 0, "findings": [], "broken": []}
    try:
        d = json.load(open(os.path.join(DATA, "OVERWATCH.json"), encoding="utf-8"))
        out["rounds"] = d.get("rounds", 0)
        openf = [v for v in (d.get("findings") or {}).values() if v.get("state") == "open"]
        out["open"] = len(openf)
        out["high"] = sum(1 for f in openf if (f.get("severity") or "").lower() == "high")
        out["findings"] = [{"module": f.get("module"), "symbol": f.get("symbol"),
                            "actual": (f.get("actual") or "")[:160],
                            "severity": f.get("severity", "medium")}
                           for f in openf[:12]]
    except Exception:
        silence.note("dashboard.py:watch")
    try:
        f = json.load(open(os.path.join(STATE, "failures.json"), encoding="utf-8"))
        out["swallowed"] = sorted(f.items(), key=lambda kv: -kv[1])[:6]
        out["swallowed_total"] = sum(f.values())
    except Exception:
        silence.note("dashboard.py:failures")
    return out


HISTORY = os.path.join(STATE, "dashboard_history.json")
# How far back "moved" looks. Long enough that slow work still registers, short enough that the
# number answers "is it going right now" rather than "did it ever".
MOVED_WINDOW_MIN = 30


def movement(now_state):
    """What has CHANGED, not what the level is.

    The panel showed bars and the bars did not move, so it read as a system doing nothing --
    which was half right and impossible to tell from the levels alone. A progress bar at 12.8%
    looks identical whether it reached 12.8% a minute ago or three hours ago.

    So every reading is appended to a small history and the deltas are computed against the
    oldest sample inside the window. A number that has not moved now SAYS it has not moved,
    which is the difference between an instrument and a decoration.
    """
    keys = {
        "cited": ((now_state.get("library") or {}).get("coverage") or {}).get("cited"),
        "settled": ((now_state.get("library") or {}).get("coverage") or {}).get("settled"),
        "feats": ((now_state.get("library") or {}).get("coverage") or {}).get("feats"),
        "entities read": (now_state.get("library") or {}).get("readfeats"),
        "chunks": next((j.get("done") for j in (now_state.get("jobs") or [])
                        if j.get("name") == "corpus read"), None),
        "standards met": sum(1 for x in (now_state.get("standards") or []) if x.get("holds")),
    }
    row = {"at": time.time(), **{k: v for k, v in keys.items() if v is not None}}
    try:
        hist = []
        if os.path.exists(HISTORY):
            with open(HISTORY, encoding="utf-8") as f:
                hist = json.load(f)
        hist.append(row)
        cutoff = time.time() - 24 * 3600
        hist = [h for h in hist if h.get("at", 0) > cutoff][-2000:]
        tmp = HISTORY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(hist, f)
        os.replace(tmp, HISTORY)
    except Exception:
        silence.note("dashboard.py:movement")
        return []

    window = time.time() - MOVED_WINDOW_MIN * 60
    older = [h for h in hist if h.get("at", 0) <= window]
    base = older[-1] if older else (hist[0] if hist else {})
    span = (row["at"] - base.get("at", row["at"])) / 60 if base else 0
    out = []
    for k, v in keys.items():
        if v is None:
            continue
        was = base.get(k)
        delta = None if was is None else v - was
        out.append({"metric": k, "now": v, "delta": delta,
                    "minutes": round(span), "stalled": delta == 0 and span >= 10})
    return out


def state():
    s = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "quotas": quotas(),
         "throughput": throughput(), "jobs": jobs(), "library": library(),
         "watch": watch()}
    try:
        import standards as ST
        s["standards"] = ST.check(s)
    except Exception:
        silence.note("dashboard.py:standards")
        s["standards"] = []
    s["movement"] = movement(s)
    return s


# --------------------------------------------------------------------------- the page

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Panscriptum — Instruments</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#e8e3d9; --ink-dim:#9b968c; --ink-faint:#6b675f;
  --ground:#14140f; --panel:#1c1c16; --panel-2:#232219; --rule:#332f26;
  --brass:#c8a44a; --brass-dim:#8a7333;
  --good:#7fa650; --warn:#c8853a; --bad:#b4483c;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace;
  --serif:'Spectral',Georgia,'Times New Roman',serif;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--serif);
  font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
header{padding:26px 30px 18px;border-bottom:1px solid var(--rule);
  display:flex;align-items:baseline;gap:18px;flex-wrap:wrap}
h1{font-size:19px;font-weight:600;margin:0;letter-spacing:.14em;text-transform:uppercase}
.stamp{font-family:var(--mono);font-size:11px;color:var(--ink-faint);letter-spacing:.1em}
.wrap{display:grid;grid-template-columns:repeat(auto-fit,minmax(370px,1fr));gap:18px;padding:22px 30px 60px}
section{background:var(--panel);border:1px solid var(--rule);border-radius:2px;padding:18px 20px 20px}
section.wide{grid-column:1/-1}
h2{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.2em;
  text-transform:uppercase;color:var(--brass);margin:0 0 14px;padding-bottom:9px;
  border-bottom:1px solid var(--rule)}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin:11px 0 5px}
.label{font-family:var(--mono);font-size:12px;color:var(--ink)}
.value{font-family:var(--mono);font-size:12px;color:var(--ink-dim);
  font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{height:7px;background:var(--panel-2);border:1px solid var(--rule);overflow:hidden}
.bar>i{display:block;height:100%;background:var(--brass);transition:width .5s ease}
.bar>i.good{background:var(--good)} .bar>i.warn{background:var(--warn)} .bar>i.bad{background:var(--bad)}
.sub{font-family:var(--mono);font-size:11px;color:var(--ink-faint);margin:5px 0 14px;
  font-variant-numeric:tabular-nums}
.note{font-family:var(--mono);font-size:11px;color:var(--warn)}
.bucket{margin:0 0 15px;padding-bottom:13px;border-bottom:1px solid var(--rule)}
.bucket:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.win{display:grid;grid-template-columns:74px 1fr 96px;gap:9px;align-items:center;margin:4px 0}
.win .n{font-family:var(--mono);font-size:10px;color:var(--ink-faint);letter-spacing:.08em;
  text-transform:uppercase}
.win .v{font-family:var(--mono);font-size:10.5px;color:var(--ink-dim);text-align:right;
  font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;
  padding:2px 7px;border:1px solid var(--rule);color:var(--ink-faint);text-transform:uppercase}
.pill.dry{color:var(--bad);border-color:var(--bad)}
.pill.low{color:var(--warn);border-color:var(--warn)}
.pill.ok{color:var(--good);border-color:var(--good)}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:11.5px}
td{padding:5px 8px 5px 0;border-bottom:1px solid var(--rule);color:var(--ink-dim);
  font-variant-numeric:tabular-nums}
td.k{color:var(--ink)} tr:last-child td{border-bottom:none}
.empty{font-family:var(--mono);font-size:11.5px;color:var(--ink-faint);font-style:normal}
footer{padding:0 30px 40px;font-family:var(--mono);font-size:10.5px;color:var(--ink-faint)}
.sgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:14px 0 4px}
.gname{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;text-transform:uppercase;
  color:var(--brass-dim);margin-bottom:6px}
.srow{display:grid;grid-template-columns:1fr auto;gap:6px;align-items:baseline;
  font-family:var(--mono);font-size:11px;padding:3px 0;border-bottom:1px solid var(--rule)}
.srow:last-child{border-bottom:none}
.sname{color:var(--ink-dim)} .sval{color:var(--good);font-variant-numeric:tabular-nums}
.sfloor{grid-column:1/-1;font-size:9.5px;color:var(--ink-faint)}
.srow.miss .sname{color:var(--ink)} .srow.miss .sval{color:var(--bad);font-weight:600}
.srow.miss{border-left:2px solid var(--bad);padding-left:7px;margin-left:-9px}
.order{margin:10px 0 0;padding:10px 12px;background:var(--panel-2);border-left:2px solid var(--warn)}
.otitle{font-family:var(--mono);font-size:11px;color:var(--warn);margin-bottom:5px}
.obody{font-size:13.5px;color:var(--ink-dim);line-height:1.5}
td.up{color:var(--good)} td.down{color:var(--bad);font-weight:600}
</style></head><body>
<header>
  <h1>Panscriptum · Instruments</h1>
  <span class="stamp" id="stamp">reading…</span>
</header>
<div class="wrap" id="wrap"></div>
<footer>Served by <code>src/dashboard.py</code>. Every number is read from what the pipeline
already writes — logs, ledgers, and Cascade's own accounting — so this page cannot disagree with
the system it reports on. Refreshes every 5 seconds.</footer>
<script>
const el=(t,c,x)=>{const n=document.createElement(t);if(c)n.className=c;
  if(x!==undefined)n.textContent=x;return n};
const cls=f=>f<=0.001?'bad':f<0.15?'bad':f<0.4?'warn':'good';
const pct=f=>(f*100).toFixed(0)+'%';
function bar(frac,kind){const b=el('div','bar');const i=el('i',kind||cls(frac));
  i.style.width=Math.max(0,Math.min(1,frac))*100+'%';b.appendChild(i);return b}

function panelMovement(d){const s=el('section','wide');
  s.appendChild(el('h2',null,'Movement — what has changed, not what the level is'));
  const M=d.movement||[];
  if(!M.length){s.appendChild(el('div','empty','No history yet. Deltas appear after the second reading.'));return s}
  const t=el('table');
  M.forEach(m=>{const tr=el('tr');
    const d1=el('td','k',m.metric);
    const d2=el('td',null,(m.now||0).toLocaleString());
    let txt='—', cls='';
    if(m.delta===null||m.delta===undefined){txt='first reading'}
    else if(m.delta>0){txt='+'+m.delta.toLocaleString()+' in '+m.minutes+' min';cls='up'}
    else if(m.delta<0){txt=m.delta.toLocaleString()+' in '+m.minutes+' min';cls='down'}
    else{txt=m.stalled?('NO CHANGE in '+m.minutes+' min'):'no change yet';cls=m.stalled?'down':''}
    const d3=el('td',cls,txt);
    tr.append(d1,d2,d3);t.appendChild(tr)});
  s.appendChild(t);
  s.appendChild(el('div','sub','A bar that has not moved looks identical to one that just '+
    'moved. This says which.'));
  return s}

function panelStandards(d){const s=el('section','wide');
  const S=d.standards||[];
  const bad=S.filter(x=>!x.holds);
  s.appendChild(el('h2',null,'Standards — where things stand against spec'));
  if(!S.length){s.appendChild(el('div','empty','Standards not readable.'));return s}
  const r=el('div','row');r.appendChild(el('span','label','met'));
  r.appendChild(el('span','value',(S.length-bad.length)+' of '+S.length));
  s.appendChild(r);s.appendChild(bar((S.length-bad.length)/S.length,''));
  const groups={};S.forEach(x=>{(groups[x.group]=groups[x.group]||[]).push(x)});
  const grid=el('div','sgrid');
  Object.keys(groups).forEach(g=>{
    const col=el('div','scol');col.appendChild(el('div','gname',g));
    groups[g].forEach(x=>{
      const row=el('div','srow '+(x.holds?'':'miss'));
      row.appendChild(el('span','sname',x.standard));
      row.appendChild(el('span','sval',String(x.observed)));
      row.appendChild(el('span','sfloor','floor '+x.floor));
      col.appendChild(row)});
    grid.appendChild(col)});
  s.appendChild(grid);
  if(bad.length){
    s.appendChild(el('div','sub','WORK ORDERS'));
    bad.sort((a,b)=>({high:0,medium:1,low:2}[a.severity]||3)-({high:0,medium:1,low:2}[b.severity]||3));
    bad.forEach(x=>{const o=el('div','order');
      o.appendChild(el('div','otitle','['+x.severity.toUpperCase()+'] '+x.standard+
        ' — observed '+x.observed+', floor '+x.floor));
      o.appendChild(el('div','obody',x.order));
      s.appendChild(o)})}
  return s}

function panelJobs(d){const s=el('section','wide');s.appendChild(el('h2',null,'Work in progress'));
  if(!d.jobs.length){s.appendChild(el('div','empty','No job is writing a progress line right now.'));return s}
  d.jobs.forEach(j=>{const f=j.total?j.done/j.total:0;
    const r=el('div','row');r.appendChild(el('span','label',j.name));
    r.appendChild(el('span','value',
      j.done.toLocaleString()+' / '+j.total.toLocaleString()+' '+j.unit+
      '  ·  '+pct(f)+'  ·  eta '+j.eta_h.toFixed(1)+'h'));
    s.appendChild(r);s.appendChild(bar(f,''));
    const sub=el('div','sub',j.detail);s.appendChild(sub);
    if(j.warn){const w=el('div','note',j.warn);s.appendChild(w)}});
  return s}

function panelQuota(d){const s=el('section');
  s.appendChild(el('h2',null,'Provider quota — what is left'));
  if(!d.quotas.length){s.appendChild(el('div','empty','No buckets reporting.'));return s}
  d.quotas.forEach(q=>{const b=el('div','bucket');
    const r=el('div','row');r.appendChild(el('span','label',q.bucket));
    const st=q.unlimited?'ok':(q.worst<=0.001?'dry':q.worst<0.2?'low':'ok');
    const txt=q.unlimited?'unlimited':(q.worst<=0.001?'exhausted':pct(q.worst)+' left');
    const p=el('span','pill '+st,txt);r.appendChild(p);b.appendChild(r);
    q.windows.forEach(w=>{const g=el('div','win');
      g.appendChild(el('div','n',w.name));g.appendChild(bar(w.frac,''));
      g.appendChild(el('div','v',w.left.toLocaleString()+'/'+w.cap.toLocaleString()));
      b.appendChild(g)});
    if(q.unlimited)b.appendChild(el('div','sub','local — no meter'));
    s.appendChild(b)});
  return s}

function panelSpend(d){const s=el('section');
  s.appendChild(el('h2',null,'Provider spend — last '+d.throughput.window_min+' minutes'));
  const r=el('div','row');r.appendChild(el('span','label','calls per hour'));
  r.appendChild(el('span','value',d.throughput.per_hour.toLocaleString()));s.appendChild(r);
  const t=el('table');
  if(!d.throughput.buckets.length){s.appendChild(el('div','empty','Nothing has called out recently.'));return s}
  d.throughput.buckets.forEach(b=>{const tr=el('tr');
    const a=el('td','k',b.bucket);const c=el('td',null,b.calls+' calls');
    const o=el('td',null,b.ok+' ok');tr.append(a,c,o);t.appendChild(tr)});
  s.appendChild(t);return s}

function panelLibrary(d){const s=el('section');s.appendChild(el('h2',null,'The library'));
  const L=d.library;
  if(L.coverage){const c=L.coverage;
    [['cited',c.cited,c.entries],['settled',c.settled,c.entries]].forEach(([k,v,n])=>{
      const r=el('div','row');r.appendChild(el('span','label',k));
      r.appendChild(el('span','value',v.toLocaleString()+' / '+n.toLocaleString()+
        '  ·  '+pct(v/n)));s.appendChild(r);s.appendChild(bar(v/n,''))});
    s.appendChild(el('div','sub',c.feats.toLocaleString()+' feats on record  ·  measured '+
      c.age_h+'h ago'))}
  if(L.sources){const q=L.sources;const t=el('table');
    [['sources with a host',q.with_host+' of '+q.total],
     ['entries reachable',q.entries_with_host.toLocaleString()],
     ['entries with no wiki',q.entries_without_host.toLocaleString()+
       ' in '+q.without_host+' sources'],
     ['entities read by the model',(L.readfeats||0).toLocaleString()]].forEach(([k,v])=>{
      const tr=el('tr');tr.append(el('td','k',k),el('td',null,v));t.appendChild(tr)});
    s.appendChild(t)}
  return s}

function panelPhases(d){const s=el('section');s.appendChild(el('h2',null,'Phases'));
  const ph=(d.library.phases)||[];
  if(!ph.length){s.appendChild(el('div','empty','Runner not readable.'));return s}
  const built=ph.filter(p=>p.built).length;
  const r=el('div','row');r.appendChild(el('span','label','implemented'));
  r.appendChild(el('span','value',built+' of '+ph.length));s.appendChild(r);
  s.appendChild(bar(built/ph.length,''));
  const t=el('table');ph.forEach(p=>{const tr=el('tr');
    tr.append(el('td','k',p.name),
      el('td',null,p.built?'built':'not built'));t.appendChild(tr)});
  s.appendChild(t);return s}

function panelWatch(d){const s=el('section','wide');
  s.appendChild(el('h2',null,'Overwatch — the standing sweep'));
  const w=d.watch;
  const r=el('div','row');r.appendChild(el('span','label','open findings'));
  r.appendChild(el('span','value',w.open+' ('+w.high+' high) after '+w.rounds+' round(s)'));
  s.appendChild(r);
  if(w.findings.length){const t=el('table');w.findings.forEach(f=>{const tr=el('tr');
    tr.append(el('td','k',f.module+'.py'),el('td',null,f.symbol||''),
      el('td',null,f.actual));t.appendChild(tr)});s.appendChild(t)}
  else s.appendChild(el('div','empty','Nothing open — every finding was fixed or retired when its file changed.'));
  if(w.swallowed&&w.swallowed.length){
    s.appendChild(el('div','sub','swallowed failures recorded: '+
      (w.swallowed_total||0).toLocaleString()));
    const t2=el('table');w.swallowed.forEach(([k,v])=>{const tr=el('tr');
      tr.append(el('td','k',k),el('td',null,v.toLocaleString()));t2.appendChild(tr)});
    s.appendChild(t2)}
  return s}

async function tick(){
  try{const d=await (await fetch('/api/state',{cache:'no-store'})).json();
    document.getElementById('stamp').textContent=d.at;
    const w=document.getElementById('wrap');w.innerHTML='';
    w.append(panelMovement(d),panelStandards(d),panelJobs(d),panelQuota(d),panelSpend(d),
             panelLibrary(d),panelPhases(d),panelWatch(d));
  }catch(e){document.getElementById('stamp').textContent='server unreachable';}
}
tick();setInterval(tick,5000);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        raw = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            try:
                self._send(json.dumps(state()), "application/json; charset=utf-8")
            except Exception as e:
                silence.note("dashboard.py:state")
                self._send(json.dumps({"error": f"{type(e).__name__}: {str(e)[:120]}"}),
                           "application/json; charset=utf-8")
            return
        self._send(PAGE, "text/html; charset=utf-8")

    def log_message(self, *a):
        # Silent: this polls every five seconds and a request log would bury the console it
        # shares with everything else.
        return


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser(description="every meter in this project, on one page")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--once", action="store_true", help="print the state as JSON and exit")
    a = ap.parse_args()
    if a.once:
        print(json.dumps(state(), indent=1))
        return 0
    with Server(("127.0.0.1", a.port), Handler) as srv:
        print(f"instruments on http://127.0.0.1:{a.port}   (ctrl-c to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
