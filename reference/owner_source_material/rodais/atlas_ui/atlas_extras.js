/* atlas_extras.js -- the glossary drawer, "This day in Dia-thìr", the small web of an event's links, and
   "Read the telling" (the book section that tells an event). */
(function(){
var A = ATLAS, esc = A.esc;

/* ---- the glossary: every Dia-thìris name on screen, with its English and, where there is a recording, its sound ---- */
A.namesOnScreen = function(){
  var seen = {}, out = [], top = 0, bottom = window.innerHeight;
  document.querySelectorAll('#tl .ev-card').forEach(function(c){
    var r = c.getBoundingClientRect(); if (r.bottom < top || r.top > bottom) return;
    c.querySelectorAll('.gl').forEach(function(g){ var dt = g.textContent; if (!seen[dt]) { seen[dt] = 1; out.push(dt); } });
  });
  return out;
};
function glossRow(n){
  var snd = A.meta.audio[n[0]];
  return '<div class="gloss-row"><div><b>' + esc(n[0]) + '</b><small>' + esc(n[1]) + (n[4] ? ' · ' + esc(n[4]) : '') + '</small></div>' +
    (snd ? '<button data-play="' + esc(snd) + '" aria-label="Hear ' + esc(n[0]) + '" title="Hear it">▶︎</button>' : '<span></span>') + '</div>';
}
A.showGlossary = function(){
  var on = A.namesOnScreen(), byDt = {};
  A.meta.names.forEach(function(n){ if (!byDt[n[0]]) byDt[n[0]] = n; });
  var h = '<h2>Glossary</h2><p class="sub">The Dia-thìris names in the annals, with their English. ' +
    (Object.keys(A.meta.audio).length ? '▶ plays a recording of the name.' : 'Recordings of the names will play here once they are made.') + '</p>';
  h += '<h3>On screen now</h3>' + (on.length ? on.map(function(dt){ return glossRow(byDt[dt] || [dt, '', '', [], '']); }).join('') : '<p class="hint">No glossed name is in view; scroll the annals, or search all of them below.</p>');
  h += '<h3>All names</h3><input type="search" id="glq" placeholder="A name, in English or Dia-thìris" aria-label="Find a name"><div id="gllist"></div>';
  A.openSheet(h, '#glossary');
  var inp = document.getElementById('glq');
  function draw(){
    var q = A.fold(inp.value.trim()), rows = A.meta.names.filter(function(n, i, all){
      return all.findIndex(function(x){ return x[0] === n[0]; }) === i && (!q || [n[0], n[1], n[2]].concat(n[3] || []).some(function(x){ return A.fold(x).indexOf(q) >= 0; }));
    });
    rows.sort(function(a, b){ return A.fold(a[0]).localeCompare(A.fold(b[0])); });
    document.getElementById('gllist').innerHTML = rows.slice(0, q ? 300 : 120).map(glossRow).join('') + (rows.length > (q ? 300 : 120) ? '<p class="hint">…and ' + (rows.length - (q ? 300 : 120)) + ' more; narrow the search.</p>' : '');
  }
  inp.oninput = draw; draw();
};

/* ---- This day in Dia-thìr: today's day and month, the year in every era's count, and what happened on this day ---- */
A.eraYear = function(y, k){ var a = A.ageOf[k], n = y - a.first + 1; if (a.first < 0 && y > 0) n -= 1; return n; };
A.showThisDay = function(){
  var now = new Date(), m = now.getMonth() + 1, d = now.getDate(), y = now.getFullYear();
  var last = A.meta.ages[A.meta.ages.length - 1];
  var h = '<div class="thisday"><h2>This day in Dia-thìr</h2><p class="today">' + d + ' ' + esc(A.meta.months[m - 1]) + ', ' + esc(last.abbr) + ' ' + A.eraYear(y, last.key).toLocaleString('en') + '</p>' +
    '<p class="sub">' + d + ' ' + esc(A.meta.months_en[m - 1]) + '. Counted in the era of every age:</p><div class="yearsacross">' +
    A.meta.ages.map(function(a){ return '<span><b style="color:var(' + a.css + ')">' + esc(a.abbr) + '</b> ' + A.eraYear(y, a.key).toLocaleString('en') + ' <small>' + esc(a.era_dt) + '</small></span>'; }).join('') + '</div>';
  var draw = function(){
    var rows = '';
    AGE_KEYS.forEach(function(k){
      var ids = (A.eraLoaded[k] ? A.order[k] : A.masterIds.filter(function(i){ return A.EV[i].age === k; })).filter(function(i){ var e = A.EV[i]; return e.m === m && e.d === d; });
      rows += '<h3 style="color:' + A.ageColor(k) + '">' + esc(A.ageName(k)) + '</h3>' + (ids.length ? '<div class="rows">' + ids.map(function(i){ var e = A.EV[i];
        return '<button data-go="' + esc(i) + '" data-scope="' + k + '"><span class="d">' + esc(e.date) + '</span><b>' + A.md(e.title) + '</b></button>'; }).join('') + '</div>' : '<p class="hint">Nothing is recorded on this day.</p>');
    });
    return rows;
  };
  A.openSheet(h + '<div id="tdrows">' + draw() + '</div></div>', '#thisday');
  if (!A.allLoaded()) A.loadAll().then(function(){ var el = document.getElementById('tdrows'); if (el) el.innerHTML = draw(); });
};

/* ---- the small web: an event's links, one and two steps out ---- */
A.showWeb = function(id){
  var e = A.EV[id]; if (!e) return;
  var W = 480, H = 440, cx = W / 2, cy = H / 2, nodes = [{id: id, x: cx, y: cy, r: 13, ring: 0}], edges = [], at = {};
  at[id] = nodes[0];
  var one = [];
  (e.links || []).forEach(function(l){ if (!at[l.to] && one.length < 12) { var n = {id: l.to, ring: 1, l: l}; at[l.to] = n; one.push(n); } if (at[l.to]) edges.push([id, l.to, l.arrow]); });
  one.forEach(function(n, i){ var a = -Math.PI / 2 + i * 2 * Math.PI / Math.max(1, one.length); n.a = a; n.x = cx + 118 * Math.cos(a); n.y = cy + 118 * Math.sin(a); n.r = 10; nodes.push(n); });
  var two = [];
  one.forEach(function(n){
    var t = A.EV[n.id]; if (!t) return;
    (t.links || []).forEach(function(l){
      if (!at[l.to] && two.length < 24) { var m = {id: l.to, ring: 2, l: l, parent: n}; at[l.to] = m; two.push(m); }
      if (at[l.to] && at[l.to].ring === 2) edges.push([n.id, l.to, l.arrow]);
    });
  });
  var perParent = {};
  two.forEach(function(m){ (perParent[m.parent.id] = perParent[m.parent.id] || []).push(m); });
  Object.keys(perParent).forEach(function(p){
    var list = perParent[p], base = at[p].a, spread = Math.min(0.9, 2 * Math.PI / Math.max(1, one.length) * 0.8);
    list.forEach(function(m, i){ var a = base + (list.length > 1 ? (i / (list.length - 1) - 0.5) * spread : 0); m.x = cx + 196 * Math.cos(a); m.y = cy + 196 * Math.sin(a); m.r = 7; nodes.push(m); });
  });
  function title(n){ var t = A.EV[n.id]; return (t ? t.title : (n.l && n.l.title) || n.id).replace(/[*_]/g, ''); }
  function col(n){ var t = A.EV[n.id]; return t ? A.cat(t).color : '#777'; }
  var svg = '<svg class="web" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="The links of this event">';
  edges.forEach(function(ed){ var a = at[ed[0]], b = at[ed[1]]; if (a && b && a.x != null && b.x != null) svg += '<line x1="' + a.x.toFixed(1) + '" y1="' + a.y.toFixed(1) + '" x2="' + b.x.toFixed(1) + '" y2="' + b.y.toFixed(1) + '"/>' +
    (a.ring === 0 ? '<text class="lab" x="' + ((a.x + b.x) / 2).toFixed(1) + '" y="' + ((a.y + b.y) / 2 - 3).toFixed(1) + '" text-anchor="middle">' + esc(ed[2]) + '</text>' : ''); });
  nodes.forEach(function(n){
    if (n.x == null) return;
    var t = title(n), s = t.length > 24 ? t.slice(0, 23) + '…' : t, anchor = n.ring === 0 ? 'middle' : (n.x < cx - 5 ? 'end' : n.x > cx + 5 ? 'start' : 'middle');
    var dx = n.ring === 0 ? 0 : (anchor === 'end' ? -n.r - 3 : anchor === 'start' ? n.r + 3 : 0), dy = n.ring === 0 ? n.r + 14 : (anchor === 'middle' ? (n.y < cy ? -n.r - 4 : n.r + 12) : 4);
    svg += '<g class="n" data-go="' + esc(n.id) + '" tabindex="0" role="button" aria-label="' + esc(t) + '"><title>' + esc(t) + '</title><circle cx="' + n.x.toFixed(1) + '" cy="' + n.y.toFixed(1) + '" r="' + n.r + '" fill="' + col(n) + '" stroke="' + (n.ring === 0 ? '#c9a435' : 'rgba(255,255,255,.3)') + '" stroke-width="' + (n.ring === 0 ? 2.5 : 1) + '"/>' +
      (n.ring < 2 ? '<text x="' + (n.x + dx).toFixed(1) + '" y="' + (n.y + dy).toFixed(1) + '" text-anchor="' + anchor + '">' + esc(s) + '</text>' : '') + '</g>';
  });
  svg += '</svg>';
  var h = '<h2>The web of an event</h2><p class="sub">' + A.md(e.title) + ' — ' + esc(e.date) + '</p>' + svg +
    '<p class="hint">The inner ring: its own links; the outer ring: their links. Choose any to go to it.</p><div class="rows">' +
    one.map(function(n){ return '<button data-go="' + esc(n.id) + '"><span class="d">' + esc(n.l.arrow + ' ' + n.l.label + ' · ' + (n.l.year || n.l.date || '')) + '</span><b>' + A.md(title(n)) + '</b></button>'; }).join('') + '</div>';
  A.openSheet(h, null);
  var sv = document.querySelector('#sheet svg.web');
  if (sv) sv.addEventListener('keydown', function(ev){ var g = ev.target.closest('g.n'); if (g && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); A.act(g); } });
};

/* ---- Read the telling ---- */
A.showTelling = function(id){
  var e = A.EV[id], t = e && e.told_in && A.meta.tellings[e.told_in.key];
  if (!t) { A.toast('The telling of this event is not in this build.'); return; }
  A.openSheet('<h2>' + esc(t.section || t.book) + '</h2><p class="sub">' + esc(t.book) + (t.section && t.book !== t.section ? '' : '') + ' · told of ' + A.md(e.title) + ', ' + esc(e.date) + '</p>' +
    '<div class="telling">' + A.gloss(t.html) + '</div>' + (t.more ? '<p class="hint">The telling goes on in the book.</p>' : '') +
    '<p><button class="pill" data-go="' + esc(id) + '">◂ Back to the event</button></p>', null);
};
})();
