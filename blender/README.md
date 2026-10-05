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
- `scripts/sites/build_sites.py`：生成芦雪广、凹晶馆、凸碧山庄（从现有 .blend 借构件），同时写各自的碰撞框。
- 坐标约定：网页 x → Blender X，网页 z → Blender −Y，网页 y → Blender Z；新景点正面一律朝网页 +z。

## 大观楼改样（blender/scripts/sites/）

正殿与大观楼原来摞成一座两层楼。改成：正殿（顾恩思义殿）前移 16 m、改重檐；大观楼立在殿后 4.5 m 高的须弥座白石台上，三层、整座放大（顶脊约 35 m），全组最高；
复道接大观楼首层两山；前面两层白石台基、汉白玉甬路与栏杆、两方水池；屋面全改灰瓦。玉石牌坊、石狮、石灯座是 Tripo 件
（`models/p/paifang.glb`、`shishi.glb`、`shideng.glb`，提示词在 `tools/props.json`），网页 `PROPS.daguan` 放置。

```bash
python3 blender/scripts/sites/daguan_rebuild.py                      # 只能跑一次（在 daguan_doors.py 之后）
flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_cols.py  # 外壳碰撞，可重复跑
flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_in_shift.py   # 殿内陈设随正殿前移，只能跑一次
python3 blender/scripts/web/export_glb.py blender/daguan.blend /tmp/daguan.glb
node blender/scripts/web/pack_glb.mjs /tmp/daguan.glb models/b/daguan.wasm models/b/daguan.wasm
```

- `build_daguan.py`（室内）仍按旧坐标生成；重跑它之后要再跑一次 `daguan_in_shift.py`（先删 col.json 里的 `daguan_in_shift` 标记）。
## 竹（blender/scripts/flora/build_bamboo.py）

潇湘馆一带和园中竹丛用的三株竹（models/t/zhu_1–3.wasm）和叶簇贴图（tex/zhu_spray.png）：先在 Blender 里建两枝真实的竹叶簇、用 Cycles 俯拍成透明贴图，再建竹竿（节环、上细下粗）、互生下垂的枝，枝上挂十字交叉的叶簇片。网页按每竿高度等比缩放，低画质下退回程序生成的竹。

```bash
python3 blender/scripts/flora/build_bamboo.py --out /tmp/zhu
for n in 1 2 3; do node blender/scripts/web/pack_prop.mjs /tmp/zhu/zhu_$n.glb models/t/zhu_$n.wasm 99999 256; done
cp /tmp/zhu/zhu_spray.png tex/zhu_spray.png
```

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
# 潇湘馆室内：方块家具换成 Tripo 道具（index.html PROPS.xiaoxiang_in），剪掉原来的：书案、圈椅、书架、琴桌、明间条案、花几西、花几东、棋桌、官帽椅西、官帽椅东、瓷墩西、瓷墩东、床、榻、梳妆台、绣墩
node tools/glb_cut.mjs models/b/xiaoxiang_in.wasm models/b/xiaoxiang_in.wasm '[[-3.56,-0.45,0.48,-2.94,1.29,1.3,"花梨"],[-2.95,0.08,0.48,-2.15,0.76,1.6,"湘妃竹|青布"],[-3.67,2.07,0.48,-1.5,2.53,3.42,"湘妃竹|书函|书页"],[-3.22,-1.62,0.48,-1.88,-1.12,1.0,"黑漆|描金|白布|瓷白"],[-1.13,1.95,0.48,1.13,2.5,1.35,"花梨"],[-1.39,1.98,0.48,-0.98,2.42,1.9,"湘妃竹|青花|叶绿"],[0.98,1.98,0.48,1.39,2.42,1.9,"湘妃竹|青花|叶绿"],[-0.45,0.6,0.48,0.45,1.5,1.33,"花梨"],[-1.1,0.72,0.48,-0.47,1.38,1.6,"湘妃竹|青布"],[0.47,0.72,0.48,1.1,1.38,1.6,"湘妃竹|青布"],[-1.16,-0.82,0.48,-0.74,-0.38,0.95,"瓷白|青花"],[0.74,-0.82,0.48,1.16,-0.38,0.95,"瓷白|青花"],[2.05,0.12,0.48,3.68,2.4,2.95,"花梨|青纱|素绸|青布|锦缎|描金|紫檀"],[1.92,-1.72,0.48,3.62,-0.95,1.5,"湘妃竹|青布|锦缎"],[3.05,-0.8,0.48,3.68,0.1,1.8,"花梨|紫檀|镜面|粉彩"],[2.55,-0.55,0.48,2.95,-0.15,0.95,"锦缎|描金"]]'
```
