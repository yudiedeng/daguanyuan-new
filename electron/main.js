// 大观园桌面壳：给云渲染平台跑的 Windows 程序。
// 默认打开线上网页（config.json 的 url），网站一更新，云端下次启动就是新版，不用重新打包。
// 线上打不开（断网、域名被墙）时退回包里自带的 site/ 目录；加 --local 则直接用本地文件。
const { app, BrowserWindow, protocol, net } = require('electron');
const VENDOR = (app.isPackaged ? process.resourcesPath : __dirname + '/node_modules');  // three.js 打进包里（国内机房连 jsdelivr 常卡住）
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');

const RES = app.isPackaged ? process.resourcesPath : __dirname;
const SITE = app.isPackaged ? path.join(RES, 'site') : path.join(__dirname, '..');

function readConfig() {
  const cfg = { url: 'https://yudiedeng.github.io/daguanyuan-new/', fullscreen: true };
  // exe 旁边的 config.json 优先，方便在云平台上改地址而不重新打包
  for (const p of [path.join(path.dirname(process.execPath), 'config.json'), path.join(RES, 'config.json')]) {
    try { Object.assign(cfg, JSON.parse(fs.readFileSync(p, 'utf8'))); break; } catch (e) {}
  }
  const arg = process.argv.find(a => a.startsWith('--url='));
  if (arg) cfg.url = arg.slice(6);
  if (process.argv.includes('--local')) cfg.url = null;
  if (process.argv.includes('--windowed')) cfg.fullscreen = false;
  return cfg;
}

// 运行日志：写在 exe 旁边的 daguanyuan.log（写不进就写到用户数据目录），云平台上出错时用来排查
let LOG = path.join(path.dirname(process.execPath), 'daguanyuan.log');
function log(...a) {
  const line = new Date().toISOString() + ' ' + a.map(x => (x && x.stack) || String(x)).join(' ') + '\n';
  try { fs.appendFileSync(LOG, line); } catch (e) {
    try { LOG = path.join(app.getPath('userData'), 'daguanyuan.log'); fs.appendFileSync(LOG, line); } catch (e2) {}
  }
}
process.on('uncaughtException', e => log('uncaughtException', e));
log('start', process.execPath, process.argv.join(' '));

// 云渲染平台常以服务账号运行程序，Chromium 沙箱在那里起不来会直接闪退，所以关掉沙箱
app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('disable-gpu-sandbox');
// 云端机器上没人点“允许”：声音自动播放、不限 GPU、窗口失焦也照常渲染
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-background-timer-throttling');

// 本地模式走 app:// 协议而不是 file://，这样 fetch('models/b/col.json') 和 GLTFLoader 都能正常读文件
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true } }
]);

const MIME = { js: 'text/javascript', mjs: 'text/javascript', css: 'text/css', html: 'text/html', json: 'application/json', wasm: 'application/wasm', png: 'image/png', jpg: 'image/jpeg', webp: 'image/webp', glb: 'model/gltf-binary' };
const fileResp = (file) => { if (!fs.existsSync(file)) return new Response('not found', { status: 404 });
  return new Response(fs.readFileSync(file), { headers: { 'content-type': MIME[path.extname(file).slice(1)] || 'application/octet-stream', 'access-control-allow-origin': '*' } }); };
const VMAP = [[/^https:\/\/cdn\.jsdelivr\.net\/npm\/three@[^/]+\/(.*)$/, () => path.join(VENDOR, 'three')], [/^https:\/\/cdn\.jsdelivr\.net\/npm\/@dgreenheck\/ez-tree@[^/]+\/(.*)$/, () => path.join(VENDOR, '@dgreenheck', 'ez-tree')]];

function serveLocal() {
  protocol.handle('app', req => {
    const rel = decodeURIComponent(new URL(req.url).pathname).replace(/^\/+/, '') || 'index.html';
    const file = path.normalize(path.join(SITE, rel));
    if (!file.startsWith(SITE)) return new Response('forbidden', { status: 403 });
    return net.fetch(pathToFileURL(file).toString());
  });
  // three.js、ez-tree 用包里的；Google 字体直接给空（用系统字体）；其余照常联网
  protocol.handle('https', req => {
    for (const [re, base] of VMAP) { const m = req.url.match(re); if (m) { const f = path.normalize(path.join(base(), m[1].split('?')[0])); if (f.startsWith(base())) return fileResp(f); } }
    if (/^https:\/\/fonts\.(googleapis|gstatic)\.com\//.test(req.url)) return new Response('', { headers: { 'content-type': 'text/css' } });
    return net.fetch(req, { bypassCustomProtocolHandlers: true });
  });
}

app.whenReady().then(() => {
  serveLocal();
  const cfg = readConfig();
  log('config', JSON.stringify(cfg), 'gpu', JSON.stringify(app.getGPUFeatureStatus()));
  const win = new BrowserWindow({
    width: 1920, height: 1080,
    fullscreen: cfg.fullscreen, autoHideMenuBar: true, backgroundColor: '#000000',
    title: '大观园',
    webPreferences: { backgroundThrottling: false, contextIsolation: true, sandbox: false }
  });
  win.setMenu(null);

  const LOCAL = 'app://site/index.html';
  let fellBack = false;
  let domReady = false;
  win.webContents.on('dom-ready', () => { domReady = true; log('dom-ready', win.webContents.getURL()); });
  win.webContents.on('did-finish-load', () => log('loaded', win.webContents.getURL()));
  // 线上网页 20 秒还没出来（国内机房连 github.io 常常不报错地卡住，只剩黑屏），改用包里的本地网页
  if (cfg.url) setTimeout(() => { if (!domReady && !fellBack) { fellBack = true; log('online timeout, use local'); win.loadURL(LOCAL); } }, 20000);
  win.webContents.on('console-message', (e, level, msg) => { if (level >= 2) log('console', msg); });
  // 渲染进程崩了（显卡驱动、内存）就重新打开页面，而不是留一个黑窗口
  win.webContents.on('render-process-gone', (e, d) => { log('render-process-gone', d.reason, d.exitCode); setTimeout(() => win.webContents.reload(), 1000); });
  app.on('child-process-gone', (e, d) => log('child-process-gone', d.type, d.reason, d.exitCode));
  win.webContents.on('did-fail-load', (e, code, desc, url, isMain) => {
    log('did-fail-load', code, desc, url);
    if (!isMain || fellBack || !cfg.url) return;
    fellBack = true;
    console.warn('线上页面打不开，改用本地文件：', desc);
    win.loadURL(LOCAL);
  });

  // F11 切全屏，F5 刷新，F12 开发者工具（调试用）
  win.webContents.on('before-input-event', (e, input) => {
    if (input.type !== 'keyDown') return;
    if (input.key === 'F11') { win.setFullScreen(!win.isFullScreen()); e.preventDefault(); }
    else if (input.key === 'F5') { win.webContents.reloadIgnoringCache(); e.preventDefault(); }
    else if (input.key === 'F12') { win.webContents.toggleDevTools(); e.preventDefault(); }
  });

  win.loadURL(cfg.url || LOCAL);
});

app.on('window-all-closed', () => app.quit());
