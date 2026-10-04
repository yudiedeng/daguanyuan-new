"""秋爽斋开门（在 blender/qiushuang.blend 上就地修改，可重复执行）。
用法：python3 blender/scripts/sites/qiushuang_doors.py
  1. 院门：原来是两片带拱形浮雕的实心墙（借栊翠庵山门），这里把拱形凿通，砌出通道，门扇向院内敞开贴在两侧。
  2. 晓翠堂抱厦明间：四扇隔扇门删去；正房前檐五块木板隔断也剪去（陈设与敞开的门扇在 qiushuang_in 里）。
  3. 探春三间明间：四扇隔扇门删去。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z；原点在秋爽斋院心，网页 (-86, 19)）。
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'qiushuang.blend')
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(SRC))
M = bpy.data.materials
O = bpy.data.objects
col = bpy.data.collections.get('QS_秋爽斋') or bpy.context.scene.collection

# ---- 先清掉上次生成的东西（保证可重复执行） ----
for o in [o for o in O if o.name.startswith('QS_开门_')]:
    bpy.data.objects.remove(o, do_unlink=True)

def mat(name):
    return M[name]

def new_box(name, x0, y0, z0, x1, y1, z1, m):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    o.data.materials.append(mat(m)); return o

def cut_faces(obj_name, box, mats=None):
    """删除整个落在盒子里的面（可按材质过滤）。返回删除面数"""
    o = O[obj_name]; me = o.data
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    mw = o.matrix_world
    x0, y0, z0, x1, y1, z1 = box
    dead = []
    for f in bm.faces:
        if mats and not (f.material_index < len(o.material_slots) and o.material_slots[f.material_index].material and
                         o.material_slots[f.material_index].material.name in mats):
            continue
        ok = True
        for v in f.verts:
            w = mw @ v.co
            if not (x0 <= w.x <= x1 and y0 <= w.y <= y1 and z0 <= w.z <= z1): ok = False; break
        if ok: dead.append(f)
    n = len(dead)
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me); bm.free(); return n


def B(x, y, z):
    return Vector((x, -z, y))

ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花')

def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS)

# --------------------------------------------------------------------------- 碰撞框（自动）
def colliders(objs, half, step=0.4, skip=lambda o: False):
    """在建筑范围内按 step 网格扫描：先向下找地坪（台基、台阶，作可走面），
    再在离地 0.4–1.6 m 处找是否贴着构件（墙、柱、栏杆、门窗），有则为挡人框。
    返回 col.json 格式 [lx, lz, hx, hz, top, bot]（局部坐标）。"""
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
            hit = bvh.ray_cast(B(x, 2.2, z), Vector((0, 0, -1)), 4.0)   # 檐下向下找地坪
            floor = hit[0].z if (hit[0] is not None and hit[1].z > 0.6 and hit[0].z < 1.5) else 0.0
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



# ================= 1. 院门 =================
# 前后两片墙（y -14.45…-13.95 与 -11.45…-10.95），拱形浮雕内径 0.88、拱顶约 2.96。
AR, AZ = 0.88, 2.08          # 拱半径、拱心高度
bpy.ops.mesh.primitive_cube_add(size=1); cutter = bpy.context.active_object; cutter.name = 'QS_开门_cutter'
cutter.scale = (AR * 2, 4.2, AZ - 0.18); cutter.location = (0, -12.7, 0.18 + (AZ - 0.18) / 2)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=AR, depth=4.2, rotation=(math.pi / 2, 0, 0), location=(0, -12.7, AZ)); cyl = bpy.context.active_object; cyl.name = 'QS_开门_cutter2'
# 合并两块
bpy.ops.object.select_all(action='DESELECT'); cutter.select_set(True); cyl.select_set(True); bpy.context.view_layer.objects.active = cutter
bpy.ops.object.join()
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for n in ('QS_院门_墙_-2', 'QS_院门_墙_+2', 'QS_院门_下碱_-2', 'QS_院门_下碱_+2'):
    o = O[n]; md = o.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='cut')
bpy.data.objects.remove(cutter, do_unlink=True)

# 原山门留下的几列悬空门钉（原门扇已不在）：删掉，换成下面敞开的门扇
print('悬空门钉', cut_faces('QS_院门_gold', (-0.9, -13.95, 0.3, 0.9, -13.25, 2.0)))
print('悬空旧门扇碎片', cut_faces('QS_院门_lacquer_red', (-0.95, -13.96, 0.15, 0.95, -11.45, 2.95)))
# 通道内衬：两侧墙、顶、地（把两片墙之间的空腔收成 1.76 宽的门洞）
Y0, Y1 = -13.95, -11.45
new_box('QS_开门_院门内墙W', -2.15, Y0, 0.2, -AR, Y1, 3.1, 'M_白灰墙')
new_box('QS_开门_院门内墙E', AR, Y0, 0.2, 2.15, Y1, 3.1, 'M_白灰墙')
new_box('QS_开门_院门顶', -AR, Y0, AZ + AR, AR, Y1, 3.12, 'M_旧木')
# 拱洞内圈衬：半圆柱内壁（让拱洞侧面不透）
def arch_lining():
    bm = bmesh.new(); seg = 32
    prof = [(-AR, 0.2)] + [(-AR * math.cos(math.pi * i / seg), AZ + AR * math.sin(math.pi * i / seg)) for i in range(seg + 1)] + [(AR, 0.2)]
    # 内壁面朝洞内
    pts = [(-AR, 0.2)] + [(-AR * math.cos(math.pi * i / seg), AZ + AR * math.sin(math.pi * i / seg)) for i in range(seg + 1)] + [(AR, 0.2)]
    vs = [(bm.verts.new((x, Y0, z)), bm.verts.new((x, Y1, z))) for x, z in pts]
    for i in range(len(vs) - 1):
        a, b = vs[i], vs[i + 1]
        bm.faces.new((a[0], b[0], b[1], a[1]))
    me = bpy.data.meshes.new('QS_开门_拱内壁'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('QS_开门_拱内壁', me); col.objects.link(o); o.data.materials.append(mat('M_白灰墙'))
    for p in o.data.polygons: p.use_smooth = False
    return o
arch_lining()
# 门扇：向院内（+Y）敞开，贴着门洞两侧；朱漆，门钉，铺首
def leaf(sx):
    x_in = sx * (AR - 0.03)
    y0 = Y0 + 0.02
    body = new_box(f'QS_开门_院门扇{"E" if sx > 0 else "W"}', x_in - 0.03, y0, 0.22, x_in + 0.03, y0 + AR - 0.04, 2.7, 'M_朱漆')
    # 门钉 5×5
    for r in range(5):
        for c in range(5):
            yy = y0 + 0.1 + c * (AR - 0.24) / 4; zz = 0.55 + r * 0.42
            for face in (-1, 1):
                s = new_box(f'QS_开门_钉', x_in + face * 0.03 + (0.005 if face > 0 else -0.025), yy - 0.02, zz - 0.02, x_in + face * 0.03 + (0.025 if face > 0 else -0.005), yy + 0.02, zz + 0.02, 'M_描金')
    return body
leaf(1); leaf(-1)

# ================= 2. 晓翠堂抱厦明间 =================
n1 = cut_faces('QS_晓翠堂_抱厦_lat', (-1.62, 2.6, 0.93, 1.62, 2.95, 3.2))
n2 = cut_faces('QS_晓翠堂_抱厦_paper', (-1.62, 2.6, 0.93, 1.62, 2.95, 3.2))
n3 = cut_faces('QS_晓翠堂_抱厦_red', (-1.62, 2.6, 0.93, 1.62, 2.95, 3.2))
n4 = cut_faces('QS_晓翠堂_抱厦_gold', (-1.62, 2.6, 0.93, 1.62, 2.95, 3.2))
print('抱厦明间删面', n1, n2, n3, n4)
# 正房前檐（y≈5.9）的五块木板隔断（借怡红院时带过来的）：整排剪去，晓翠堂前后通敞
for part in ('red', 'gold', 'green'):
    n = f'QS_晓翠堂_正房_{part}'
    if n in O: print('正房前檐隔断', part, cut_faces(n, (-7.9, 5.8, 0.78, 7.9, 6.0, 5.24)))

# ================= 3. 探春三间明间 =================
B3 = (-10.75, -8.62, 0.55, -10.45, -5.40, 2.99)
for part in ('lacquer_red', 'paper', 'gold', 'lacquer_green', 'wood_dark'):
    n = f'QS_秋爽斋三间_{part}'
    if n in O: print('三间', part, cut_faces(n, B3))


# ================= 4. 重新生成外壳碰撞框 =================
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.context.view_layer.update()
boxes = colliders([o for o in bpy.data.objects if o.type == 'MESH'], (16.0, 18.0), skip=is_roof)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['qiushuang'] = boxes
json.dump(cj, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
print('col qiushuang boxes', len(boxes))

bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(SRC), compress=True)
print('saved')
