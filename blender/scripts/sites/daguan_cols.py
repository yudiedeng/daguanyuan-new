"""大观楼外壳碰撞框（改样之后；可重复执行）：写 col.json['daguan']。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_cols.py
体素式（同 daguan_doors.colliders）：先向下找地坪（台基、台阶，作可走面），再在离地 0.45/0.9/1.35 m 处找是否贴着构件。
楼台 4.5 m、楼内地面约 5.2 m，射线从 7.5 m 起。白石栏杆单独处理：栏杆细、柱头又在 1 m 以上，向下的射线会把柱头当成地坪，
所以先不算栏杆求地坪，再把栏杆经过的格子一律记成挡人框。
"""
import bpy, bmesh, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'daguan.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
assert 'daguan_改样标记' in O, '先跑 daguan_rebuild.py'


def B(x, y, z):
    return Vector((x, -z, y))


ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花', 'ridge', '水池_water', '水池底')


def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS) or o.users_collection[0].name.startswith('__')


is_rail = lambda o: '栏杆' in o.name


def bvh_of(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        me = o.evaluated_get(dg).to_mesh(); t = bmesh.new(); t.from_mesh(me); t.transform(o.matrix_world)
        tm = bpy.data.meshes.new('tmp'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
        o.evaluated_get(dg).to_mesh_clear()
    bvh = BVHTree.FromBMesh(bm); bm.free()
    return bvh


def colliders(xr, zr, step=0.4, ray_z=7.5, floor_max=6.2):
    meshes = [o for o in O if o.type == 'MESH' and not is_roof(o)]
    bvh = bvh_of([o for o in meshes if not is_rail(o)])
    rail = bvh_of([o for o in meshes if is_rail(o)])
    cells = {}
    for ix in range(int(round(xr[0] / step)), int(round(xr[1] / step)) + 1):
        for iz in range(int(round(zr[0] / step)), int(round(zr[1] / step)) + 1):
            x, z = ix * step, iz * step
            hit = bvh.ray_cast(B(x, ray_z, z), Vector((0, 0, -1)), ray_z + 1.0)
            floor = hit[0].z if (hit[0] is not None and hit[1].z > 0.6 and hit[0].z < floor_max) else 0.0
            if any(rail.find_nearest(B(x, floor + dy, z), step * 0.55)[0] is not None for dy in (0.3, 0.7, 1.1)):
                cells[(ix, iz)] = ('w', round((floor + 1.3) * 4) / 4, round((floor - 0.6) * 4) / 4)   # 底放低：台下的人也钻不进台基
                continue
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
boxes = colliders((-40.0, 40.0), (-39.4, 34.4))
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['daguan'] = boxes
json.dump(cj, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
print('col daguan boxes', len(boxes))
