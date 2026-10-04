# Blender 源文件

网页里 `models/b/<id>.wasm`（meshopt 压缩的 GLB）对应的源文件。

| 文件 | 院落 | 网页模型 |
|---|---|---|
| qinfang.blend | 沁芳亭 | models/b/qinfang.wasm |
| xiaoxiang.blend | 潇湘馆（原 xiaoxiang_yuanzhu.blend，Blender 5.2 保存） | models/b/xiaoxiang.wasm |
| daoxiang.blend | 稻香村 | models/b/daoxiang.wasm |
| hengwu.blend | 蘅芜苑 | models/b/hengwu.wasm |
| daguan.blend | 正殿·大观楼 | models/b/daguan.wasm |
| yihong.blend | 怡红院 | models/b/yihong.wasm |
| ouxiang.blend | 藕香榭 | models/b/ouxiang.wasm |
| longcui.blend | 栊翠庵 | models/b/longcui.wasm |
| cuizhang.blend | 翠嶂（园门内假山、石洞） | models/b/cuizhang.wasm |
| luxue.blend | 芦雪广（东岸桥头，借稻香村茅屋） | models/b/luxue.wasm |
| aojing.blend | 凹晶馆（湖西岸，借怡红院东厢房） | models/b/aojing.wasm |
| tubi.blend | 凸碧山庄（湖西小山顶，借栊翠庵佛殿） | models/b/tubi.wasm |

- `scripts/xiaoxiang/`：潇湘馆逐步建模脚本与《木构搭建依据与修订清单》。
- `scripts/export/`：潇湘馆导出 / 减面脚本。
- 注意：仓库里 `models/b/xiaoxiang.wasm` 的窗格是烘焙贴图版，若在 Blender 里改潇湘馆，导出时要重新做窗格烘焙。

## 导出到网页

```bash
pip install bpy                       # Blender 5.0 的 Python 模块
(cd blender/scripts/web && npm i)
python3 blender/scripts/web/export_glb.py blender/<id>.blend /tmp/<id>.glb
node blender/scripts/web/pack_glb.mjs /tmp/<id>.glb models/b/<id>.wasm models/b/<id>.wasm   # 第三个参数：沿用旧模型的节点命名
```

- `scripts/cuizhang/build_cuizhang.py`：从零生成翠嶂，同时写 `models/b/col.json` 的 `cuizhang` 碰撞框与 `cuizhang_trees`。
- `scripts/sites/yihong_garden.py`：怡红院的花木，程序化建模，各存 `yh_*.blend`：西府海棠 yh_haitang（伞形树冠、细梗垂花、朱砂花苞）、碧桃 yh_bitao、芭蕉丛 yh_bajiao、月季花坛 yh_rosebed、花径 yh_huajing、单丛月季 yh_rosebush、常绿灌木 yh_shrub。花瓣叶片贴 `yihong_atlas.py` 画的贴图集，树皮、芭蕉用 `tex/` 里的贴图。
  ```bash
  python3 blender/scripts/sites/yihong_garden.py /tmp/yh          # YH_ONLY=haitang,bitao 只重建其中几种
  node blender/scripts/web/pack_prop.mjs /tmp/yh/yh_haitang.glb models/p/yh_haitang.glb 85000 1024   # 其余 200000 1024（不减面）
  node blender/scripts/web/alpha_mask.mjs models/p/yh_*.glb       # 花叶、芭蕉叶改 alphaMode MASK
  ```
  网页里在 `PROPS.yihong` 按地形摆放（院门外花园、院内花池与花坛）。
- 怡红院其余道具（仙鹤、鸟笼、竹篱花障月洞门、牡丹）由 Tripo 生成：`python3 tools/tripo_text.py tools/props.json <out> <名…>`，再 `pack_prop.mjs`；牡丹叶子发黄，再跑 `node blender/scripts/web/leaf_dark.mjs models/p/huacong_mudan.glb` 压暗。
- `scripts/sites/build_sites.py`：生成芦雪广、凹晶馆、凸碧山庄（从现有 .blend 借构件），同时写各自的碰撞框。
- 坐标约定：网页 x → Blender X，网页 z → Blender −Y，网页 y → Blender Z；新景点正面一律朝网页 +z。

## 室内（blender/scripts/interiors/）

四处室内：怡红院、潇湘馆、蘅芜苑、稻香村。陈设按原著与 `references/cs971 …/` 里的室内格局图布置，各脚本开头注明依据的回目与图。

| 脚本 | 源文件 | 网页模型 | 外壳改动（tools/glb_cut.mjs） |
|---|---|---|---|
| build_yihong.py | yihong_in.blend | models/b/yihong_in.wasm | 抱厦明间四扇槅扇；正房前檐五块木板隔断 |
| build_xiaoxiang.py | xiaoxiang_in.blend | models/b/xiaoxiang_in.wasm | 明间两扇半掩隔扇（另删 tex/xx_win.json 中两张门格心贴片）；xiaoxiang_ct 里湘帘明间下半幅 |
| build_hengwu.py | hengwu_in.blend | models/b/hengwu_in.wasm | 清厦前檐明间四扇隔扇 |
| build_daoxiang.py | daoxiang_in.blend | models/b/daoxiang_in.wasm | 正房明间柴门 |

```bash
python3 blender/scripts/interiors/build_yihong.py      # 生成陈设 → 存 .blend → 导出 .wasm → 写 col.json 的 yihong_in
node tools/glb_cut.mjs models/b/yihong.wasm models/b/yihong.wasm '[[x0,y0,z0,x1,y1,z1,"材质正则"],…]'
```

- `kit.py`：构件库（桌案、椅凳、罗汉床、架子床、多宝格、书架、落地罩/圆光罩/八方罩、碧纱橱、屏风、穿衣镜、宫灯、天花、器物）。
- 碰撞：脚本会从 `col.json[<id>]` 删掉原来的实心房屋块，把墙体、隔断、家具写进 `col.json[<id>_in]`。
- 网页：`*_in` 模型在园子载完后懒加载；`美人画`、`墨竹图`、`横披`、`对联上/下`、`棋盘`、`碧绿凿花砖` 等材质在网页里贴画布纹理，`穿衣镜` 换成实时反射；进屋时有两盏暖色补光跟着走。
- glb_cut 的剪切盒是 Blender 坐标；每处用的盒子见各 build 脚本开头说明。

本次实际执行的剪切（从各自原始模型出发；可重复执行）：

```bash
node tools/glb_cut.mjs models/b/yihong.wasm models/b/yihong.wasm '[[-1.62,4.75,0.93,1.62,5.0,3.2,"朱漆|窗纸|描金"],[-7.82,7.9,0.85,-5.18,8.1,5.21,"朱漆"],[-4.82,7.9,0.85,-1.98,8.1,5.21,"朱漆"],[-1.62,7.9,0.85,1.62,8.1,5.21,"朱漆"],[1.98,7.9,0.85,4.82,8.1,5.21,"朱漆"],[5.18,7.9,0.85,7.82,8.1,5.21,"朱漆"]]'
node tools/glb_cut.mjs models/b/xiaoxiang.wasm models/b/xiaoxiang.wasm '[[-0.73,-1.97,0.55,0.73,-1.36,3.31,"深绿漆|窗纸"],[-0.69,-1.97,0.62,0.69,-1.36,3.31,"暗褐旧木|深绿漆|窗纸|铜|门窗深褐木|门环"]]'
node tools/glb_cut.mjs models/b/xiaoxiang_ct.wasm models/b/xiaoxiang_ct.wasm '[[-1.2,-3.85,0.1,1.2,-3.6,2.5,"湘"]]'
node tools/glb_cut.mjs models/b/hengwu.wasm models/b/hengwu.wasm '[[-1.62,4.3,0.78,1.62,4.75,3.45,"绿漆|窗纸|描金"]]'
node tools/glb_cut.mjs models/b/daoxiang.wasm models/b/daoxiang.wasm '[[-4.74,12.1,0.4,-3.26,12.5,2.58,"本色木|描金"]]'
```
