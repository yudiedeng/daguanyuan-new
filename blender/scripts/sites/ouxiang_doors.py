"""藕香榭：去掉榭内旧条桌、重新生成外壳碰撞（在 blender/ouxiang.blend 上就地修改，可重复执行）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/ouxiang_doors.py
  外壳 wasm 只剪掉同一张条桌（可重复执行）：
    node tools/glb_cut.mjs models/b/ouxiang.wasm models/b/ouxiang.wasm "$(python3 blender/scripts/sites/ouxiang_doors.py --cutspec)"
  榭内原有一张栗壳漆长条桌（ouxiang_陈设_chestnut，x ±1.2，y 1.45…2.15）正挡在北门里口，删去；
  南面廊下原有两张竹案（ouxiang_陈设_bamboo_old）把曲廊→东/西廊→南廊→南门这条路堵死（廊宽 1 m，案占 0.64 m），也删去；
  竹案按原文「栏杆外」移到南面美人靠外的月台上（在 ouxiang_in 里重做）。
  东、西两面的南次间（y −3.16…−0.14，左右曲廊正接在这间外面的廊下）原是四扇窗 + 槛墙，整间剪开做门，
  敞开的隔扇门扇折在室内（ouxiang_in）。横披窗与柱子保留。
  三张席面（上面一桌、东边一桌、西边靠门一小桌）在 ouxiang_in（blender/scripts/interiors/build_ouxiang.py）。
  外壳现状：榭身南北明间的隔扇门本来就是敞开的（门扇已向内开），匾额「藕香榭」与黑漆嵌蚌对联已挂在南面明间檐柱上；
  左右曲廊接到榭东、西两侧的廊下，绕到南廊进南门。
  原 col.json['ouxiang'] 是 13 个整件包围盒（榭身被 index.html 的 ROOF 补丁整个掏空，人能穿窗）；
  这里换成体素式碰撞框（同秋爽斋），四面窗、槛墙、美人靠都挡人，只有南北两门可进。
  注意：index.html 里 ROOF={ouxiang:[…]} 是按旧框编号写的，换新碰撞框后要删掉。
  水面、荷叶、水藻不进射线（池底碎石垫层仍按原来的 0.62 m 当可站面，与旧碰撞一致）。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。
"""
import sys, json
TABLE = (-1.25, 1.40, 0.85, 1.25, 2.20, 1.80)       # 旧条桌
BAMBOO = (-4.0, -4.20, 0.85, 4.0, -3.40, 1.75)      # 南廊下两张旧竹案
SIDE = [(4.58, -3.16, 0.88, 5.00, -0.14, 3.36), (-5.00, -3.16, 0.88, -4.58, -0.14, 3.36)]   # 东、西面南次间（接曲廊）整间隔扇窗+槛墙
SIDE_RE = '^M_(栗壳漆|栗壳漆_棂|窗纸|描金|青砖)$'
RAIL = [(4.58, -3.22, 1.70, 5.00, -0.08, 1.85), (-5.00, -3.22, 1.70, -4.58, -0.08, 1.85)]   # 槛墙上的榻板（两头伸进柱里）
if '--cutspec' in sys.argv:
    print(json.dumps([list(TABLE) + ['^M_栗壳漆$'], list(BAMBOO) + ['^M_黄竹$']] + [list(b) + [SIDE_RE] for b in SIDE] + [list(b) + ['^M_栗壳漆$'] for b in RAIL])); sys.exit(0)
import bpy, bmesh, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ouxiang.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
def cut_faces(obj_name, box):
    """删除整个落在盒子里的面（可重复执行：第二次为 0）"""
    o = bpy.data.objects[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me); mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = [f for f in bm.faces if all(x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1 for w in (mw @ v.co for v in f.verts))]
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(me); bm.free(); return len(dead)


for b in SIDE:
    for n in ('ouxiang_榭_lattice', 'ouxiang_榭_paper', 'ouxiang_榭_gold', 'ouxiang_榭_chestnut', 'ouxiang_榭_brick'):
        print('侧门', n, cut_faces(n, b))
for b in RAIL:
    print('榻板', cut_faces('ouxiang_榭_chestnut', b))
for n in ('ouxiang_陈设_chestnut', 'ouxiang_陈设_bamboo_old'):
    if n in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True); print('removed', n)


def B(x, y, z):
    return Vector((x, -z, y))

ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花', 'ridge', '水面', '_荷_', 'algae')

def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS) or o.users_collection[0].name.startswith('__')


def colliders(objs, half, step=0.4, skip=lambda o: False, ray_z=2.3, floor_max=2.0, override=None):
    """同 qiushuang_doors.colliders；可调向下找地坪的起点 ray_z 与可接受的地坪上限 floor_max，override 覆盖个别格。"""
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



bpy.context.view_layer.update()
boxes = colliders([o for o in bpy.data.objects if o.type == 'MESH'], (10.4, 8.4), skip=is_roof, ray_z=2.0, floor_max=1.5)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['ouxiang'] = boxes
with open(colp, 'w', encoding='utf-8') as f:
    json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))
print('col ouxiang boxes', len(boxes))
bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
