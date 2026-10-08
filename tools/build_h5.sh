#!/usr/bin/env bash
# 打 H5 可玩 Demo 的 ZIP（比赛提交用）：只放网页运行要的文件，three.js / ez-tree 放进 vendor/ 不走 CDN。
# 用法：tools/build_h5.sh <node_modules 目录（含 three@0.170.0、@dgreenheck/ez-tree@1.1.0）> [输出 zip]
# 解压后要用 http 服务打开 index.html（ES 模块和模型加载不能走 file://），例如在解压目录里：python3 -m http.server 8000
set -euo pipefail
NM=$(realpath "${1:?node_modules 目录}"); OUT=$(realpath -m "${2:-daguanyuan-h5.zip}")
ROOT=$(cd "$(dirname "$0")/.." && pwd); TMP=$(mktemp -d); D=$TMP/daguanyuan
mkdir -p "$D/vendor/three/build" "$D/vendor/three/examples" "$D/vendor/ez-tree"
cp "$ROOT"/index.html "$ROOT"/game.js "$ROOT"/i18n.js "$D"/
cp -r "$ROOT"/models "$ROOT"/tex "$D"/
cp "$NM"/three/build/three.module.js "$D"/vendor/three/build/
cp -r "$NM"/three/examples/jsm "$D"/vendor/three/examples/
cp "$NM"/@dgreenheck/ez-tree/build/ez-tree.es.js "$D"/vendor/ez-tree/
sed -i -e 's#https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js#./vendor/three/build/three.module.js#' \
       -e 's#https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/#./vendor/three/examples/jsm/#' \
       -e 's#https://cdn.jsdelivr.net/npm/@dgreenheck/ez-tree@1.1.0/build/ez-tree.es.js#./vendor/ez-tree/ez-tree.es.js#' "$D"/index.html
! grep -q 'cdn.jsdelivr' "$D"/index.html
cp "$ROOT"/tools/h5_README.txt "$D"/游戏操作说明.txt
cp "$ROOT"/tools/h5_ABOUT.txt "$D"/作品说明（创作初衷与AI使用说明）.txt
(cd "$TMP" && zip -qr -9 "$OUT" daguanyuan)
rm -rf "$TMP"; ls -l "$OUT"
