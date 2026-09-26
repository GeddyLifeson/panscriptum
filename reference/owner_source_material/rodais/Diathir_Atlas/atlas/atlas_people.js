/* atlas_people.js -- people pages, the family trees and ruler lists of Appendix A (the Line of the Mason, the Line
   of Aisling, the Stone Kings, the rulers of each age, the houses), and the threads that run across the ages.
   People come from Appendix A and houses.json at build time, and from eras/PEOPLE.json as the writers fill it. */
(function(){
var A = ATLAS, esc = A.esc;

function evRow(id){
  var e = A.EV[id]; if (!e) return '';
  return '<button data-go="' + esc(id) + '"><span class="d">' + esc(e.date) + ' · ' + esc(A.ageName(e.age)) + '</span><b>' + A.md(e.title) + '</b></button>';
}
function personLink(id){ var p = A.person(id); return p ? '<button class="linkish" data-person="' + esc(p.id) + '">' + esc(p.name) + '</button>' : esc(id); }
function treeOf(id){ return A.meta.trees.find(function(t){ return t.id === id; }); }
function whenOf(v){ return A.EV[v] ? A.EV[v].date : v; }

/* ---- a person ---- */
A.showPerson = function(id){
  var p = A.person(id);
  if (!p) { A.toast('No one of that name is in this build.'); return; }
  var h = '<h2>' + esc(p.name) + '</h2>';
  if (p.houses && p.houses.length) h += '<p class="sub">' + esc(p.houses.join(' · ')) + '</p>';
  if (p.office) h += '<p class="sub">' + esc(p.office) + (p.reign ? ', ' + esc(p.reign) : '') + '</p>';
  h += '<dl class="kv">';
  if (p.born || p.born_date) h += '<dt>Born</dt><dd>' + esc(p.born ? whenOf(p.born) : p.born_date) + '</dd>';
  if (p.died || p.died_date) h += '<dt>Died</dt><dd>' + esc(p.died ? whenOf(p.died) : p.died_date) + '</dd>';
  if (p.spouse) h += '<dt>Married</dt><dd>' + esc(p.spouse) + '</dd>';
  if (p.parents.length) h += '<dt>Parent' + (p.parents.length > 1 ? 's' : '') + '</dt><dd>' + p.parents.map(personLink).join(', ') + '</dd>';
  if (p.children.length) h += '<dt>Child' + (p.children.length > 1 ? 'ren' : '') + '</dt><dd>' + p.children.map(personLink).join(', ') + '</dd>';
  h += '</dl>';
  if (p.deed) h += '<p>' + A.gloss(A.md(p.deed)) + '.</p>';
  if (p.note) h += '<p>' + A.gloss(A.md(p.note)) + '</p>';
  var th = {};
  (p.events || []).forEach(function(i){ ((A.EV[i] || {}).threads || []).forEach(function(t){ th[t] = 1; }); });
  if (Object.keys(th).length) h += '<h3>Threads</h3><p>' + Object.keys(th).map(function(t){ var x = A.meta.threads[t] || {}; return '<button class="thread-chip" style="--tc:' + esc(x.colour || '#888') + '" data-thread="' + esc(t) + '">' + esc(x.dt || t) + '</button>'; }).join(' ') + '</p>';
  if (p.trees.length) h += '<h3>In the family trees</h3><div class="rows">' + p.trees.map(function(t){ var x = treeOf(t); return x ? '<button data-tree="' + esc(t) + '" data-me="' + esc(p.id) + '"><b>' + esc(x.title) + '</b></button>' : ''; }).join('') + '</div>';
  var evs = (p.events || []).filter(function(i){ return A.EV[i]; }).sort(function(a, b){ a = A.EV[a]; b = A.EV[b]; return a.y - b.y || a.m - b.m || a.d - b.d; });
  if (evs.length) h += '<h3>' + evs.length + ' event' + (evs.length > 1 ? 's' : '') + '</h3><div class="rows">' + evs.map(evRow).join('') + '</div>';
  A.openSheet(h, '#person/' + encodeURIComponent(p.id));
};

/* ---- the list of people and of trees ---- */
A.showPeople = function(){
  var h = '<h2>People and family trees</h2><h3>The trees and ruler lists</h3><div class="rows">' +
    A.meta.trees.map(function(t){ var n = (t.rows || t.members || []).filter(function(r){ return !r.gap; }).length;
      return '<button data-tree="' + esc(t.id) + '"><span class="n">' + n + '</span><b>' + esc(t.title) + '</b><small>' + (t.kind === 'line' ? 'a line, father to son' : t.kind === 'house' ? 'a house, its family tree' : 'a list of rulers') + '</small></button>'; }).join('') + '</div>' +
    '<h3>Everyone</h3><input type="search" id="ppq" placeholder="Find a person" aria-label="Find a person"><div class="rows" id="pplist"></div>';
  A.openSheet(h, null);
  var inp = document.getElementById('ppq');
  function draw(){
    var q = A.fold(inp.value.trim()), all = Object.keys(A.meta.people).map(function(k){ return A.meta.people[k]; });
    all = all.filter(function(p){ return !q || A.fold(p.name).indexOf(q) >= 0; }).sort(function(a, b){ return b.events.length - a.events.length || a.name.localeCompare(b.name); });
    document.getElementById('pplist').innerHTML = all.slice(0, q ? 200 : 60).map(function(p){
      var t = treeOf(p.trees[0]);
      return '<button data-person="' + esc(p.id) + '"><span class="n">' + (p.events.length || '') + '</span><b>' + esc(p.name) + '</b>' + (t ? '<small>' + esc(t.title) + '</small>' : '') + '</button>'; }).join('');
  }
  inp.oninput = draw; draw();
};

/* ---- one tree: a line or a list drawn as a descent; a house as a branching tree ---- */
A.showTree = function(id, me){
  var t = treeOf(id); if (!t) { A.toast('No such tree in this build.'); return; }
  var h = '<h2>' + esc(t.title) + '</h2>' + (t.intro ? '<p class="sub">' + A.gloss(A.md(t.intro)) + '</p>' : '');
  if (t.kind === 'house') {
    var kids = {};
    t.members.forEach(function(m){ (kids[m.parent || ''] = kids[m.parent || ''] || []).push(m); });
    var node = function(m){
      var p = A.meta.people[m.person] || {};
      return '<li><button class="node' + (m.person === me ? ' me' : '') + '" data-person="' + esc(m.person) + '"><b>' + esc(m.name) + '</b>' +
        '<small>' + esc([m.born ? 'b. ' + m.born : '', m.died ? 'd. ' + m.died : '', m.spouse ? '∞ ' + m.spouse : ''].filter(Boolean).join(' · ')) + '</small></button>' +
        (kids[m.id] ? '<ul>' + kids[m.id].map(node).join('') + '</ul>' : '') + '</li>';
    };
    var roots = t.members.filter(function(m){ return !m.parent || !t.members.some(function(x){ return x.id === m.parent; }); });
    h += '<ul class="htree">' + roots.map(node).join('') + '</ul>';
  } else {
    var rel = t.rel, when = t.columns.find(function(c){ return /told of|reign|keeping/i.test(c) && c !== 'The reign' && c !== 'The keeping'; });
    var deed = t.columns.find(function(c){ return /the deed|the reign|the keeping/i.test(c); });
    h += '<ol class="lineage">';
    t.rows.forEach(function(r, n){
      if (r.gap) { h += '<li><div class="gapnode">~ ~ ~ ' + esc(r.name) + (r.cells && (r.cells[when] || '') ? ' (' + esc(r.cells[when]) + ')' : '') + ' ~ ~ ~</div></li>'; return; }
      var c = r.cells || {}, by = c.Byname && c.Byname !== '—' ? ', ' + c.Byname : '';
      var link = n && rel && c[rel] && t.kind === 'list' ? '<div class="rel">' + esc(c[rel]) + '</div>' : '';
      var after = t.kind === 'line' && rel && c[rel] && !/^none: (his|her) (son|daughter) follows/i.test(c[rel]) && c[rel] !== '—' ? '<div class="rel">generations to the next named: ' + esc(c[rel]) + '</div>' : '';
      h += '<li>' + link + '<button class="node' + (r.person === me ? ' me' : '') + '" data-person="' + esc(r.person) + '"><b>' + esc(r.name) + esc(by) + '</b>' +
        '<small>' + esc([c[when], c['Age at death'] ? 'died aged ' + c['Age at death'] : '', c.House && c.House !== '—' ? c.House : ''].filter(Boolean).join(' · ')) + '</small>' +
        (c[deed] ? '<small>' + A.gloss(A.md(c[deed])) + '</small>' : '') + '</button>' + after + '</li>';
    });
    h += '</ol>';
  }
  A.openSheet(h, '#tree/' + encodeURIComponent(id));
  var cur = document.querySelector('#sheet .node.me'); if (cur) cur.scrollIntoView({block: 'center'});
};

/* ---- threads: named storylines across the ages ---- */
A.showThreads = function(){
  var ts = Object.keys(A.meta.threads).map(function(k){ return A.meta.threads[k]; });
  var h = '<h2>Threads</h2><p class="sub">Storylines that run across the ages. Follow one to narrow the annals to it; playback then walks it from age to age, changing maps.</p><div class="rows">';
  h += ts.map(function(t){ return '<button data-thread="' + esc(t.id) + '"><span class="n">' + (t.count || '') + '</span><b style="border-left:4px solid ' + esc(t.colour || '#888') + ';padding-left:8px">' + esc(t.dt) + '</b><small>' + esc(t.gloss) + '</small></button>'; }).join('');
  A.openSheet(h + '</div>', null);
};
A.showThread = function(id){
  var t = A.meta.threads[id]; if (!t) { A.toast('No such thread.'); return; }
  var h = '<h2 style="border-left:5px solid ' + esc(t.colour || '#888') + ';padding-left:10px">' + esc(t.dt) + '</h2><p class="sub">' + esc(t.gloss) + '</p><p>' + A.gloss(A.md(t.description || '')) + '</p>' +
    '<p><button class="pill" id="followBtn">Follow this thread</button> <button class="pill" id="playThread">▶ Play it</button></p>';
  var ids = [];
  AGE_KEYS.forEach(function(k){ (A.eraLoaded[k] ? A.order[k] : []).forEach(function(i){ if ((A.EV[i].threads || []).indexOf(id) >= 0) ids.push(i); }); });
  h += ids.length ? '<h3>' + ids.length + ' events</h3><div class="rows">' + ids.map(evRow).join('') + '</div>' : '<p class="hint">No event names this thread yet: the writers tag events as they go, and the thread fills on the next build.</p>';
  A.openSheet(h, '#thread/' + encodeURIComponent(id));
  document.getElementById('followBtn').onclick = function(){ A.closeSheet(); A.followThread(id); };
  document.getElementById('playThread').onclick = function(){ A.closeSheet(); A.followThread(id); A.showPlaybar(true); A.at(0); A.play(); };
};
A.followThread = function(id, fromLink){
  if (!A.meta.threads[id]) { A.toast('No such thread.'); return; }
  A.state.thread = id; A.state.q = ''; A.focus = null;
  showTab('timeline'); A.syncTools(); A.render();
  document.getElementById('panel-timeline').scrollTop = 0;
  A.setHash('#thread/' + encodeURIComponent(id), !fromLink);
};
})();
