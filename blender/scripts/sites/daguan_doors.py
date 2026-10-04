"""大观楼开门（在 blender/daguan.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_doors.py
  然后导出外壳：python3 blender/scripts/web/export_glb.py blender/daguan.blend /tmp/daguan.glb
               node blender/scripts/web/pack_glb.mjs /tmp/daguan.glb models/b/daguan.wasm models/b/daguan.wasm
  1. 顾恩思义殿（正殿）明间（x ±2.17，前檐隔扇在 y≈14.8）：四扇隔扇门删去（下槛、中槛、横披窗保留）。
     殿内原有一圈“室内暗”黑板（贴在隔扇背后挡视线，殿内本是空壳）：整件删去，殿内陈设在 daguan_in。
  2. 缀锦阁（东，x 28.3…37.7）/ 含芳阁（西，镜像）：底层明间（x ±31.64…34.36，y≈15）四扇隔扇门删去；
     底层的“室内暗”黑板删去（楼上的保留，楼上仍是封闭的）。
  3. 重新生成外壳碰撞框（体素式，同秋爽斋/栊翠庵），写 col.json['daguan']。
     殿台 2.1 m、月台 1.5 m，故向下找地坪的射线从 2.9 m 起，可接受地坪上限 2.8 m。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import bpy, bmesh, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'daguan.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects


def cut_faces(obj_name, box):
    """删除整个落在盒子里的面。返回删除面数（可重复执行：第二次为 0）"""
    if obj_name not in O:
        return 0
    o = O[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = [f for f in bm.faces if all(x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1 for w in (mw @ v.co for v in f.verts))]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free(); return len(dead)


PARTS = ('lacquer_red', 'paper', 'gold', 'cai_blue', 'cai_green', 'wood_dark', 'lacquer_green', 'brick')

# ================= 1. 顾恩思义殿 明间 =================
HALL_DOOR = (-2.165, 14.70, 2.29, 2.165, 14.90, 6.17)
for p in PARTS:
    n = cut_faces(f'daguan_顾恩思义殿_{p}', HALL_DOOR)
    if n: print('正殿明间', p, n)
if 'daguan_顾恩思义殿_dark' in O:
    bpy.data.objects.remove(O['daguan_顾恩思义殿_dark'], do_unlink=True)
    print('正殿室内暗板 删去')

# ================= 2. 缀锦阁 / 含芳阁 底层明间 =================
for name, sx in (('缀锦阁', 1), ('含芳阁', -1)):
    xa, xb = sorted((sx * 31.62, sx * 34.38))
    box = (xa, 14.90, 1.09, xb, 15.10, 3.32)
    for p in PARTS:
        n = cut_faces(f'daguan_{name}_{p}', box)
        if n: print(name, '明间', p, n)
    xa, xb = sorted((sx * 28.4, sx * 37.6))
    n = cut_faces(f'daguan_{name}_dark', (xa, 15.0, 0.8, xb, 23.0, 4.1))
    print(name, '底层室内暗板', n)


# ================= 2b. 匾额字转网格 =================
# 线上旧 daguan.wasm 里匾额金字是网格（网页 PT 表里没有 daguan，不会另画），export_glb.py 跳过 FONT 对象，
# 所以这里把每个 FONT 复制成网格对象（<名>_网格，描金），重导出时金字才不会丢。
for o in [o for o in O if o.name.endswith('_字_网格')]:
    bpy.data.objects.remove(o, do_unlink=True)
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in O if o.type == 'FONT']:
    ru = o.data.resolution_u; o.data.resolution_u = 5          # 字形曲线降精度，金字三角面约减半
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.data.resolution_u = ru
    ob = bpy.data.objects.new(o.name + '_网格', me)
    ob.matrix_world = o.matrix_world.copy()
    o.users_collection[0].objects.link(ob)
    print('匾字网格', ob.name, len(me.polygons))


# ================= 3. 外壳碰撞框 =================
def B(x, y, z):
    return Vector((x, -z, y))

ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花', 'ridge')

def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS) or o.users_collection[0].name.startswith('__')


def colliders(objs, xr, zr, step=0.4, skip=lambda o: False, ray_z=2.9, floor_max=2.8):
    """体素式碰撞框（同 qiushuang_doors.colliders），扫描网页局部 x∈xr、z∈zr。
    先向下找地坪（台基、台阶，作可走面），再在离地 0.45/0.9/1.35 m 处找是否贴着构件，有则为挡人框。"""
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        if o.type != 'MESH' or skip(o): continue
        me = o.evaluated_get(dg).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(o.matrix_world)
        tm = bpy.data.meshes.new('tmp'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
        o.evaluated_get(dg).to_mesh_clear()
    bvh = BVHTree.FromBMesh(bm); bm.free()
    cells = {}
    for ix in range(int(round(xr[0] / step)), int(round(xr[1] / step)) + 1):
        for iz in range(int(round(zr[0] / step)), int(round(zr[1] / step)) + 1):
            x, z = ix * step, iz * step
            hit = bvh.ray_cast(B(x, ray_z, z), Vector((0, 0, -1)), ray_z + 1.0)
            floor = hit[0].z if (hit[0] is not None and hit[1].z > 0.6 and hit[0].z < floor_max) else 0.0
            solid = False
            for dy in (0.45, 0.9, 1.35):
                n = bvh.find_nearest(B(x, floor + dy, z), step * 0.55)
                if n[0] is not None: solid = True; break
            if solid:
                up = bvh.ray_cast(B(x, floor + 0.3, z), Vector((0, 0, 1)), 8)
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


bpy.context.view_layer.update()
boxes = colliders([o for o in O if o.type == 'MESH'], (-40.0, 40.0), (-31.2, 16.4), skip=is_roof)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['daguan'] = boxes
json.dump(cj, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
print('col daguan boxes', len(boxes))

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
