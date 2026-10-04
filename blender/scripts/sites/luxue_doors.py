"""芦雪广开门（在 blender/luxue.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/luxue_doors.py
  然后导出外壳：python3 blender/scripts/web/export_glb.py blender/luxue.blend /tmp/luxue.glb
               node blender/scripts/web/pack_glb.mjs /tmp/luxue.glb models/b/luxue.wasm models/b/luxue.wasm
  1. 明间板门（x ±0.7，前墙 y≈−2.8，门洞 x ±0.75、高 0.47…2.48）：八条门板、三道门带（旧木）、门环（描金）删去；
     敞开的门扇在 luxue_in（blender/scripts/interiors/build_luxue.py）。
  2. 重新生成外壳碰撞框（体素式，同秋爽斋），写 col.json['luxue']；芦苇、芦花、槿篱不算（原碰撞也不含）。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import bpy, bmesh, os, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'luxue.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects


def cut_faces(obj_name, box):
    o = O[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = [f for f in bm.faces if all(x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1 for w in (mw @ v.co for v in f.verts))]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free(); return len(dead)


print('门板', cut_faces('LX_茅屋_wood', (-0.71, -2.81, 0.46, 0.71, -2.74, 2.48)))
print('门带', cut_faces('LX_茅屋_wood_dark', (-0.69, -2.86, 0.7, 0.68, -2.78, 2.25)))
print('门环', cut_faces('LX_茅屋_gold', (-0.2, -2.9, 1.4, 0.2, -2.8, 1.7)))


def B(x, y, z):
    return Vector((x, -z, y))

SKIP_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', 'rope', '芦苇', '芦花', '槿篱')

def skip(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in SKIP_WORDS)


def colliders(objs, xr, zr, step=0.4, skip=lambda o: False, ray_z=2.2, floor_max=1.5, clear=()):
    """同 daguan_doors.colliders（体素式），扫描网页局部 x∈xr、z∈zr。"""
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
            hit = bvh.ray_cast(B(x, ray_z, z), Vector((0, 0, -1)), ray_z + 2.0)
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
    # clear：网页局部矩形 (x0,x1,z0,z1) 内的挡人格删去（门洞两侧门框另补精确的框）
    for k in [k for k, v in cells.items() if v[0] == 'w']:
        x, z = k[0] * step, k[1] * step
        if any(a <= x <= b and c <= z <= d for a, b, c, d in clear): del cells[k]
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
boxes = colliders([o for o in O if o.type == 'MESH'], (-8.4, 8.4), (-8.8, 4.8), step=0.2, skip=skip,
                  clear=[(-0.65, 0.65, 2.4, 3.3)])
# 门框（旧木门柱 x ±0.64…0.76，y −2.96…−2.74）
boxes += [[sx * 0.7, 2.85, 0.06, 0.11, 2.75, 0.5] for sx in (-1, 1)]   # 0.2 格：门洞只有 1.5 m，0.4 格会把门口量化成 0.8 m
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['luxue'] = boxes
json.dump(cj, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
print('col luxue boxes', len(boxes))
bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
