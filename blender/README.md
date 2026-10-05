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

## “Blender 原样”导出（bake_court.py，目前用于怡红院、蘅芜苑）

`.blend` 的材质 = 照片贴图（PolyHaven，盒式投影）× 底色 ×“做旧”（缝隙 AO、竖向雨痕、污渍、屋面青苔，均为节点）。普通导出（export_glb）不带贴图，网页再按材质名用自己的配色，所以比 Blender 里平、亮。
`blender/scripts/web/bake_court.py <院.blend> <标签> <out.glb> [采样]`：
- 做旧层用 Cycles 烘进顶点色（每种材质临时去掉照片和底色、接自发光，bake EMIT → 顶点色）；纯程序材质整块底色一起烘；
- 照片贴图转灰度存 `tex/bk_<名>_g.jpg`、法线 `_n.jpg`，材质表写 `tex/bk_<标签>.json`（底色、投影尺度、粗糙度、法线强度）；
- 材质改名 `M_<标签>B_<原名>`；`pack_glb.mjs` 对这类材质保留顶点色；网页 `bmat` 按 json 建材质：底色 × 灰度照片（世界坐标三向投影）× 顶点色，再乘 `BAKED_GAIN`（网页太阳比 Blender 强，整体压暗）。
新的院子要用：烘焙、在 `loadBuildings` 里把标签加进 `for(const t of['yh'])`。

## 导出到网页

```bash
pip install bpy                       # Blender 5.0 的 Python 模块
(cd blender/scripts/web && npm i)
python3 blender/scripts/web/export_glb.py blender/<id>.blend /tmp/<id>.glb
node blender/scripts/web/pack_glb.mjs /tmp/<id>.glb models/b/<id>.wasm models/b/<id>.wasm   # 第三个参数：沿用旧模型的节点命名
```

- `scripts/cuizhang/build_cuizhang.py`：从零生成翠嶂，同时写 `models/b/col.json` 的 `cuizhang` 碰撞框与 `cuizhang_trees`。
- `scripts/sites/yihong_garden.py`：怡红院的花木，程序化建模，各存 `yh_*.blend`：西府海棠 yh_haitang（伞形树冠、细梗垂花、朱砂花苞）、碧桃 yh_bitao、芭蕉丛 yh_bajiao（`bajiao_textures.py` 画鲜叶、老叶、枯叶、假茎贴图：侧脉、沿脉撕裂、焦边；叶两半下垂、叶缘起伏，茎上挂枯叶、茎基枯鞘）、月季花坛 yh_rosebed、院中大花床 yh_bigbed、花径 yh_huajing、单丛月季 yh_rosebush、常绿灌木 yh_shrub、青花盆栽 yh_pot、竹篱花障月洞门 yh_huazhang、粉墙漏窗窗心 yh_lc_*（海棠、冰裂、套方、鱼鳞；原模型窗心用 glb_cut 剪掉了材质 屋脊灰 在各窗洞里的部分）。贴图集每格四周留空边并用本格颜色填满，远处 mip 不串色。花瓣叶片贴 `yihong_atlas.py` 画的贴图集，树皮、芭蕉用 `tex/` 里的贴图。
  ```bash
  python3 blender/scripts/sites/yihong_garden.py /tmp/yh          # YH_ONLY=haitang,bitao 只重建其中几种
  node blender/scripts/web/pack_prop.mjs /tmp/yh/yh_haitang.glb models/p/yh_haitang.glb 85000 1024   # 其余 200000 1024（不减面）
  node blender/scripts/web/alpha_mask.mjs models/p/yh_*.glb       # 花叶、芭蕉叶改 alphaMode MASK
  ```
  网页里在 `PROPS.yihong` 按地形摆放（院门外花园、院内花池与花坛）。
- `pack_prop.mjs`：带透明的贴图不缩放、存无损 webp（exact），否则透明处颜色被抹黑、远处叶丛发黑发红。
- 怡红院外檐精修 `scripts/sites/yihong_refine.py`（就地改 yihong.blend：槅扇单独 M_槅扇、屋面 M_YH_灰瓦、包袱贴苏式彩画 M_彩画_baofu、柱头雀替 M_雕花_huaya/huayar、倒挂楣子 M_雕花_meizi）。
  然后烘焙、整座重导（原来线上那版是简化过的：屋面平直、没有瓦垄瓦当），再按上面的清单重开门洞、剪窗心：
  ```bash
  python3 blender/scripts/sites/yihong_refine.py
  python3 blender/scripts/web/bake_court.py blender/yihong.blend yh /tmp/yh_baked.glb 10      # 约 7 分钟（CPU）
  node blender/scripts/web/pack_glb.mjs /tmp/yh_baked.glb models/b/yihong.wasm models/b/yihong.wasm
  ```
- `tools/glb_patch.mjs`：只把 .blend 里改过的对象补进线上模型（不整座重导时用）。
- 怡红院其余道具（仙鹤、鸟笼、牡丹、描金宫灯、青花龙纹鱼缸）由 Tripo 生成：`python3 tools/tripo_text.py tools/props.json <out> <名…>`，再 `pack_prop.mjs`；牡丹叶子发黄，再跑 `node blender/scripts/web/leaf_dark.mjs models/p/huacong_mudan.glb` 压暗。
- `scripts/sites/build_sites.py`：生成芦雪广、凹晶馆、凸碧山庄（从现有 .blend 借构件），同时写各自的碰撞框。
- 坐标约定：网页 x → Blender X，网页 z → Blender −Y，网页 y → Blender Z；新景点正面一律朝网页 +z。

## 大观楼改样（blender/scripts/sites/）

正殿与大观楼原来摞成一座两层楼。改成：正殿（顾恩思义殿）前移 16 m、改重檐；大观楼立在殿后 4.5 m 高的须弥座白石台上，三层逐层收分、金宝顶（顶脊约 33 m），全组最高；缀锦阁、含芳阁加成三层；
复道接大观楼首层两山；前面两层白石台基、汉白玉甬路与栏杆、两方水池；屋面全改灰瓦。玉石牌坊、石狮、石灯座是 Tripo 件
（`shishi.glb`、`shideng.glb`，提示词在 `tools/props.json`），网页 `PROPS.daguan` 放置。
牌坊 `models/p/paifang.glb` 由 `paifang_build.py` 搭白石骨架、挂 Tripo 精雕件（盘龙柱 pf_zhu、镂空螭纹花板 pf_hua、明间脊上二龙戏珠 pf_jilong、次间脊上卷草 pf_juancao；脊饰自带的底座在脚本里切掉）：
`python3 blender/scripts/sites/paifang_build.py <tripo 原始 glb 目录> /tmp/paifang.glb && node blender/scripts/web/pack_prop.mjs /tmp/paifang.glb models/p/paifang.glb 150000 1024`

```bash
python3 blender/scripts/sites/daguan_rebuild.py                      # 只能跑一次（在 daguan_doors.py 之后）
flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_cols.py  # 外壳碰撞，可重复跑
flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_in_shift.py   # 殿内陈设随正殿前移，只能跑一次
python3 blender/scripts/web/export_glb.py blender/daguan.blend /tmp/daguan.glb
node blender/scripts/web/pack_glb.mjs /tmp/daguan.glb models/b/daguan.wasm models/b/daguan.wasm
```

- `build_daguan.py`（室内）仍按旧坐标生成；重跑它之后要再跑一次 `daguan_in_shift.py`（先删 col.json 里的 `daguan_in_shift` 标记）。
## 栊翠庵外观细部（blender/scripts/sites/longcui_detail.py）

原模型佛殿檐檩直接压在额枋上、檐下一片平板；各屋正脊是两块方条，吻兽、戗脊翘头是小方块垒的“像素”弯钩。改为：
佛殿屋面抬高 0.66 m，让出一圈五踩单翘单昂斗栱（柱头科、平身科、角科，青绿相间，拱眼壁朱红）；
各屋正脊重做（当沟、压当条、混砖、盖脊筒瓦）+ 正吻（吞脊龙头、卷尾、剑把、背兽）；佛殿垂脊、戗脊（随屋面、末端起翘）、
垂兽戗兽、仙人走兽、套兽、风铎、莲座宝瓶宝顶、山花绶带、博缝梅花钉、悬鱼；佛殿、禅堂、耳房檐柱加雀替；
顺手封住歇山山花与屋面之间原有的一道缝（殿里抬头能看见天）。新件在 `models/b/longcui_xi.wasm`（网页 `{id:'longcui_xi'}`，与 longcui 同位）。

```bash
python3 blender/scripts/sites/longcui_detail.py        # 改 longcui.blend（抬屋面只做一次）、导出 /tmp/longcui_xi.glb
node blender/scripts/web/pack_glb.mjs /tmp/longcui_xi.glb models/b/longcui_xi.wasm
# 外壳 wasm 只能从原始模型跑一次：
node tools/glb_lift.mjs models/b/longcui.wasm models/b/longcui.wasm "$(python3 blender/scripts/sites/longcui_detail.py --liftspec)"
node tools/glb_cut.mjs  models/b/longcui.wasm models/b/longcui.wasm "$(python3 blender/scripts/sites/longcui_detail.py --cutspec)"
```

- 凸碧山庄（build_sites.py）从 longcui.blend 借佛殿；重跑它会借到抬高后的屋面，须连斗栱一起借。

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
| build_hengwu.py | hengwu_in.blend | models/b/hengwu_in.wasm | 清厦前檐明间四扇隔扇；室内雪洞白墙、素作井口天花、前窗内侧方格棂；外廊倒挂楣子+花牙子、鼓镜柱础 |
| build_daoxiang.py | daoxiang_in.blend | models/b/daoxiang_in.wasm | 正房明间柴门 |

```bash
python3 blender/scripts/interiors/build_yihong.py      # 生成陈设 → 存 .blend → 导出 .wasm → 写 col.json 的 yihong_in
node tools/glb_cut.mjs models/b/yihong.wasm models/b/yihong.wasm '[[x0,y0,z0,x1,y1,z1,"材质正则"],…]'
```

- 怡红院透雕：`diao_textures.py` 画 `tex/diao_*.png`（流云百蝠嵌玉、缠枝花卉五彩、岁寒三友、回纹、冰梅，512² 可平铺、透明即镂空；另有多宝格柜门 guimen、角花 huaya/huayar、满墙槽子板 caozi）。`duobaoge(carve=True)` 贴金边、角花、团寿柜门；`niche_wall()` 立满墙槽子板并在槽里摆琴、剑、悬瓶、桌屏等。`kit.py` 里 `carved_panel()` 和 `luodizhao(..., fill='雕花_*')` 用这些材质，`雕花_*` 网格按面朝向自动展 UV（0.5 m 一格），`pack_glb.mjs` 只为 `雕花_*` 保留 UV，网页 `bmat` 按材质名贴图、alphaTest 裁空。
  ```bash
  python3 blender/scripts/interiors/diao_textures.py tex
  python3 blender/scripts/interiors/build_yihong.py
  ```
- `kit.py`：构件库（桌案、椅凳、罗汉床、架子床、多宝格、书架、落地罩/圆光罩/八方罩、碧纱橱、屏风、穿衣镜、宫灯、天花、器物）。
- 碰撞：脚本会从 `col.json[<id>]` 删掉原来的实心房屋块，把墙体、隔断、家具写进 `col.json[<id>_in]`。
- 网页：`*_in` 模型在园子载完后懒加载；`美人画`、`墨竹图`、`横披`、`对联上/下`、`棋盘`、`碧绿凿花砖` 等材质在网页里贴画布纹理，`穿衣镜` 换成实时反射；进屋时有两盏暖色补光跟着走。
- glb_cut 的剪切盒是 Blender 坐标；每处用的盒子见各 build 脚本开头说明。

本次实际执行的剪切（从各自原始模型出发；可重复执行）：

```bash
node tools/glb_cut.mjs models/b/yihong.wasm models/b/yihong.wasm '[[-1.62,4.75,0.93,1.62,5.0,3.2,"朱漆|槅扇|窗纸|描金"],[-7.82,7.9,0.85,-5.18,8.1,5.21,"朱漆|槅扇"],[-4.82,7.9,0.85,-1.98,8.1,5.21,"朱漆|槅扇"],[-1.62,7.9,0.85,1.62,8.1,5.21,"朱漆|槅扇"],[1.98,7.9,0.85,4.82,8.1,5.21,"朱漆|槅扇"],[5.18,7.9,0.85,7.82,8.1,5.21,"朱漆|槅扇"]]'
node tools/glb_cut.mjs models/b/xiaoxiang.wasm models/b/xiaoxiang.wasm '[[-0.73,-1.97,0.55,0.73,-1.36,3.31,"深绿漆|窗纸"],[-0.69,-1.97,0.62,0.69,-1.36,3.31,"暗褐旧木|深绿漆|窗纸|铜|门窗深褐木|门环"]]'
node tools/glb_cut.mjs models/b/xiaoxiang_ct.wasm models/b/xiaoxiang_ct.wasm '[[-1.2,-3.85,0.1,1.2,-3.6,2.5,"湘"]]'
# 蘅芜苑按 .blend 原样重导（玲珑山石原来只剩 13% 的面）：
#   python3 blender/scripts/web/bake_court.py blender/hengwu.blend hw /tmp/hw.glb 10
#   node blender/scripts/web/pack_glb.mjs /tmp/hw.glb models/b/hengwu.wasm models/b/hengwu.wasm - 0.0004
# 然后依次执行下面五步
node tools/glb_cut.mjs models/b/hengwu.wasm models/b/hengwu.wasm '[[-1.62,4.3,0.78,1.62,4.75,3.45,"绿漆|窗纸|描金"]]'
node tools/glb_cut.mjs models/b/hengwu.wasm models/b/hengwu.wasm '[[-1.62,4.3,0.78,1.62,4.75,3.45,"枋青"]]'   # 隔扇下半截的裙板框（上一行漏剪，门洞地上留着四个蓝框）
node blender/scripts/web/fix_hw_drum.mjs   # 院门右边门枕石上的石鼓建模时偏外 0.18 m，挪回与左边对称
node tools/glb_cut.mjs models/b/hengwu.wasm models/b/hengwu.wasm '[[-7.93,4.72,0.77,7.93,10.3,1.75,"青石|水磨砖"]]'   # 清厦室内露出的外壳槛墙内侧（青砖），室内另贴白灰墙
node tools/glb_cut.mjs models/b/hengwu.wasm models/b/hengwu.wasm '[[-0.95,-16,3.3,0.95,-12.5,4.1,"灰瓦"]]'   # 墙帽灰瓦穿过院门楼，在匾上露出一排圆瓦当：剪掉两门垛之间这一截
node tools/glb_cut.mjs models/b/daoxiang.wasm models/b/daoxiang.wasm '[[-4.74,12.1,0.4,-3.26,12.5,2.58,"本色木|描金"]]'
# 稻香村正房明间：门板剪掉后残留在门洞里的横带也剪掉，另由 daoxiang_men 补两扇敞开的板门（scripts/sites/daoxiang_door.py）
node tools/glb_cut.mjs models/b/daoxiang.wasm models/b/daoxiang.wasm '[[-4.62,12.05,0.42,-3.38,12.55,2.52,"旧木|本色木|描金"]]'
# 稻香村菜畦：剪掉旧的光滑垄条和凸起边框（连同其下地面），由 daoxiang_tian 接替，见下文「菜畦」
node tools/glb_cut.mjs models/b/daoxiang.wasm models/b/daoxiang.wasm '[[16.26,-4.04,-0.5,26.24,9.64,0.6,"田土|夯土地"],[12.26,-22.54,-0.5,26.24,-4.96,0.6,"田土|夯土地"],[-1.44,-22.54,-0.5,11.74,-4.96,0.6,"田土|夯土地"],[-26.24,-22.54,-0.5,-7.96,-8.76,0.6,"田土|夯土地"]]'
# 潇湘馆室内：方块家具换成 Tripo 道具（index.html PROPS.xiaoxiang_in），剪掉原来的：书案、圈椅、书架、琴桌、明间条案、花几西、花几东、棋桌、官帽椅西、官帽椅东、瓷墩西、瓷墩东、床、榻、梳妆台、绣墩
node tools/glb_cut.mjs models/b/xiaoxiang_in.wasm models/b/xiaoxiang_in.wasm '[[-3.56,-0.45,0.48,-2.94,1.29,1.3,"花梨"],[-2.95,0.08,0.48,-2.15,0.76,1.6,"湘妃竹|青布"],[-3.67,2.07,0.48,-1.5,2.53,3.42,"湘妃竹|书函|书页"],[-3.22,-1.62,0.48,-1.88,-1.12,1.0,"黑漆|描金|白布|瓷白"],[-1.13,1.95,0.48,1.13,2.5,1.35,"花梨"],[-1.39,1.98,0.48,-0.98,2.42,1.9,"湘妃竹|青花|叶绿"],[0.98,1.98,0.48,1.39,2.42,1.9,"湘妃竹|青花|叶绿"],[-0.45,0.6,0.48,0.45,1.5,1.33,"花梨"],[-1.1,0.72,0.48,-0.47,1.38,1.6,"湘妃竹|青布"],[0.47,0.72,0.48,1.1,1.38,1.6,"湘妃竹|青布"],[-1.16,-0.82,0.48,-0.74,-0.38,0.95,"瓷白|青花"],[0.74,-0.82,0.48,1.16,-0.38,0.95,"瓷白|青花"],[2.05,0.12,0.48,3.68,2.4,2.95,"花梨|青纱|素绸|青布|锦缎|描金|紫檀"],[1.92,-1.72,0.48,3.62,-0.95,1.5,"湘妃竹|青布|锦缎"],[3.05,-0.8,0.48,3.68,0.1,1.8,"花梨|紫檀|镜面|粉彩"],[2.55,-0.55,0.48,2.95,-0.15,0.95,"锦缎|描金"]]'
```

## 蘅芜苑的藤萝异草（scripts/web/hw_plants.py）

网页里蘅芜苑的藤蔓、异草和花溆洞口的垂藤都是 Blender 用脚本建的（叶片是带弧度的三维面片、茎是细管、红果和小金花是小球，颜色写在顶点色里）：

```bash
node blender/scripts/web/hw_vines.mjs        # 从院落模型算挂点、贴石垂藤的路径、玲珑石摆放 → models/b/hw_vines.json
python3 blender/scripts/web/hw_plants.py     # 建模 → models/b/hw_vines.wasm（院中藤蔓，按位置烘好）、models/p/hw_plants.glb（单株异草、垂藤）
```

## 树（blender/scripts/trees/）

`build_trees.py`：程序化生成稻香村青篱边的桑、榆、木槿、柘（第十七回「桑、榆、槿、柘，各色树稚新条，随其曲折，编就两溜青篱」），与 `models/t` 里原有精品树同一格式。

```bash
python3 blender/scripts/trees/build_trees.py [sang yu mujin zhe] [--preview]
```

- 叶片卡：在 Blender 里按各树种叶形摆一段带叶小枝（桑叶卵形心形基、粗齿；榆是一簇簇榆钱；槿叶三浅裂；柘全缘、枝上有刺），Cycles 俯视渲染 → `tex/leaf_<sp>_c.png` / `_a.png`。
- 树模型：递归分枝的树皮管 + 叶卡四边形 → `models/t/<sp>_1.wasm`（`<sp>_bark`、`<sp>_leaf` 两个节点）。
- 远景替身：侧视自发光渲染 → `tex/imp_<sp>1.png`，尺寸写进 `tex/imp.json`。
- 网页里是两类树：`sangyu`（v0 桑、v1 榆）和 `jinzhe`（v0 槿、v1 柘），栽在 `buildDaoxiang()` 里。

## 菜畦（blender/scripts/sites/daoxiang_fields.py）

第十七回「下面分畦列亩，佳蔬菜花，漫然无际」。原来四块菜畦像沙盘（一圈硬边框、光滑等宽的垄、两种插片作物），重做为：

```bash
python3 blender/scripts/sites/daoxiang_fields.py [--preview]
node blender/scripts/web/pack_glb.mjs /tmp/daoxiang_tian.glb models/b/daoxiang_tian.wasm
```

- 垄沟 → `models/b/daoxiang_tian.wasm`：畦面比原菜畦四边各收进 0.9 m，外围一道土埂（夯土地）；窄垄（垄距 1.1 m）宽窄高低、走向略有起伏，土块颗粒，垄头参差，边缘缓缓落进地面；与 daoxiang 同一原点。
- 作物 → `models/p/crops.glb`：三维小株、顶点色——油菜（开花，「菜花」）、青菜、葱，各两三种变体。
- 株位 → `tex/crops_daoxiang.json`：顺着弯曲的垄排，偶有缺苗；网页 `buildCrops()` 实例化，低画质退回插片。
- 原 `daoxiang.blend` 里的菜畦没动；网页模型里的旧菜畦用上面那条 glb_cut 剪掉。
