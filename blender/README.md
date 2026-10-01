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
