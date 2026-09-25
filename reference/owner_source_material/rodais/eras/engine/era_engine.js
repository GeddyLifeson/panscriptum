/*
 * era_engine.js -- runs INSIDE Azgaar's page (injected by driver.js after the master map has loaded).
 *
 * window.EraEngine.apply(spec) edits Azgaar's own data (pack.*, options.map.lore) to the era the spec describes,
 * recalculates the derived data with Azgaar's own functions where they exist (States.collectStatistics,
 * States.findNeighbors, States.getPoles, Provinces.getPoles, Religions.checkCenters, Routes.remove/getPoints/
 * getWaterPoints/getLandPathCost/getWaterPathCost/sync, Burgs.remove/defineGroup/defineFeatures/defineEmblem/
 * definePopulation/getType/getCloseToEdgePoint, Emblems.generate/getShield, States.getFullName/defineTaxRates,
 * Markers.getMarkerCoordinates, AddedLabels.add, Markets.removeMarket/relocateMarket/expandTerritories/sync,
 * Military.generate/getName/getEmblem, Goods.sync, Production.regenerateEconomy) and redraws every layer with
 * Layers.drawAll(). The .map string is then made by Azgaar's Save.prepareMapData() (driver.js).
 *
 * Returns a report: {warnings, ids: {burg: {key: id}, ...}, counts, integrity: [...]}.
 * See SPEC.md for the spec format.
 */
(() => {
  'use strict';

  const TYPES = ['burg', 'state', 'province', 'culture', 'religion', 'marker', 'zone', 'route', 'label'];
  const PALETTE = ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3',
    '#8dd3c7', '#bebada', '#fb8072', '#80b1d3', '#fdb462', '#b3de69', '#fccde5', '#bc80bd', '#ccebc5', '#ffed6f'];
  const ZONE_HATCH = {Invasion: 'url(#hatch1)', Rebels: 'url(#hatch3)', Proselytism: 'url(#hatch6)',
    Crusade: 'url(#hatch6)', Disease: 'url(#hatch12)', Disaster: 'url(#hatch5)', Eruption: 'url(#hatch7)',
    Avalanche: 'url(#hatch5)', Fault: 'url(#hatch2)', Flood: 'url(#hatch13)', Tsunami: 'url(#hatch13)'};
  const RELATIONS = ['Ally', 'Friendly', 'Neutral', 'Suspicion', 'Enemy', 'Unknown', 'Rival', 'Vassal', 'Suzerain'];

  let warnings, keys, master, placeIds;

  const warn = (msg) => warnings.push(msg);
  const clone = (o) => (o === undefined ? undefined : JSON.parse(JSON.stringify(o)));
  const isLand = (c) => pack.cells.h[c] >= 20;
  const rn = (v, d = 0) => { const m = 10 ** d; return Math.round(v * m) / m; };

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hashString(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  // ------------------------------------------------------------------ references: numbers or "@key"
  // era place ids: a new town declared in eras/age_<K>/places.json has the id 1000*K+n (e.g. 4001); a burg added
  // with "id": 4001 answers to that number anywhere a burg id is expected (Azgaar's own ids stay below 1000)
  const PLACE_MIN = 1000;
  function ref(type, v, where) {
    if (v === null || v === undefined) return v;
    if (type === 'burg' && (typeof v === 'number' || (typeof v === 'string' && /^\d+$/.test(v))) && Number(v) >= PLACE_MIN) {
      const id = placeIds[Number(v)];
      if (id === undefined) throw new Error(`${where}: no new burg with place id ${v} (give it in burgs.add with "id": ${v})`);
      return id;
    }
    if (typeof v === 'number') return v;
    if (typeof v === 'string' && v.startsWith('@')) {
      const id = keys[type][v.slice(1)];
      if (id === undefined) throw new Error(`${where}: no ${type} with key ${v}`);
      return id;
    }
    if (typeof v === 'string' && /^\d+$/.test(v)) return Number(v);
    throw new Error(`${where}: bad ${type} reference ${JSON.stringify(v)}`);
  }
  const refs = (type, list, where) => (list || []).map((v) => ref(type, v, where));
  function setKey(type, key, id, where) {
    if (!key) return;
    if (keys[type][key] !== undefined) throw new Error(`${where}: ${type} key @${key} is used twice`);
    keys[type][key] = id;
  }

  // cells of master shires (the master's provinces, as the master map has them)
  // shire 0 is the master's land in no shire (the windy coast): its land cells only
  function shireCells(ids, where) {
    const set = new Set(ids.map(Number));
    for (const id of set) if (id !== 0 && !master.provinceIds.has(id)) throw new Error(`${where}: no master shire ${id}`);
    const out = [];
    for (const c of pack.cells.i) {
      const p = master.cellProvince[c];
      if (set.has(p) && (p !== 0 || isLand(c))) out.push(c);
    }
    return out;
  }
  function checkCells(list, where) {
    const n = pack.cells.i.length;
    return (list || []).map((c) => {
      if (!Number.isInteger(c) || c < 0 || c >= n) throw new Error(`${where}: bad cell ${c}`);
      return c;
    });
  }
  // a "where" selector used by assignments and zones: shires, provinces (era), states (era), cells, burgs
  function selectCells(sel, where) {
    const out = new Set();
    if (sel.shires) shireCells(sel.shires, where).forEach((c) => out.add(c));
    if (sel.cells) checkCells(sel.cells, where).forEach((c) => out.add(c));
    if (sel.around) {                                 // cells within `steps` neighbours of the given cells
      let front = checkCells(sel.around.cells, where);
      const seen = new Set(front);
      for (let k = 0; k < (sel.around.steps ?? 1); k++) {
        const next = [];
        for (const c of front) for (const nb of pack.cells.c[c]) if (!seen.has(nb)) { seen.add(nb); next.push(nb); }
        front = next;
      }
      seen.forEach((c) => out.add(c));
    }
    if (sel.water_box) {                              // water cells inside [x0, y0, x1, y1] (a sea zone)
      const [x0, y0, x1, y1] = sel.water_box;
      for (const c of pack.cells.i) {
        const [x, y] = pack.cells.p[c];
        if (!isLand(c) && x >= x0 && x <= x1 && y >= y0 && y <= y1) out.add(c);
      }
    }
    if (sel.burgs) refs('burg', sel.burgs, where).forEach((b) => out.add(pack.burgs[b].cell));
    if (sel.provinces) {
      const set = new Set(refs('province', sel.provinces, where));
      for (const c of pack.cells.i) if (set.has(pack.cells.province[c])) out.add(c);
    }
    if (sel.states) {
      const set = new Set(refs('state', sel.states, where));
      for (const c of pack.cells.i) if (set.has(pack.cells.state[c])) out.add(c);
    }
    if (sel.from_culture !== undefined) {
      const v = ref('culture', sel.from_culture, where);
      for (const c of pack.cells.i) if (pack.cells.culture[c] === v) out.add(c);
    }
    if (sel.from_religion !== undefined) {
      const v = ref('religion', sel.from_religion, where);
      for (const c of pack.cells.i) if (pack.cells.religion[c] === v) out.add(c);
    }
    if (sel.where_culture !== undefined) {           // narrows the selection (or selects, if nothing else did)
      const v = ref('culture', sel.where_culture, where);
      const base = out.size ? [...out] : Array.from(pack.cells.i);
      out.clear();
      base.filter((c) => pack.cells.culture[c] === v).forEach((c) => out.add(c));
    }
    return [...out];
  }

  function mixColor(hex, amount = 0.2) {
    // a variant of a colour, for a new province of a state (Azgaar's getMixedColor does the same kind of thing)
    try {
      const c = d3.color(hex).rgb();
      const r = Math.random();
      const k = (v) => Math.max(0, Math.min(255, Math.round(v + (r - 0.5) * 2 * amount * 255)));
      return d3.rgb(k(c.r), k(c.g), k(c.b)).formatHex();
    } catch (e) { return PALETTE[Math.floor(Math.random() * PALETTE.length)]; }
  }

  // ------------------------------------------------------------------ lore, features, rivers
  function applyLore(spec) {
    const L = spec.lore;
    if (!L) return;
    const lore = options.map.lore;
    if (L.name !== undefined) lore.name = L.name;
    if (L.description !== undefined) lore.description = L.description;
    if (L.calendar) {
      lore.calendar = lore.calendar || {};
      for (const k of ['year', 'era', 'eraShort']) if (L.calendar[k] !== undefined) lore.calendar[k] = L.calendar[k];
    }
  }
  // map settings: the era map keeps the master's units and geography (it is the master, edited) unless the spec
  // overrides them: "units" merges into options.map.units, "geography" into options.map.geography
  function applyUnits(spec) {
    const merge = (dst, src) => {
      for (const [k, v] of Object.entries(src)) {
        if (v && typeof v === 'object' && !Array.isArray(v) && dst[k] && typeof dst[k] === 'object') merge(dst[k], v);
        else dst[k] = clone(v);
      }
    };
    if (spec.units) merge(options.map.units, spec.units);
    if (spec.geography) merge(options.map.geography, spec.geography);
  }
  function applyRenames(spec) {
    for (const [id, name] of Object.entries(spec.features?.rename || {})) {
      const f = pack.features[+id];
      if (!f) { warn(`features.rename: no feature ${id}`); continue; }
      f.name = name;
    }
    for (const [id, v] of Object.entries(spec.rivers?.rename || {})) {
      const r = pack.rivers.find((x) => x.i === +id);
      if (!r) { warn(`rivers.rename: no river ${id}`); continue; }
      if (typeof v === 'string') r.name = v; else Object.assign(r, v);
    }
  }

  // ------------------------------------------------------------------ cultures
  function applyCultures(spec) {
    const S = spec.cultures;
    if (!S) return false;
    const cul = pack.cultures;
    for (const [id, v] of Object.entries(S.edit || S.rename || {})) {
      const c = cul[+id];
      if (!c || c.removed) throw new Error(`cultures.edit: no culture ${id}`);
      Object.assign(c, typeof v === 'string' ? {name: v} : v);
    }
    for (const a of S.add || []) {
      const i = cul.length;
      const where = `cultures.add ${a.name}`;
      const center = a.center !== undefined ? checkCells([a.center], where)[0] : undefined;
      const c = {name: a.name, i, base: a.base ?? cul[cul.length - 1].base, shield: a.shield || 'heater',
        color: a.color || PALETTE[(i * 5) % PALETTE.length], type: a.type || 'Generic',
        expansionism: a.expansionism ?? 1, origins: a.origins ? refs('culture', a.origins, where) : [0],
        code: a.code || a.name.replace(/[^A-Za-zÀ-ÿ]/g, '').slice(0, 2), center: center ?? 0,
        urban: 0, rural: 0, area: 0, cells: 0};
      if (a.note) c.note = a.note;
      cul.push(c);
      setKey('culture', a.key, i, where);
    }
    let assigned = false;
    for (const a of S.assign || []) {
      const where = `cultures.assign`;
      const to = ref('culture', a.culture, where);
      if (!cul[to] || cul[to].removed) throw new Error(`${where}: no culture ${a.culture}`);
      for (const c of selectCells(a, where)) if (isLand(c)) pack.cells.culture[c] = to;
      assigned = true;
    }
    for (const [id, repl] of Object.entries(S.remove || {})) {
      const i = +id, to = ref('culture', repl, 'cultures.remove');
      if (!i) throw new Error('cultures.remove: culture 0 (the wildlands) cannot be removed');
      for (const c of pack.cells.i) if (pack.cells.culture[c] === i) pack.cells.culture[c] = to;
      for (const b of pack.burgs) if (b && b.i && b.culture === i) b.culture = to;
      for (const s of pack.states) if (s && s.culture === i) s.culture = to;
      for (const r of pack.religions) if (r && r.culture === i) r.culture = to;
      cul[i] = {name: cul[i].name, i, base: cul[i].base, removed: true, origins: cul[i].origins,
        urban: 0, rural: 0, area: 0, cells: 0, color: cul[i].color, code: cul[i].code, shield: cul[i].shield,
        type: cul[i].type};
      for (const c of cul) if (c && Array.isArray(c.origins)) c.origins = c.origins.map((o) => (o === i ? to : o));
      assigned = true;
    }
    for (const c of cul) {      // a culture's centre must be one of its own cells
      if (!c.i || c.removed) continue;
      if (pack.cells.culture[c.center] !== c.i) {
        const cells = Array.from(pack.cells.i).filter((x) => pack.cells.culture[x] === c.i);
        if (cells.length) c.center = cells[Math.floor(cells.length / 2)];
      }
    }
    return assigned;
  }

  // ------------------------------------------------------------------ religions
  function applyReligions(spec) {
    const S = spec.religions;
    if (!S) return;
    const rel = pack.religions;
    for (const [id, v] of Object.entries(S.edit || S.rename || {})) {
      const r = rel[+id];
      if (!r || r.removed) throw new Error(`religions.edit: no religion ${id}`);
      const val = typeof v === 'string' ? {name: v} : clone(v);
      if (val.culture !== undefined) val.culture = ref('culture', val.culture, 'religions.edit');
      if (val.origins) val.origins = refs('religion', val.origins, 'religions.edit');
      Object.assign(r, val);
    }
    for (const a of S.add || []) {
      const i = rel.length;
      const where = `religions.add ${a.name}`;
      const culture = a.culture !== undefined ? ref('culture', a.culture, where) : 0;
      const r = {i, name: a.name, color: a.color || PALETTE[(i * 7 + 3) % PALETTE.length], culture,
        type: a.type || 'Organized', form: a.form || 'Monotheism', deity: a.deity ?? null,
        expansion: a.expansion || 'global', expansionism: a.expansionism ?? 1,
        center: a.center ?? 0, cells: 0, area: 0, rural: 0, urban: 0,
        origins: a.origins ? refs('religion', a.origins, where) : [0],
        code: a.code || a.name.replace(/[^A-Za-zÀ-ÿ]/g, '').slice(0, 2)};
      if (a.note) r.note = a.note;
      rel.push(r);
      setKey('religion', a.key, i, where);
    }
    for (const a of S.assign || []) {
      const to = ref('religion', a.religion, 'religions.assign');
      if (!rel[to] || rel[to].removed) throw new Error(`religions.assign: no religion ${a.religion}`);
      for (const c of selectCells(a, 'religions.assign')) if (isLand(c)) pack.cells.religion[c] = to;
    }
    for (const [id, repl] of Object.entries(S.remove || {})) {
      const i = +id, to = ref('religion', repl, 'religions.remove');
      if (!i) throw new Error('religions.remove: religion 0 cannot be removed');
      for (const c of pack.cells.i) if (pack.cells.religion[c] === i) pack.cells.religion[c] = to;
      rel[i] = {i, name: rel[i].name, removed: true, origins: rel[i].origins, color: rel[i].color, code: rel[i].code,
        type: rel[i].type, form: rel[i].form, culture: rel[i].culture, cells: 0, area: 0, rural: 0, urban: 0};
      for (const r of rel) if (r && Array.isArray(r.origins)) r.origins = r.origins.map((o) => (o === i ? to : o));
    }
    for (const r of rel) {      // centres of new religions left at 0: the middle of their cells
      if (!r.i || r.removed || r.center) continue;
      const cells = Array.from(pack.cells.i).filter((x) => pack.cells.religion[x] === r.i);
      if (cells.length) r.center = cells[Math.floor(cells.length / 2)];
    }
    Religions.checkCenters();
  }

  // ------------------------------------------------------------------ burgs (placement: before the states)
  function applyBurgs(spec) {
    const S = spec.burgs || {};
    const burgs = pack.burgs;
    const changed = new Set();     // burgs whose group must be defined anew
    let keep = null;
    if (Array.isArray(S.keep)) keep = new Set(S.keep.map(Number));
    const remove = new Set((S.remove || []).map(Number));
    for (const b of burgs) {
      if (!b || !b.i || b.removed) continue;
      if ((keep && !keep.has(b.i)) || remove.has(b.i)) removeBurg(b);
    }
    if (keep) for (const id of keep) if (!burgs[id] || burgs[id].removed) warn(`burgs.keep: burg ${id} does not exist in the master`);

    if (S.population_scale !== undefined) {
      for (const b of burgs) if (b && b.i && !b.removed) { b.population = rn(Math.max(b.population * S.population_scale, 0.01), 3); changed.add(b.i); }
    }
    for (const [id, v] of Object.entries(S.edit || {})) {
      const b = burgs[+id];
      if (!b || b.removed) throw new Error(`burgs.edit: burg ${id} is not on this map (removed or never there)`);
      editBurg(b, v, `burgs.edit ${id}`);
      if (v.population !== undefined || v.group !== undefined) changed.add(b.i);
    }
    const added = [];
    for (const a of S.add || []) {
      const where = `burgs.add ${a.name}`;
      let cell, x, y;
      if (a.cell !== undefined) { cell = checkCells([a.cell], where)[0]; [x, y] = pack.cells.p[cell]; }
      else if (a.x !== undefined) { x = a.x; y = a.y; cell = Pack.findCell(x, y); }
      else throw new Error(`${where}: give a cell or x,y`);
      if (!isLand(cell)) throw new Error(`${where}: cell ${cell} is water`);
      if (pack.cells.burg[cell]) throw new Error(`${where}: cell ${cell} already holds burg ${pack.cells.burg[cell]} (${burgs[pack.cells.burg[cell]].name})`);
      const i = burgs.length;
      const b = {cell, x: rn(x, 2), y: rn(y, 2), i, state: 0, culture: pack.cells.culture[cell], name: a.name,
        feature: pack.cells.f[cell], capital: 0, port: 0};
      burgs.push(b);
      pack.cells.burg[cell] = i;
      if (a.port) {
        const haven = pack.cells.haven[cell];
        if (haven !== undefined && haven !== null && pack.cells.h[haven] < 20) {
          b.port = pack.cells.f[haven];
          [b.x, b.y] = Burgs.getCloseToEdgePoint(cell, haven);
        } else warn(`${where}: cell ${cell} is not on the coast, so the burg cannot be a port`);
      }
      if (a.population !== undefined) b.population = a.population; else Burgs.definePopulation(b);
      b.type = a.type || Burgs.getType(cell, b.port);
      editBurg(b, a, where);
      b.market = pack.cells.market ? pack.cells.market[cell] || 0 : 0;
      setKey('burg', a.key, i, where);
      if (a.id !== undefined) {
        if (!Number.isInteger(a.id) || a.id < PLACE_MIN) throw new Error(`${where}: "id" is an era place id (1000*age+n), not ${a.id}`);
        if (placeIds[a.id] !== undefined) throw new Error(`${where}: place id ${a.id} is used twice`);
        if (i >= PLACE_MIN) throw new Error(`${where}: Azgaar id ${i} would clash with the era place ids`);
        placeIds[a.id] = i;
        b.placeId = a.id;
      }
      added.push({b, a});
      changed.add(i);
    }
    return {changed, added};
  }
  function removeBurg(b) {
    Burgs.remove(b.i);                // cells.burg cleared, removed flag set, note and arms dropped (Azgaar's own)
    delete b.production; delete b.treasury; delete b.product; delete b.lock;
    b.capital = 0;
    b.market = 0;
    b.plaza = b.plaza ? 0 : b.plaza;
  }
  function editBurg(b, v, where) {
    for (const k of ['name', 'population', 'type', 'coa', 'note', 'x', 'y']) if (v[k] !== undefined) b[k] = clone(v[k]);
    if (v.culture !== undefined) { b.culture = ref('culture', v.culture, where); b._cultureSet = true; }
    if (v.group !== undefined) {
      if (!options.map.burgs.groups.find((g) => g.name === v.group)) throw new Error(`${where}: no burg group "${v.group}"`);
      b.group = v.group; b._groupSet = true;
    }
    if (v.features) for (const [k, val] of Object.entries(v.features)) b[k] = Number(val);
    if (v.features) b._featuresSet = true;
    if (v.x !== undefined && v.cell === undefined) {
      const c = Pack.findCell(b.x, b.y);
      if (c !== b.cell) warn(`${where}: x,y lie in cell ${c}, not the burg's cell ${b.cell}; the burg keeps its cell`);
    }
  }

  // ------------------------------------------------------------------ states and the cells' states
  function applyStates(spec) {
    const S = spec.states;
    if (!S) return false;
    const list = Array.isArray(S) ? S : S.list;
    const opts = Array.isArray(S) ? {} : S;
    const n = pack.cells.i.length;
    const cellState = new Uint16Array(n);
    const s0 = pack.states[0];
    const states = [{i: 0, name: opts.neutral_name || s0.name, salesTax: 0, pollTax: 0, treasury: 0, neighbors: [],
      diplomacy: clone(opts.chronicle || []), urban: 0, rural: 0, burgs: 0, area: 0, cells: 0, provinces: []}];
    list.forEach((st, k) => {
      const id = k + 1;
      const where = `states[${k}] ${st.name}`;
      if (st.id !== undefined && st.id !== id) throw new Error(`${where}: states are numbered by their order; this one is ${id}, not ${st.id}`);
      setKey('state', st.key, id, where);
    });
    list.forEach((st, k) => {
      const id = k + 1;
      const where = `states[${k}] ${st.name}`;
      const base = st.base !== undefined ? clone(master.states[st.base]) : null;
      if (st.base !== undefined && (!base || base.removed)) throw new Error(`${where}: no master state ${st.base}`);
      const s = base || {};
      s.i = id;
      for (const k2 of ['name', 'form', 'formName', 'fullName', 'color', 'expansionism', 'type', 'salesTax', 'pollTax',
        'treasury', 'alert', 'note']) if (st[k2] !== undefined) s[k2] = st[k2];
      if (!s.name) throw new Error(`${where}: a state needs a name`);
      s.capital = st.capital !== undefined ? ref('burg', st.capital, where) : s.capital;
      const cap = pack.burgs[s.capital];
      if (!s.capital || !cap || cap.removed) throw new Error(`${where}: capital burg ${st.capital ?? s.capital} is not on this map`);
      s.center = cap.cell;
      s.culture = st.culture !== undefined ? ref('culture', st.culture, where) : (s.culture ?? pack.cells.culture[cap.cell]);
      if (!pack.cultures[s.culture] || pack.cultures[s.culture].removed) throw new Error(`${where}: culture ${s.culture} is not on this map`);
      s.type = s.type || pack.cultures[s.culture].type || 'Generic';
      s.expansionism = s.expansionism ?? 1;
      s.form = s.form || 'Monarchy';
      s.formName = s.formName || (s.form === 'Monarchy' ? 'Kingdom' : s.form);
      if (st.fullName === undefined && (!base || st.name !== undefined || st.formName !== undefined)) s.fullName = States.getFullName(s);
      if (st.coa && typeof st.coa === 'object') s.coa = clone(st.coa);
      else if (st.coa === 'generate' || !s.coa) {
        s.coa = Emblems.generate(null, null, null, s.type);
        s.coa.shield = Emblems.getShield(s.culture, null);
      }
      if (st.salesTax === undefined && s.salesTax === undefined) Object.assign(s, States.defineTaxRates(s));
      s.treasury = s.treasury ?? 0;
      s.alert = s.alert ?? 1;
      s.campaigns = clone(st.campaigns) || (base ? s.campaigns || [] : []);
      for (const c of s.campaigns) { c.attacker = ref('state', c.attacker, where); c.defender = ref('state', c.defender, where); }
      if (st.label) s.label = clone(st.label); else if (!st.keep_label) delete s.label;
      s._military = st.military !== undefined ? st.military : (base ? 'keep' : []);
      delete s.removed; delete s.lock;
      states.push(s);
      const where2 = `${where} (cells)`;
      if (st.shires) for (const c of shireCells(st.shires, where2)) if (isLand(c)) cellState[c] = id;
      if (st.cells) for (const c of checkCells(st.cells, where2)) if (isLand(c)) cellState[c] = id;
    });
    for (const [c, v] of Object.entries(opts.cell_state || {})) {
      const cell = checkCells([+c], 'states.cell_state')[0];
      if (isLand(cell)) cellState[cell] = ref('state', v, 'states.cell_state');
    }
    if (opts.default_state !== undefined) {
      const d = ref('state', opts.default_state, 'states.default_state');
      for (const c of pack.cells.i) if (isLand(c) && !cellState[c]) cellState[c] = d;
    }
    // a capital lies in its own state
    for (const s of states) {
      if (!s.i) continue;
      if (cellState[s.center] !== s.i) {
        warn(`state ${s.i} (${s.name}): its capital's cell ${s.center} was assigned to state ${cellState[s.center]}; given to the state`);
        cellState[s.center] = s.i;
      }
    }
    pack.states = states;
    pack.cells.state = cellState;
    return true;
  }

  // ------------------------------------------------------------------ provinces
  function applyProvinces(spec, statesChanged) {
    const S = spec.provinces || {};
    const P = pack.provinces;
    const cp = pack.cells.province;
    const removeP = (p) => { P[p.i] = {i: p.i, state: 0, center: p.center, burg: 0, name: p.name, formName: p.formName, fullName: p.fullName, color: p.color, removed: true}; };
    const newProvince = (a, where) => {
      const i = P.length;
      const p = {i, state: 0, center: 0, burg: a.burg !== undefined ? ref('burg', a.burg, where) : 0, name: a.name,
        formName: a.formName ?? '', fullName: a.fullName, color: a.color, coa: clone(a.coa)};
      if (a.note) p.note = a.note;
      P.push(p);
      setKey('province', a.key, i, where);
      return p;
    };
    if (S.base === 'none') {
      for (const p of P) if (p && p.i && !p.removed) removeP(p);
      cp.fill(0);
    }
    for (const id of S.remove || []) {
      const p = P[+id];
      if (!p || p.removed) throw new Error(`provinces.remove: no province ${id}`);
      for (const c of pack.cells.i) if (cp[c] === p.i) cp[c] = 0;
      removeP(p);
    }
    for (const m of S.merge || []) {
      const where = `provinces.merge into ${m.into}`;
      const into = P[ref('province', m.into, where)];
      if (!into || into.removed) throw new Error(`${where}: no province ${m.into}`);
      for (const f of refs('province', m.from, where)) {
        if (!P[f] || P[f].removed) throw new Error(`${where}: no province ${f}`);
        for (const c of pack.cells.i) if (cp[c] === f) cp[c] = into.i;
        removeP(P[f]);
      }
      editProvince(into, m, where);
    }
    for (const a of [...(S.split || []), ...(S.add || [])]) {
      const where = `provinces ${a.name}`;
      const p = newProvince(a, where);
      const sel = {...a};
      if (a.from !== undefined) {         // a split: the named cells of one province, or its cells in given shires
        const from = ref('province', a.from, where);
        const cells = selectCells(sel, where).filter((c) => cp[c] === from);
        if (!cells.length) warn(`${where}: none of the cells given lie in province ${from}`);
        cells.forEach((c) => { cp[c] = p.i; });
      } else {
        selectCells(sel, where).forEach((c) => { if (isLand(c)) cp[c] = p.i; });
      }
    }
    for (const [id, v] of Object.entries(S.edit || S.rename || {})) {
      const p = P[ref('province', /^\d+$/.test(id) ? Number(id) : id, 'provinces.edit')];
      if (!p || p.removed) throw new Error(`provinces.edit: no province ${id}`);
      editProvince(p, typeof v === 'string' ? {name: v} : v, `provinces.edit ${id}`);
    }
    for (const [c, v] of Object.entries(S.cell_province || {})) {
      const cell = checkCells([+c], 'provinces.cell_province')[0];
      if (isLand(cell)) cp[cell] = ref('province', v, 'provinces.cell_province');
    }
    // provinces live inside states: neutral land holds none (unless the spec keeps them)
    if ((S.neutral || 'clear') === 'clear') for (const c of pack.cells.i) if (!pack.cells.state[c]) cp[c] = 0;
    for (const c of pack.cells.i) if (!isLand(c)) cp[c] = 0;

    // each province: its state (the state most of its land lies in), seat, centre, colour, arms
    const count = P.map(() => new Map());
    const cellsOf = P.map(() => []);
    for (const c of pack.cells.i) {
      const p = cp[c];
      if (!p) continue;
      const m = count[p];
      m.set(pack.cells.state[c], (m.get(pack.cells.state[c]) || 0) + 1);
      cellsOf[p].push(c);
    }
    for (const p of P) {
      if (!p || !p.i || p.removed) continue;
      if (!cellsOf[p.i].length) { warn(`province ${p.i} (${p.name}) has no land left; removed`); removeP(p); continue; }
      const byState = [...count[p.i].entries()].sort((a, b) => b[1] - a[1]);
      p.state = byState[0][0];
      if (byState.length > 1) warn(`province ${p.i} (${p.name}) spans states ${byState.map(([s, n]) => `${s}:${n}`).join(', ')}; it is given to state ${p.state}`);
      const seat = pack.burgs[p.burg];
      if (p.burg && (!seat || seat.removed || cp[seat.cell] !== p.i)) {
        const inside = pack.burgs.filter((b) => b && b.i && !b.removed && cp[b.cell] === p.i).sort((a, b) => b.population - a.population);
        const old = p.burg;
        p.burg = inside.length ? inside[0].i : 0;
        if (statesChanged || spec.burgs) warn(`province ${p.i} (${p.name}): seat burg ${old} is gone; seat now ${p.burg ? `${p.burg} (${pack.burgs[p.burg].name})` : 'none'}`);
      }
      if (p.burg) p.center = pack.burgs[p.burg].cell;
      else if (cp[p.center] !== p.i) p.center = cellsOf[p.i][Math.floor(cellsOf[p.i].length / 2)];
      if (!p.fullName) p.fullName = p.formName ? `${p.formName} ${p.name}` : p.name;
      if (!p.color) p.color = mixColor(pack.states[p.state]?.color || PALETTE[p.i % PALETTE.length]);
      if (!p.coa) {
        const st = pack.states[p.state];
        p.coa = Emblems.generate(p.burg ? pack.burgs[p.burg].coa : st?.coa, p.burg ? 0.8 : 0.4, null,
          Burgs.getType(p.center, p.burg ? pack.burgs[p.burg].port : undefined));
        p.coa.shield = Emblems.getShield(pack.cells.culture[p.center], p.state);
      }
    }
    for (const s of pack.states) if (s && !s.removed) s.provinces = P.filter((p) => p && p.i && !p.removed && p.state === s.i).map((p) => p.i);
  }
  function editProvince(p, v, where) {
    for (const k of ['name', 'formName', 'fullName', 'color', 'coa', 'note']) if (v[k] !== undefined) p[k] = clone(v[k]);
    if (v.burg !== undefined) p.burg = ref('burg', v.burg, where);
    if (v.name !== undefined && v.fullName === undefined) p.fullName = p.formName ? `${p.formName} ${p.name}` : p.name;
  }

  // ------------------------------------------------------------------ burgs, after the states
  function finishBurgs(spec, burgInfo, culturesAssigned) {
    const burgs = pack.burgs;
    const capitals = new Set(pack.states.filter((s) => s.i && !s.removed).map((s) => s.capital));
    for (const b of burgs) {
      if (!b || !b.i || b.removed) continue;
      b.state = pack.cells.state[b.cell];
      if (culturesAssigned && !b._cultureSet) b.culture = pack.cells.culture[b.cell];
      const cap = capitals.has(b.i) ? 1 : 0;
      if (cap !== (b.capital || 0)) { b.capital = cap; burgInfo.changed.add(b.i); }
      if (pack.cultures[b.culture]?.removed) b.culture = pack.cells.culture[b.cell];
    }
    for (const {b} of burgInfo.added) {
      if (!b._featuresSet) Burgs.defineFeatures(b);
      if (!b.coa) Burgs.defineEmblem(b);
      if (!b.coa.shield) b.coa.shield = Emblems.getShield(b.culture, b.state);
      b.type = b.type || Burgs.getType(b.cell, b.port);
    }
    const pops = burgs.filter((b) => b && b.i && !b.removed).map((b) => b.population).sort((a, b) => a - b);
    for (const id of burgInfo.changed) {
      const b = burgs[id];
      if (b.removed) continue;
      if (b._groupSet) continue;
      Burgs.defineGroup(b, pops);
    }
    for (const b of burgs) if (b) { delete b._groupSet; delete b._featuresSet; delete b._cultureSet; }
  }

  // ------------------------------------------------------------------ statistics (Azgaar's own, and the same way for cultures and faiths)
  function recalculate() {
    States.collectStatistics();
    States.findNeighbors();
    States.getPoles();
    Provinces.getPoles();
    const {cells} = pack;
    for (const list of [pack.cultures, pack.religions]) for (const x of list) if (x) { x.cells = 0; x.area = 0; x.rural = 0; x.urban = 0; }
    for (const c of cells.i) {
      if (cells.h[c] < 20) continue;
      for (const [list, arr] of [[pack.cultures, cells.culture], [pack.religions, cells.religion]]) {
        const x = list[arr[c]];
        if (!x) continue;
        x.cells += 1; x.area += cells.area[c]; x.rural += cells.pop[c];
        if (cells.burg[c]) x.urban += pack.burgs[cells.burg[c]].population;
      }
    }
    for (const x of pack.religions) if (x && !x.i) { delete x.cells; delete x.area; delete x.rural; delete x.urban; }
  }

  // ------------------------------------------------------------------ diplomacy, campaigns, military
  function applyDiplomacy(spec, statesChanged) {
    const S = spec.diplomacy;
    const states = pack.states;
    if (!statesChanged && !S) return;
    const n = states.length;
    for (const s of states) {
      if (!s.i || s.removed) continue;
      const old = s.diplomacy;
      s.diplomacy = Array(n).fill(spec.diplomacy_default || 'Neutral');
      s.diplomacy[s.i] = 'x';
      if (!statesChanged && Array.isArray(old)) old.forEach((v, j) => { if (j < n) s.diplomacy[j] = v; });
    }
    for (const row of S || []) {
      const [a0, b0, rel, back] = row;
      const a = ref('state', a0, 'diplomacy'), b = ref('state', b0, 'diplomacy');
      if (!RELATIONS.includes(rel)) throw new Error(`diplomacy: unknown relation ${rel} (one of ${RELATIONS.join(', ')})`);
      const rev = back || (rel === 'Vassal' ? 'Suzerain' : rel === 'Suzerain' ? 'Vassal' : rel);
      if (!RELATIONS.includes(rev)) throw new Error(`diplomacy: unknown relation ${rev}`);
      if (!states[a] || !states[b] || !a || !b) throw new Error(`diplomacy: no state ${a0} or ${b0}`);
      states[a].diplomacy[b] = rel;
      states[b].diplomacy[a] = rev;
    }
    for (const c of spec.campaigns || []) {
      const camp = {name: c.name, start: c.start, end: c.end, attacker: ref('state', c.attacker, 'campaigns'), defender: ref('state', c.defender, 'campaigns')};
      if (camp.end === undefined) delete camp.end;
      for (const s of [camp.attacker, camp.defender]) if (s && states[s]) states[s].campaigns.push({...camp});
    }
  }

  function applyMilitary(spec, statesChanged) {
    const states = pack.states.filter((s) => s.i && !s.removed);
    const wantGen = states.filter((s) => s._military === 'generate');
    if (!statesChanged && !spec.military) return;
    if (wantGen.length) {
      const kept = new Map(states.map((s) => [s.i, s.military]));
      Military.generate();
      for (const s of states) if (s._military !== 'generate') s.military = kept.get(s.i);
    }
    for (const s of states) {
      const m = s._military;
      if (m === 'keep' || m === undefined) { s.military = (s.military || []).map((r) => ({...r, state: s.i})); }
      else if (Array.isArray(m)) s.military = regiments(m, s);
    }
    for (const [sid, list] of Object.entries(spec.military?.regiments || {})) {
      const s = pack.states[ref('state', /^\d+$/.test(sid) ? Number(sid) : sid, 'military.regiments')];
      if (!s) throw new Error(`military.regiments: no state ${sid}`);
      s.military = regiments(list, s);
    }
    for (const s of pack.states) delete s._military;
  }
  function regiments(list, s) {
    const out = [];
    list.forEach((r, k) => out.push(regiment(r, k, s, out)));
    return out;
  }
  function regiment(r, k, s, done) {
    const where = `regiment ${r.name || k} of ${s.name}`;
    let cell, x, y;
    if (r.burg !== undefined) { const b = pack.burgs[ref('burg', r.burg, where)]; cell = b.cell; x = b.x; y = b.y; }
    else if (r.cell !== undefined) { cell = checkCells([r.cell], where)[0]; [x, y] = pack.cells.p[cell]; }
    else if (r.x !== undefined) { x = r.x; y = r.y; cell = Pack.findCell(x, y); }
    else { cell = s.center; [x, y] = pack.cells.p[cell]; }
    const naval = r.naval ? 1 : 0;
    if (naval && r.x === undefined) {
      const haven = pack.cells.haven[cell];
      if (haven !== undefined && pack.cells.h[haven] < 20) [x, y] = pack.cells.p[haven];
    }
    const u = clone(r.units || {});
    for (const name of Object.keys(u)) if (!options.map.military.units.find((x2) => x2.name === name)) warn(`${where}: unit type "${name}" is not in the map's military units`);
    const reg = {i: k, a: Object.values(u).reduce((a, b) => a + b, 0), cell, x: rn(x, 2), y: rn(y, 2),
      bx: rn(r.bx ?? x, 2), by: rn(r.by ?? y, 2), u, n: naval, name: r.name || '', icon: r.icon || '', state: s.i};
    if (!reg.name) reg.name = Military.getName(reg, done);
    if (!reg.icon) reg.icon = Military.getEmblem(reg);
    if (r.note) reg.note = r.note;
    return reg;
  }

  // ------------------------------------------------------------------ routes
  function dijkstra(start, isExit, cost, enterExit = false) {
    const n = pack.cells.i.length;
    const dist = new Float64Array(n).fill(Infinity), from = new Int32Array(n).fill(-1);
    const q = new FlatQueue();
    dist[start] = 0; q.push(start, 0);
    while (q.length) {
      const d = q.peekValue(), c = q.pop();
      if (d > dist[c]) continue;
      if (isExit(c, from[c] === -1 ? undefined : from[c])) {
        const path = [c]; let x = c;
        while (from[x] !== -1) { x = from[x]; path.push(x); }
        return path.reverse();
      }
      for (const nb of pack.cells.c[c]) {
        if (enterExit && isExit(nb, c)) {    // a sea route ends on a land (port) cell, which water costs never enter
          const path = [nb, c]; let x = c;
          while (from[x] !== -1) { x = from[x]; path.push(x); }
          return path.reverse();
        }
        const w = cost(c, nb);
        if (!Number.isFinite(w)) continue;
        const nd = d + w;
        if (nd < dist[nb]) { dist[nb] = nd; from[nb] = c; q.push(nb, nd); }
      }
    }
    return null;
  }
  function routeCells(a, where) {
    const group = a.group || 'roads';
    if (a.cells) return checkCells(a.cells, where);
    const stops = a.burgs ? refs('burg', a.burgs, where).map((b) => {
      if (!pack.burgs[b] || pack.burgs[b].removed) throw new Error(`${where}: burg ${b} is not on this map`);
      return pack.burgs[b].cell;
    }) : checkCells(a.stops || [], where);
    if (stops.length < 2) throw new Error(`${where}: a route needs at least two burgs or cells`);
    const water = group === 'searoutes';
    const cost = water ? Routes.getWaterPathCost.bind(Routes) : Routes.getLandPathCost.bind(Routes);
    let out = [];
    for (let k = 0; k < stops.length - 1; k++) {
      const exit = water ? Routes.createWaterExitCheck(stops[k + 1]) : (c) => c === stops[k + 1];
      const leg = dijkstra(stops[k], exit, cost, water);
      if (!leg) throw new Error(`${where}: no ${water ? 'sea' : 'land'} path from cell ${stops[k]} to cell ${stops[k + 1]}`);
      out = out.length ? out.concat(leg.slice(1)) : leg;
    }
    return out;
  }
  function applyRoutes(spec) {
    const S = spec.routes;
    if (!S) return;
    Routes.sync();
    let keep = Array.isArray(S.keep) ? new Set(S.keep.map(Number)) : null;
    const remove = new Set((S.remove || []).map(Number));
    for (const r of [...pack.routes]) if ((keep && !keep.has(r.i)) || remove.has(r.i)) Routes.remove(r);
    // as Azgaar's loader tidies them: no cell left with an empty set of links, no link to a route that is gone
    const live = new Set(pack.routes.map((r) => r.i));
    for (const c of Object.keys(pack.cells.routes)) {
      const links = pack.cells.routes[c];
      for (const n of Object.keys(links)) if (!live.has(links[n])) delete links[n];
      if (!Object.keys(links).length) delete pack.cells.routes[c];
    }
    for (const [id, v] of Object.entries(S.edit || S.rename || {})) {
      const r = pack.routes.find((x) => x.i === +id);
      if (!r) { warn(`routes.edit: route ${id} is not on this map`); continue; }
      if (typeof v === 'string') r.name = v;
      else { if (v.name !== undefined) r.name = v.name; if (v.group) r.group = v.group; if (v.note !== undefined) r.note = v.note; }
    }
    for (const a of S.add || []) {
      const where = `routes.add ${a.name || ''}`;
      const cells = routeCells(a, where);
      const group = a.group || 'roads';
      const points = group === 'searoutes' ? Routes.getWaterPoints(cells) : Routes.getPoints(group, cells, Routes.preparePointsArray());
      const i = Routes.getNextId();
      const r = {i, group, feature: pack.cells.f[cells.find(isLand) ?? cells[0]], points};
      if (a.name) r.name = a.name;
      if (a.note) r.note = a.note;
      pack.routes.push(r);
      const links = pack.cells.routes;
      for (let k = 0; k < cells.length - 1; k++) {
        const x = cells[k], y = cells[k + 1];
        if (x === y) continue;
        (links[x] ||= {})[y] = i;
        (links[y] ||= {})[x] = i;
      }
      setKey('route', a.key, i, where);
      Routes.sync();
    }
    Routes.sync();
  }

  // ------------------------------------------------------------------ markers, zones, labels
  function applyMarkers(spec) {
    const S = spec.markers;
    if (!S) return;
    const keep = Array.isArray(S.keep) ? new Set(S.keep.map(Number)) : null;
    const remove = new Set((S.remove || []).map(Number));
    pack.markers = pack.markers.filter((m) => !(keep && !keep.has(m.i)) && !remove.has(m.i));
    for (const [id, v] of Object.entries(S.edit || {})) {
      const m = pack.markers.find((x) => x.i === +id);
      if (!m) { warn(`markers.edit: marker ${id} is not on this map`); continue; }
      Object.assign(m, clone(v));
    }
    for (const a of S.add || []) {
      const where = `markers.add ${a.name}`;
      let cell, x, y;
      if (a.burg !== undefined) { const b = pack.burgs[ref('burg', a.burg, where)]; cell = b.cell; }
      if (a.cell !== undefined) cell = checkCells([a.cell], where)[0];
      if (cell !== undefined) [x, y] = Markers.getMarkerCoordinates(cell);
      if (a.x !== undefined) { x = a.x; y = a.y; cell = Pack.findCell(x, y); }
      if (cell === undefined) throw new Error(`${where}: give a cell, a burg or x,y`);
      const cfg = Markers.config.find((c) => c.type === a.type) || {};
      const i = pack.markers.length ? Math.max(...pack.markers.map((m) => m.i)) + 1 : 0;
      const m = {icon: a.icon || cfg.icon || '📍', type: a.type || 'custom'};
      for (const k of ['dx', 'dy', 'px', 'size', 'pin', 'fill', 'stroke']) if ((a[k] ?? cfg[k]) !== undefined) m[k] = a[k] ?? cfg[k];
      Object.assign(m, {x: rn(x, 2), y: rn(y, 2), cell, i, name: a.name || a.type});
      if (a.note) m.note = a.note;
      if (a.lock) m.lock = true;
      pack.markers.push(m);
      setKey('marker', a.key, i, where);
    }
    pack.markers.sort((a, b) => a.i - b.i);
  }
  function applyZones(spec) {
    const S = spec.zones;
    if (!S) return;
    const keep = Array.isArray(S.keep) ? new Set(S.keep.map(Number)) : null;
    const remove = new Set((S.remove || []).map(Number));
    pack.zones = pack.zones.filter((z) => !(keep && !keep.has(z.i)) && !remove.has(z.i));
    for (const [id, v] of Object.entries(S.edit || {})) {
      const z = pack.zones.find((x) => x.i === +id);
      if (!z) { warn(`zones.edit: zone ${id} is not on this map`); continue; }
      const val = clone(v);
      if (val.cells || val.shires || val.provinces || val.states || val.burgs) { z.cells = selectCells(val, `zones.edit ${id}`); }
      for (const k of ['cells', 'shires', 'provinces', 'states', 'burgs']) delete val[k];
      Object.assign(z, val);
    }
    for (const a of S.add || []) {
      const where = `zones.add ${a.name}`;
      const i = pack.zones.length ? Math.max(...pack.zones.map((z) => z.i)) + 1 : 0;
      const cells = selectCells(a, where);
      if (!cells.length) throw new Error(`${where}: a zone needs cells (cells, shires, provinces, states or burgs)`);
      const z = {i, name: a.name, type: a.type || 'Custom', cells, color: a.color || ZONE_HATCH[a.type] || 'url(#hatch4)'};
      if (a.hidden) z.hidden = true;
      if (a.note) z.note = a.note;
      pack.zones.push(z);
      setKey('zone', a.key, i, where);
    }
  }
  function applyLabels(spec) {
    const S = spec.labels;
    if (!S) return;
    if (S.keep !== undefined) {
      const keep = new Set((Array.isArray(S.keep) ? S.keep : []).map(Number));
      if (S.keep !== 'all') pack.addedLabels = pack.addedLabels.filter((l) => keep.has(l.i));
    }
    for (const a of S.add || []) {
      const where = `labels.add ${a.text}`;
      let x = a.x, y = a.y;
      if (a.cell !== undefined) [x, y] = pack.cells.p[checkCells([a.cell], where)[0]];
      if (x === undefined) throw new Error(`${where}: give x,y or a cell`);
      const label = {text: a.text, group: a.group || 'added'};
      for (const k of ['fontSize', 'letterSpacing', 'startOffset', 'dx', 'dy']) if (a[k] !== undefined) label[k] = a[k];
      if (a.pathPoints) label.pathPoints = clone(a.pathPoints);
      const l = AddedLabels.add({x: rn(x, 2), y: rn(y, 2), label});
      if (a.note) l.note = a.note;
      setKey('label', a.key, l.i, where);
    }
    for (const [sid, v] of Object.entries(S.state || {})) {
      const s = pack.states[ref('state', /^\d+$/.test(sid) ? Number(sid) : sid, 'labels.state')];
      if (!s) throw new Error(`labels.state: no state ${sid}`);
      s.label = clone(v);
    }
  }

  // ------------------------------------------------------------------ economy
  function applyEconomy(spec) {
    const S = spec.economy || {};
    const burgs = pack.burgs;
    const alive = (id) => burgs[id] && burgs[id].i && !burgs[id].removed;
    let marketsChanged = false;
    for (const m of [...(pack.markets || [])]) {
      if (alive(m.centerBurgId)) continue;
      // the market's centre is gone: the largest burg of its territory takes it over, or the market closes
      const cand = burgs.filter((b) => b && b.i && !b.removed && pack.cells.market[b.cell] === m.i &&
        !pack.markets.some((x) => x.centerBurgId === b.i)).sort((a, b) => b.population - a.population);
      if (cand.length && S.relocate_markets !== false) {
        const old = m.centerBurgId;
        Markets.relocateMarket(m.i, cand[0].i);
        warn(`market ${m.i}: centre burg ${old} is gone; moved to ${cand[0].i} (${cand[0].name})`);
      } else {
        Markets.removeMarket(m.i);
        warn(`market ${m.i}: centre burg ${m.centerBurgId} is gone; market removed`);
      }
      marketsChanged = true;
    }
    for (const id of S.remove_markets || []) { Markets.removeMarket(+id); marketsChanged = true; }
    for (const b of refs('burg', S.add_markets || [], 'economy.add_markets')) { if (Markets.addMarket(b)) marketsChanged = true; }
    for (const [id, v] of Object.entries(S.edit_goods || {})) {
      const g = pack.goods.find((x) => x.i === +id);
      if (!g) { warn(`economy.edit_goods: no good ${id}`); continue; }
      Object.assign(g, clone(v));
    }
    Goods.sync();
    Markets.sync();
    if (S.mode === 'regenerate') {
      Production.regenerateEconomy();          // Azgaar's own: territories, deals and burg production anew
      return;
    }
    if (marketsChanged) Markets.expandTerritories(pack.markets);
    // prune: no deal with a burg or market that is not on the map, and no burg production entry for a dropped deal
    const markets = new Set(pack.markets.map((m) => m.i));
    const ok = (type, id) => (type === 'market' ? markets.has(id) : type === 'burg' ? alive(id) : true);
    const before = pack.deals.length;
    pack.deals = pack.deals.filter((d) => ok(d.sellerType, d.seller) && ok(d.buyerType, d.buyer));
    const deals = new Set(pack.deals.map((d) => d.i));
    for (const b of burgs) if (b && b.production) b.production = b.production.filter((p) => !('dealId' in p) || deals.has(p.dealId));
    for (const b of burgs) if (b && b.i && !b.removed && b.market && !markets.has(b.market)) b.market = pack.cells.market[b.cell] || 0;
    if (before !== pack.deals.length) warn(`economy: ${before - pack.deals.length} deals with burgs or markets not on this map dropped`);
  }

  // ------------------------------------------------------------------ journeys, notes, population, layers
  function applyJourneys(spec) {
    const S = spec.journeys;
    if (!S) return;
    if (Array.isArray(S.keep)) {
      const keep = new Set(S.keep.map(Number));
      pack.journeys = pack.journeys.filter((j, k) => keep.has(j.i ?? k));
    }
  }
  function applyNotes(spec) {
    for (const [key, text] of Object.entries(spec.notes || {})) {
      const m = /^(\w+):(@?[\w-]+?)(?:-(\d+))?$/.exec(key);
      if (!m) throw new Error(`notes: bad key ${key} (use type:id, e.g. burg:19, state:2, marker:@key, regiment:1-0)`);
      const [, type, idRaw, sub] = m;
      const id = idRaw.startsWith('@') || type === 'burg' ? ref(type === 'addedLabel' ? 'label' : type, idRaw, 'notes') : Number(idRaw);
      const lists = {state: pack.states, province: pack.provinces, burg: pack.burgs, marker: pack.markers,
        river: pack.rivers, route: pack.routes, feature: pack.features, zone: pack.zones, journey: pack.journeys,
        market: pack.markets, addedLabel: pack.addedLabels, culture: pack.cultures, religion: pack.religions,
        biome: pack.biomes, good: pack.goods};
      let el;
      if (type === 'regiment') el = pack.states[id]?.military?.find((r) => r.i === Number(sub));
      else if (lists[type]) el = lists[type][id]?.i === id ? lists[type][id] : lists[type].find((x) => x && x.i === id);
      else throw new Error(`notes: unknown element type ${type}`);
      if (!el || el.removed) { warn(`notes: ${key} is not on this map`); continue; }
      if (text) el.note = text; else delete el.note;
    }
  }
  function applyPopulation(spec) {
    const S = spec.rural_population;
    if (!S) return;
    const scale = new Float64Array(pack.cells.i.length).fill(S.scale ?? 1);
    for (const [shire, k] of Object.entries(S.shires || {})) for (const c of shireCells([+shire], 'rural_population')) scale[c] = k;
    for (const c of pack.cells.i) if (pack.cells.pop[c]) pack.cells.pop[c] = Math.round(pack.cells.pop[c] * scale[c] * 1e4) / 1e4;
  }

  // ------------------------------------------------------------------ checks: what Azgaar's loader would complain about
  function integrity() {
    const out = [];
    const {cells} = pack;
    const bad = (m) => out.push(m);
    const exists = (list, i) => list[i] && !list[i].removed;
    for (const c of cells.i) {
      if (!exists(pack.states, cells.state[c])) bad(`cell ${c}: state ${cells.state[c]}`);
      if (cells.province[c] && !exists(pack.provinces, cells.province[c])) bad(`cell ${c}: province ${cells.province[c]}`);
      if (!exists(pack.cultures, cells.culture[c])) bad(`cell ${c}: culture ${cells.culture[c]}`);
      if (!exists(pack.religions, cells.religion[c])) bad(`cell ${c}: religion ${cells.religion[c]}`);
      if (cells.burg[c] && (!exists(pack.burgs, cells.burg[c]) || pack.burgs[cells.burg[c]].cell !== c)) bad(`cell ${c}: burg ${cells.burg[c]}`);
    }
    for (const b of pack.burgs) {
      if (!b || !b.i || b.removed) continue;
      if (cells.burg[b.cell] !== b.i) bad(`burg ${b.i}: its cell ${b.cell} holds burg ${cells.burg[b.cell]}`);
      if (b.state !== cells.state[b.cell]) bad(`burg ${b.i}: state ${b.state}, cell state ${cells.state[b.cell]}`);
      if (!exists(pack.cultures, b.culture)) bad(`burg ${b.i}: culture ${b.culture}`);
      if (b.capital && !b.state) bad(`burg ${b.i}: a neutral capital`);
    }
    for (const s of pack.states) {
      if (!s.i || s.removed) continue;
      const caps = pack.burgs.filter((b) => b && b.i && !b.removed && b.state === s.i && b.capital);
      if (caps.length !== 1) bad(`state ${s.i}: ${caps.length} capitals`);
      if (s.diplomacy.length !== pack.states.length) bad(`state ${s.i}: diplomacy has ${s.diplomacy.length} entries for ${pack.states.length} states`);
      if (!exists(pack.cultures, s.culture)) bad(`state ${s.i}: culture ${s.culture}`);
    }
    for (const p of pack.provinces) if (p && p.i && !p.removed && !exists(pack.states, p.state)) bad(`province ${p.i}: state ${p.state}`);
    for (const r of pack.routes) if (!r.points || r.points.length < 2) bad(`route ${r.i}: fewer than 2 points`);
    const ids = new Set();
    for (const m of pack.markers) { if (ids.has(m.i)) bad(`marker ${m.i}: id used twice`); ids.add(m.i); }
    pack.states.forEach((s, k) => { if (s.i !== k) bad(`state at ${k} has id ${s.i}`); });
    pack.provinces.forEach((p, k) => { if (k && p.i !== k) bad(`province at ${k} has id ${p.i}`); });
    pack.burgs.forEach((b, k) => { if (k && b.i !== k) bad(`burg at ${k} has id ${b.i}`); });
    pack.cultures.forEach((c, k) => { if (c.i !== k) bad(`culture at ${k} has id ${c.i}`); });
    pack.religions.forEach((r, k) => { if (r.i !== k) bad(`religion at ${k} has id ${r.i}`); });
    return out;
  }

  function counts() {
    const live = (l) => l.filter((x) => x && x.i && !x.removed).length;
    return {states: live(pack.states), provinces: live(pack.provinces), burgs: live(pack.burgs),
      cultures: live(pack.cultures), religions: live(pack.religions), routes: pack.routes.length,
      markers: pack.markers.length, zones: pack.zones.length, addedLabels: pack.addedLabels.length,
      regiments: pack.states.reduce((a, s) => a + (s.military?.length || 0), 0), markets: pack.markets.length,
      deals: pack.deals.length, journeys: pack.journeys.length};
  }

  // ------------------------------------------------------------------ the whole spec
  function apply(spec) {
    warnings = [];
    keys = Object.fromEntries(TYPES.map((t) => [t, {}]));
    placeIds = {};
    const seed = hashString(String(spec.seed ?? spec.name ?? 'era'));
    const savedRandom = Math.random;
    Math.random = mulberry32(seed);
    try {
      master = {
        cellProvince: Uint16Array.from(pack.cells.province),
        provinceIds: new Set(pack.provinces.filter((p) => p && p.i && !p.removed).map((p) => p.i)),
        states: clone(pack.states),
      };
      Routes.sync();
      Goods.sync();
      Markets.sync();
      applyLore(spec);
      applyUnits(spec);
      applyRenames(spec);
      const culturesAssigned = applyCultures(spec);
      applyReligions(spec);
      const burgInfo = applyBurgs(spec);
      const statesChanged = applyStates(spec);
      applyProvinces(spec, statesChanged);
      finishBurgs(spec, burgInfo, culturesAssigned);
      applyPopulation(spec);
      recalculate();
      // colours for states that were given none: one no neighbour has
      for (const s of pack.states) {
        if (!s.i || s.removed || s.color) continue;
        s.color = PALETTE.find((c) => s.neighbors.every((n) => pack.states[n]?.color !== c)) || PALETTE[s.i % PALETTE.length];
      }
      applyDiplomacy(spec, statesChanged);
      applyMilitary(spec, statesChanged);
      applyRoutes(spec);
      applyMarkers(spec);
      applyZones(spec);
      applyLabels(spec);
      applyEconomy(spec);
      applyJourneys(spec);
      applyNotes(spec);
      recalculate();
      if (statesChanged) for (const s of pack.states) if (s.i && !s.removed && s.form === 'Monarchy' && !s.formName) s.formName = 'Kingdom';
    } finally {
      Math.random = savedRandom;
    }
    return {warnings, ids: keys, placeIds, counts: counts(), integrity: integrity()};
  }

  function redraw(active) {
    if (active) Layers.set(active);
    Layers.drawAll();
  }

  window.EraEngine = {apply, redraw, integrity, counts};
})();
