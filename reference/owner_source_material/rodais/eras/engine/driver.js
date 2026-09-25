/*
 * driver.js -- drives Azgaar's Fantasy Map Generator headless (Playwright + Chromium) for build_era_map.py.
 *
 *   node driver.js CONFIG.json
 *
 * CONFIG: {mode: "build" | "verify", base: "http://127.0.0.1:PORT", fmg: "/Diathir_Atlas/fmg/",
 *          save: "save-<hash>.js", map: "/path/of/map/under/the/server", spec: "spec.json" (build),
 *          out: "out.map" (build), report: "report.json", shots: "dir" (verify, optional),
 *          active: [layer ids] (build, optional)}
 *
 * build:  load the master by ?maplink=, inject era_engine.js, EraEngine.apply(spec), redraw every layer
 *         (Layers.drawAll), make the .map text with Azgaar's own Save.prepareMapData(), write it to `out`.
 * verify: load a map by ?maplink= in a fresh page; record page errors, error dialogs and Azgaar's
 *         "[Data integrity]" messages; counts; borders; save it again with Save.prepareMapData() (round trip);
 *         screenshots of the states, cultures, religions and routes layers.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const IGNORE = [/Failed to load resource: net::ERR_FAILED/, /fonts\.gstatic|fonts\.googleapis/];

async function openMap(browser, mapPath) {
  // the page is the map's own size, so the whole map is in view (Azgaar draws only the labels in view)
  const page = await browser.newPage({ viewport: { width: cfg.width || 1536, height: cfg.height || 702 } });
  const log = { pageErrors: [], consoleErrors: [], integrity: [], warnings: [] };
  await page.addInitScript(() => {
    try { localStorage.clear(); localStorage.setItem('version', '1.153.1'); } catch (e) { /* storage may be off */ }
  });
  // nothing leaves the machine: only our own server is reachable (Google fonts fall back to local ones)
  await page.route((u) => !u.href.startsWith(cfg.base), (r) => r.abort());
  page.on('pageerror', (e) => log.pageErrors.push(String(e && e.stack || e)));
  page.on('console', (m) => {
    const t = m.text();
    if (/\[Data integrity\]/.test(t)) log.integrity.push(t);
    else if (m.type() === 'error' && !IGNORE.some((r) => r.test(t))) log.consoleErrors.push(t.slice(0, 500));
  });
  const url = `${cfg.base}${cfg.fmg}index.html?maplink=${cfg.base}${mapPath}`;
  await page.goto(url);
  await page.waitForFunction(() => {
    const tip = document.getElementById('tooltip');
    if (tip && /successfully loaded/.test(tip.innerText)) return true;
    const alert = document.getElementById('alert');
    const dlg = alert && alert.closest('.ui-dialog');
    return !!(dlg && dlg.style.display !== 'none' && /error|Error|invalid|Cannot/.test(dlg.innerText));
  }, null, { timeout: 120000, polling: 200 });
  log.dialogs = await page.evaluate(() => [...document.querySelectorAll('.ui-dialog')]
    .filter((d) => d.style.display !== 'none' && d.offsetParent !== null).map((d) => d.innerText.slice(0, 600)));
  log.loaded = await page.evaluate(() => /successfully loaded/.test(document.getElementById('tooltip')?.innerText || ''));
  return { page, log };
}

async function saveString(page) {
  return page.evaluate(async (mod) => {
    const { Save } = await import(mod);
    return Save.prepareMapData();
  }, `${cfg.base}${cfg.fmg}${cfg.save}`);
}

async function build(browser) {
  const { page, log } = await openMap(browser, cfg.map);
  if (!log.loaded) throw new Error('the master map did not load: ' + JSON.stringify(log));
  await page.addScriptTag({ path: path.join(__dirname, 'era_engine.js') });
  const spec = JSON.parse(fs.readFileSync(cfg.spec, 'utf8'));
  let report;
  try {
    report = await page.evaluate((s) => window.EraEngine.apply(s), spec);
  } catch (e) {
    throw new Error('the spec could not be applied: ' + (e.message || e));
  }
  const active = cfg.active || (spec.layers && spec.layers.active) || null;
  await page.evaluate((a) => window.EraEngine.redraw(a), active);
  await page.waitForTimeout(500);
  report.drawErrors = log.pageErrors.slice();
  report.masterLoad = log;
  const text = await saveString(page);
  fs.writeFileSync(cfg.out, text, 'utf8');
  report.bytes = Buffer.byteLength(text, 'utf8');
  report.records = text.split('\r\n').length;
  fs.writeFileSync(cfg.report, JSON.stringify(report, null, 1));
  await page.close();
}

async function verify(browser) {
  const { page, log } = await openMap(browser, cfg.map);
  const res = { load: log };
  if (!log.loaded) { fs.writeFileSync(cfg.report, JSON.stringify(res, null, 1)); return; }
  await page.addScriptTag({ path: path.join(__dirname, 'era_engine.js') });
  res.counts = await page.evaluate(() => window.EraEngine.counts());
  res.integrity = await page.evaluate(() => window.EraEngine.integrity());
  res.layers = await page.evaluate(() => {
    const out = {};
    const q = (s) => document.querySelector(s);
    out.active = window.Layers.layers.filter((l) => window.Layers.isOn(l.id)).map((l) => l.id);
    out.burgIcons = document.querySelectorAll('#burgIcons use, #icons use').length;
    out.labels = document.querySelectorAll('#labels text').length;
    out.routes = document.querySelectorAll('#routes path').length;
    out.stateBordersLength = (q('#stateBorders path')?.getAttribute('d') || '').length;
    out.provinceBordersLength = (q('#provinceBorders path')?.getAttribute('d') || '').length;
    return out;
  });
  // the round trip: save the freshly loaded map again, before any layer is toggled
  const again = await saveString(page);
  const orig = fs.readFileSync(path.join(cfg.root, cfg.map.replace(/^\//, '')), 'utf8');
  const a = orig.split('\r\n'), b = again.split('\r\n');
  res.roundTrip = { identical: orig === again, records: [a.length, b.length], differing: [] };
  for (let k = 0; k < Math.max(a.length, b.length); k++) {
    if (a[k] === b[k]) continue;
    const x = a[k] || '', y = b[k] || '';
    let i = 0;
    while (i < x.length && x[i] === y[i]) i++;
    res.roundTrip.differing.push({ record: k, lengths: [x.length, y.length], at: i,
      before: x.slice(Math.max(0, i - 60), i + 120), after: y.slice(Math.max(0, i - 60), i + 120) });
  }
  if (cfg.againOut) fs.writeFileSync(cfg.againOut, again, 'utf8');
  // every layer drawn, then the screenshots
  res.draw = await page.evaluate(() => {
    const out = {};
    const all = ['states', 'borders', 'provinces', 'cultures', 'religions', 'burgIcons', 'labels', 'routes', 'markers',
      'zones', 'emblems', 'military', 'rivers', 'lakes', 'coastline', 'relief', 'goods', 'markets', 'journeys', 'biomes',
      'population'];
    window.Layers.set(all);
    const n = (s) => document.querySelectorAll(s).length;
    out.statesBody = n('#statesBody path');
    out.provinces = n('#provincesBody path');
    out.cultures = n('#cults path');
    out.religions = n('#relig path');
    out.routes = n('#routes path');
    out.markers = n('#markers svg, #markers use, #markers g');
    out.zones = n('#zones > *');
    out.military = n('#armies g');
    out.burgs = n('#burgIcons use, #icons use');
    out.emblems = n('#emblems use');
    return out;
  });
  await page.waitForTimeout(1500);
  res.draw.emblems = await page.evaluate(() => document.querySelectorAll('#emblems use').length);
  res.drawErrors = log.pageErrors.slice();
  if (cfg.shots) {
    fs.mkdirSync(cfg.shots, { recursive: true });
    await page.addStyleTag({ content: '#optionsContainer,#tooltip,.ui-dialog,#dialogs,#mapLayers,#loading{display:none!important}' });
    const base = ['burgIcons', 'labels', 'rivers', 'lakes', 'coastline'];
    const views = { states: ['states', 'borders'], cultures: ['cultures'], religions: ['religions'],
      routes: ['routes', 'borders', 'markers', 'zones'], provinces: ['provinces', 'borders'] };
    res.shots = {};
    for (const [name, layers] of Object.entries(views)) {
      await page.evaluate((l) => { window.Layers.set(l); if (window.resetZoom) window.resetZoom(0); }, [...base, ...layers]);
      await page.waitForTimeout(700);
      const file = path.join(cfg.shots, `${cfg.prefix || ''}${name}.png`);
      await page.locator('#map').screenshot({ path: file });
      res.shots[name] = file;
    }
  }
  res.pageErrorsAfterDraw = log.pageErrors.slice();
  fs.writeFileSync(cfg.report, JSON.stringify(res, null, 1));
  await page.close();
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--no-sandbox'] });
  try {
    if (cfg.mode === 'build') await build(browser);
    else await verify(browser);
  } catch (e) {
    console.error(String(e && e.message || e));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
