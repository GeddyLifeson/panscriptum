/* atlas_eras.js -- the eight maps (the master Diathir.map and maps/Diathir_Age_I..VII.map) in the embedded
   map-maker, flights to a place on the right age's map, the record of a place across time, and "compare two ages".
   The template's startMap/openGenerator ask ATLAS which map to open (mapWanted, mapFile) and how to know it is in
   (mapIsLoaded); an age's map is the island at the close of that age. */
(function(){
var A = ATLAS, esc = A.esc;

A.mapWant = null;
A.mapWanted = function(){
  if (A.mapWant && (A.mapWant === 'M' || A.meta.maps[A.mapWant])) return A.mapWant;
  var s = A.state.scope; return (s !== 'M' && A.meta.maps[s]) ? s : 'M';
};
var baseSetScope = A.setScope;
A.setScope = function(k, o){ A.mapWant = k; baseSetScope(k, o); };
A.mapLabel = function(key){
  if (key === 'M') return 'Dia-thìr today (the whole chronicle)';
  var a = A.ageOf[key]; return a ? a.dt + ' (' + a.en + ')' : key;
};
A.mapTitle = function(key){ return key === 'M' ? 'Opening the map of Dia-thìr' : 'Opening the map of ' + A.mapLabel(key) + ', at its close'; };
A.mapFile = function(key){ var m = A.meta.maps[key]; return m ? m.file : null; };
A.mapBurgs = function(key){ var m = A.meta.maps[key]; return m ? Math.max(1, m.burgs) : 500; };
A.mapIsLoaded = function(w, key){
  var m = A.meta.maps[key], B = w.pack.burgs;
  if (!m) return B.length > 500;
  return B.length === m.n && !!B[m.probe[0]] && B[m.probe[0]].name === m.probe[1];
};
A.mapReady = function(w, key){
  var sel = document.getElementById('mapEra'); if (sel) sel.value = key;
  document.getElementById('panel-map').dataset.map = key;
};

/* the age chooser on the map itself */
A.mapControls = function(){
  var stage = document.querySelector('#panel-map .stage'); if (!stage || document.getElementById('mapEra')) return;
  var d = document.createElement('div'); d.className = 'mapera';
  var h = '<select id="mapEra" aria-label="The map of which age">';
  h += '<option value="M">All ages · today</option>';
  A.meta.ages.forEach(function(a){ if (A.meta.maps[a.key]) h += '<option value="' + a.key + '">' + a.key + ' · ' + esc(a.dt) + '</option>'; });
  d.innerHTML = h + '</select>'; stage.appendChild(d);
  document.getElementById('mapEra').onchange = function(){ A.setScope(this.value, {clear: true}); };
  document.getElementById('mapEra').value = A.mapWanted();
};

/* ---- places: the master record (PLACES), names on every age's map (meta.burgs), and every event there ---- */
function burgId(ref){ var p = /^burg:(\d+)$/.exec(ref || ''); return p ? p[1] : null; }
function azgaarId(ref, key){   // an age's own new town (burg:4001) is a different id on that age's map
  var id = burgId(ref), m = A.meta.maps[key]; if (!id) return null;
  return m && m.placeIds && m.placeIds[id] != null ? String(m.placeIds[id]) : (key === 'M' || Number(id) < 1000 ? id : null);
}
A.placeNames = function(ref){
  var out = [], p = PLACES[ref]; if (p) out.push(p.name);
  ['M'].concat(AGE_KEYS).forEach(function(k){ var i = azgaarId(ref, k), n = i && A.meta.burgs[i] && A.meta.burgs[i][k]; if (n && out.indexOf(n) < 0) out.push(n); });
  return out;
};
A.placeName = function(ref){
  if (PLACES[ref]) return PLACES[ref].name;
  var n = A.placeNames(ref); if (n.length) return n[0];
  for (var i in A.EV) if (A.EV[i].place === ref && A.EV[i].place_name) return A.EV[i].place_name;
  return ref;
};
A.byPlace = function(){
  var out = {};
  Object.keys(A.EV).forEach(function(i){ var e = A.EV[i]; if (e.place) (out[e.place] = out[e.place] || []).push(e); });
  Object.keys(out).forEach(function(r){ out[r].sort(function(a, b){ return a.y - b.y || a.m - b.m || a.d - b.d; }); });
  return out;
};
A.placeRefs = function(){
  var seen = {}, out = [];
  Object.keys(PLACES).concat(Object.keys(A.byPlace())).forEach(function(r){ if (!seen[r]) { seen[r] = 1; out.push(r); } });
  return out;
};
A.placeHTML = function(ref, o){
  o = o || {};
  var p = PLACES[ref] || {}, key = document.getElementById('panel-map').dataset.map || 'M';
  var h = '<h2>' + esc(A.placeName(ref)) + '</h2>';
  var i = azgaarId(ref, key), here = i && A.meta.burgs[i] && A.meta.burgs[i][key];
  if (o.drawer && key !== 'M') h += '<p class="facts">On the map of ' + esc(A.mapLabel(key)) + ': ' + (here ? '<b>' + esc(here) + '</b>' : 'not yet a town, or no longer one') + '.</p>';
  if (p.facts) h += '<p class="facts">' + esc(p.facts) + '</p>';
  if (p.founded) h += '<p class="facts">Founded ' + esc(p.founded) + (p.by ? ' by ' + esc(p.by) : '') + '.</p>';
  if (p.history) h += '<p>' + A.gloss(A.md(p.history)) + '</p>';
  if (p.known) h += '<p class="facts">Known for ' + esc(p.known.replace(/\.$/, '')) + '.</p>';
  if (burgId(ref)) {
    h += '<h3>Through the ages</h3><table class="across"><tbody>';
    AGE_KEYS.concat(['M']).forEach(function(k){
      if (!A.meta.maps[k]) return;
      var j = azgaarId(ref, k), n = j && A.meta.burgs[j] && A.meta.burgs[j][k];
      h += '<tr><td>' + (k === 'M' ? 'today' : k) + '</td><td>' + (n ? esc(n) : '<span class="gone">not a town at the close of this age</span>') +
        '</td><td><button data-mapat="' + k + '|' + esc(ref) + '" title="Show this spot on the map of ' + esc(A.mapLabel(k)) + '">map</button></td></tr>';
    });
    h += '</tbody></table>';
  } else if (ref) {
    h += '<p><button class="pill" data-mapat="' + A.mapWanted() + '|' + esc(ref) + '">◎ Show on the map</button></p>';
  }
  var evs = A.byPlace()[ref] || [];
  if (evs.length) {
    h += '<h3>' + evs.length + ' event' + (evs.length > 1 ? 's' : '') + ' recorded here</h3>';
    var age = null;
    evs.forEach(function(e){
      if (e.age !== age) { age = e.age; h += '<p class="hint" style="margin:10px 0 2px;color:' + A.ageColor(age) + '">' + esc(A.ageName(age)) + '</p>'; }
      h += '<div class="rows"><button class="ev' + (e.id === o.evId ? ' cur' : '') + '" data-go="' + esc(e.id) + '" data-scope="' + (e.master && !o.eraScope ? '' : e.age) + '"><span class="d">' + esc(e.date) + '</span><b>' + A.md(e.title) + '</b></button></div>';
    });
  }
  if (!A.allLoaded()) h += '<p class="hint">Opening the ages\' own annals; their events here will show when you open this page again.</p>';
  return h;
};
A.showPlacePage = function(ref){ A.openSheet(A.placeHTML(ref), '#place/' + encodeURIComponent(ref)); };

/* the drawer on the map tab (the template's showPlace, showList and listPlaces, now across the ages) */
window.showPlace = function(ref, evId){
  var d = document.getElementById('drawer');
  d.innerHTML = '<button class="back" onclick="showList()">◂ All places</button>' + A.placeHTML(ref, {evId: evId, drawer: true});
  d.hidden = false; d.scrollTop = 0; document.getElementById('drawtoggle').textContent = 'Record ◂';
  d.onclick = function(ev){ var b = ev.target.closest('[data-go],[data-mapat],[data-person]'); if (!b) return;
    if (b.dataset.go) { showTab('timeline'); A.goTo(b.dataset.go, {scope: b.dataset.scope || undefined}); return; }
    A.act(b); };
  var cur = d.querySelector('.ev.cur'); if (cur) cur.scrollIntoView({block: 'center'});
};
window.showList = function(){
  var d = document.getElementById('drawer');
  d.innerHTML = '<h2>The record on the map</h2><p class="hint">Click a town or a marker on the map, or choose a place below, to read its ' +
    'history, its names through the ages and every event recorded there. Choose the age of the map at the top left.</p>' +
    '<input id="pq" type="search" placeholder="Find a place (any age\'s name)" oninput="listPlaces()"><div class="plist" id="plist"></div>';
  listPlaces();
};
window.listPlaces = function(){
  var q = A.fold((document.getElementById('pq') || {value: ''}).value.trim()), bp = A.byPlace();
  var refs = A.placeRefs().filter(function(r){ return !q || A.placeNames(r).concat([A.placeName(r)]).some(function(n){ return A.fold(n).indexOf(q) >= 0; }); });
  refs.sort(function(a, b){ return (bp[b] || []).length - (bp[a] || []).length || A.placeName(a).localeCompare(A.placeName(b)); });
  var el = document.getElementById('plist'); if (!el) return;
  el.innerHTML = refs.slice(0, q ? 200 : 80).map(function(r){
    var p = PLACES[r] || {}, names = A.placeNames(r), n = A.placeName(r), old = names.filter(function(x){ return x !== n; });
    return '<button onclick="flyTo(\'' + r + '\')"><span>' + ((bp[r] || []).length || '') + '</span>' + esc(n) +
      (old.length ? '<small>also ' + esc(old.slice(0, 3).join(', ')) + '</small>' : p.facts ? '<small>' + esc(p.facts.split(' · ').slice(0, 2).join(' · ')) + '</small>' : '') + '</button>';
  }).join('');
};
A.showPlaces = function(){
  A.openSheet('<h2>Places across time</h2><p class="sub">Every town and storied place: its names on each age\'s map and every event recorded there.</p>' +
    '<input type="search" id="spq" placeholder="A place, by any age\'s name" aria-label="Find a place"><div class="rows" id="splist"></div>', null);
  var inp = document.getElementById('spq');
  function draw(){
    var q = A.fold(inp.value.trim()), bp = A.byPlace();
    var refs = A.placeRefs().filter(function(r){ return !q || A.placeNames(r).concat([A.placeName(r)]).some(function(n){ return A.fold(n).indexOf(q) >= 0; }); });
    refs.sort(function(a, b){ return (bp[b] || []).length - (bp[a] || []).length || A.placeName(a).localeCompare(A.placeName(b)); });
    document.getElementById('splist').innerHTML = refs.slice(0, q ? 200 : 60).map(function(r){
      var names = A.placeNames(r), n = A.placeName(r), old = names.filter(function(x){ return x !== n; });
      return '<button data-place="' + esc(r) + '"><span class="n">' + ((bp[r] || []).length || '') + '</span><b>' + esc(n) + '</b>' + (old.length ? '<small>also ' + esc(old.slice(0, 4).join(', ')) + '</small>' : '') + '</button>';
    }).join('');
  }
  inp.oninput = draw; draw();
};

/* ---- flights: to a place on the map of the right age ---- */
function liveRef(w, ref, key){
  var k = ref.split(':')[0];
  if (k === 'burg') { var i = azgaarId(ref, key); return i ? 'burg:' + i : null; }
  if (k === 'marker' && key !== 'M') {   // the ages' maps number their markers afresh: find it by its name
    var name = (PLACES[ref] || {}).name, notes = w.notes || [];
    var n = name && notes.find(function(x){ return x.name === name && /^marker\d+$/.test(x.id); });
    return n ? 'marker:' + n.id.slice(6) : null;
  }
  return ref;
}
window.flyTo = function(ref, evId, key){
  if (!ref) return;
  key = key || A.mapWanted(); A.mapWant = key;
  if (document.body.dataset.tab !== 'map') showTab('map');
  if (!ready || mapKey !== key) { pending = [ref, evId]; startMap(key); return; }
  var w = fmg(), r = liveRef(w, ref, key), at = r ? locate(w, r) : null;
  if (at) { w.zoomTo(at[0], at[1], at[2], 1600); mark(w, at[0], at[1]); }
  else A.toast('That place is not drawn on the map of ' + A.mapLabel(key) + '.');
  if (evId) A.focus = evId;
  showPlace(ref, evId);
  A.setHash();
};
window.showMapBurg = function(i){
  var key = mapKey || 'M', m = A.meta.maps[key] || {}, ref = 'burg:' + i;
  Object.keys(m.placeIds || {}).forEach(function(k){ if (String(m.placeIds[k]) === String(i)) ref = 'burg:' + k; });
  showPlace(ref);
};
window.showMapMarker = function(i){
  var key = mapKey || 'M';
  if (key === 'M' && PLACES['marker:' + i]) return showPlace('marker:' + i);
  var w = fmg(), n = ((w && w.notes) || []).find(function(x){ return x.id === 'marker' + i; });
  if (!n) return;
  var master = Object.keys(PLACES).find(function(r){ return /^marker:/.test(r) && PLACES[r].name === n.name; });
  if (master) return showPlace(master);
  var d = document.getElementById('drawer'), tmp = document.createElement('div'); tmp.innerHTML = n.legend || '';
  d.innerHTML = '<button class="back" onclick="showList()">◂ All places</button><h2>' + esc(n.name) + '</h2><p class="facts">On the map of ' + esc(A.mapLabel(key)) + '</p><p>' + esc(tmp.textContent.trim()) + '</p>';
  d.hidden = false;
};
A.showEventInDrawer = function(e){
  var d = document.getElementById('drawer');
  d.innerHTML = '<button class="back" onclick="showList()">◂ All places</button><p class="facts">' + esc(e.date) + '</p><h2>' + A.md(e.title) + '</h2><p>' + A.gloss(A.md(e.body)) + '</p>' +
    '<p class="hint">No place on the map is given for this event.</p>';
  d.hidden = false;
};

/* ---- compare two ages: a split slider over the two maps' pictures ---- */
A.showCompare = function(a, b){
  var keys = AGE_KEYS.filter(function(k){ return (A.meta.shots[k] || []).length; });
  if (keys.length < 2) { A.openSheet('<h2>Compare two ages</h2><p>The pictures of the ages\' maps are not in this build.</p>'); return; }
  a = keys.indexOf(a) >= 0 ? a : keys[Math.max(0, keys.indexOf(A.state.scope) - 1)] || keys[0];
  b = keys.indexOf(b) >= 0 ? b : (keys[keys.indexOf(a) + 1] || keys[keys.length - 1]);
  var layers = (A.meta.shots[a] || []).filter(function(l){ return (A.meta.shots[b] || []).indexOf(l) >= 0; });
  var layer = layers.indexOf(A.prefs.cmpLayer) >= 0 ? A.prefs.cmpLayer : (layers.indexOf('states') >= 0 ? 'states' : layers[0]);
  function opts(sel){ return keys.map(function(k){ return '<option value="' + k + '"' + (k === sel ? ' selected' : '') + '>' + k + ' · ' + esc(A.ageOf[k].dt) + '</option>'; }).join(''); }
  function src(k){ return 'maps/shots/Diathir_Age_' + k + '_' + layer + '.png'; }
  var h = '<h2>Compare two ages</h2><p class="sub">The island at the close of each age. Drag the slider to wipe from one to the other.</p>' +
    '<div class="cmp-row"><select id="cmpA" aria-label="Left age">' + opts(a) + '</select><select id="cmpB" aria-label="Right age">' + opts(b) + '</select></div>' +
    '<select id="cmpL" aria-label="What to show">' + layers.map(function(l){ return '<option' + (l === layer ? ' selected' : '') + '>' + l + '</option>'; }).join('') + '</select>' +
    '<div class="compare" id="cmp" style="--split:50%"><img alt="' + esc(A.ageOf[b].dt) + '" src="' + src(b) + '"><img class="a" alt="' + esc(A.ageOf[a].dt) + '" src="' + src(a) + '">' +
    '<span class="handle"></span><span class="lab l">' + a + '</span><span class="lab r">' + b + '</span></div>' +
    '<input type="range" id="cmpSplit" min="0" max="100" value="50" aria-label="Wipe between the two ages">' +
    '<p><button class="pill" data-mapat="' + a + '|">Open the map of ' + a + '</button> <button class="pill" data-mapat="' + b + '|">Open the map of ' + b + '</button></p>';
  A.openSheet(h, '#compare/' + a + '/' + b, A.sheetStack.length && /^#compare/.test((A.sheetStack[A.sheetStack.length - 1] || {}).hash || ''));
  if (A.sheetStack.length && /^#compare/.test(A.sheetStack[A.sheetStack.length - 1].hash || '')) A.sheetStack[A.sheetStack.length - 1] = {html: h, hash: '#compare/' + a + '/' + b};
  var cmp = document.getElementById('cmp'), sl = document.getElementById('cmpSplit');
  sl.oninput = function(){ cmp.style.setProperty('--split', sl.value + '%'); };
  function drag(ev){ var r = cmp.getBoundingClientRect(), x = ((ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left) / r.width * 100;
    sl.value = Math.max(0, Math.min(100, x)); sl.oninput(); }
  cmp.addEventListener('pointerdown', function(ev){ drag(ev); cmp.onpointermove = drag; cmp.setPointerCapture(ev.pointerId); });
  cmp.addEventListener('pointerup', function(){ cmp.onpointermove = null; });
  document.getElementById('cmpA').onchange = function(){ A.showCompare(this.value, b); };
  document.getElementById('cmpB').onchange = function(){ A.showCompare(a, this.value); };
  document.getElementById('cmpL').onchange = function(){ A.setPref('cmpLayer', this.value); A.showCompare(a, b); };
};
})();

/* a map button with no place ("Open the map of IV") just opens that age's map */
(function(){
  var act = ATLAS.act;
  ATLAS.act = function(b){
    if (b.dataset.mapat && !b.dataset.mapat.split('|')[1]) { ATLAS.closeSheet(); ATLAS.setScope(b.dataset.mapat.split('|')[0], {clear: true}); showTab('map'); return; }
    return act(b);
  };
})();
