# 大观园书法补充字体

游戏通过 `fonts.css` 的 `DGY Calligraphy` 组合字族使用原字体与补充字体。

- 原 `tex/msz.woff2` 保留不变。
- 从 [Ma Shan Zheng 官方源文件](https://github.com/google/fonts/tree/main/ofl/mashanzheng) 恢复 881 个被原裁剪文件遗漏的字形。
- 使用内置 OpenAI imagegen 分别生成嶒、槅、湲、罽、醾、鹴、齁，再将透明 PNG 的笔画边界转为 TrueType 轮廓。生成参考仅用于结构、风格核对；没有复制系统字体的轮廓。
- 补充字体内部名称为 DGY Calligraphy Supplement；原字形授权和版权见同目录 `OFL-MaShanZheng.txt`。
- 当前覆盖 `index.html`、`game.js`、`i18n.js` 中审计到的 1521 个汉字。未来添加新文案后需重新审计，并非完整 CJK 字库。

`manifest.json` 保存来源、Unicode、原图路径及哈希。项目根目录 `perf/calligraphy-source/generation.json` 保存每个字的完整提示词及参考图路径；`perf/calligraphy-source/generated/` 保留原始透明 PNG。

开发维护：使用带 fontTools、Brotli、OpenCV、Pillow 的 Python 运行 `perf/prepare-calligraphy.py` 和 `perf/build-calligraphy.py`；运行 `node perf/check-calligraphy.mjs` 验证集成与慢加载重绘。`profile-calligraphy.html` 可直接检查浏览器中的小字、诗句和 Canvas 匾额效果。
