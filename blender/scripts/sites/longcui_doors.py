"""栊翠庵开门（在 blender/longcui.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/longcui_doors.py
  外壳 wasm：原 longcui.wasm 不是 pack_glb 流水线出的（三角形约少一半，2.6 MB）；用 export_glb+pack_glb 重导会涨到 4.4 MB，
  所以改为直接从线上模型剪掉同样的门扇面（可重复执行）：
    node tools/glb_cut.mjs models/b/longcui.wasm models/b/longcui.wasm "$(python3 blender/scripts/sites/longcui_doors.py --cutspec)"

  山门：原模型里拱洞已用 CUT_山门_± 布尔凿通、门扇已敞开，不动。
  1. 佛殿明间（x ±1.73，前檐 y≈4.8）：四扇隔扇门删去（下槛、中槛、横披窗保留）。
  2. 东禅堂明间（前金柱 x≈8.3，y −3.37…−0.23）：四扇隔扇门删去。第四十一回贾母在此吃茶。
  3. 东耳房当中两扇（y≈5.5，x 8.06…9.44）：删去。妙玉拉宝钗黛玉进耳房吃体己茶。
  敞开的门扇与陈设在 longcui_in（blender/scripts/interiors/build_longcui.py）。
  3b. 东禅堂前廊北头：廊子尽端原是台明边（高出夹道 0.45–0.6 m），补一级青石踏跺（实体在 longcui_in）通向东耳房前的夹道；
      碰撞网格在这里把台明边误判成墙，用 OVERRIDE 改成地坪/踏步格。
  4. 重新生成外壳碰撞框（体素式，同秋爽斋），写 col.json['longcui']。
     注意：index.html 里 DOOR/DROP/HOLLOW 对 longcui 的补丁是按旧碰撞框编号写的，换新碰撞框后要删掉。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import sys, json
FD = (-1.735, 4.68, 1.76, 1.735, 4.92, 4.43)        # 佛殿明间门扇 z 1.77–4.42；下槛 z 1.65–1.77 不在盒内
CT = (8.15, -3.375, 1.46, 8.45, -0.225, 3.65)       # 东禅堂明间门扇 z 1.47–3.64；横披窗与下槛保留
EF = (8.03, 5.40, 1.41, 9.47, 5.60, 3.28)           # 东耳房当中两扇
if '--cutspec' in sys.argv:                          # 给 tools/glb_cut.mjs 用的盒子（材质：朱漆/窗纸/描金/绿漆）
    print(json.dumps([list(b) + ['^M_(朱漆|窗纸|描金|绿漆)$'] for b in (FD, CT, EF)])); sys.exit(0)
import bpy, bmesh, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'longcui.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
for o in [o for o in O if o.name.startswith('开门_')]:      # 上次生成的东西先清掉（可重复执行）
    bpy.data.objects.remove(o, do_unlink=True)


def cut_faces(obj_name, box):
    """删除整个落在盒子里的面。返回删除面数（可重复执行：第二次为 0）"""
    o = O[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = [f for f in bm.faces if all(x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1 for w in (mw @ v.co for v in f.verts))]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free(); return len(dead)


def B(x, y, z):
    return Vector((x, -z, y))

ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花', 'ridge')

def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS) or o.users_collection[0].name.startswith('__')


def colliders(objs, half, step=0.4, skip=lambda o: False, ray_z=2.3, floor_max=2.0, override=None):
    """同 qiushuang_doors.colliders；栊翠庵台地高（佛殿地坪 1.64），故向下找地坪的起点、可接受的地坪上限都抬高。"""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        if o.type != 'MESH' or skip(o): continue
        me = o.evaluated_get(dg).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(o.matrix_world)
        tm = bpy.data.meshes.new('tmp'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
        o.evaluated_get(dg).to_mesh_clear()
    bvh = BVHTree.FromBMesh(bm); bm.free()
    cells = {}
    nx, nz = int(half[0] / step) + 1, int(half[1] / step) + 1
    for ix in range(-nx, nx + 1):
        for iz in range(-nz, nz + 1):
            x, z = ix * step, iz * step
            hit = bvh.ray_cast(B(x, ray_z, z), Vector((0, 0, -1)), 4.0)
            floor = hit[0].z if (hit[0] is not None and hit[1].z > 0.6 and hit[0].z < floor_max) else 0.0
            solid = False
            for dy in (0.45, 0.9, 1.35):
                n = bvh.find_nearest(B(x, floor + dy, z), step * 0.55)
                if n[0] is not None: solid = True; break
            if solid:
                up = bvh.ray_cast(B(x, floor + 0.3, z), Vector((0, 0, 1)), 6)
                top = (up[0].z if up[0] is not None else floor + 3.0)
                cells[(ix, iz)] = ('w', round(max(top, floor + 2.0) * 4) / 4, round((floor + 0.2) * 4) / 4)
            elif floor > 0.12:
                cells[(ix, iz)] = ('f', round(floor * 8) / 8, -1.0)
    cells.update(override or {})
    boxes, used = [], set()
    for (ix, iz), v in sorted(cells.items()):
        if (ix, iz) in used: continue
        j = ix
        while (j + 1, iz) in cells and cells[(j + 1, iz)] == v and (j + 1, iz) not in used and j - ix < 13: j += 1
        for k in range(ix, j + 1): used.add((k, iz))
        _, top, bot = v
        boxes.append([round((ix + j) / 2 * step, 2), round(iz * step, 2), round((j - ix + 1) * step / 2, 2), step / 2, top, bot])
    return boxes


# ================= 1. 佛殿明间 =================
for n in ('佛殿_lacquer_red', '佛殿_paper', '佛殿_gold', '佛殿_lacquer_green'):
    print('佛殿明间', n, cut_faces(n, FD))

# ================= 2. 东禅堂明间 =================
for n in ('东禅堂_lacquer_red', '东禅堂_paper', '东禅堂_gold', '东禅堂_lacquer_green'):
    print('东禅堂明间', n, cut_faces(n, CT))

# ================= 3. 东耳房当中两扇 =================
for n in ('东耳房_lacquer_red', '东耳房_paper', '东耳房_gold', '东耳房_lacquer_green'):
    print('东耳房', n, cut_faces(n, EF))

# ================= 3b. 东禅堂前廊北头 =================
# 踏跺实体放在室内模型 longcui_in 里（外壳 wasm 用 glb_cut 从原模型剪，不重新导出）。
# 碰撞格（ix = x/0.4，iz = 网页 z/0.4 = −y/0.4）：廊子尽端两排算廊地（1.375），台明外一排算踏步（1.125）
OVERRIDE = {}
for ix in range(17, 21):
    OVERRIDE[(ix, -7)] = OVERRIDE[(ix, -8)] = ('f', 1.375, -1.0)
    OVERRIDE[(ix, -9)] = ('f', 1.125, -1.0)

# ================= 4. 重新生成外壳碰撞框 =================
bpy.context.view_layer.update()
boxes = colliders([o for o in bpy.data.objects if o.type == 'MESH'], (13.6, 11.6), skip=is_roof, override=OVERRIDE)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['longcui'] = boxes
with open(colp, 'w', encoding='utf-8') as f:
    json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))
print('col longcui boxes', len(boxes))

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
