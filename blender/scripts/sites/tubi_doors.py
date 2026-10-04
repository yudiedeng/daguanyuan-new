"""凸碧山庄开门（在 blender/tubi.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/tubi_doors.py
  然后导出外壳：python3 blender/scripts/web/export_glb.py blender/tubi.blend /tmp/tubi.glb
               node blender/scripts/web/pack_glb.mjs /tmp/tubi.glb models/b/tubi.wasm models/b/tubi.wasm
  凸碧堂（山顶敞厅，五开间带前廊）：明间（x ±1.73，前金柱线 y≈-1.3）四扇隔扇门删去，
  下槛（z 0.89–1.01）与中槛、横披窗保留。敞开的门扇与陈设在 tubi_in（blender/scripts/interiors/build_tubi.py）。
  山顶只此一座，无院门；月台前踏跺本来就通。
  重新生成外壳碰撞框（体素式，同秋爽斋），写 col.json['tubi']。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import bpy, bmesh, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tubi.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects


def cut_faces(obj_name, box):
    """删除整个落在盒子里的面。返回删除面数（可重复执行：第二次为 0）"""
    o = O[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = [f for f in bm.faces if all(x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1 for w in (mw @ v.co for v in f.verts))]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(me); bm.free(); return len(dead)


def B(x, y, z):
    return Vector((x, -z, y))

ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '撒头', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花', 'ridge', 'wood_dark')

def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS) or o.users_collection[0].name.startswith('__')


def colliders(objs, half, step=0.4, skip=lambda o: False, ray_z=2.2, floor_max=1.5):
    """同 qiushuang_doors.colliders。"""
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
    boxes, used = [], set()
    for (ix, iz), v in sorted(cells.items()):
        if (ix, iz) in used: continue
        j = ix
        while (j + 1, iz) in cells and cells[(j + 1, iz)] == v and (j + 1, iz) not in used and j - ix < 13: j += 1
        for k in range(ix, j + 1): used.add((k, iz))
        _, top, bot = v
        boxes.append([round((ix + j) / 2 * step, 2), round(iz * step, 2), round((j - ix + 1) * step / 2, 2), step / 2, top, bot])
    return boxes


# ================= 1. 凸碧堂明间 =================
# 四扇门：x −1.73…1.73，y −1.35…−1.27，z 1.01…3.66（门框立边、抹头、裙板、格心棂条、窗纸、看叶）
MJ = (-1.735, -1.41, 1.005, 1.735, -1.20, 3.665)
for n in ('TB_凸碧堂_lacquer_red', 'TB_凸碧堂_paper', 'TB_凸碧堂_gold'):
    print('明间', n, cut_faces(n, MJ))
print('明间门扇角叶', cut_faces('TB_凸碧堂_gold', (-1.745, -1.41, 1.02, 1.745, -1.20, 3.65)))

# ================= 2. 重新生成外壳碰撞框 =================
bpy.context.view_layer.update()
boxes = colliders([o for o in bpy.data.objects if o.type == 'MESH'], (8.4, 6.6), skip=is_roof)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['tubi'] = boxes
with open(colp, 'w', encoding='utf-8') as f:
    json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))
print('col tubi boxes', len(boxes))

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
