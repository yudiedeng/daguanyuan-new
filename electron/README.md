# 桌面版（云渲染托管用）

把网页包成 Windows 程序，上传到 3DCAT、平行云 LarkXR 这类云渲染平台，访客点链接就能用云端显卡流畅地看。

## 更新方式

程序默认打开线上网页（`config.json` 里的 `url`，即 GitHub Pages）。
**网站照常推送更新即可，不用重新打包**：云端程序下次启动就会加载新版（GitHub Pages 缓存约 10 分钟）。
只有改了这个壳本身（`main.js`）才需要重新打包。

包里也带了一份网站文件（`resources/site/`）作为后备：线上打不开时自动改用它。

## 打包

**不用 Windows 电脑**：GitHub 会在它的 Windows 机器上自动打包（`.github/workflows/electron.yml`）。
改了 `electron/` 推送后自动跑；也可以在仓库 Actions → 打包桌面版 → Run workflow 手动跑。
跑完（约 5–10 分钟）在那次运行页面底部 Artifacts 下载 `daguanyuan-win.zip`，**不用解压，直接上传**（zip 最外层就是 `daguanyuan.exe`）。

**在 Mac 上先试效果**（打开的是 Mac 版窗口，只用来看效果）：

```bash
cd electron
npm i
npm start            # 打开线上网页
npm run start:local  # 打开本地文件版
```

在 Windows 电脑上也可以直接 `npm run dist`，生成 `dist/daguanyuan-1.0.0-win.zip`。

## 启动参数

| 参数 | 作用 |
|---|---|
| `--url=https://…` | 打开别的地址（比如国内镜像） |
| `--local` | 只用包里的本地文件 |
| `--windowed` | 不全屏 |

也可以在 `daguanyuan.exe` 旁边放一个 `config.json` 覆盖地址，不用重新打包。

运行中：F11 切全屏，F5 强制刷新，F12 开发者工具。

## 注意

- three.js 从 `cdn.jsdelivr.net` 加载。云服务器在国内的话，先在服务器上用浏览器确认这个地址打得开。
