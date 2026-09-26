/* atlas_layers.js -- what can be laid over the open map (the "Layers" button beside the age chooser), the Posters
   gallery, and the recordings of the names found after a build.

   Overlays, all off until chosen:
     realms of another age   that age's realms as its own map draws them (data/overlay_<K>.js, made by
                             tools/make_posters.py), outlined over whichever map is open: every map shares one grid
     faiths, cultures        Azgaar's own religions and cultures layers of the open map
     story threads           a thread's places, joined in the order of its events (on an age's map, that age's)
     campaigns and battles   the war events with a place, and the war-to-war links between them; Azgaar's armies
     journeys                Azgaar's own journeys layer; where a map has none, the voyages of the annals
   The drawings live in one <g id="atlasOv"> inside the map-maker's #viewbox, so they pan and zoom with the map. */
(function(){
var A = ATLAS, esc = A.esc, NS = 'http://www.w3.org/2000/svg';

A.ov = {realms: '', faith: null, culture: null, threads: false, thread: '', war: false, journeys: false};
var AZ = {faith: 'religions', culture: 'cultures'};   // overlays that are Azgaar's own layers
var madeOn = {};                                        // Azgaar layers the Atlas turned on (so it turns them off again)

function live(){ var w = fmg(); return (ready && w && w.document && w.document.getElementById('viewbox')) ? w : null; }
function group(w){
  var g = w.document.getElementById('atlasOv');
  if (!g) { g = w.document.createElementNS(NS, 'g'); g.id = 'atlasOv'; w.document.getElementById('viewbox').appendChild(g);
    g.addEventListener('click', function(ev){ var t = ev.target.closest('[data-ref]'); if (t) { ev.stopPropagation(); showPlace(t.getAttribute('data-ref')); } }); }
  return g;
}
function sub(w, id){
  var g = group(w), s = w.document.getElementById(id);
  if (!s) { s = w.document.createElementNS(NS, 'g'); s.id = id; g.appendChild(s); }
  return s;
}
function clear(w, id){ var s = w.document.getElementById(id); if (s) s.innerHTML = ''; }

/* where a place is on the open map, remembered per map */
var posCache = {};
function pos(w, ref){
  var c = posCache[mapKey] = posCache[mapKey] || {};
  if (ref in c) return c[ref];
  var at = null;
  try { var r = A.liveRef(w, ref, mapKey); at = r ? locate(w, r) : null; } catch(e){ at = null; }
  return (c[ref] = at ? [at[0], at[1]] : null);
}
function inScope(e){ return mapKey === 'M' || e.age === mapKey; }
function evsWhere(test){
  return Object.keys(A.EV).map(function(i){ return A.EV[i]; }).filter(function(e){ return e.place && inScope(e) && test(e); })
    .sort(function(a, b){ return a.y - b.y || a.m - b.m || a.d - b.d; });
}
function title(el, text){ var t = el.ownerDocument.createElementNS(NS, 'title'); t.textContent = text; el.appendChild(t); }
function el(w, parent, tag, attrs, text){
  var x = w.document.createElementNS(NS, tag);
  for (var k in attrs) x.setAttribute(k, attrs[k]);
  if (text != null) x.textContent = text;
  parent.appendChild(x); return x;
}

/* ---- the realms of another age ---- */
function drawRealms(w){
  clear(w, 'atlasOvRealms');
  var k = A.ov.realms; if (!k) return;
  A.loadScript('data/overlay_' + k + '.js', 'ov' + k, function(){ return !!A.overlayData[k]; }).then(function(ok){
    var w2 = live(); if (!w2 || A.ov.realms !== k) return;
    if (!ok) { A.toast('The realms of ' + A.mapLabel(k) + ' are not in this build (tools/make_posters.py makes them).'); return; }
    var g = sub(w2, 'atlasOvRealms'); g.innerHTML = '';
    g.setAttribute('pointer-events', 'none');
    A.overlayData[k].states.forEach(function(s){
      el(w2, g, 'path', {d: s.d, fill: s.color || '#888', 'fill-opacity': .16, stroke: s.color || '#888', 'stroke-width': 1.6,
        'stroke-dasharray': '5 3', 'vector-effect': 'non-scaling-stroke', 'stroke-linejoin': 'round'});
    });
    A.overlayData[k].states.forEach(function(s){
      if (!s.pole) return;
      el(w2, g, 'text', {x: s.pole[0], y: s.pole[1], 'text-anchor': 'middle', 'font-family': 'Cinzel, serif', 'font-size': 11,
        fill: '#1b1520', stroke: '#fff', 'stroke-width': 2.4, 'paint-order': 'stroke', 'font-weight': 600, opacity: .9}, s.name);
    });
  });
}

/* ---- a story thread's places, joined in the order of its events ---- */
function threadsHere(){
  var n = {};
  evsWhere(function(e){ return e.threads && e.threads.length; }).forEach(function(e){ e.threads.forEach(function(t){ n[t] = (n[t] || 0) + 1; }); });
  return Object.keys(A.meta.threads).filter(function(t){ return n[t]; }).sort(function(a, b){ return n[b] - n[a]; }).map(function(t){ return [t, n[t]]; });
}
function drawThreads(w){
  clear(w, 'atlasOvThreads');
  if (!A.ov.threads) return;
  var list = threadsHere(); if (!list.length) return;
  var t = A.ov.thread && list.some(function(x){ return x[0] === A.ov.thread; }) ? A.ov.thread : list[0][0];
  var th = A.meta.threads[t] || {}, col = th.colour || '#c9a435', g = sub(w, 'atlasOvThreads');
  var evs = evsWhere(function(e){ return (e.threads || []).indexOf(t) >= 0; }), path = [], count = {}, first = {};
  evs.forEach(function(e){
    var p = pos(w, e.place); if (!p) return;
    count[e.place] = (count[e.place] || 0) + 1;
    if (!(e.place in first)) first[e.place] = e;
    var last = path[path.length - 1];
    if (!last || last.ref !== e.place) path.push({ref: e.place, p: p});
  });
  if (path.length > 1) el(w, g, 'polyline', {points: path.map(function(x){ return x.p[0].toFixed(1) + ',' + x.p[1].toFixed(1); }).join(' '),
    fill: 'none', stroke: col, 'stroke-width': 1.4, 'stroke-opacity': .55, 'vector-effect': 'non-scaling-stroke', 'stroke-linejoin': 'round', 'pointer-events': 'none'});
  var refs = Object.keys(count).sort(function(a, b){ return count[b] - count[a]; });
  refs.forEach(function(r, i){
    var p = pos(w, r), c = el(w, g, 'circle', {cx: p[0], cy: p[1], r: (1.6 + Math.sqrt(count[r]) * .9).toFixed(2), fill: col, stroke: '#fff',
      'stroke-width': .6, 'data-ref': r, style: 'cursor:pointer'});
    title(c, A.placeName(r) + ': ' + count[r] + ' event' + (count[r] > 1 ? 's' : '') + ' of ' + (th.gloss || t));
    if (i < 10) el(w, g, 'text', {x: p[0] + 4, y: p[1] - 3, 'font-size': 7, fill: '#1b1520', stroke: '#fff', 'stroke-width': 1.8, 'paint-order': 'stroke',
      'font-family': 'Georgia, serif', 'pointer-events': 'none'}, A.placeName(r));
  });
}

/* ---- campaigns and battles ---- */
function drawWar(w){
  clear(w, 'atlasOvWar');
  if (!A.ov.war) return;
  var g = sub(w, 'atlasOvWar'), evs = evsWhere(function(e){ return e.category === 'war'; }), byId = {}, at = {};
  evs.forEach(function(e){ var p = pos(w, e.place); if (p) { byId[e.id] = e; (at[e.place] = at[e.place] || []).push(e); } });
  var defs = w.document.getElementById('atlasOvArrow');
  if (!defs) { var d = el(w, group(w), 'defs', {}); d.innerHTML = '<marker id="atlasOvArrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#8e2f28"/></marker>'; }
  var seen = {};
  evs.forEach(function(e){   // the campaigns: one war event leading to another at another place
    if (!byId[e.id]) return;
    (e.links || []).forEach(function(l){
      var o = byId[l.to]; if (!o || o.place === e.place) return;
      var a = e, b = o; if (o.y < e.y || (o.y === e.y && (o.m < e.m || (o.m === e.m && o.d < e.d)))) { a = o; b = e; }
      var key = a.id + '>' + b.id; if (seen[key]) return; seen[key] = 1;
      var p = pos(w, a.place), q = pos(w, b.place), mx = (p[0] + q[0]) / 2 - (q[1] - p[1]) * .15, my = (p[1] + q[1]) / 2 + (q[0] - p[0]) * .15;
      el(w, g, 'path', {d: 'M' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + 'Q' + mx.toFixed(1) + ' ' + my.toFixed(1) + ' ' + q[0].toFixed(1) + ' ' + q[1].toFixed(1),
        fill: 'none', stroke: '#8e2f28', 'stroke-width': 1.3, 'stroke-dasharray': '4 2.5', 'stroke-opacity': .75, 'vector-effect': 'non-scaling-stroke',
        'marker-end': 'url(#atlasOvArrow)', 'pointer-events': 'none'});
    });
  });
  Object.keys(at).forEach(function(r){
    var p = pos(w, r), list = at[r], s = el(w, g, 'g', {'data-ref': r, style: 'cursor:pointer'});
    el(w, s, 'circle', {cx: p[0], cy: p[1], r: 4.2 + Math.min(4, list.length * .4), fill: '#fff', 'fill-opacity': .85, stroke: '#8e2f28', 'stroke-width': .8});
    el(w, s, 'text', {x: p[0], y: p[1] + 2.4, 'text-anchor': 'middle', 'font-size': 7, fill: '#8e2f28'}, '⚔︎');
    title(s, A.placeName(r) + '\n' + list.slice(0, 6).map(function(e){ return (e.year || e.date) + ': ' + e.title.replace(/[*_]/g, ''); }).join('\n') +
      (list.length > 6 ? '\n…and ' + (list.length - 6) + ' more' : ''));
  });
}

/* ---- journeys: Azgaar's own, or the voyages of the annals where the map has none ---- */
function drawJourneys(w){
  clear(w, 'atlasOvVoyages');
  if (!A.ov.journeys) return;
  if (w.pack && w.pack.journeys && w.pack.journeys.length) return;   // Azgaar's layer shows them
  var g = sub(w, 'atlasOvVoyages'), evs = evsWhere(function(e){ return e.kind === 'voyage' || /\b(voyage|sail(ed|s)?|journey(ed)?)\b/i.test(e.title || ''); }), at = {};
  evs.forEach(function(e){ if (pos(w, e.place)) (at[e.place] = at[e.place] || []).push(e); });
  Object.keys(at).forEach(function(r){
    var p = pos(w, r), s = el(w, g, 'g', {'data-ref': r, style: 'cursor:pointer'});
    el(w, s, 'circle', {cx: p[0], cy: p[1], r: 4.4, fill: '#fff', 'fill-opacity': .85, stroke: '#2f5f8e', 'stroke-width': .8});
    el(w, s, 'text', {x: p[0], y: p[1] + 2.4, 'text-anchor': 'middle', 'font-size': 7, fill: '#2f5f8e'}, '⚓︎');
    title(s, A.placeName(r) + '\n' + at[r].slice(0, 6).map(function(e){ return (e.year || e.date) + ': ' + e.title.replace(/[*_]/g, ''); }).join('\n'));
  });
  if (!Object.keys(at).length) A.toast('No journeys are drawn on this map, and no voyage of its age has a place.');
}

/* Azgaar's own layers: turned on by the Atlas when asked, and off again only if the Atlas turned them on */
function azLayer(w, id, on){
  try {
    if (on && !w.Layers.isOn(id)) { w.Layers.show(id); madeOn[id] = true; }
    else if (!on && madeOn[id] && w.Layers.isOn(id)) { w.Layers.hide(id); madeOn[id] = false; }
  } catch(e){}
}

A.applyOverlays = function(){
  var w = live(); if (!w) return;
  var o = A.ov;
  Object.keys(AZ).forEach(function(k){ if (o[k] != null) azLayer(w, AZ[k], !!o[k]); });
  azLayer(w, 'military', !!o.war);
  azLayer(w, 'journeys', !!o.journeys && !!(w.pack.journeys && w.pack.journeys.length));
  drawRealms(w); drawThreads(w); drawWar(w); drawJourneys(w);
  if ((o.threads || o.war || o.journeys) && !A.allLoaded()) A.loadAll().then(function(){ var w2 = live(); if (w2) { drawThreads(w2); drawWar(w2); drawJourneys(w2); } });
  var n = (o.realms ? 1 : 0) + ['faith', 'culture', 'threads', 'war', 'journeys'].filter(function(k){ return o[k]; }).length;
  var b = document.getElementById('lyrBtn'); if (b) { b.textContent = n ? 'Layers · ' + n : 'Layers'; b.setAttribute('aria-pressed', n > 0); }
};

/* ---- the panel ---- */
function panelHTML(){
  var w = live(), o = A.ov, keys = (A.meta.overlays || []).filter(function(k){ return k !== mapKey; });
  var isOn = function(id){ try { return w && w.Layers.isOn(id); } catch(e){ return false; } };
  var h = '<h4>Lay over this map</h4>';
  h += '<label class="lyr-sel"><span>Realms of another age</span><select id="lyrRealms"><option value="">none</option>' +
    keys.map(function(k){ return '<option value="' + k + '"' + (o.realms === k ? ' selected' : '') + '>' + (k === 'M' ? 'Today' : k + ' · ' + esc(A.ageOf[k].dt)) + '</option>'; }).join('') + '</select></label>';
  if (!keys.length) h += '<p class="hint">The realms of the ages come with tools/make_posters.py.</p>';
  var box = function(k, label, on, note){ return '<label><input type="checkbox" data-ov="' + k + '"' + (on ? ' checked' : '') + '><span>' + label + (note ? ' <small>' + note + '</small>' : '') + '</span></label>'; };
  h += box('faith', 'Faiths', o.faith != null ? o.faith : isOn('religions'));
  h += box('culture', 'Cultures', o.culture != null ? o.culture : isOn('cultures'));
  h += box('threads', 'Story threads', o.threads);
  if (o.threads) {
    var list = threadsHere();
    h += '<select id="lyrThread" aria-label="Which thread">' + list.map(function(x){ var t = A.meta.threads[x[0]];
      return '<option value="' + esc(x[0]) + '"' + (x[0] === o.thread ? ' selected' : '') + '>' + esc(t.gloss || t.dt) + ' (' + x[1] + ')</option>'; }).join('') + '</select>';
  }
  h += box('war', 'Campaigns &amp; battles', o.war, '⚔ battles, ⇢ one leading to the next');
  h += box('journeys', 'Journeys', o.journeys);
  h += '<p class="hint">' + (mapKey === 'M' ? 'Events of every age.' : 'Events of ' + esc(A.mapLabel(mapKey)) + '.') + ' Choose a mark to read its place.</p>';
  return h;
}
A.toggleLayers = function(open){
  var p = document.getElementById('lyrPanel'); if (!p) return;
  open = open == null ? p.hidden : open;
  if (open && !live()) { A.toast('The map is still opening.'); return; }
  if (open) p.innerHTML = panelHTML();
  p.hidden = !open; document.getElementById('lyrBtn').setAttribute('aria-expanded', open);
};
function wire(){
  var d = document.querySelector('.mapera'); if (!d || document.getElementById('lyrBtn')) return;
  var b = document.createElement('button'); b.id = 'lyrBtn'; b.className = 'lyr-btn'; b.textContent = 'Layers';
  b.setAttribute('aria-haspopup', 'true'); b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-pressed', 'false');
  b.title = 'Lay the realms of another age, faiths, cultures, threads, campaigns or journeys over this map';
  d.appendChild(b);
  var p = document.createElement('div'); p.id = 'lyrPanel'; p.className = 'lyr-panel'; p.hidden = true;
  document.querySelector('#panel-map .stage').appendChild(p);
  b.onclick = function(){ A.toggleLayers(); };
  p.onchange = function(ev){
    var t = ev.target;
    if (t.id === 'lyrRealms') A.ov.realms = t.value;
    else if (t.id === 'lyrThread') A.ov.thread = t.value;
    else if (t.dataset.ov) A.ov[t.dataset.ov] = t.checked;
    A.applyOverlays();
    if (t.dataset.ov === 'threads') p.innerHTML = panelHTML();
  };
  document.addEventListener('click', function(ev){ if (!p.hidden && !ev.target.closest('#lyrPanel') && !ev.target.closest('#lyrBtn')) p.hidden = true; });
}
var baseControls = A.mapControls;
A.mapControls = function(){ baseControls(); wire(); };
var baseReady = A.mapReady;
A.mapReady = function(w, key){
  baseReady(w, key); madeOn = {};
  if (A.ov.realms === key) A.ov.realms = '';   // an age's own realms need no overlay
  A.applyOverlays();
  var p = document.getElementById('lyrPanel'); if (p && !p.hidden) p.innerHTML = panelHTML();
};

/* ---- the Posters gallery (Diathir_Atlas/posters/, made by tools/make_posters.py) ---- */
A.showPosters = function(){
  A.loadScript('posters/posters.js', 'posters', function(){ return !!A.posters; }).then(function(ok){
    var P = A.posters;
    if (!ok || !P || !P.posters || !P.posters.length) {
      A.openSheet('<h2>Posters</h2><p>No posters are in this folder yet. <code>python3 tools/make_posters.py</code> makes one for every age.</p>', '#posters');
      return;
    }
    var h = '<h2>Posters</h2><p class="sub">The island in every age, for printing: each map at the close of its age, with its title, its realms and its chief events.' +
      (P.made ? ' Made ' + esc(P.made) + '.' : '') + '</p>' + (P.pdf ? '<p><a class="pill" href="' + esc(P.pdf) + '" target="_blank" rel="noopener">All posters as one PDF</a></p>' : '') +
      '<div class="posters">' + P.posters.map(function(p){
        return '<figure><a href="' + esc(p.file) + '" target="_blank" rel="noopener" title="Open the full poster"><img loading="lazy" src="' + esc(p.thumb) + '" alt="' + esc(p.dt + ', ' + p.age) + '"></a>' +
          '<figcaption><b>' + esc(p.dt) + '</b><span>' + esc(p.age) + '</span><small>' + esc(p.span) + (p.snap ? ' · the map: ' + esc(p.snap) : '') + '</small>' +
          '<span class="acts"><a href="' + esc(p.file) + '" download>PNG</a>' + (p.key ? '<button class="linkish" data-mapat="' + esc(p.key) + '|">Open the map</button>' : '') + '</span></figcaption></figure>';
      }).join('') + '</div>';
    A.openSheet(h, '#posters');
    document.getElementById('sheet').classList.add('wide');
  });
};

/* ---- the recordings of the names: audio/names/manifest.json, read when the Atlas opens, so recordings made after
   the build play too (the build's own list, meta.audio, stands when the manifest cannot be read) ---- */
A.loadAudio = function(){
  if (location.protocol === 'file:' || !window.fetch) return;
  fetch('audio/names/manifest.json', {cache: 'no-store'}).then(function(r){ return r.ok ? r.json() : null; }).then(function(m){
    if (!m || typeof m !== 'object') return;
    Object.keys(m).forEach(function(dt){ var f = m[dt]; if (typeof f !== 'string' || !f) return;
      A.meta.audio[dt] = /^audio\//.test(f) ? f : 'audio/names/' + f.replace(/^\.?\//, ''); });
  }).catch(function(){});
};
var baseStart = A.start;
A.start = function(){ baseStart(); A.loadAudio(); };
})();
