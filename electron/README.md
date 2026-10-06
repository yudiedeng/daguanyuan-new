# 桌面版（云渲染托管用）

把网页包成 Windows 程序，上传到 3DCAT、平行云 LarkXR 这类云渲染平台，访客点链接就能用云端显卡流畅地看。

## 更新方式

程序默认打开线上网页（`config.json` 里的 `url`，即 GitHub Pages）。
**网站照常推送更新即可，不用重新打包**：云端程序下次启动就会加载新版（GitHub Pages 缓存约 10 分钟）。
只有改了这个壳本身（`main.js`）才需要重新打包。

包里也带了一份网站文件（`resources/site/`）作为后备：线上打不开时自动改用它。

## 打包（在 Windows 电脑上）

```bash
cd electron
npm i
npm start            # 先本机试一下（打开线上网页）
npm run start:local  # 试一下本地文件版
npm run dist         # 生成 dist/daguanyuan-1.0.0-win.zip，上传这个
```

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
