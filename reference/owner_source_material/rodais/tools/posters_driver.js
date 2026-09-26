/*
 * posters_driver.js -- the headless half of tools/make_posters.py (Playwright + Chromium).
 *
 *   node posters_driver.js CONFIG.json
 *
 * mode "maps":    for every map, load it in Azgaar's generator (Diathir_Atlas/fmg/) by ?maplink=, and write
 *                 - work/map_<K>.png and .jpg: the map at `scale` times its size, with the poster's layers
 *                 - work/info_<K>.json: its realms (name, colour, label point), calendar, counts
 *                 - overlay (optional): its realms' outlines, as Azgaar draws them (#statesBody), for the Atlas's
 *                   "realms of another age" overlay
 *                 - shots (optional): the states, cultures, religions, routes and provinces pictures, made exactly as
 *                   eras/engine/driver.js makes the era maps' (1536 x 702, the same layers), for "then and now"
 * mode "compose": screenshot each poster page (an HTML file under the server) to its PNG and thumbnail, and print
 *                 every poster, one to a page, to the PDF.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const W = 1536, H = 702;

async function openMap(browser, mapPath, scale) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: scale });
  const log = { pageErrors: [] };
  await page.addInitScript(() => {
    try { localStorage.clear(); localStorage.setItem('version', '1.153.1'); } catch (e) { /* storage may be off */ }
  });
  await page.route((u) => !u.href.startsWith(cfg.base), (r) => r.abort());   // nothing leaves the machine
  page.on('pageerror', (e) => log.pageErrors.push(String(e && e.message || e)));
  await page.goto(`${cfg.base}${cfg.fmg}index.html?maplink=${cfg.base}${mapPath}`);
  await page.waitForFunction(() => /successfully loaded/.test(document.getElementById('tooltip')?.innerText || ''),
    null, { timeout: 180000, polling: 250 });
  await page.waitForTimeout(800);
  return { page, log };
}

const HIDE = '#optionsContainer,#tooltip,.ui-dialog,#dialogs,#mapLayers,#loading,#journeyPlayer,[id*="layer-toggle"],' +
  'button{display:none!important}';

async function doMap(browser, m) {
  const { page, log } = await openMap(browser, m.path, cfg.scale);
  await page.addStyleTag({ content: HIDE });
  // hide anything fixed-position over the map (a player button, a notice): the picture is the map alone
  await page.evaluate(() => {
    document.querySelectorAll('body *').forEach((el) => {
      if (el.closest('#map')) return;
      const s = getComputedStyle(el);
      if ((s.position === 'fixed' || s.position === 'absolute') && el.id !== 'map' && !el.querySelector('#map')) el.style.visibility = 'hidden';
    });
  });
  const info = await page.evaluate(() => {
    const st = pack.states.filter((s) => s.i && !s.removed).map((s) => ({
      i: s.i, name: s.name, full: s.fullName || s.name, color: s.color, pole: s.pole || null,
      cells: (s.cells != null ? s.cells : null), capital: s.capital ? (pack.burgs[s.capital] || {}).name : null }));
    const burgs = pack.burgs.filter((b) => b.i && !b.removed);
    const groups = {};
    (pack.routes || []).forEach((r) => { groups[r.group] = (groups[r.group] || 0) + 1; });
    return {
      states: st, burgs: burgs.length, capitals: burgs.filter((b) => b.capital).length, ports: burgs.filter((b) => b.port).length,
      routes: groups, markers: (pack.markers || []).length, journeys: (pack.journeys || []).length,
      zones: (pack.zones || []).filter((z) => !z.hidden).length,
      year: window.options && options.year, era: window.options && options.era, eraShort: window.options && options.eraShort,
      name: window.mapName && mapName.value
    };
  });
  // the realms' outlines, as Azgaar draws them
  if (m.overlay) {
    const ov = await page.evaluate(() => {
      Layers.show('states');
      const out = [];
      pack.states.filter((s) => s.i && !s.removed).forEach((s) => {
        const p = document.getElementById('state' + s.i);
        const d = p && p.getAttribute('d');
        if (d) out.push({ i: s.i, name: s.name, full: s.fullName || s.name, color: s.color,
          pole: s.pole ? [Math.round(s.pole[0] * 10) / 10, Math.round(s.pole[1] * 10) / 10] : null, d: d });
      });
      return out;
    });
    fs.mkdirSync(path.dirname(m.overlay), { recursive: true });
    fs.writeFileSync(m.overlay, JSON.stringify({ key: m.key, width: 1536, height: 702, states: ov }));
  }
  // the five pictures, exactly as the era maps' are made (eras/engine/driver.js), at the map's own size
  if (m.shots) {
    fs.mkdirSync(m.shots, { recursive: true });
    const base = ['burgIcons', 'labels', 'rivers', 'lakes', 'coastline'];
    const views = { states: ['states', 'borders'], cultures: ['cultures'], religions: ['religions'],
      routes: ['routes', 'borders', 'markers', 'zones'], provinces: ['provinces', 'borders'] };
    for (const [name, layers] of Object.entries(views)) {
      await page.evaluate((l) => { window.Layers.set(l); if (window.resetZoom) window.resetZoom(0); }, [...base, ...layers]);
      await page.waitForTimeout(700);
      await page.locator('#map').screenshot({ path: path.join(m.shots, `${m.shotPrefix}${name}.png`), scale: 'css' });
    }
  }
  // the poster's map
  await page.evaluate((l) => {
    window.Layers.set(l); if (window.resetZoom) window.resetZoom(0);
    const sb = document.getElementById('statesBody'); if (sb) sb.setAttribute('opacity', '0.55');
  }, cfg.layers);
  await page.waitForTimeout(1800);
  await page.locator('#map').screenshot({ path: path.join(cfg.work, `map_${m.key}.png`) });
  await page.locator('#map').screenshot({ path: path.join(cfg.work, `map_${m.key}.jpg`), type: 'jpeg', quality: 88 });
  info.errors = log.pageErrors;
  fs.writeFileSync(path.join(cfg.work, `info_${m.key}.json`), JSON.stringify(info));
  await page.close();
  console.log('map ' + m.key + ': ' + info.states.length + ' realms, ' + info.burgs + ' towns');
}

async function compose(browser) {
  for (const p of cfg.posters) {
    const page = await browser.newPage({ viewport: { width: cfg.pw, height: cfg.ph }, deviceScaleFactor: cfg.pscale });
    await page.route((u) => !u.href.startsWith(cfg.base), (r) => r.abort());
    await page.goto(cfg.base + p.url);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth), null, { timeout: 60000 });
    await page.screenshot({ path: p.png, fullPage: false });
    await page.screenshot({ path: p.print, type: 'jpeg', quality: 90 });
    await page.close();
    const th = await browser.newPage({ viewport: { width: cfg.pw, height: cfg.ph }, deviceScaleFactor: 480 / cfg.pw });
    await th.route((u) => !u.href.startsWith(cfg.base), (r) => r.abort());
    await th.goto(cfg.base + p.url);
    await th.evaluate(() => document.fonts.ready);
    await th.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth), null, { timeout: 60000 });
    await th.screenshot({ path: p.thumb, type: 'jpeg', quality: 82 });
    await th.close();
    console.log('poster ' + path.basename(p.png));
  }
  if (cfg.pdf) {
    const page = await browser.newPage({ viewport: { width: cfg.pw, height: cfg.ph } });
    await page.route((u) => !u.href.startsWith(cfg.base), (r) => r.abort());
    await page.goto(cfg.base + cfg.pdf.url);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth), null, { timeout: 120000 });
    await page.pdf({ path: cfg.pdf.out, width: cfg.pw + 'px', height: cfg.ph + 'px', printBackground: true,
      margin: { top: 0, right: 0, bottom: 0, left: 0 } });
    await page.close();
    console.log('pdf ' + path.basename(cfg.pdf.out));
  }
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--no-sandbox'] });
  try {
    if (cfg.mode === 'maps') { for (const m of cfg.maps) await doMap(browser, m); }
    else await compose(browser);
  } catch (e) {
    console.error(String(e && e.stack || e));
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
