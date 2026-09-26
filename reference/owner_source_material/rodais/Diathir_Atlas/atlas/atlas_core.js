/* atlas_core.js -- the Atlas's data, choices, links (#...) and the three visible controls.
   Data arrives as script files (data/*.js calling ATLAS_LOAD), so the Annals work from the launcher's server and
   from the folder alike. The master events come first; each age's own annals (data/era_<K>.js) load after the page
   is drawn, and anything that needs them waits for them. */
var ATLAS = {
  meta: {ages: [], categories: {}, link_types: {}, threads: {}, people: {}, trees: [], names: [], maps: {}, burgs: {}, shots: {}, tellings: {}, audio: {}, months: [], months_en: []},
  EV: {},              // id -> event
  masterIds: [],       // the master events, in order
  order: {},           // age -> [ids] (master and era events) once the age's annals are in
  eraLoaded: {},
  state: {scope: 'M', detail: 'hi', q: '', cats: {}, canon: false, thread: null},
  prefs: {},
  ageOf: {}            // age key -> its meta
};
var AGE_KEYS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII'];

function ATLAS_LOAD(kind, a, b){
  if (kind === 'meta') { ATLAS.meta = a; a.ages.forEach(function(x){ ATLAS.ageOf[x.key] = x; }); }
  else if (kind === 'master') a.forEach(function(e){ ATLAS.EV[e.id] = e; ATLAS.masterIds.push(e.id); });
  else if (kind === 'era') {
    b.events.forEach(function(e){ ATLAS.EV[e.id] = e; });
    ATLAS.order[a] = b.order; ATLAS.eraLoaded[a] = true;
    (ATLAS._wait[a] || []).forEach(function(f){ f(); }); delete ATLAS._wait[a];
    if (ATLAS.onEra) ATLAS.onEra(a);
  }
  else if (kind === 'overlay') { ATLAS.overlayData[a] = b; (ATLAS._wait['ov' + a] || []).forEach(function(f){ f(); }); delete ATLAS._wait['ov' + a]; }
  else if (kind === 'posters') { ATLAS.posters = a; (ATLAS._wait.posters || []).forEach(function(f){ f(); }); delete ATLAS._wait.posters; }
}
ATLAS.overlayData = {};
/* a data file (overlay_<K>.js, posters/posters.js) loaded once, on demand; resolves false when it is not there */
ATLAS.loadScript = function(src, key, have){
  return new Promise(function(done){
    if (have()) return done(true);
    (ATLAS._wait[key] = ATLAS._wait[key] || []).push(function(ok){ done(ok !== false); });
    if (ATLAS._wait[key].length > 1) return;
    var s = document.createElement('script'); s.src = src; s.async = true;
    s.onerror = function(){ var w = ATLAS._wait[key] || []; delete ATLAS._wait[key]; s.remove(); w.forEach(function(f){ f(false); }); };
    document.head.appendChild(s);
  });
};
ATLAS._wait = {};

/* ---- small helpers ---- */
ATLAS.fold = function(s){ return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); };
ATLAS.esc = function(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
ATLAS.md = function(s){ return ATLAS.esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\*(.+?)\*/g, '<i>$1</i>'); };
ATLAS.toast = function(msg){
  var t = document.getElementById('atl-toast');
  if (!t) { t = document.createElement('div'); t.id = 'atl-toast'; t.className = 'toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
  t.textContent = msg; t.hidden = false; clearTimeout(ATLAS._tt); ATLAS._tt = setTimeout(function(){ t.hidden = true; }, 2600);
};
ATLAS.ageName = function(k){ var a = ATLAS.ageOf[k]; return a ? a.dt : 'the whole chronicle'; };
ATLAS.ageColor = function(k){ var a = ATLAS.ageOf[k]; return a ? 'var(' + a.css + ')' : 'var(--parchment)'; };
ATLAS.shortDate = function(e){ return e ? (e.year || e.date || '') : ''; };
ATLAS.dayMonth = function(e){ return e && e.m ? e.d + ' ' + ATLAS.meta.months[e.m - 1] : ''; };
ATLAS.ageOfId = function(id){
  var e = ATLAS.EV[id]; if (e) return e.age;
  var m = /^E(I|II|III|IV|V|VI|VII)-/.exec(id); return m ? m[1] : null;
};
ATLAS.cat = function(e){ return ATLAS.meta.categories[e && e.category] || {name: '', color: '#888', icon: '·'}; };

/* ---- the choices a viewer makes, kept between visits (atlas.* keys; startMap clears storage and calls persist) ---- */
ATLAS.loadPrefs = function(){
  try { var raw = localStorage.getItem('atlas.prefs'); if (raw) ATLAS.prefs = JSON.parse(raw) || {}; } catch(e){ ATLAS.prefs = {}; }
};
ATLAS.persist = function(){ try { localStorage.setItem('atlas.prefs', JSON.stringify(ATLAS.prefs)); } catch(e){} };
ATLAS.setPref = function(k, v){ ATLAS.prefs[k] = v; ATLAS.persist(); };

/* ---- the ages' own annals, loaded on demand ---- */
ATLAS.loadEra = function(k){
  return new Promise(function(done){
    if (ATLAS.eraLoaded[k] || AGE_KEYS.indexOf(k) < 0) return done();
    (ATLAS._wait[k] = ATLAS._wait[k] || []).push(done);
    if (ATLAS._wait[k].length > 1) return;
    var s = document.createElement('script'); s.src = 'data/era_' + k + '.js'; s.async = true;
    s.onerror = function(){   // no era file: the age is its master events alone
      ATLAS.order[k] = ATLAS.masterIds.filter(function(i){ return ATLAS.EV[i].age === k; }); ATLAS.eraLoaded[k] = true;
      (ATLAS._wait[k] || []).forEach(function(f){ f(); }); delete ATLAS._wait[k];
    };
    document.head.appendChild(s);
  });
};
ATLAS.loadAll = function(){ return Promise.all(AGE_KEYS.map(ATLAS.loadEra)); };
ATLAS.allLoaded = function(){ return AGE_KEYS.every(function(k){ return ATLAS.eraLoaded[k]; }); };

/* ---- shareable links: #<age>/<event id>, #person/<id>, #place/<ref>, #thread/<id>, and a few more ---- */
ATLAS.hashFor = function(){
  var s = ATLAS.state;
  if (s.thread) return '#thread/' + encodeURIComponent(s.thread);
  var h = '#' + s.scope + (ATLAS.focus ? '/' + encodeURIComponent(ATLAS.focus) : '');
  if (document.body.dataset.tab === 'map') h = '#map/' + s.scope + (ATLAS.focus ? '/' + encodeURIComponent(ATLAS.focus) : '');
  return h;
};
ATLAS.setHash = function(h, push){
  h = h || ATLAS.hashFor();
  if (location.hash === h) return;
  ATLAS._ownHash = h;
  try { history[push ? 'pushState' : 'replaceState'](null, '', h); } catch(e){ location.hash = h; }
};
ATLAS.route = function(){
  var h = decodeURIComponent(location.hash.replace(/^#/, ''));
  if (!h) return false;
  var p = h.split('/'), head = p[0];
  if (head === 'person' && p[1]) { ATLAS.showPerson(p.slice(1).join('/')); return true; }
  if (head === 'place' && p[1]) { ATLAS.showPlacePage(p.slice(1).join('/')); return true; }
  if (head === 'thread' && p[1]) { ATLAS.followThread(p[1], true); return true; }
  if (head === 'tree' && p[1]) { ATLAS.showTree(p[1]); return true; }
  if (head === 'glossary') { ATLAS.showGlossary(); return true; }
  if (head === 'thisday') { ATLAS.showThisDay(); return true; }
  if (head === 'compare') { ATLAS.showCompare(p[1], p[2], p.slice(3).join('/') || null); return true; }
  if (head === 'posters') { ATLAS.showPosters(); return true; }
  if (head === 'search' && p[1]) { ATLAS.search(p.slice(1).join('/')); return true; }
  var map = head === 'map'; if (map) p = p.slice(1);
  var scope = p[0] === 'M' || ATLAS.ageOf[p[0]] ? p[0] : null, id = p[1];
  if (!scope) return false;
  if (map) {
    ATLAS.setScope(scope, {silent: true, noMap: true});
    if (id) ATLAS.goTo(id, {scope: scope, map: true}); else showTab('map');
  } else if (id) ATLAS.goTo(id, {scope: scope});
  else ATLAS.setScope(scope);
  return true;
};
window.addEventListener('hashchange', function(){
  if (ATLAS._ownHash === location.hash) return;
  ATLAS.route();
});

/* ---- the three visible controls ---- */
ATLAS.drawTools = function(){
  var t = document.getElementById('tools'), s = ATLAS.state, h = '';
  h += '<div class="ribbon" role="group" aria-label="Choose an age">';
  h += '<button data-scope="M" title="The whole chronicle, the master map" aria-pressed="' + (s.scope === 'M') + '">All ages</button>';
  ATLAS.meta.ages.forEach(function(a){
    h += '<button data-scope="' + a.key + '" style="--c:var(' + a.css + ')" aria-pressed="' + (s.scope === a.key) + '" title="' +
      ATLAS.esc(a.dt + ' · ' + a.en + ' · ' + a.span) + '">' + a.key + '</button>';
  });
  h += '</div><div class="detail" role="group" aria-label="How much to show">';
  [['hi', 'Highlights', 'The chronicle\'s own events'], ['std', 'Standard', 'With the ages\' linked and notable events'], ['all', 'Everything', 'Every event of every age']].forEach(function(d){
    h += '<button data-detail="' + d[0] + '" title="' + d[2] + '" aria-pressed="' + (s.detail === d[0]) + '">' + d[1] + '</button>';
  });
  h += '</div><div class="tl-search"><input id="q" type="search" autocomplete="off" placeholder="Search in English or Dia-thìris" aria-label="Search the annals in English or Dia-thìris" value="' + ATLAS.esc(s.q) + '"></div>';
  h += '<button class="tl-more" id="moreBtn" aria-haspopup="true" aria-expanded="false" title="More: playback, filters, threads, people, places, glossary">⋯</button>';
  h += '<div class="menu" id="menu" hidden></div><div class="tl-status" id="count" aria-live="polite"></div>';
  t.innerHTML = h;
  t.onclick = function(ev){
    var b = ev.target.closest('button'); if (!b) return;
    if (b.dataset.scope) ATLAS.setScope(b.dataset.scope, {clear: true});
    else if (b.dataset.detail) ATLAS.setDetail(b.dataset.detail);
    else if (b.id === 'moreBtn') ATLAS.toggleMenu();
  };
  var q = document.getElementById('q'), timer;
  q.addEventListener('input', function(){ clearTimeout(timer); timer = setTimeout(function(){ ATLAS.search(q.value); }, 220); });
  q.addEventListener('keydown', function(ev){ if (ev.key === 'Enter') { clearTimeout(timer); ATLAS.search(q.value); } });
};
ATLAS.syncTools = function(){
  var s = ATLAS.state;
  document.querySelectorAll('.ribbon button').forEach(function(b){ b.setAttribute('aria-pressed', !s.thread && !s.q && b.dataset.scope === s.scope); });
  document.querySelectorAll('.detail button').forEach(function(b){ b.setAttribute('aria-pressed', b.dataset.detail === s.detail); });
  document.body.dataset.detail = s.detail;
  var q = document.getElementById('q'); if (q && document.activeElement !== q) q.value = s.q;
  var sel = document.getElementById('mapEra'); if (sel) sel.value = ATLAS.mapWanted();
};
ATLAS.setDetail = function(d){
  ATLAS.state.detail = d; ATLAS.setPref('detail', d); ATLAS.syncTools(); ATLAS.render();
};
ATLAS.setScope = function(k, o){
  o = o || {};
  var s = ATLAS.state;
  if (o.clear) { s.thread = null; s.q = ''; }
  s.scope = k; ATLAS.focus = null; ATLAS.setPref('scope', k);
  ATLAS.syncTools();
  if (!o.noRender) ATLAS.render();
  if (!o.noMap && document.body.dataset.tab === 'map') startMap(ATLAS.mapWanted());
  if (!o.silent) ATLAS.setHash(null, true);
};
ATLAS.search = function(q){
  q = String(q || '').trim(); ATLAS.state.q = q;
  if (q) ATLAS.state.thread = null;
  ATLAS.syncTools(); ATLAS.render(); ATLAS.setHash(q ? '#search/' + encodeURIComponent(q) : null);
};

/* ---- the ⋯ menu ---- */
ATLAS.toggleMenu = function(open){
  var m = document.getElementById('menu'), b = document.getElementById('moreBtn');
  open = open == null ? m.hidden : open;
  if (open) ATLAS.drawMenu();
  m.hidden = !open; b.setAttribute('aria-expanded', open);
};
ATLAS.drawMenu = function(){
  var m = document.getElementById('menu'), s = ATLAS.state, h = '';
  h += '<h4>Open</h4><div class="items">' +
    '<button data-m="play">▶ Play the years</button><button data-m="threads">Threads</button>' +
    '<button data-m="people">People &amp; family trees</button><button data-m="places">Places across time</button>' +
    '<button data-m="glossary">Glossary</button><button data-m="thisday">This day in Dia-thìr</button>' +
    '<button data-m="compare">Then and now</button><button data-m="posters">Posters</button><button data-m="share">Copy a link to this view</button></div>';
  h += '<h4>Show</h4><div class="cats">';
  Object.keys(ATLAS.meta.categories).forEach(function(c){
    var cc = ATLAS.meta.categories[c];
    h += '<label><input type="checkbox" data-cat="' + c + '"' + (s.cats[c] === false ? '' : ' checked') + '><span class="dot" style="--cc:' + cc.color + '"></span><span>' + ATLAS.esc(cc.name) + '</span></label>';
  });
  h += '</div><div class="cats" style="margin-top:6px"><label><input type="checkbox" data-canon="1"' + (s.canon ? ' checked' : '') + '><span class="dot" style="--cc:var(--holy)"></span><span>◆ the chronicle\'s entries only</span></label></div>';
  var guessed = ATLAS.masterIds.some(function(i){ return ATLAS.EV[i].cat_guess; });
  if (guessed) h += '<p style="font-size:14px;color:var(--parchment-dim);margin:8px 0 0">Where the annals do not yet name an event\'s kind, its dot is a guess from its words (an outlined badge).</p>';
  m.innerHTML = h;
  m.onclick = function(ev){
    var b = ev.target.closest('button[data-m]'); if (!b) return;
    ATLAS.toggleMenu(false);
    ({play: function(){ ATLAS.showPlaybar(true); }, threads: ATLAS.showThreads, people: ATLAS.showPeople, places: ATLAS.showPlaces,
      glossary: ATLAS.showGlossary, thisday: ATLAS.showThisDay, compare: function(){ ATLAS.showCompare(); }, posters: function(){ ATLAS.showPosters(); }, share: ATLAS.share})[b.dataset.m]();
  };
  m.onchange = function(ev){
    var i = ev.target;
    if (i.dataset.cat) { s.cats[i.dataset.cat] = i.checked; ATLAS.setPref('cats', s.cats); }
    if (i.dataset.canon) { s.canon = i.checked; ATLAS.setPref('canon', s.canon); }
    ATLAS.render();
  };
};
document.addEventListener('click', function(ev){
  var m = document.getElementById('menu');
  if (m && !m.hidden && !ev.target.closest('#menu') && !ev.target.closest('#moreBtn')) ATLAS.toggleMenu(false);
});
ATLAS.share = function(){
  var url = location.href;
  function ok(){ ATLAS.toast('Link copied: ' + url); }
  try { navigator.clipboard.writeText(url).then(ok, function(){ window.prompt('Copy this link', url); }); }
  catch(e){ window.prompt('Copy this link', url); }
};

/* ---- the sheet: one panel for the pages (person, place, thread, tree, glossary, this day, compare, web, telling) ---- */
ATLAS.sheetStack = [];
ATLAS.openSheet = function(html, hash, again){
  var sh = document.getElementById('sheet');
  if (!sh) { sh = document.createElement('aside'); sh.id = 'sheet'; sh.className = 'sheet'; sh.setAttribute('aria-label', 'Page'); document.body.appendChild(sh); }
  if (!again) ATLAS.sheetStack.push({html: html, hash: hash});
  sh.classList.remove('wide');
  var back = ATLAS.sheetStack.length > 1 ? '<button data-sheet="back">◂ Back</button>' : '<span></span>';
  sh.innerHTML = '<div class="bar">' + back + '<button data-sheet="close" aria-label="Close">Close ✕</button></div>' + html;
  sh.hidden = false; sh.scrollTop = 0;
  sh.onclick = function(ev){
    var b = ev.target.closest('[data-sheet],[data-go],[data-person],[data-place],[data-thread],[data-tree],[data-mapat],[data-play],[data-cmp]');
    if (!b) return;
    if (b.dataset.sheet === 'close') return ATLAS.closeSheet();
    if (b.dataset.sheet === 'back') { ATLAS.sheetStack.pop(); var top = ATLAS.sheetStack[ATLAS.sheetStack.length - 1]; ATLAS.openSheet(top.html, top.hash, true); if (top.hash) ATLAS.setHash(top.hash); return; }
    ATLAS.act(b);
  };
  if (hash) ATLAS.setHash(hash, !again);
  var f = sh.querySelector('input[type=search]'); if (f && window.matchMedia('(min-width:760px)').matches) f.focus();
};
ATLAS.closeSheet = function(){
  var sh = document.getElementById('sheet'); if (sh) sh.hidden = true;
  ATLAS.sheetStack = []; ATLAS.setHash(ATLAS.hashFor());
};
/* one handler for every link-like button anywhere: data-go (an event), data-person, data-place, data-thread, data-tree, data-mapat */
ATLAS.act = function(b){
  if (b.dataset.go) { var sh = document.getElementById('sheet'); if (sh && window.matchMedia('(max-width:760px)').matches) sh.hidden = true;
    ATLAS.goTo(b.dataset.go, {scope: b.dataset.scope}); return; }
  if (b.dataset.person) return ATLAS.showPerson(b.dataset.person);
  if (b.dataset.place) return ATLAS.showPlacePage(b.dataset.place);
  if (b.dataset.thread) return ATLAS.showThread(b.dataset.thread);
  if (b.dataset.tree) return ATLAS.showTree(b.dataset.tree, b.dataset.me);
  if (b.dataset.mapat) { var p = b.dataset.mapat.split('|'); ATLAS.closeSheet(); flyTo(p[1], null, p[0]); return; }
  if (b.dataset.cmp) return ATLAS.showCompare(null, null, b.dataset.cmp);
  if (b.dataset.play) { var a = new Audio(b.dataset.play); a.play().catch(function(){ ATLAS.toast('The recording could not be played.'); }); }
};

/* ---- start ---- */
ATLAS.start = function(){
  ATLAS.loadPrefs();
  var p = ATLAS.prefs, s = ATLAS.state;
  if (p.detail) s.detail = p.detail;
  if (p.scope && (p.scope === 'M' || ATLAS.ageOf[p.scope])) s.scope = p.scope;
  if (p.cats) s.cats = p.cats;
  if (p.canon) s.canon = true;
  ATLAS.drawTools(); ATLAS.syncTools();
  ATLAS.mapControls();
  ATLAS.render();
  showList();
  try { ATLAS.route(); } catch(e){ console.error(e); }
  // the ages' own annals come in after the first drawing, so the page is quick to open
  setTimeout(function(){ ATLAS.loadAll(); }, 300);
};

/* the tab buttons keep the link in step (#map/<age> or #<age>) */
(function(){
  var show = window.showTab;
  window.showTab = function(name){ show(name); if (ATLAS.meta.ages.length) ATLAS.setHash(); };
})();
