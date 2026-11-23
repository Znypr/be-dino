// Be Dino Desk (docs/247-be-dino-desk.md, BD-1292). Shows what is in the game as grids and keeps the owner's verdict per item.
// The catalog comes from tools/desk_catalog.py (run with the system python); pictures load through desk://repo/<rel>, which only
// serves image files under the repo. Feedback is written to docs/feedback/asset-desk.json on every change (never in smoke mode).
const { app, BrowserWindow, ipcMain, protocol, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { Readable } = require('stream');

// The repo to show: BE_DINO_REPO, else repo.txt in the app's data folder (build.ps1 writes the main checkout there), else the
// checkout this source sits in (apps/be-dino-desk -> ../..). No machine path is stored in the repo (public repo rule).
function repoPath() {
  if (process.env.BE_DINO_REPO) return process.env.BE_DINO_REPO;
  try { const t = fs.readFileSync(path.join(app.getPath('appData'), 'Be Dino Desk', 'repo.txt'), 'utf8').trim(); if (t && fs.existsSync(t)) return t; } catch {}
  return path.resolve(__dirname, '..', '..');
}
const REPO = repoPath();
const PY = process.env.BE_DINO_PYTHON || 'python';
const TOOLS = process.env.BE_DINO_TOOLS || path.join(REPO, 'tools');   // a worktree's tools can list the main checkout
const FEEDBACK = path.join(REPO, 'docs', 'feedback', 'asset-desk.json');
const SMOKE = process.argv.includes('--smoke');
const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const TYPES = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp' };
if (SMOKE) app.setPath('userData', path.join(require('os').tmpdir(), 'be-dino-desk-smoke-' + process.pid));

protocol.registerSchemesAsPrivileged([{ scheme: 'desk', privileges: { standard: true, secure: true, supportFetchAPI: true } }]);

const readJson = (p, d = null) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return d; } };

function run(script, args, timeoutMs = 120000) {
  return new Promise((resolve) => {
    const p = spawn(PY, [path.join(TOOLS, script), ...args], { cwd: REPO, windowsHide: true, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
    let out = '', err = '';
    p.stdout.on('data', (d) => { out += d; });
    p.stderr.on('data', (d) => { err += d; });
    const t = setTimeout(() => p.kill(), timeoutMs);
    p.on('error', (e) => { clearTimeout(t); resolve({ code: -1, out, err: String(e) }); });
    p.on('close', (code) => { clearTimeout(t); resolve({ code, out, err }); });
  });
}

async function catalog() {
  const r = await run('desk_catalog.py', ['--root', REPO]);
  if (r.code !== 0) throw new Error('desk_catalog.py failed: ' + (r.err || r.out).slice(-600));
  return JSON.parse(r.out);
}

function media(req) {
  const u = new URL(req.url);
  const rel = decodeURIComponent(u.pathname).replace(/^\/+/, '');
  const file = path.resolve(REPO, rel);
  const ok = u.host === 'repo' && file.toLowerCase().startsWith(path.resolve(REPO).toLowerCase() + path.sep) && TYPES[path.extname(file).toLowerCase()];
  if (!ok || !fs.existsSync(file) || !fs.statSync(file).isFile()) return new Response('not found', { status: 404 });
  return new Response(Readable.toWeb(fs.createReadStream(file)), {
    status: 200, headers: { 'Content-Type': TYPES[path.extname(file).toLowerCase()], 'Cache-Control': 'max-age=60' },
  });
}

// feedback: { items: { id: {verdict, note, at} }, groups: { id: {note, at} } }
function feedbackLoad() { return readJson(FEEDBACK, { items: {}, groups: {} }); }
function feedbackSave(fb) {
  if (!fb || typeof fb !== 'object' || typeof fb.items !== 'object') throw new Error('bad feedback');
  const clean = { about: 'Owner verdicts from the Be Dino Desk (docs/247). verdict = like | dislike | upgrade; id = repo-relative path.',
    items: {}, groups: {} };
  for (const [id, v] of Object.entries(fb.items || {}).slice(0, 5000)) {
    if (!v || (!v.verdict && !v.note)) continue;
    if (v.verdict && !['like', 'dislike', 'upgrade'].includes(v.verdict)) continue;
    clean.items[String(id).slice(0, 300)] = { ...(v.verdict ? { verdict: v.verdict } : {}), ...(v.note ? { note: String(v.note).slice(0, 2000) } : {}), at: String(v.at || '').slice(0, 19) };
  }
  for (const [id, v] of Object.entries(fb.groups || {}).slice(0, 500)) {
    if (v && v.note) clean.groups[String(id).slice(0, 300)] = { note: String(v.note).slice(0, 4000), at: String(v.at || '').slice(0, 19) };
  }
  if (SMOKE) return { smoke: true, items: Object.keys(clean.items).length };
  fs.mkdirSync(path.dirname(FEEDBACK), { recursive: true });
  const ordered = { about: clean.about, items: Object.fromEntries(Object.entries(clean.items).sort()), groups: Object.fromEntries(Object.entries(clean.groups).sort()) };
  fs.writeFileSync(FEEDBACK, JSON.stringify(ordered, null, 1) + '\n', 'utf8');
  return { saved: true, items: Object.keys(clean.items).length };
}

// Menus tab (BD-1301): owner notes per spec element and free pins, in docs/feedback/menu-feedback.json
// { screens: { screen: { elements: { specId: [note] }, pins: [note + {x, y, side}] } } }, note = {id, tags, note, severity, should,
// at, check, status}. Every change is one operation applied to the file as it is on disk right now (agents may have set a note to
// "done" meanwhile), so the desk never writes back a stale copy. Smoke mode applies it in memory only and never writes.
const MENU_FB = path.join(REPO, 'docs', 'feedback', 'menu-feedback.json');
const MENU_TAGS = ['Size', 'Position', 'Colour', 'Outline', 'Text size', 'Words', 'Font', 'Spacing', 'Art', 'Missing', 'Remove'];
let smokeMenuFb = null;
const menuFbRead = () => {
  if (SMOKE && smokeMenuFb) return smokeMenuFb;
  const d = readJson(MENU_FB, null);
  return d && typeof d === 'object' && d.screens && typeof d.screens === 'object' ? d : { screens: {} };
};
const str = (v, n) => String(v ?? '').slice(0, n);
function noteFields(f, base = {}) {
  const out = { ...base };
  if ('tags' in f) out.tags = (Array.isArray(f.tags) ? f.tags : []).filter((t) => MENU_TAGS.includes(t));
  if ('note' in f) out.note = str(f.note, 2000).trim();
  if ('severity' in f) out.severity = f.severity === 'nice' ? 'nice' : 'must';
  if ('should' in f) out.should = str(f.should, 300).trim();
  if ('status' in f) out.status = f.status === 'done' ? 'done' : 'open';
  if ('check' in f) out.check = str(f.check, 19);
  return out;
}
function menuFbOp(op) {
  const data = JSON.parse(JSON.stringify(menuFbRead()));
  const screen = str(op && op.screen, 80);
  if (!/^[a-z0-9][a-z0-9_-]*$/i.test(screen)) throw new Error('bad screen');
  const scr = (data.screens[screen] = data.screens[screen] || { elements: {}, pins: [] });
  scr.elements = scr.elements || {}; scr.pins = scr.pins || [];
  const all = () => [...Object.values(scr.elements).flat(), ...scr.pins];
  if (op.kind === 'add') {
    const n = noteFields({ tags: [], note: '', severity: 'must', should: '', status: 'open', check: '', ...op.fields },
      { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6) });
    if (!n.tags.length && !n.note) throw new Error('empty note');
    n.at = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 19);   // local time, like report.json
    const t = op.target || {};
    if (t.element) {
      const id = str(t.element, 80);
      if (!/^[a-z0-9_.*-]+$/i.test(id)) throw new Error('bad element');
      (scr.elements[id] = scr.elements[id] || []).push(n);
    } else {
      const clamp = (v) => Math.round(Math.max(-50, Math.min(150, Number(v) || 0)) * 100) / 100;
      scr.pins.push({ ...n, x: clamp(t.x), y: clamp(t.y), side: t.side === 'proposal' ? 'proposal' : 'build' });
    }
  } else if (op.kind === 'update' || op.kind === 'remove') {
    const n = all().find((x) => x && x.id === op.id);
    if (!n) throw new Error('note not found (changed on disk?)');
    if (op.kind === 'update') Object.assign(n, noteFields(op.fields || {}));
    else {
      for (const k of Object.keys(scr.elements)) { scr.elements[k] = scr.elements[k].filter((x) => x !== n); if (!scr.elements[k].length) delete scr.elements[k]; }
      scr.pins = scr.pins.filter((x) => x !== n);
    }
  } else throw new Error('bad op');
  const ordered = { about: 'Owner notes per menu element from the Be Dino Desk Menus tab (docs/247, BD-1301). Agents: read before each menu step; '
    + 'set status "done" + "commit" when fixed; never delete a note.', screens: {} };
  for (const s of Object.keys(data.screens).sort()) {
    const v = data.screens[s];
    ordered.screens[s] = { elements: Object.fromEntries(Object.entries(v.elements || {}).sort()), pins: v.pins || [] };
  }
  if (SMOKE) { smokeMenuFb = ordered; return { smoke: true, data: ordered }; }
  fs.mkdirSync(path.dirname(MENU_FB), { recursive: true });
  fs.writeFileSync(MENU_FB, JSON.stringify(ordered, null, 1) + '\n', 'utf8');
  return { saved: true, data: ordered };
}

const winFile = () => path.join(app.getPath('userData'), 'window.json');
function createWindow() {
  const b = readJson(winFile(), { width: 1360, height: 900 });
  const win = new BrowserWindow({
    ...b, minWidth: 800, minHeight: 560, backgroundColor: '#18181b', title: 'Be Dino Desk', show: false,
    icon: path.join(__dirname, 'build', 'icon.ico'),
    webPreferences: { preload: path.join(__dirname, 'preload.js'), contextIsolation: true, nodeIntegration: false, backgroundThrottling: !SMOKE, offscreen: SMOKE },
  });
  if (b.maximized) win.maximize();
  win.once('ready-to-show', () => { if (!SMOKE) win.show(); });
  win.on('close', () => { try { fs.writeFileSync(winFile(), JSON.stringify({ ...win.getNormalBounds(), maximized: win.isMaximized() })); } catch {} });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https:\/\//.test(url)) shell.openExternal(url); return { action: 'deny' }; });
  if (SMOKE) win.webContents.on('console-message', (e) => console.log('page:', e.message));
  win.loadFile(path.join(__dirname, 'dist', 'index.html'), { query: SMOKE ? { smoke: arg('--smoke') || 'all' } : {} });
  return win;
}

if (!SMOKE && !app.requestSingleInstanceLock()) app.quit();
app.on('second-instance', () => { const w = BrowserWindow.getAllWindows()[0]; if (w) { if (w.isMinimized()) w.restore(); w.focus(); } });

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  protocol.handle('desk', media);
  const handle = (ch, fn) => ipcMain.handle(ch, async (_e, ...a) => fn(...a));
  handle('catalog', catalog);
  handle('feedback:load', feedbackLoad);
  handle('feedback:save', feedbackSave);
  handle('menufb:load', menuFbRead);
  handle('menufb:op', menuFbOp);
  handle('open:file', (rel) => {   // "Show in folder" for one picture
    const file = path.resolve(REPO, String(rel));
    if (!file.startsWith(path.resolve(REPO) + path.sep) || !fs.existsSync(file)) throw new Error('not found');
    shell.showItemInFolder(file); return true;
  });
  handle('smoke:shot', async (name) => {   // BE_DINO_DESK_SHOTS=<dir>: smoke run saves screenshots there
    const dir = process.env.BE_DINO_DESK_SHOTS; if (!dir) return;
    const img = await BrowserWindow.getAllWindows()[0].webContents.capturePage();
    fs.writeFileSync(path.join(dir, String(name).replace(/[^a-z0-9-]/gi, '_') + '.png'), img.toPNG());
  });
  handle('smoke:done', (report) => { console.log('SMOKE ' + JSON.stringify(report)); setTimeout(() => app.exit(report.ok ? 0 : 1), 50); });
  createWindow();
  if (SMOKE) setTimeout(() => { console.log('SMOKE timeout'); app.exit(2); }, 120000);
});
app.on('window-all-closed', () => app.quit());
