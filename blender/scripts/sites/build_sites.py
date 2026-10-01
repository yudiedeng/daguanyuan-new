"""芦雪广、凹晶馆、凸碧山庄三处新景点建模。

做法：从现有院落 .blend 里借用同一套构件（材质名与网页配方一致），重新组合，再补新部件：
- 芦雪广（第四十九回）：「傍山临水河滩之上，一带几间，茅檐土壁，槿篱竹牖，推窗便可垂钓，
  四面都是芦苇掩覆」——借稻香村「茅屋_正房」，加竹篱、临水钓台、四周芦苇。
- 凹晶馆（第七十六回）：「山之低洼近水处，就叫凹晶」——借怡红院「东厢房」作三间小馆，
  加临水石台、石栏，题「凹晶溪馆」。
- 凸碧山庄（第七十六回）：「山之高处，就叫凸碧」——借栊翠庵「佛殿」作山顶敞厅，加石台阶，题「凸碧山庄」。

坐标约定同网页：局部原点在建筑地面中心，网页 x→Blender X，网页 z→Blender -Y，网页 y→Blender Z。
正面一律朝网页 +z（Blender -Y，即 bbox 的 min.y 一侧）。
每处输出 blender/<id>.blend，并把自动生成的碰撞框写进 models/b/col.json[<id>]。

用法：python3 build_sites.py <repo根目录> [luxue|aojing|tubi ...]   （需要 pip install bpy）
"""
import bpy, bmesh, math, random, json, sys, os
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

args = [a for a in sys.argv[1:] if not a.startswith('-')]
REPO = next((a for a in args if os.path.isdir(a)), os.getcwd())
ONLY = [a for a in args if a in ('luxue', 'aojing', 'tubi')] or ['luxue', 'aojing', 'tubi']
SRC = os.path.join(REPO, 'blender')


def B(x, y, z):
    return Vector((x, -z, y))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def coll(name):
    c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c); return c


def mat(name, rgb=(0.6, 0.6, 0.6), rough=0.9):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1); m.roughness = rough
    return m


def append_group(blend, collection, prefix, into):
    """把 blend 里某集合的网格对象（按名字前缀筛选）复制进当前场景的 into 集合，返回对象列表。"""
    path = os.path.join(SRC, blend)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.collections = [collection]
    c = dst.collections[0]
    objs = []
    for o in list(c.all_objects):
        if o.type != 'MESH' or (prefix and not o.name.startswith(prefix)):
            continue
        into.objects.link(o); objs.append(o)
    bpy.context.view_layer.update()        # 刚链接进来的对象要先刷新世界矩阵
    for o in objs:                         # 解除父级（保留世界坐标），后面才能整体旋转
        if o.parent is not None:
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    for o in list(c.all_objects):          # 没用到的对象不留在文件里
        if o not in objs: bpy.data.objects.remove(o)
    bpy.data.collections.remove(c)
    return objs


def bbox(objs):
    mn = Vector((1e9,) * 3); mx = -mn
    for o in objs:
        for c in o.bound_box:
            v = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, v)); mx = Vector(map(max, mx, v))
    return mn, mx


def place(objs, *, center_to=Vector((0, 0, 0)), rot_z=0.0, base_z=None):
    """把一组对象的底面中心移到 center_to，并绕 Z 旋转 rot_z。"""
    bpy.context.view_layer.update()
    mn, mx = bbox(objs)
    c = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z if base_z is None else base_z))
    M = Matrix.Translation(center_to) @ Matrix.Rotation(rot_z, 4, 'Z') @ Matrix.Translation(-c)
    for o in objs:
        if o.parent is None:
            o.matrix_world = M @ o.matrix_world


def mesh_obj(name, bm, material, into):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(material)
    o = bpy.data.objects.new(name, me); into.objects.link(o); return o


def box(bm, ctr, size, rz=0.0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(ctr) @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts'])


def reeds(bm_blade, bm_plume, centers, count, radius, seed, avoid=lambda p: False, h=(1.6, 2.6)):
    """芦苇丛：每株一片弯曲的窄叶带 + 顶端芦花。"""
    rnd = random.Random(seed); made = 0
    for _ in range(count * 4):
        if made >= count: break
        cx, cz, r = rnd.choice(centers)
        a = rnd.uniform(0, 6.283); d = r * math.sqrt(rnd.random())
        x, z = cx + math.cos(a) * d, cz + math.sin(a) * d
        if avoid((x, z)): continue
        made += 1
        H = rnd.uniform(*h); lean = Vector((rnd.uniform(-.35, .35), rnd.uniform(-.35, .35), 0))
        side = Vector((math.cos(a + 1.57), math.sin(a + 1.57), 0)) * 0.025
        base = B(x, -0.6, z); prev = None
        for k in range(5):
            t = k / 4; p = base + Vector((0, 0, (H + 0.6) * t)) + lean * t * t
            w = side * (1 - 0.7 * t)
            vs = (bm_blade.verts.new(p - w), bm_blade.verts.new(p + w))
            if prev: bm_blade.faces.new((prev[0], prev[1], vs[1], vs[0]))
            prev = vs
        top = base + Vector((0, 0, H + 0.6)) + lean
        if rnd.random() < 0.7:  # 芦花
            q = [top + Vector((0, 0, 0.05)), top + side * 3 + Vector((0, 0, -0.25)), top + Vector((0, 0, -0.42)), top - side * 3 + Vector((0, 0, -0.25))]
            bm_plume.faces.new([bm_plume.verts.new(v) for v in q])
    return made


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


def save(site, boxes):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SRC, site + '.blend'), compress=True)
    colp = os.path.join(REPO, 'models', 'b', 'col.json')
    col = json.load(open(colp, encoding='utf-8')); col[site] = boxes
    json.dump(col, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
    print('SITE', site, 'objects', len([o for o in bpy.data.objects if o.type == 'MESH']), 'boxes', len(boxes))


def plaque(name, ctr, w, h, into, rz=0.0):
    bm = bmesh.new(); box(bm, ctr, (w, 0.08, h), rz)
    return mesh_obj(name, bm, mat('M_匾心', (0.15, 0.12, 0.1)), into)


ROOF_WORDS = ('瓦', '脊', '望板', '椽', '屋面', '茅草', 'thatch', 'roof', '吻', '宝顶', '角梁', '博缝', '山花')


def is_roof(o):
    n = o.name; m = o.active_material.name if o.active_material else ''
    return any(w in n or w in m for w in ROOF_WORDS)


# =========================================================================== 芦雪广
def build_luxue():
    reset(); C = coll('LX_芦雪广'); G = coll('LX_芦苇竹篱')
    house = append_group('daoxiang.blend', '茅屋_正房', '', C)
    place(house, rot_z=0.0)                       # 正面朝网页 +z（与原稻香村正房朝向一致）
    mn, mx = bbox(house); W, D = mx.x - mn.x, mx.y - mn.y
    for o in house: o.name = o.name.replace('茅屋_正房', 'LX_茅屋')
    # 临水钓台：屋后（网页 -z 侧）伸出水面的木平台，下有木桩
    wood = mat('M_旧木', (0.35, 0.27, 0.2))
    bm = bmesh.new()
    zb = mx.y + 0.2   # 屋后（Blender +Y = 网页 -z）
    for i in range(14):
        box(bm, Vector((-3.5 + i * 0.5, zb + 1.6, 0.42)), (0.46, 3.2, 0.06))
    for x in (-3.6, -0.25, 3.1):
        for y in (zb + 0.3, zb + 3.0):
            box(bm, Vector((x, y, -0.4)), (0.16, 0.16, 1.7))
    for x in (-3.6, 3.1):   # 两侧低栏
        box(bm, Vector((x, zb + 1.6, 0.85)), (0.08, 3.2, 0.06))
    mesh_obj('LX_钓台', bm, wood, C)
    # 槿篱：正面一道矮竹篱（留出柴门口）
    bamboo = mat('M_竹篱', (0.55, 0.5, 0.3))
    bm = bmesh.new(); fz = mn.y - 3.2   # 屋前
    for s in (-1, 1):
        x0, x1 = s * 1.2, s * (W / 2 + 1.5)
        n = int(abs(x1 - x0) / 0.12)
        for k in range(n + 1):
            x = x0 + (x1 - x0) * k / n
            box(bm, Vector((x, fz, 0.55)), (0.05, 0.05, 1.1 + 0.08 * math.sin(k * 1.7)))
        for hgt in (0.35, 0.85):
            box(bm, Vector(((x0 + x1) / 2, fz, hgt)), (abs(x1 - x0), 0.04, 0.04))
    mesh_obj('LX_槿篱', bm, bamboo, G)
    # 芦苇：屋两侧、屋后水边、篱外，避开屋身与门前小径
    def avoid(p):
        x, z = p   # 网页局部坐标
        bx, bz = abs(x), z
        if bx < W / 2 + 0.8 and -D / 2 - 4.0 < bz < D / 2 + 3.6: return True   # 屋、钓台、前院
        if abs(x) < 1.4 and bz > 0: return True                               # 门前小径
        return False
    bm1, bm2 = bmesh.new(), bmesh.new()
    # 屋前（网页 +z）是园路，不种；两侧与屋后水边种满
    n = reeds(bm1, bm2, [(-W / 2 - 4, 0, 5), (W / 2 + 4, 0, 5), (0, -D / 2 - 6, 8),
                         (-W / 2 - 2, -D / 2 - 4, 4), (W / 2 + 2, -D / 2 - 4, 4)], 2400, 0, 49, avoid)
    mesh_obj('LX_芦苇', bm1, mat('M_草', (0.42, 0.52, 0.25)), G)
    mesh_obj('LX_芦花', bm2, mat('M_散草', (0.75, 0.7, 0.55)), G)
    print('reeds', n, 'house', round(W, 1), round(D, 1))
    # 河滩上的虎皮石台基，往下埋 1.6 m，压住坡地
    bm = bmesh.new(); box(bm, Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, -0.8)), (W + 0.6, D + 0.6, 1.6))
    mesh_obj('LX_台基', bm, mat('M_虎皮石', (0.55, 0.52, 0.48)), C)
    boxes = colliders(house + [bpy.data.objects['LX_钓台'], bpy.data.objects['LX_台基']], (W / 2 + 1, D / 2 + 5), skip=is_roof)
    save('luxue', boxes)


# =========================================================================== 凹晶馆
def build_aojing():
    reset(); C = coll('AJ_凹晶馆')
    hall = append_group('yihong.blend', 'yihong_厢房耳房', 'yihong_东厢房', C)
    place(hall, rot_z=math.pi / 2)               # 东厢房原本正面朝 -X，转成朝 -Y（网页 +z，临水一面）
    for o in hall: o.name = o.name.replace('yihong_东厢房', 'AJ_馆')
    mn, mx = bbox(hall); W, D = mx.x - mn.x, mx.y - mn.y
    stone, white = mat('M_青石', (0.7, 0.71, 0.68)), mat('M_汉白玉', (0.94, 0.93, 0.89), 0.5)
    # 临水石台：馆前（网页 +z）伸出 4 m，台面略高于水面，四周石栏
    bm = bmesh.new(); ty = 0.5
    box(bm, Vector((0, mn.y - 2.0, (ty - 3.5) / 2)), (W + 1.2, 4.2, ty + 3.5))   # 一直砌到池底
    box(bm, Vector((0, (mn.y + mx.y) / 2, -1.75)), (W + 0.4, D + 0.4, 3.5))           # 馆身台基
    mesh_obj('AJ_临水石台', bm, stone, C)
    bm = bmesh.new(); y0 = mn.y - 0.2; y1 = mn.y - 4.1; x0, x1 = -W / 2 - 0.5, W / 2 + 0.5
    for (a, b) in (((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(2, int(L / 1.6))
        for k in range(n + 1):
            p = Vector((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n, ty + 0.45))
            box(bm, p, (0.16, 0.16, 0.9))
        mid = Vector(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0))
        rz = math.atan2(b[1] - a[1], b[0] - a[0])
        box(bm, mid + Vector((0, 0, ty + 0.78)), (L, 0.1, 0.1), rz)
        box(bm, mid + Vector((0, 0, ty + 0.2)), (L, 0.12, 0.12), rz)
        for k in range(n):
            q = Vector((a[0] + (b[0] - a[0]) * (k + .5) / n, a[1] + (b[1] - a[1]) * (k + .5) / n, ty + 0.48))
            box(bm, q, (L / n - 0.3 if abs(rz) < 0.1 or abs(abs(rz) - math.pi) < 0.1 else 0.06, 0.06 if abs(rz) < 0.1 else L / n - 0.3, 0.42))
    mesh_obj('AJ_石栏', bm, white, C)
    lat = [o for o in hall if o.name.endswith('_lat')]
    lmn, lmx = bbox(lat) if lat else (mn, mx)
    plaque('AJ_凹晶溪馆_匾底', Vector((0, lmn.y - 0.12, lmx.z + 0.38)), 1.7, 0.5, C)   # 槅扇上方门楣
    boxes = colliders(hall + [bpy.data.objects['AJ_临水石台'], bpy.data.objects['AJ_石栏']], (W / 2 + 1.5, D / 2 + 5), skip=is_roof)
    save('aojing', boxes)


# =========================================================================== 凸碧山庄
def build_tubi():
    reset(); C = coll('TB_凸碧山庄')
    hall = append_group('longcui.blend', '栊翠庵_佛殿', '', C)
    for o in hall: o.name = o.name.replace('佛殿', 'TB_凸碧堂')
    place(hall, rot_z=0.0)                       # 佛殿原本就面朝 -Y（网页 +z）
    mn, mx = bbox(hall); W, D = mx.x - mn.x, mx.y - mn.y
    # 山顶石台基外再铺一圈散水，往下埋 1.5 m，免得坡地露底
    stone = mat('M_青石', (0.7, 0.71, 0.68))
    bm = bmesh.new(); box(bm, Vector((0, (mn.y + mx.y) / 2, -0.75)), (W + 3, D + 3, 1.5))
    mesh_obj('TB_山顶台基', bm, stone, C)
    if not any('匾' in o.name for o in hall):
        plaque('TB_凸碧山庄_匾底', Vector((0, mn.y + 1.2, 3.6)), 2.0, 0.6, C)
    boxes = colliders(hall + [bpy.data.objects['TB_山顶台基']], (W / 2 + 2, D / 2 + 2), skip=is_roof)
    save('tubi', boxes)


for s in ONLY:
    {'luxue': build_luxue, 'aojing': build_aojing, 'tubi': build_tubi}[s]()
