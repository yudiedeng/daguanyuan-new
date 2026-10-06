// 大观园桌面壳：给云渲染平台跑的 Windows 程序。
// 默认打开线上网页（config.json 的 url），网站一更新，云端下次启动就是新版，不用重新打包。
// 线上打不开（断网、域名被墙）时退回包里自带的 site/ 目录；加 --local 则直接用本地文件。
const { app, BrowserWindow, protocol, net } = require('electron');
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');

const RES = app.isPackaged ? process.resourcesPath : __dirname;
const SITE = app.isPackaged ? path.join(RES, 'site') : path.join(__dirname, '..');

function readConfig() {
  const cfg = { url: 'https://yudiedeng.github.io/daguanyuan/', fullscreen: true };
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

// 云端机器上没人点“允许”：声音自动播放、不限 GPU、窗口失焦也照常渲染
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-background-timer-throttling');

// 本地模式走 app:// 协议而不是 file://，这样 fetch('models/b/col.json') 和 GLTFLoader 都能正常读文件
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true, stream: true } }
]);

function serveLocal() {
  protocol.handle('app', req => {
    const rel = decodeURIComponent(new URL(req.url).pathname).replace(/^\/+/, '') || 'index.html';
    const file = path.normalize(path.join(SITE, rel));
    if (!file.startsWith(SITE)) return new Response('forbidden', { status: 403 });
    return net.fetch(pathToFileURL(file).toString());
  });
}

app.whenReady().then(() => {
  serveLocal();
  const cfg = readConfig();
  const win = new BrowserWindow({
    width: 1920, height: 1080,
    fullscreen: cfg.fullscreen, autoHideMenuBar: true, backgroundColor: '#000000',
    title: '大观园',
    webPreferences: { backgroundThrottling: false, contextIsolation: true, sandbox: true }
  });
  win.setMenu(null);

  const LOCAL = 'app://site/index.html';
  let fellBack = false;
  win.webContents.on('did-fail-load', (e, code, desc, url, isMain) => {
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
