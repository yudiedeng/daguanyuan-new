#!/usr/bin/env bash
# 打 H5 可玩 Demo 的 ZIP（比赛提交用）：只放网页运行要的文件。
# three.js 用仓库里的 vendor/（three@0.170.0 打过 DGY-* 补丁：阴影缓存、遮挡剔除、分批上传等，性能版离不开它，不能换回 npm/CDN 原版）。
# 用法：tools/build_h5.sh [输出 zip]
# 解压后用 http 服务打开（ES 模块和模型加载不能走 file://）：在解压目录里 node serve.cjs，或双击「启动游戏.cmd」
set -euo pipefail
OUT=$(realpath -m "${1:-daguanyuan-h5.zip}")
ROOT=$(cd "$(dirname "$0")/.." && pwd); TMP=$(mktemp -d); D=$TMP/daguanyuan
mkdir -p "$D"
cp "$ROOT"/index.html "$ROOT"/*.js "$ROOT"/*.mjs "$D"/
cp -r "$ROOT"/models "$ROOT"/tex "$ROOT"/fonts "$ROOT"/generated "$ROOT"/vendor "$D"/
! grep -q 'cdn.jsdelivr' "$D"/index.html
cp "$ROOT"/tools/h5_README.txt "$D"/游戏操作说明.txt
cp "$ROOT"/tools/h5_ABOUT.txt "$D"/作品说明（创作初衷与AI使用说明）.txt
cp "$ROOT"/tools/h5_serve.cjs "$TMP"/serve.cjs
cp "$ROOT"/tools/h5_start.cmd "$TMP"/启动游戏.cmd
cp "$ROOT"/tools/h5_USAGE.txt "$TMP"/使用说明.txt
cp "$ROOT"/tools/h5_RELEASE_NOTES.txt "$TMP"/版本说明.txt
(cd "$TMP" && zip -qr -9 "$OUT" daguanyuan serve.cjs 启动游戏.cmd 使用说明.txt 版本说明.txt)
rm -rf "$TMP"; ls -l "$OUT"
