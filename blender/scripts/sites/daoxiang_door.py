"""稻香村正房明间：补回两扇向屋内敞开的旧木板门。

当初为了进屋，用 glb_cut 剪掉了门板（本色木|描金），门上的横带（旧木）却留在门洞中间，看着像坏门。
现在把残留的横带也剪掉（命令见 blender/README.md），这里另做两扇板门，敞开约 75°贴向屋内两侧。
→ models/b/daoxiang_men.wasm（与 daoxiang 同一原点，Blender 坐标）

用法：python3 blender/scripts/sites/daoxiang_door.py
      node blender/scripts/web/pack_glb.mjs /tmp/daoxiang_men.glb models/b/daoxiang_men.wasm
"""
import bpy, math
from mathutils import Matrix, Vector

X0, X1 = -4.72, -3.28      # 门洞左右（门轴）
Y = 12.3                   # 门所在墙面
Z0, Z1 = 0.45, 2.5         # 门扇上下
T = 0.05                   # 门板厚
OPEN = math.radians(75)    # 开启角

bpy.ops.wm.read_factory_settings(use_empty=True)
mats = {n: bpy.data.materials.new(n) for n in ('M_旧木', 'M_本色木')}


def box(name, mat, size, loc, parent):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object; o.name = name; o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mats[mat]); o.parent = parent
    return o


def leaf(name, hinge_x, sgn):
    """sgn=+1：门轴在左，门扇向 +x 伸；sgn=-1：门轴在右。"""
    piv = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(piv)
    piv.location = (hinge_x, Y, 0)
    W = (X1 - X0) / 2 - 0.01
    n = 5                                   # 竖板
    for i in range(n):
        w = W / n
        cx = sgn * (w * (i + 0.5))
        dz = 0.01 * ((i * 7) % 3)           # 板头参差一点
        box(f'{name}_板{i}', 'M_旧木', (w - 0.006, T, Z1 - Z0 - dz), (cx, 0, (Z0 + Z1 - dz) / 2), piv)
    for z in (Z0 + 0.25, (Z0 + Z1) / 2, Z1 - 0.25):   # 三道横带，在屋内一侧
        box(f'{name}_带', 'M_旧木', (W * 0.96, 0.035, 0.11), (sgn * W / 2, T / 2 + 0.017, z), piv)
    # 门环（铁）：外侧中缝附近
    bpy.ops.mesh.primitive_torus_add(major_radius=0.05, minor_radius=0.008, location=(sgn * (W - 0.08), -T / 2 - 0.01, 1.35),
                                     rotation=(math.pi / 2, 0, 0), major_segments=16, minor_segments=6)
    r = bpy.context.active_object; r.name = f'{name}_门环'; r.data.materials.append(mats['M_本色木']); r.parent = piv
    piv.rotation_euler = (0, 0, sgn * OPEN)  # 绕门轴转向屋内（+y）
    return piv


leaf('正房_门扇左', X0, +1)
leaf('正房_门扇右', X1, -1)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath='/tmp/daoxiang_men.glb', export_format='GLB', use_selection=True, export_apply=True,
                          export_yup=True, export_materials='EXPORT', export_image_format='NONE')
print('exported /tmp/daoxiang_men.glb')
