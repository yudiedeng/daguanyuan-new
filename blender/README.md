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

- `scripts/xiaoxiang/`：潇湘馆逐步建模脚本与《木构搭建依据与修订清单》。
- `scripts/export/`：潇湘馆导出 / 减面脚本。
- 注意：仓库里 `models/b/xiaoxiang.wasm` 的窗格是烘焙贴图版，若在 Blender 里改潇湘馆，导出时要重新做窗格烘焙。
