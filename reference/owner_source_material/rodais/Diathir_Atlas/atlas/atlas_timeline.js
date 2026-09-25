/* atlas_timeline.js -- the annals as a vertical timeline, after the Middle-earth interactive map's: era headers,
   "~ ~ ~ N years ~ ~ ~" gap markers, cards with a category dot, "View on map" and "Related (N)", typed links with
   arrows (incoming links show the reversed label), a gold highlight, cards fading in, and playback. */
(function(){
var A = ATLAS, esc = A.esc;

/* ---- which events show ---- */
var NOTABLE = {rulers: 1, war: 1, coalblood: 1};
A.detailOk = function(e, d){
  d = d || A.state.detail;
  if (e.master || d === 'all') return true;
  if (d === 'hi') return false;
  return (e.links && e.links.length) || (e.people && e.people.length) || (e.threads && e.threads.length) || e.told_in ||
    (!e.cat_guess && NOTABLE[e.category]);
};
A.filterOk = function(e){
  var s = A.state;
  if (s.cats[e.category] === false) return false;
  if (s.canon && !e.canon) return false;
  return true;
};
function idsOfAge(k){ return A.eraLoaded[k] ? A.order[k] : A.masterIds.filter(function(i){ return A.EV[i].age === k; }); }

/* bilingual search: an English word finds the Dia-thìris name it glosses, and a Dia-thìris name its English */
A.searchTerms = function(q){
  var f = A.fold(q).trim(), terms = [f];
  if (f.length < 3) return terms;
  var bare = function(x){ return A.fold(x).replace(/^(the|an|a|na|an t-|am|a')\s+/, '').replace(/[;(].*$/, '').trim(); };
  var fb = bare(f);
  // a name counts when the words asked for are most of it (so "Dùn ìseal" does not bring in every hall at Dùn ìseal)
  var covers = function(x){ x = bare(x); return x.length && x.indexOf(fb) >= 0 && fb.length >= 0.6 * x.length; };
  A.meta.names.forEach(function(n){
    var dt = A.fold(n[0]);
    if ([n[1], n[2]].concat(n[3] || []).some(covers)) { if (terms.indexOf(dt) < 0) terms.push(dt); }
    else if (covers(n[0])) [n[2], n[1]].forEach(function(x){ x = bare(x); if (x.length > 3 && terms.indexOf(x) < 0) terms.push(x); });
  });
  return terms;
};
function hay(e){
  if (!e._hay) {
    var who = (e.people || []).map(function(p){ var q = A.person(p); return q ? q.name : p; }).join(' ');
    e._hay = A.fold([e.title, e.body, e.place_name || '', e.date, e.year, e.id, who].join(' \u0001 '));
  }
  return e._hay;
}
A.matches = function(e, terms){ var h = hay(e); return terms.some(function(t){ return h.indexOf(t) >= 0; }); };

A.shownList = function(){
  var s = A.state, ages, out = [], terms = s.q ? A.searchTerms(s.q) : null;
  ages = (s.scope === 'M' || s.thread || s.q) ? AGE_KEYS : [s.scope];
  ages.forEach(function(k){
    idsOfAge(k).forEach(function(i){
      var e = A.EV[i]; if (!e) return;
      if (s.thread) { if ((e.threads || []).indexOf(s.thread) < 0) return; }
      else if (terms) { if (!A.matches(e, terms)) return; }
      else if (!A.detailOk(e)) return;
      if (!A.filterOk(e)) return;
      out.push(i);
    });
  });
  return out;
};

/* ---- glosses: the first mention of a Dia-thìris name in a card gets its English as a tooltip ---- */
var GLRX = null, GL = {};
function glossRx(){
  if (GLRX !== null) return GLRX;
  var forms = A.meta.names.map(function(n){ GL[esc(n[0])] = GL[esc(n[0])] || n[1]; return esc(n[0]); });
  forms = forms.filter(function(f, i){ return f && forms.indexOf(f) === i; }).sort(function(a, b){ return b.length - a.length; });
  if (!forms.length) return (GLRX = false);
  try {
    GLRX = new RegExp('(?<![\\p{L}\\p{N}\\-])(' + forms.map(function(f){ return f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![\\p{L}\\p{N}\\-])', 'gu');
  } catch(e){ GLRX = false; }
  return GLRX;
}
A.gloss = function(html, seen){
  var rx = glossRx(); if (!rx) return html;
  seen = seen || {};
  return html.replace(rx, function(m){
    if (seen[m]) return m; seen[m] = 1;
    return '<span class="gl" title="' + esc(GL[m] || '') + '" data-dt="' + m + '">' + m + '</span>';
  });
};

/* ---- the cards ---- */
function yearsBetween(a, b){ var n = b.y - a.y; if (a.y < 0 && b.y > 0) n -= 1; return n; }
function short(text, n){
  if (text.length <= n) return null;
  var cut = text.lastIndexOf(' ', n); return text.slice(0, cut > 120 ? cut : n);
}
A.mapKeyFor = function(e){ var s = A.state; return (s.scope === 'M' && !s.thread && !s.q && e.master) ? 'M' : e.age; };
A.person = function(id){
  var p = A.meta.people[id]; if (p) return p;
  for (var k in A.meta.people) if (A.meta.people[k].alias === id) return A.meta.people[k];
  return null;
};
A.card = function(e){
  var c = A.cat(e), seen = {}, desc = short(e.body || '', 220);
  var h = '<article class="ev-card' + (e.master ? '' : ' era') + '" id="ev-' + esc(e.id) + '" data-id="' + esc(e.id) + '" data-cat="' + esc(e.category) + '" style="--cc:' + c.color + '">';
  h += '<div class="ev-date"><span class="era-tag">' + esc(e.era || '') + '</span><span class="year-num">' + esc((e.year || '').replace(/^\S+\s/, '')) + '</span><span class="day">' + esc(A.dayMonth(e)) + '</span></div>';
  h += '<div class="ev-dot" aria-hidden="true">' + c.icon + '</div><div class="ev-main">';
  h += '<div class="ev-head"><span class="badge' + (e.cat_guess ? ' guess' : '') + '">' + esc(c.name) + '</span><h3 class="ev-title">' + A.gloss(A.md(e.title), seen) +
    (e.canon ? ' <span class="canon" title="an entry of the royal chronicle">◆</span>' : '') + '<span class="eid">' + esc(e.id) + '</span></h3></div>';
  h += '<p class="ev-desc">' + A.gloss(A.md(desc === null ? e.body : desc), seen) + (desc === null ? '' : '… <button class="more" data-act="more">more</button>') + '</p>';
  var who = (e.people || []).map(function(p){ var q = A.person(p); return q ? '<button data-person="' + esc(q.id) + '">' + esc(q.name) + '</button>' : ''; }).filter(Boolean);
  var th = (e.threads || []).map(function(t){ var x = A.meta.threads[t]; return x ? '<button class="thread-chip" style="--tc:' + esc(x.colour || '#888') + '" data-thread="' + esc(t) + '" title="' + esc(x.gloss) + '">' + esc(x.dt) + '</button>' : ''; }).join('');
  var acts = '';
  if (e.place) acts += '<button data-act="map" title="' + esc(e.place_name || '') + '">◎ View on map</button>';
  if (e.links && e.links.length) acts += '<button data-act="rel" aria-expanded="false">Related (' + e.links.length + ')</button>';
  if (e.told_in && A.meta.tellings[e.told_in.key]) acts += '<button data-act="tell">Read the telling</button>';
  h += '<div class="ev-foot"><span class="ev-people">' + (who.length ? who.join(', ') + ' ' : '') + th + '</span><span class="ev-acts">' + acts + '</span></div>';
  h += '<div class="links-panel" hidden></div></div></article>';
  return h;
};
A.linksPanel = function(e){
  var h = '<div class="links-title"><span>Related events</span><button data-act="web" title="The links one and two steps out">Web ◌</button></div>';
  e.links.forEach(function(l){
    var t = A.EV[l.to] || l, other = l.age && l.age !== e.age;
    var when = other ? (A.ageOf[l.age] ? A.ageOf[l.age].dt + ', ' : '') + (l.year || l.date || '') : (l.date || '');
    h += '<div class="link-item" data-type="' + esc(l.type) + '"><span class="link-arrow" aria-hidden="true">' + esc(l.arrow) + '</span>' +
      '<span class="link-type">' + esc(l.label) + '</span><button class="link-target" data-go="' + esc(l.to) + '">' + A.md(t.title || l.to) +
      ' <span class="link-era">' + esc(when) + (other ? ' →' : '') + '</span>' + (l.note ? ' <span class="link-note">(' + esc(l.note) + ')</span>' : '') + '</button></div>';
  });
  return h;
};

/* ---- drawing the timeline ---- */
var io = null;
A.render = function(){
  var s = A.state, tl = document.getElementById('tl');
  var needAll = s.q || s.thread || (s.scope === 'M' && s.detail !== 'hi');
  var need = needAll ? AGE_KEYS : (s.scope === 'M' ? [] : [s.scope]);
  var missing = need.filter(function(k){ return !A.eraLoaded[k]; });
  missing.forEach(function(k){ A.loadEra(k).then(A.renderSoon); });
  var ids = A.shownList(), h = '', prev = null, age = null, perAge = {};
  ids.forEach(function(i){ var k = A.EV[i].age; perAge[k] = (perAge[k] || 0) + 1; });
  ids.forEach(function(i){
    var e = A.EV[i];
    if (e.age !== age) {
      age = e.age; var a = A.ageOf[age];
      h += '<div class="era-header" style="--c:var(' + a.css + ')" data-age="' + age + '"><h2>' + esc(a.dt) + ' — ' + esc(a.span) + '</h2>' +
        '<span class="range">' + esc(a.en.charAt(0).toUpperCase() + a.en.slice(1)) + ' · ' + esc(a.era_dt) + ' (' + esc(a.era) + ')' +
        ((s.q || s.thread) ? ' · ' + perAge[age] + ' found' : '') + '</span>' +
        (s.scope === 'M' || s.q || s.thread ? '<button class="pill open" data-scope="' + age + '">Open this age with its map</button>' : '') + '</div>';
    }
    if (prev && prev.y != null && e.y != null) {
      var n = yearsBetween(prev, e);
      if (n > 100) h += '<div class="time-gap"><span>~ ~ ~ ' + n.toLocaleString('en') + ' years ~ ~ ~</span></div>';
    }
    h += A.card(e); prev = e;
  });
  if (!ids.length) h = '<p class="empty">' + (missing.length ? 'Opening the annals of the ages…' :
    s.thread ? 'No event names this thread yet. The writers tag events with threads as they go; it fills on the next build.' :
    s.q ? 'Nothing found for “' + esc(s.q) + '”, in English or in Dia-thìris.' : 'Nothing to show: every kind of event is switched off in ⋯.') + '</p>';
  tl.innerHTML = h;
  A.shown = ids;
  A.status(ids, missing);
  A.drawFound();
  if (io) io.disconnect();
  if ('IntersectionObserver' in window) {
    io = new IntersectionObserver(function(en){ en.forEach(function(x){ if (x.isIntersecting) { x.target.classList.add('vis'); io.unobserve(x.target); } }); }, {rootMargin: '0px 0px -30px 0px'});
    tl.querySelectorAll('.ev-card').forEach(function(c){ io.observe(c); });
  } else tl.classList.add('no-anim');
  if (A.onRender) A.onRender();
};
A.renderSoon = function(){ clearTimeout(A._rs); A._rs = setTimeout(function(){ var f = A.focus; A.render(); if (f && document.getElementById('ev-' + f)) A.scrollTo(f, false); }, 60); };
A.onEra = function(k){
  var s = A.state;
  if (s.q || s.thread || s.scope === k || (s.scope === 'M' && s.detail !== 'hi')) A.renderSoon();
};
A.status = function(ids, missing){
  var s = A.state, el = document.getElementById('count'); if (!el) return;
  var t = ids.length.toLocaleString('en') + ' event' + (ids.length === 1 ? '' : 's');
  if (s.thread) { var th = A.meta.threads[s.thread] || {}; t = 'Following the thread ' + esc(th.dt || s.thread) + (th.gloss ? ' (' + esc(th.gloss) + ')' : '') + ': ' + t + ' <button data-clear="1">stop following</button>'; }
  else if (s.q) t = t + ' for “' + esc(s.q) + '” in every age <button data-clear="1">clear</button>';
  else {
    var where = s.scope === 'M' ? 'the whole chronicle' : esc(A.ageName(s.scope)) + ' (' + esc(A.ageOf[s.scope].en) + ')';
    var total = 0;
    (s.scope === 'M' ? AGE_KEYS : [s.scope]).forEach(function(k){ if (A.eraLoaded[k]) total += A.order[k].length; });
    t = t + ' · ' + where + (total > ids.length && s.detail !== 'all' ? ' · <button data-detail-set="all">show all ' + total.toLocaleString('en') + '</button>' : '');
  }
  if (missing && missing.length) t += ' · opening the ages\' own annals…';
  el.innerHTML = t;
  el.onclick = function(ev){
    var b = ev.target.closest('button'); if (!b) return;
    if (b.dataset.clear) { s.q = ''; s.thread = null; A.syncTools(); A.render(); A.setHash(); }
    if (b.dataset.detailSet) A.setDetail(b.dataset.detailSet);
  };
};
A.drawFound = function(){
  var s = A.state, el = document.getElementById('found');
  if (!el) { el = document.createElement('div'); el.id = 'found'; el.className = 'found'; var tl = document.getElementById('tl'); tl.parentNode.insertBefore(el, tl); }
  if (!s.q || s.q.length < 2) { el.hidden = true; el.innerHTML = ''; return; }
  var f = A.fold(s.q), h = [];
  Object.keys(A.meta.people).forEach(function(k){ var p = A.meta.people[k]; if (A.fold(p.name).indexOf(f) >= 0 && h.length < 12) h.push('<button class="pill" data-person="' + esc(k) + '">◇ ' + esc(p.name) + '</button>'); });
  A.placeRefs().forEach(function(r){ var names = A.placeNames(r); if (h.length < 24 && names.some(function(n){ return A.fold(n).indexOf(f) >= 0; })) h.push('<button class="pill" data-place="' + esc(r) + '">○ ' + esc(A.placeName(r)) + '</button>'); });
  A.meta.names.forEach(function(n){ if (h.length < 30 && (A.fold(n[0]).indexOf(f) >= 0 || A.fold(n[2]).indexOf(f) >= 0)) h.push('<span class="pill" title="' + esc(n[1]) + '">' + esc(n[0]) + ' · <i>' + esc(n[1]) + '</i></span>'); });
  el.hidden = !h.length; el.innerHTML = h.length ? '<span>Also:</span> ' + h.join(' ') : '';
  el.onclick = function(ev){ var b = ev.target.closest('button'); if (b) A.act(b); };
};

/* ---- going to an event: same age scrolls and glows; another age opens that age's annals (and its map) ---- */
A.scrollTo = function(id, glow){
  var el = document.getElementById('ev-' + id); if (!el) return;
  el.classList.add('vis');
  el.scrollIntoView({block: 'center'});
  setTimeout(function(){ el.scrollIntoView({block: 'center', behavior: 'smooth'}); }, 90);
  if (glow !== false) {
    document.querySelectorAll('.ev-card.hl').forEach(function(x){ x.classList.remove('hl'); });
    el.classList.add('hl'); clearTimeout(A._hl); A._hl = setTimeout(function(){ el.classList.remove('hl'); }, 3000);
  }
};
A.goTo = function(id, o){
  o = o || {};
  var s = A.state, k = A.ageOfId(id), e = A.EV[id];
  var scope = o.scope || (e && e.master && s.scope === 'M' && !s.q && !s.thread ? 'M' : k);
  if (k && !A.eraLoaded[k] && !(e && scope === 'M')) return A.loadEra(k).then(function(){ A.goTo(id, o); });
  if (!e) { A.toast('That event (' + id + ') is not in the annals of this build.'); return; }
  var here = document.getElementById('ev-' + id);
  if (!here || (o.scope && o.scope !== s.scope)) {
    s.q = ''; s.thread = null;
    s.scope = scope; A.setPref('scope', scope);
    if (s.cats[e.category] === false) { s.cats[e.category] = true; A.setPref('cats', s.cats); }
    if (s.canon && !e.canon) { s.canon = false; A.setPref('canon', false); }
    if (!A.detailOk(e)) A.state.detail = A.detailOk(e, 'std') ? 'std' : 'all';
    A.syncTools(); A.render();
  }
  A.focus = id; A.mapWant = A.mapKeyFor(e);
  if (o.map || document.body.dataset.tab === 'map') {
    if (document.body.dataset.tab !== 'map') showTab('map');
    else startMap(A.mapWanted());
    if (e.place) flyTo(e.place, id, A.mapKeyFor(e)); else A.showEventInDrawer(e);
  } else {
    if (document.body.dataset.tab !== 'timeline') showTab('timeline');
    A.scrollTo(id, true);
  }
  A.setHash(null, !o.noPush);
};
A.showInAnnals = function(id){ showTab('timeline'); A.goTo(id); };

/* ---- the card's buttons ---- */
document.getElementById('tl').addEventListener('click', function(ev){
  var b = ev.target.closest('button'); if (!b) return;
  var card = b.closest('.ev-card');
  if (b.dataset.scope) { A.setScope(b.dataset.scope, {clear: true}); document.getElementById('panel-timeline').scrollTop = 0; return; }
  if (b.dataset.go || b.dataset.person || b.dataset.thread || b.dataset.place) return A.act(b);
  if (!card) return;
  var e = A.EV[card.dataset.id], act = b.dataset.act;
  A.focus = e.id; A.setHash();
  if (act === 'more') { b.parentNode.innerHTML = A.gloss(A.md(e.body)); }
  else if (act === 'map') { flyTo(e.place, e.id, A.mapKeyFor(e)); }
  else if (act === 'rel') {
    var p = card.querySelector('.links-panel'), open = p.hidden;
    if (open) p.innerHTML = A.linksPanel(e);
    p.hidden = !open; b.setAttribute('aria-expanded', open);
  }
  else if (act === 'web') A.showWeb(e.id);
  else if (act === 'tell') A.showTelling(e.id);
});

/* ---- playback: Play/Pause, Prev/Next, speed, a scrubber; Space, ←/→, Esc ---- */
var SPEEDS = {slow: 4200, normal: 2400, fast: 1100}, timer = null, pos = -1;
A.playing = false;
A.showPlaybar = function(open){
  var pb = document.getElementById('playbar');
  if (!pb) {
    pb = document.createElement('div'); pb.id = 'playbar'; pb.className = 'playbar'; pb.setAttribute('role', 'region'); pb.setAttribute('aria-label', 'Play the years');
    pb.innerHTML = '<button data-p="prev" title="Previous (←)" aria-label="Previous">⏮︎</button><button data-p="play" id="playBtn" title="Play or pause (Space)" aria-label="Play">▶︎</button>' +
      '<button data-p="next" title="Next (→)" aria-label="Next">⏭︎</button><select id="speed" aria-label="Speed"><option value="slow">Slow</option><option value="normal">Normal</option><option value="fast">Fast</option></select>' +
      '<div class="scrub"><input type="range" id="scrubber" min="0" max="0" value="0" aria-label="The years"><span id="scrubLabel"></span></div>' +
      '<button data-p="close" title="Stop (Esc)" aria-label="Close">✕</button><div class="hint">Space plays · ← → step · Esc stops · on the Map tab the map follows each event</div>';
    document.body.appendChild(pb);
    pb.onclick = function(ev){ var b = ev.target.closest('button'); if (!b) return;
      ({prev: function(){ A.pause(); A.step(-1); }, next: function(){ A.pause(); A.step(1); }, play: A.togglePlay, close: function(){ A.pause(); A.showPlaybar(false); }})[b.dataset.p](); };
    var sp = document.getElementById('speed'); sp.value = A.prefs.speed || 'normal';
    sp.onchange = function(){ A.setPref('speed', sp.value); };
    document.getElementById('scrubber').addEventListener('input', function(){ A.pause(); A.at(Number(this.value), true); });
  }
  pb.hidden = !open; document.body.classList.toggle('playing', !!open);
  if (open) { A.syncScrub(); if (pos < 0) A.at(A.firstVisible(), false); }
};
A.firstVisible = function(){
  var ids = A.shown || [], top = document.getElementById('panel-timeline').getBoundingClientRect().top + 80;
  if (A.focus && ids.indexOf(A.focus) >= 0) return ids.indexOf(A.focus);
  for (var i = 0; i < ids.length; i++) { var el = document.getElementById('ev-' + ids[i]); if (el && el.getBoundingClientRect().bottom > top) return i; }
  return 0;
};
A.syncScrub = function(){ var sc = document.getElementById('scrubber'); if (!sc) return; sc.max = Math.max(0, (A.shown || []).length - 1); sc.value = Math.max(0, pos); };
A.onRender = function(){ pos = A.focus && A.shown ? A.shown.indexOf(A.focus) : -1; A.syncScrub(); };
A.at = function(i, fly){
  var ids = A.shown || []; if (!ids.length) return;
  i = Math.max(0, Math.min(ids.length - 1, i)); var before = pos >= 0 ? A.EV[ids[pos]] : null; pos = i;
  var e = A.EV[ids[i]]; A.focus = e.id;
  document.querySelectorAll('.ev-card.cur').forEach(function(x){ x.classList.remove('cur'); });
  var el = document.getElementById('ev-' + e.id); if (el) el.classList.add('cur');
  document.getElementById('scrubLabel').textContent = (e.date || '') + ' · ' + e.title.replace(/[*_]/g, '');
  A.syncScrub();
  if (document.body.dataset.tab === 'map' && fly !== false) { if (e.place) flyTo(e.place, e.id, A.mapKeyFor(e)); else A.showEventInDrawer(e); }
  else A.scrollTo(e.id, true);
  A.setHash();
  return before && before.age !== e.age;
};
A.step = function(d){ return A.at((pos < 0 ? A.firstVisible() : pos) + d); };
A.togglePlay = function(){ A.playing ? A.pause() : A.play(); };
A.play = function(){
  A.playing = true; document.getElementById('playBtn').textContent = '⏸︎'; document.getElementById('playBtn').setAttribute('aria-label', 'Pause');
  if (pos < 0) A.at(A.firstVisible());
  (function tick(){
    var ms = SPEEDS[(document.getElementById('speed') || {}).value] || SPEEDS.normal;
    timer = setTimeout(function(){
      if (!A.playing) return;
      if (document.body.dataset.tab === 'map' && !ready) return tick();   // wait while an age's map loads
      if (pos >= (A.shown || []).length - 1) return A.pause();
      var eraChanged = A.step(1);
      if (eraChanged) { clearTimeout(timer); timer = setTimeout(tick, ms * 1.6); } else tick();
    }, ms);
  })();
};
A.pause = function(){
  A.playing = false; clearTimeout(timer);
  var b = document.getElementById('playBtn'); if (b) { b.textContent = '▶︎'; b.setAttribute('aria-label', 'Play'); }
};
document.addEventListener('keydown', function(ev){
  var pb = document.getElementById('playbar');
  if (!pb || pb.hidden || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (/^(INPUT|SELECT|TEXTAREA)$/.test((ev.target || {}).tagName) && ev.target.id !== 'scrubber') return;
  if (ev.key === ' ' || ev.code === 'Space') { ev.preventDefault(); A.togglePlay(); }
  else if (ev.key === 'ArrowRight') { ev.preventDefault(); A.pause(); A.step(1); }
  else if (ev.key === 'ArrowLeft') { ev.preventDefault(); A.pause(); A.step(-1); }
  else if (ev.key === 'Escape') { A.pause(); }
});
})();
