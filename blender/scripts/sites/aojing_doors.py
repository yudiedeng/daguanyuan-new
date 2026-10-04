"""凹晶馆开门（在 blender/aojing.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/aojing_doors.py
  然后导出外壳：python3 blender/scripts/web/export_glb.py blender/aojing.blend /tmp/aojing.glb
               node blender/scripts/web/pack_glb.mjs /tmp/aojing.glb models/b/aojing.wasm models/b/aojing.wasm
  凹晶馆（三开间卷棚，前檐面水 −Y，后檐是实心后墙 +Y 靠山）：
  1. 前檐明间（x ±1.54，y≈−0.89）四扇隔扇门删去（下槛 z 0.51–0.65、中槛、横披保留）——面水敞开。
     敞开的门扇在 aojing_in（blender/scripts/interiors/build_aojing.py）。
  2. 后墙正中凿一个后门（x ±0.75，z 0.51–2.75），朱漆门框——从凸碧山庄下山的路在北面（网页 DOOR 点 [0,-3.2] 就在这里）。
  3. 重新生成外壳碰撞框（体素式，同秋爽斋），写 col.json['aojing']。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import bpy, bmesh, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'aojing.blend'))
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



for o in [o for o in O if o.name.startswith('AJ_开门_')]:
    bpy.data.objects.remove(o, do_unlink=True)
col = bpy.data.collections.get('AJ_凹晶馆')


def new_box(name, x0, y0, z0, x1, y1, z1, m):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    o.data.materials.append(bpy.data.materials[m]); return o


# ================= 1. 前檐明间 =================
MJ = (-1.545, -1.0, 0.649, 1.545, -0.78, 3.041)
for n in ('AJ_馆_red', 'AJ_馆_lat', 'AJ_馆_gold', 'AJ_馆_paper'):
    print('明间', n, cut_faces(n, MJ))

# ================= 2. 后墙后门 =================
DW, DZ = 0.75, 2.75
YB0, YB1 = 2.60, 3.22                     # 后墙（砖下碱 + 白灰墙心）里外皮
if 'AJ_后门已凿' not in bpy.data.texts:   # 布尔只做一次（可重复执行）
    bpy.ops.mesh.primitive_cube_add(size=1)
    cutter = bpy.context.active_object
    cutter.scale = (DW * 2, 1.2, DZ - 0.505); cutter.location = (0, (YB0 + YB1) / 2, 0.505 + (DZ - 0.505) / 2)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for n in ('AJ_馆_brick', 'AJ_馆_plaster'):
        o = O[n]; md = o.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='cut')
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.texts.new('AJ_后门已凿')
# 门框：两侧抱框、上槛（朱漆），门洞内衬白灰
new_box('AJ_开门_后门抱框W', -DW - 0.02, YB0 - 0.03, 0.51, -DW + 0.08, YB1 + 0.03, DZ + 0.1, 'M_朱漆')
new_box('AJ_开门_后门抱框E', DW - 0.08, YB0 - 0.03, 0.51, DW + 0.02, YB1 + 0.03, DZ + 0.1, 'M_朱漆')
new_box('AJ_开门_后门上槛', -DW - 0.02, YB0 - 0.03, DZ - 0.02, DW + 0.02, YB1 + 0.03, DZ + 0.1, 'M_朱漆')
new_box('AJ_开门_后门下槛', -DW + 0.08, YB0 - 0.03, 0.51, DW - 0.08, YB1 + 0.03, 0.6, 'M_朱漆')
# 门外一级踏步（墙外 y 3.22–3.54 为台基 0.51，再往外地面 0；踏步面 0.30，深 0.68，让体素碰撞也认得出是可走面）
new_box('AJ_开门_后门踏步', -0.95, 3.54, 0.0, 0.95, 4.22, 0.30, 'M_青石')

# ================= 3. 重新生成外壳碰撞框 =================
bpy.context.view_layer.update()
boxes = colliders([o for o in bpy.data.objects if o.type == 'MESH'], (7.0, 8.4), skip=is_roof)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['aojing'] = boxes
with open(colp, 'w', encoding='utf-8') as f:
    json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))
print('col aojing boxes', len(boxes))

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
