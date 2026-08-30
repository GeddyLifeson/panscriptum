#!/usr/bin/env python3
"""Assemble the Registry Terminal: the omniverse as an atom, in one self-contained page."""
import os
import sys
import threading

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import silence                                                          # noqa: E402

DATA = os.path.join(HERE, "data", "NAVTREE.json")
OUT = os.path.join(HERE, "output", "registry_terminal.html")

TEMPLATE = r"""<title>The Registry Terminal</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,500;1,300&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
  :root{
    --ground:#0b0d12; --panel:#11141c; --vellum:#e8e4dc; --muted:#767d8f; --rule:#212734;
    --s0:#8b6fd4; --s1:#4f9fd4; --s2:#4fb391; --s3:#c98b3f; --s4:#c4557f; --s5:#d4b26a;
    --serif:"Spectral",Georgia,serif; --sans:"IBM Plex Sans",system-ui,sans-serif;
    --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--ground);color:var(--vellum);font-family:var(--sans);
       height:100vh;display:flex;flex-direction:column;overflow:hidden}
  header{border-bottom:1px solid var(--rule);padding:14px 24px 11px;background:var(--panel);
         display:flex;justify-content:space-between;align-items:baseline;gap:18px;flex-wrap:wrap}
  h1{margin:0;font-family:var(--serif);font-weight:300;font-size:19px;letter-spacing:.17em;
     text-transform:uppercase}
  .sub{color:var(--muted);font-size:11px;font-family:var(--serif);font-style:italic}
  .legend{display:flex;gap:13px;flex-wrap:wrap;font-family:var(--mono);font-size:10.5px;
          color:var(--muted)}
  .legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
  main{flex:1;display:flex;min-height:0}
  #stage{flex:1;min-width:0;position:relative}
  svg{display:block;width:100%;height:100%;cursor:grab;touch-action:none}
  svg:active{cursor:grabbing}
  aside{width:302px;border-left:1px solid var(--rule);background:var(--panel);padding:19px;
        overflow-y:auto}
  aside h2{font-family:var(--serif);font-weight:500;font-size:16px;margin:0 0 3px}
  .endo{font-family:var(--serif);font-size:12.5px;color:var(--vellum);margin:-1px 0 10px;
        line-height:1.5}
  .endo em{color:var(--muted);font-size:11px}
  .mark{font-family:var(--mono);font-size:11px;color:var(--muted);word-break:break-all;
        margin-bottom:15px;line-height:1.6}
  .row{display:flex;justify-content:space-between;gap:10px;padding:6px 0;
       border-bottom:1px solid var(--rule);font-size:12.5px}
  .row span:last-child{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--muted)}
  .hand{display:block;margin-top:9px;padding:10px 12px;border:1px solid var(--rule);
        border-radius:2px;color:var(--vellum);text-decoration:none;font-size:12.5px}
  .hand:hover,.hand:focus-visible{border-color:var(--muted);outline:none}
  .hand em{display:block;color:var(--muted);font-family:var(--serif);font-size:10.5px;
           font-style:italic;margin-top:3px}
  .note{color:var(--muted);font-family:var(--serif);font-style:italic;font-size:11.5px;
        line-height:1.65;margin-top:15px;border-top:1px solid var(--rule);padding-top:11px}
  /* The shelved-here roster is UNCAPPED (Hard Rule 0) -- it used to be sliced to 8, which hid
     30 of node 6.6.6's 38 sources behind no indication at all. The panel is bounded by scroll
     instead of by truncation: every name stays reachable, the box stays a box. */
  .roster{max-height:190px;overflow-y:auto;margin-top:6px}
  .ctl{display:flex;gap:6px;margin-top:14px}
  .ctl button{flex:1;background:none;border:1px solid var(--rule);color:var(--muted);
    cursor:pointer;padding:6px;font-family:var(--mono);font-size:11px;border-radius:2px}
  .ctl button:hover{color:var(--vellum);border-color:var(--muted)}
  circle.n{cursor:pointer}
  text{pointer-events:none;user-select:none}
  @media (max-width:840px){main{flex-direction:column}aside{width:auto;border-left:none;
    border-top:1px solid var(--rule);max-height:40vh}}
</style>

<header>
  <div>
    <h1>The Registry Terminal</h1>
    <div class="sub">the omniverse as an atom &#183; nucleus to valence &#183; drag to pan, scroll to zoom</div>
  </div>
  <div class="legend" id="legend"></div>
</header>
<main>
  <div id="stage"><svg id="field"></svg></div>
  <aside id="panel"></aside>
</main>

<script>
const DATA = __DATA__;
// Every catalogue-derived string goes through this before it reaches innerHTML. The names come
// from the roll and from wikis, so "Dungeons & Dragons" is not a hypothetical: unescaped, an
// `&` starts an entity, and a `<` in any name silently eats the rest of the panel's markup.
// render.py's containment_svg() already does exactly this with html.escape(); this is the same
// discipline on the JS side. (BUGS m10, 2026-08-24.)
function esc(v){ return String(v==null?"":v)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
  .replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
const TIERS=["hyperverse","xenoverse","metaverse","multiverse","universe"];
const LABEL={hyperverse:"H",xenoverse:"X",metaverse:"Mt.",multiverse:"Mv.",universe:"U-"};
const SHELL=["--s0","--s1","--s2","--s3","--s4","--s5"];
// Uniform nodes need room: 735 of them at one size cannot share the radii that variable sizing
// allowed. The field is scaled up and the shells spread so the outermost ring has arc to spare.
const NODE_R=22;                              // every node the same size, at every tier
const SHELL_R=[0,520,830,1080,1330,1580,1830];
// A name set inside a circle needs the circle to be about 300 units across, and the first shell
// never holds more than seven things, so there is room for that there and nowhere else. The
// shells beyond it carry up to 343 nodes and stay as plain dots, read by tooltip until you
// descend and they become the named ring in their own turn.
const NAV_R=185;

// How big a ring's circles can be is a question about the ring, not about taste: n things spaced
// around a circumference get 2*pi*R/n of arc each, and a disc has to fit inside that with a gap.
// Below about ninety units the disc can no longer hold a name at a size anyone can read, so the
// ring falls back to plain dots with the names set outside it.
const NAMED_MIN=90;
function discR(n,R){ return Math.min(NAV_R, 0.40*2*Math.PI*R/Math.max(1,n)); }

// A disc big enough to draw is not the same as a disc big enough to READ. Thirty-eight sources
// on one shelf each got a disc of 99 units, which fits, but "Curious DM Investigations" inside it
// came out at four pixels. The type that fits a disc is computed first, and a ring goes to named
// discs only if its LONGEST name still lands above the floor -- decided for the whole ring, so
// the circles on it stay one size. Below the floor the ring reverts to dots with the names set
// outside, where there is as much room as the arc allows.
const MIN_FIT=30;
function fitIn(len,r,cap){ return Math.min(cap,(2*r*0.86)/(Math.max(1,len)*0.52)); }
// A ring holding n labels needs enough circumference to stack them: n lines of about 1.15em.
// One universe carries 157 worlds, which on a fixed ring put every name across its neighbour's.
// The ring grows to whatever radius its own contents require instead.
function ringR(base,n,fs){ return Math.max(base, n*fs*1.7/(2*Math.PI)); }
function ringFits(names,r,cap){
  const longest=names.reduce((a,b)=>b.length>a?b.length:a,1);
  return r>=NAMED_MIN && fitIn(longest,r,cap)>=MIN_FIT;
} // nucleus, five shells, then the valence
// Only the outer shells of the branch you are IN are drawn. Rendering all 735 nodes at once
// forced a field so large that a 26px label came out at 7px on a 1920 screen. Three shells at
// overview keeps every name readable, and the deeper shells appear as you descend.
const OVERVIEW_DEPTH=3;
const W=3400,H=3400,CX=W/2,CY=H/2;
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();

// The map is rendered at the viewer's OWN screen, so it fills their monitor rather than a
// number I picked. Azgaar needs width and height alongside the seed -- without them the same
// seed lays out differently per device, which is why they are passed explicitly.
const MAPW = (window.screen && screen.width) ? Math.round(screen.width) : 1920;
const MAPH = (window.screen && screen.height) ? Math.round(screen.height) : 1080;

// ---- layout: a radial tree, re-rooted on whatever you are looking at.
//
// The first version laid the whole omniverse out once and "focus" only un-dimmed a branch. That
// left an opened hyperverse crammed into the same two-degree wedge it had when it was one of
// seven, with a hundred and forty names stacked on each other. Drilling in now recomputes the
// layout with the clicked node at the nucleus and its descendants spread across the full circle,
// which is what makes each tier a navigable bubble of the tier below it rather than a magnified
// sliver of the whole.
const TIER_OF={omniverse:0,hyperverse:1,xenoverse:2,metaverse:3,multiverse:4,universe:5,world:6};
let pos={}, rootKey="";

function layout(root){
  pos={};
  const place=(key,a0,a1,depth,parent)=>{
    const nd = key==="" ? {k:DATA.roots,n:0,src:0,t:"omniverse"} : DATA.nodes[key];
    if(!nd) return;
    const ang=(a0+a1)/2, R=SHELL_R[depth];
    pos[key]={x:CX+R*Math.cos(ang),y:CY+R*Math.sin(ang),r:R,ang,depth,node:nd,parent,a0,a1};
    if(depth>=OVERVIEW_DEPTH) return;
    const kids = key==="" ? DATA.roots : nd.k;
    if(!kids||!kids.length) return;
    // Wedge weighted by content -- but by WORLDS PLUS SOURCES, not worlds alone. Weighting on
    // worlds only gave H3 a sliver you could not see or click, because none of its sources have
    // catalogued Places entries yet. A branch that holds something addressed deserves room on the
    // shell whether or not the sweep has reached it. The sqrt keeps a branch of 654 from
    // swallowing the ring.
    const wts=kids.map(k=>{const d=DATA.nodes[k];
      return Math.sqrt(Math.max(1,((d&&d.n)||0)+((d&&d.src)||0)*3));});
    const tot=wts.reduce((a,b)=>a+b,0);

    // Weight alone put four of the seven hyperverses on top of each other: a disc wide enough to
    // hold its name needs a fixed arc, and a quiet branch was being handed less than that. Each
    // child is given the arc its own circle occupies first, and only what is left over is shared
    // out by content. Where even the floor does not fit, the ring is split evenly and the
    // weighting is dropped rather than allowed to overlap.
    const rNext=SHELL_R[depth+1];
    const childR=(depth+1===1)?Math.max(NODE_R,discR(kids.length,rNext)):12;
    const avail=a1-a0, floor=Math.min(avail/kids.length, 2.25*childR/rNext);
    const slack=Math.max(0, avail-floor*kids.length);
    let a=a0;
    kids.forEach((k,i)=>{const span=floor+slack*wts[i]/tot;
      place(k,a+span*0.08,a+span*0.92,depth+1,key); a+=span;});
  };
  place(root,-Math.PI/2,Math.PI*1.5,0,null);
}

// The view is a CENTRE and a WIDTH, with the height derived from the stage's own aspect at the
// moment it is applied. A square viewBox on a landscape stage was letterboxed into the shorter
// side and threw away a third of the available width, which cost about a third of the type size
// on every label. It also means a window resize needs no bookkeeping: the height re-derives.
let view={cx:CX,cy:CY,w:W};
function stageAR(){
  const r=document.getElementById("stage").getBoundingClientRect();
  return (r.width>2&&r.height>2) ? r.width/r.height : 1;
}

// The colour says what TIER a thing is, so a metaverse reads as a metaverse whether it is sitting
// on the third shell of the omniverse or at the nucleus of its own bubble.
const tierCol=nd=>css(SHELL[Math.min(TIER_OF[nd.t]!==undefined?TIER_OF[nd.t]:5,5)]);

function parentOf(key){
  if(key==="") return null;
  const i=key.lastIndexOf(".");
  return i<0 ? "" : key.slice(0,i);
}

function draw(){
  const stage=document.getElementById("stage");
  const root=pos[rootKey];

  // The outer shells carry up to 343 nodes, which is forty units of arc each -- less than one
  // dot is wide, so at full size they merged into a solid band. Dividing the circumference by the
  // count did not fix it either: the wedges are weighted, so the ring is not evenly spaced and
  // its tightest pair is far closer than its average. Each ring is measured for the smallest gap
  // it actually contains, and its dots are sized to sit inside that.
  const byShell={};
  Object.values(pos).forEach(p=>{(byShell[p.depth]=byShell[p.depth]||[]).push(p.ang);});
  const _dot={};
  const dotR=d=>{
    if(_dot[d]!==undefined) return _dot[d];
    const a=(byShell[d]||[]).slice().sort((x,y)=>x-y);
    let gap=Infinity;
    for(let i=1;i<a.length;i++) gap=Math.min(gap,(a[i]-a[i-1])*SHELL_R[d]);
    if(a.length>1) gap=Math.min(gap,(a[0]+2*Math.PI-a[a.length-1])*SHELL_R[d]);
    return _dot[d]=Math.max(6, Math.min(NODE_R, gap===Infinity?NODE_R:gap*0.45));
  };

  const _h=view.w/stageAR();
  let s=`<svg id="field" viewBox="${view.cx-view.w/2} ${view.cy-_h/2} ${view.w} ${_h}">`;
  for(let d=1;d<=OVERVIEW_DEPTH;d++)
    s+=`<circle cx="${CX}" cy="${CY}" r="${SHELL_R[d]}" fill="none" stroke="${css('--rule')}" stroke-width="0.8" opacity="0.55"/>`;

  Object.entries(pos).forEach(([k,p])=>{
    if(p.parent===null)return; const q=pos[p.parent]; if(!q)return;
    s+=`<line x1="${q.x.toFixed(1)}" y1="${q.y.toFixed(1)}" x2="${p.x.toFixed(1)}" y2="${p.y.toFixed(1)}" stroke="${tierCol(p.node)}" stroke-width="0.9" opacity="0.32"/>`;
  });

  // The nucleus is whatever you are inside. Clicking it steps back out one tier, so the atom is
  // navigable in both directions without reaching for the buttons.
  const up=parentOf(rootKey);
  s+=`<circle cx="${CX}" cy="${CY}" r="46" fill="#161a24" stroke="${tierCol(root.node)}" stroke-width="1.6" class="n" data-up="${up===null?'':up}" data-hasup="${up===null?0:1}"><title>${esc(rootKey===""?"the omniverse":(root.node.name||rootKey))}${up===null?"":" &#183; click to step out"}</title></circle>`;
  if(rootKey===""){
    s+=`<text x="${CX}" y="${CY+11}" text-anchor="middle" fill="${css('--s0')}" font-family="${css('--serif')}" font-size="34">&#937;</text>`;
  }else{
    s+=`<text x="${CX}" y="${CY+100}" text-anchor="middle" fill="${tierCol(root.node)}" font-family="${css('--serif')}" font-size="72" letter-spacing="4">${esc((root.node.name||rootKey).slice(0,24))}</text>`;
    s+=`<text x="${CX}" y="${CY+205}" text-anchor="middle" fill="${css('--muted')}" font-family="${css('--mono')}" font-size="44">${LABEL[root.node.t]||root.node.t}</text>`;
  }

  Object.entries(pos).forEach(([k,p])=>{
    if(k===rootKey)return;
    const col=tierCol(p.node), n=p.node.n||0;
    const dr=p.depth===1?discR(pos[rootKey].node.k?pos[rootKey].node.k.length:DATA.roots.length,p.r):0;
    const nav=p.depth===1&&dr>=NAMED_MIN;
    const rr=nav?dr:dotR(p.depth);
    s+=`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${rr}" fill="#151924" stroke="${col}" stroke-width="${nav?2.2:1.4}" class="n" data-k="${esc(k)}"><title>${esc(p.node.name||k)} &#183; ${esc(LABEL[p.node.t]||p.node.t)} &#183; ${n} worlds &#183; ${p.node.src} sources</title></circle>`;

    if(nav){
      // The name goes in the circle, so the circle has to hold the name. Rather than pick one
      // size and let "Elualaenys" spill out of it, the type shrinks to the widest line the disc
      // can take -- the circles stay uniform and the names stay inside them.
      const sibs=(pos[rootKey].node.k||DATA.roots).map(x=>(DATA.nodes[x]&&DATA.nodes[x].name)||x);
      const nm=(p.node.name||k);
      const fit=fitIn(sibs.reduce((a,b)=>b.length>a?b.length:a,1),rr,58);
      s+=`<text x="${p.x.toFixed(1)}" y="${(p.y+fit*0.34).toFixed(1)}" text-anchor="middle" `
       + `fill="${col}" font-family="${css('--serif')}" font-size="${fit.toFixed(1)}">${esc(nm)}</text>`;
      s+=`<text x="${p.x.toFixed(1)}" y="${(p.y+rr*0.76).toFixed(1)}" text-anchor="middle" `
       + `fill="${css('--muted')}" font-family="${css('--mono')}" font-size="44" letter-spacing="3">`
       + `${(LABEL[p.node.t]||p.node.t)}</text>`;
      return;
    }

    // Names, not indices, set outside the circle so a uniform node stays uncrowded.
    //
    // Angle is the scarce resource. A name on the first shell is set out past the LAST shell,
    // where its whole wedge is empty, because a name anchored at its own node runs straight
    // through every ring stacked beyond it. Names further out are set just past their node and
    // grow outward only -- a middle anchor puts half the word back on top of the ring behind it.
    // The innermost two shells are named; the third is left to its tooltip, because a hundred
    // and fifty names on one ring is a mat, not a map.
    // A shell's wedges are weighted by content, so siblings are not evenly spaced: a crowded
    // sector packs a dozen names into the arc a quiet one gives to two. Rather than pick a depth
    // and hope, each name is drawn only where its own wedge is wide enough to hold a line of it.
    // Crowded sectors go quiet and give up their names to the tooltip; opening one of them
    // re-roots the layout, the wedge widens, and the names come back.
    // Bigger type on the outer rings pays for itself. The view fits the drawing, so raising the
    // label size does push the fit out -- but only by the label's own share of the radius, while
    // the rings stay put. Measured at the same stage, 46 units renders at 11px and 72 at 16.
    // One ring of dots is named, not two. A shell-2 name is set outward and runs through the
    // radius where shell 3's names sit, so the wedge test -- which only protects a name from its
    // own neighbours on its own ring -- could not see the collision. Shell 3 keeps its tooltip
    // and gets its names when you descend and it becomes the named ring.
    const fs = 72;
    const room = (p.a1-p.a0)*p.r >= fs*1.15;
    if(p.depth===2 && room){
      const nm=(p.node.name||k).slice(0,22);
      const lr = p.r+dotR(p.depth)+16;
      const lx=CX+lr*Math.cos(p.ang), ly=CY+lr*Math.sin(p.ang);
      const deg=p.ang*180/Math.PI, flip=(deg>90||deg<-90);
      s+=`<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${flip?'end':'start'}" `
       + `transform="rotate(${flip?deg+180:deg} ${lx.toFixed(1)} ${ly.toFixed(1)})" `
       + `fill="${col}" font-family="${css('--serif')}" font-size="${fs}">${esc(nm)}</text>`;
    }
  });

  // The valence. Worlds belong to the thing you are standing in, so they ring the nucleus once
  // you have descended to a node that actually holds them.
  // Sources shelved at a node but not yet run through the cosmology pass had no node of their
  // own -- the panel listed them as text and the branch below them was empty. Eighty-three
  // metaverses ended that way, holding ninety-five sources between them, so diving into one
  // arrived nowhere. A source is an addressed thing and gets a node like everything else. It is
  // drawn open, because what is under it has not been catalogued yet.
  const ss=root.node.s||[];
  if(ss.length){
    // Sharing a ring with the tier dots put source discs straight through them at 34 nodes. A
    // source is not a tier, so it gets a shelf of its own outside all of them -- unless the node
    // has no children at all, in which case the inner ring is empty and the source belongs there,
    // where it is the only thing to look at.
    const kids=(root.node.k||[]).length;
    // Far enough out to clear the outermost tier ring and its dots, and no further: the view
    // fits the drawing, so every unit the shelf travels outward costs type size everywhere else.
    const R=ringR(kids?SHELL_R[OVERVIEW_DEPTH]+230:SHELL_R[1], ss.length, 62);
    const sr=Math.min(150,discR(ss.length,R));
    // Source titles run long ("Wayfinder's Guide to Eberron"); set whole they added eight hundred
    // units of overhang to the fit and took a third off the type everywhere. Trimmed on the ring,
    // whole in the tooltip and the panel.
    const shown=ss.map(n=>n.length>18?n.slice(0,17)+"…":n);
    const named=ringFits(shown,sr,46), srFit=fitIn(shown.reduce((a,b)=>b.length>a?b.length:a,1),sr,46);
    ss.forEach((nm,i)=>{
      const a=-Math.PI/2+2*Math.PI*(i+0.5)/ss.length;
      const x=CX+R*Math.cos(a), y=CY+R*Math.sin(a);
      s+=`<line x1="${CX}" y1="${CY}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${css('--muted')}" stroke-width="0.8" stroke-dasharray="8 10" opacity="0.4"/>`;
      s+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(named?sr:NODE_R).toFixed(1)}" fill="#141720" stroke="${css('--muted')}" stroke-width="1.6" stroke-dasharray="7 7" class="n" data-s="${i}"><title>${esc(nm)} &#183; shelved here, cosmology not yet run</title></circle>`;
      const t=shown[i];
      if(named){
        const fit=srFit;
        s+=`<text x="${x.toFixed(1)}" y="${(y+fit*0.34).toFixed(1)}" text-anchor="middle" `
         + `fill="${css('--muted')}" font-family="${css('--serif')}" font-size="${fit.toFixed(1)}">${esc(t)}</text>`;
      }else{
        const lx=CX+(R+NODE_R+16)*Math.cos(a), ly=CY+(R+NODE_R+16)*Math.sin(a);
        const deg=a*180/Math.PI, flip=(deg>90||deg<-90);
        s+=`<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${flip?'end':'start'}" `
         + `transform="rotate(${flip?deg+180:deg} ${lx.toFixed(1)} ${ly.toFixed(1)})" `
         + `fill="${css('--muted')}" font-family="${css('--serif')}" font-size="62">${esc(t)}</text>`;
      }
    });
  }

  const ws=root.node.w||[];
  if(ws.length){
    const m=ws.length, R=ringR(SHELL_R[OVERVIEW_DEPTH], m, 62), wr=discR(m,R);
    const wn=ws.map(w=>(w.cat||w.d.split("::").pop()||"").slice(0,22));
    const named=ringFits(wn,wr,52), wrFit=fitIn(wn.reduce((a,b)=>b.length>a?b.length:a,1),wr,52);
    ws.forEach((w,i)=>{
      const a=-Math.PI/2+2*Math.PI*i/m;
      const x=CX+R*Math.cos(a), y=CY+R*Math.sin(a);
      const nm=(w.cat||w.d.split("::").pop()||"").slice(0,22);
      s+=`<line x1="${CX}" y1="${CY}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="${css('--s5')}" stroke-width="0.8" opacity="0.42"/>`;
      s+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(named?wr:NODE_R).toFixed(1)}" fill="#1d1a12" stroke="${css('--s5')}" stroke-width="${named?2.2:1.4}" class="n" data-w="${i}"><title>${esc(w.cat||w.d)}</title></circle>`;
      if(named){
        const fit=wrFit;
        s+=`<text x="${x.toFixed(1)}" y="${(y+fit*0.34).toFixed(1)}" text-anchor="middle" `
         + `fill="${css('--s5')}" font-family="${css('--serif')}" font-size="${fit.toFixed(1)}">${esc(nm)}</text>`;
      }else{
        const lx=CX+(R+NODE_R+16)*Math.cos(a), ly=CY+(R+NODE_R+16)*Math.sin(a);
        const deg=a*180/Math.PI, flip=(deg>90||deg<-90);
        s+=`<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="${flip?'end':'start'}" `
         + `transform="rotate(${flip?deg+180:deg} ${lx.toFixed(1)} ${ly.toFixed(1)})" `
         + `fill="${css('--s5')}" font-family="${css('--serif')}" font-size="62">${esc(nm)}</text>`;
      }
    });
  }
  s+="</svg>";
  stage.innerHTML=s;
  bindNodes();
  bindStage();
}

function resetView(){
  // Fitting the view to an ESTIMATE of how far the drawing reaches meant budgeting for the
  // longest label any ring could ever hold, so the omniverse zoomed out to leave room for a
  // source shelf that was not on screen and its own names fell to seven pixels. The drawing is
  // measured instead: draw first, ask the SVG how far it actually extends, then fit to that.
  const f=document.getElementById("field");
  if(!f) return;
  let b; try{ b=f.getBBox(); }catch(e){ b=null; }
  if(!b||!b.width||!b.height){
    view={cx:CX,cy:CY,w:W}; applyView(); return;
  }
  const ar=stageAR();
  view.cx=b.x+b.width/2; view.cy=b.y+b.height/2;
  view.w=Math.max(b.width, b.height*ar)*1.07;
  applyView();
}

function applyView(){
  // Pan and zoom only rewrite the viewBox. A full redraw per pointermove was rebuilding 1,478
  // nodes on every mouse movement AND leaving the handler holding a detached <svg>, whose
  // getBoundingClientRect() returns width 0. The pan scale then divided by that, ran away, and
  // parked the view at -30839,-70029 where nothing is.
  const f=document.getElementById("field");
  const h=view.w/stageAR();
  if(f) f.setAttribute("viewBox", `${view.cx-view.w/2} ${view.cy-h/2} ${view.w} ${h}`);
}

function clampView(){
  // The centre may wander no further than one field beyond the drawing, so the view can never
  // leave the atom behind, and the width is bounded so a scroll cannot zoom to nothing.
  view.w=Math.max(300, Math.min(4*W, view.w));
  view.cx=Math.max(CX-W, Math.min(CX+W, view.cx));
  view.cy=Math.max(CY-W, Math.min(CY+W, view.cy));
}

function bindNodes(){
  // Only the node handlers are rebound after a redraw. Pan and zoom live on the stage, which
  // persists, and are bound exactly once.
  document.querySelectorAll("#field circle.n").forEach(c=>{
    c.addEventListener("click",()=>{
      const wi=c.getAttribute("data-w");
      if(wi!==null){selectWorld(pos[rootKey].node.w[+wi]);return;}
      const si=c.getAttribute("data-s");
      if(si!==null){selectSource(pos[rootKey].node.s[+si]);return;}
      if(c.getAttribute("data-hasup")==="1"){descend(c.getAttribute("data-up"));return;}
      if(c.getAttribute("data-hasup")==="0")return;      // already at the omniverse
      descend(c.getAttribute("data-k"));
    });
  });
}

let _stageBound=false;
function bindStage(){
  if(_stageBound) return;
  _stageBound=true;
  const stage=document.getElementById("stage");

  stage.addEventListener("wheel",e=>{
    e.preventDefault();
    view.w*=(e.deltaY<0?0.86:1.16);
    clampView(); applyView();
  },{passive:false});

  let drag=null;
  stage.addEventListener("pointerdown",e=>{
    // No pointer capture. Capturing routed every subsequent event to the stage, which swallowed
    // the click before it reached a circle and made the whole atom inert.
    drag={x:e.clientX,y:e.clientY,moved:0};
  });
  const end=()=>{drag=null;};
  stage.addEventListener("pointerup",end);
  stage.addEventListener("pointercancel",end);
  stage.addEventListener("pointerleave",end);
  stage.addEventListener("pointermove",e=>{
    if(!drag) return;
    const r=stage.getBoundingClientRect();
    if(r.width<2||r.height<2) return;          // never divide by a collapsed box
    const sc=view.w/r.width;
    const moved=drag.moved+Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y);
    view.cx-=(e.clientX-drag.x)*sc;
    view.cy-=(e.clientY-drag.y)*sc;
    drag={x:e.clientX,y:e.clientY,moved};
    clampView(); applyView();
  });
}

function shelfmark(k){
  // The breadcrumb reads in names for the same reason the map does: H0 › X0 › M3 tells you where
  // a thing sits in an array, not where it sits in the omniverse.
  //
  // AND THE NAME GOES THROUGH esc(). This built its crumb from the raw `nd.name` and the result
  // reaches innerHTML at three sinks (panel, selectSource, selectWorld), so it was one of three
  // catalogue-derived strings bypassing the rule stated at esc()'s own definition -- "every
  // catalogue-derived string goes through this before it reaches innerHTML". Latent, because no
  // node name in the live NAVTREE carries & < > " ' today; the exposure is the next one that
  // does, and this project's own cited example is "Dungeons & Dragons". Escaped where the value
  // enters the string, not at the three places it leaves, because a sink added later would
  // otherwise inherit the hole. (order 3b37494e20db)
  let s="&#937;"; if(k==="") return s;
  const parts=k.split(".");
  for(let i=0;i<parts.length;i++){
    const key=parts.slice(0,i+1).join("."), nd=DATA.nodes[key];
    s+=" › "+esc((nd&&nd.name)||LABEL[TIERS[i]]+parts[i]);
  }
  return s;
}

function panel(){
  const p=document.getElementById("panel"), k=rootKey;
  const nd = k==="" ? null : DATA.nodes[k];
  const tier = k==="" ? "The Omniverse" : (nd.name || nd.t);
  const kind = k==="" ? "omniverse" : nd.t;
  const worlds = k==="" ? DATA.roots.reduce((a,r)=>a+DATA.nodes[r].n,0) : nd.n;
  const srcs = k==="" ? DATA.roots.reduce((a,r)=>a+DATA.nodes[r].src,0) : nd.src;
  // SUM, not short-circuit. `a||b||c` returns the FIRST non-zero, so a node holding both
  // branch-children and shelved sources reported only its branches: 6.6.6 showed "contains 7"
  // while actually holding 7 branches and 38 shelved sources. 37 nodes were undercounting.
  const holds = k==="" ? DATA.roots.length
    : (nd.k.length + (nd.w?nd.w.length:0) + (nd.s?nd.s.length:0));
  p.innerHTML=`<h2>${esc(tier)}</h2>
    <div class="endo">${esc(kind)}</div>
    <div class="mark">${shelfmark(k)}</div>
    <div class="row"><span>shell</span><span>${k===""?"nucleus":k.split(".").length}</span></div>
    <div class="row"><span>contains</span><span>${holds}</span></div>
    <div class="row"><span>worlds below</span><span>${worlds.toLocaleString()}</span></div>
    <div class="row"><span>sources below</span><span>${srcs.toLocaleString()}</span></div>
    ${nd&&nd.s&&nd.s.length?`<div class="note">${nd.s.length} shelved here, not yet catalogued:<div class="roster">${nd.s.map(x=>"&#183; "+esc(x)).join("<br>")}</div></div>`:""}
    ${nd&&nd.w&&nd.w.length?`<p class="note">${nd.w.length} world${nd.w.length>1?"s":""} on the valence. Click one for its map.</p>`:`<p class="note">Structure only. Terrain begins at the valence.</p>`}
    <div class="ctl"><button id="bn">nucleus</button><button id="br">recentre</button></div>`;
  document.getElementById("bn").onclick=()=>{descend("");};
  document.getElementById("br").onclick=()=>{resetView();};
}

function selectSource(name){
  const p=document.getElementById("panel");
  p.innerHTML=`<h2>${esc(name)}</h2>
    <div class="endo">source</div>
    <div class="mark">${shelfmark(rootKey)}</div>
    <p class="note">Shelved at this address. Its worlds, and everything below them, appear once
    the cosmology pass reaches it — nothing under it is being hidden, because nothing under it
    has been written.</p>
    <div class="ctl"><button id="bb">back</button><button id="bn">nucleus</button></div>`;
  document.getElementById("bb").onclick=()=>{panel();};
  document.getElementById("bn").onclick=()=>{descend("");};
}

function selectWorld(w){
  const p=document.getElementById("panel"), f=w.f||{};
  // template is passed because testing showed it genuinely reaches the map; the climate and
// culture settings are NOT passed, because Azgaar discards them from a query string.
const TPL={archipelago:"archipelago",isles:"lowIsland",shattered:"shattered",
           pangaea:"pangea",highland:"volcano",continents:"continents"};
  const tpl=TPL[(w.f||{}).landform]||"continents";
  const u=`https://azgaar.github.io/Fantasy-Map-Generator/?seed=${w.s}&options=default&template=${tpl}&width=${MAPW}&height=${MAPH}`;
  const cat = w.cat || w.d.split("::").pop();
  const endo = w.endo || cat;
  // BOTH USES OF `cat` BELOW GO THROUGH esc(). The heading did and the closing note did not --
  // the same value, escaped once and not the other time, fifteen lines apart, which is how a
  // reader concludes the unescaped one was deliberate. Three live worlds carry an ampersand in
  // `cat` today: Baskets & Boots, DunBroch Castle & Kingdom, Cortex Power & Gas Co.
  // (order 3b37494e20db)
  p.innerHTML=`<h2>${esc(cat)}</h2>
    ${w.carried?`<div class="endo">endonym: <b>${esc(endo)}</b></div>`:""}
    <div class="mark">${shelfmark(rootKey)} › P<br>seed ${w.s}</div>
    <div class="row"><span>landform</span><span>${f.landform||"?"}</span></div>
    <div class="row"><span>climate</span><span>${f.climate||"?"}</span></div>
    <div class="row"><span>condition</span><span>${f.condition||"?"}</span></div>
    <div class="row"><span>era</span><span>${f.tech||"?"}</span></div>
    <div class="row"><span>attested axes</span><span>${w.a||0}/4</span></div>
    <div class="row"><span>primate city</span><span>${(w.b||0).toLocaleString()}</span></div>
    <div class="row"><span>burgs (est.)</span><span>${(w.nb||0).toLocaleString()}</span></div>
    <a class="hand" target="_blank" rel="noopener" href="${u}">Open the surface map
      <em>Azgaar &#183; ${MAPW}&#215;${MAPH} &#183; ${tpl}</em></a>
    <a class="hand" target="_blank" rel="noopener" href="${u}&scale=8&burg=1">Open the primate city
      <em>Azgaar &#8594; Watabou</em></a>
    <p class="note">${w.a||0} of 4 map axes attested by a source; the rest seeded.</p>
    <p class="note"><b>${esc(cat)}</b> is the catalogue heading. Place-names on the map are the
    world&rsquo;s own, generated with the terrain.</p>`;
}

document.getElementById("legend").innerHTML=
  ["hyperverse","xenoverse","metaverse","multiverse","universe","world"]
  .map((n,i)=>`<span><i style="background:${css(SHELL[i])}"></i>${n}</span>`).join("");
function descend(key){
  if(key===null||DATA.nodes[key]===undefined&&key!=="")return;
  rootKey=key; layout(rootKey); draw(); resetView(); panel();
}

layout(""); draw(); resetView(); panel();

// The height derives from the stage, so a resize only needs the viewBox reapplied.
window.addEventListener("resize",()=>{applyView();});
</script>
"""


def main():
    with open(DATA, encoding="utf-8") as f:
        data = f.read()

    # NEUTRALISE `<` BEFORE SPLICING JSON INTO AN INLINE <script>. The browser looks for the
    # literal characters `</script>` inside the block without any knowledge of JSON strings, so
    # one catalogue name containing that sequence would close the block early and take the whole
    # terminal down -- and `<!--` / `<script` can shift the parser too. Inside a JSON string
    # `<` is a valid escape that parses straight back to `<`, so this costs the data
    # nothing: every name still renders exactly as written. Done on the TEXT rather than by
    # re-serialising, so the file's own formatting is untouched. (BUGS m10, 2026-08-24.)
    data = data.replace("<", "\\u003c")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    html = TEMPLATE.replace("__DATA__", data)
    # LANDED, not written in place -- the same atomic idiom every other writer in this project
    # uses (compress_store.store(), silence.write_json()). A bare open(OUT, "w") truncates the
    # existing page before the new one is ready, so a crash or a kill mid-write leaves a reader
    # (or `catalogue_web.py`'s own writers, if this ever runs alongside them) looking at a torn
    # or empty terminal instead of the previous good one. No concurrent reader is known today,
    # but this was the only writer left in the module still doing the truncate-then-fill.
    tmp = "%s.%d.%d.tmp" % (OUT, os.getpid(), threading.get_ident())
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    landed = silence.replace_retry(tmp, OUT)
    if landed:
        print(f"wrote {OUT}  ({len(html)/1024:.0f} KB)")
    else:
        print(f"WRITE DENIED: {OUT} did not land this round; rerun to retry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
