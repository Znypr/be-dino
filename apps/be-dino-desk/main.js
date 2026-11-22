// Be Dino Desk (docs/247-be-dino-desk.md, BD-1292). Shows what is in the game as grids and keeps the owner's verdict per item.
// The catalog comes from tools/desk_catalog.py (run with the system python); pictures load through desk://repo/<rel>, which only
// serves image files under the repo. Feedback is written to docs/feedback/asset-desk.json on every change (never in smoke mode).
const { app, BrowserWindow, ipcMain, protocol, Menu, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { Readable } = require('stream');

const REPO = process.env.BE_DINO_REPO || 'C:\\Users\\znypr\\Documents\\be-dino';
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
