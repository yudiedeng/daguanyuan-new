"""翠嶂（园门内障景假山）建模脚本。

第十七回：「开门只见一带翠嶂挡在前面……白石崚嶒，或如鬼怪，或如猛兽，纵横拱立，
上面苔藓成斑，藤萝掩映，其中微露羊肠小径。」「说着，进入石洞来。」

生成：太湖石峰群（竖向、孔窍、风化坑）、可穿行的石洞、上表面苔藓、垂挂藤萝、镜面白石。
坐标：网页局部坐标原点 = 翠嶂中心（网页世界 0, 地面, 96），网页 x→Blender X，网页 z→Blender -Y，网页 y→Blender Z。
输出：blender/cuizhang.blend 以及 models/b/col.json 的 cuizhang 碰撞框、cuizhang_trees 松树位置。

用法：python3 build_cuizhang.py <repo根目录>     （需要 pip install bpy）
"""
import bpy, bmesh, math, random, json, sys, os
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

REPO = sys.argv[-1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[-1]) else os.getcwd()
random.seed(17)

def B(x, y, z):  # 网页局部 (x, 上, z) -> Blender
    return Vector((x, -z, y))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def coll(name):
    c = bpy.data.collections.new(name); scene.collection.children.link(c); return c

C_ROCK, C_GREEN, C_STONE = coll('CZ_山石'), coll('CZ_藤苔'), coll('CZ_镜面白石')

def mat(name, rgb, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1); m.roughness = rough
    return m

M_ROCK = mat('M_太湖石', (0.62, 0.62, 0.58))
M_MOSS = mat('M_苔地', (0.36, 0.43, 0.23))
M_MARBLE = mat('M_汉白玉', (0.94, 0.93, 0.89), 0.5)
M_VINE = mat('M_藤', (0.35, 0.29, 0.2))
M_LEAF = mat('M_藤叶', (0.3, 0.48, 0.23), 0.7)

def link(o, c):
    for u in list(o.users_collection): u.objects.unlink(o)
    c.objects.link(o)

def apply_mods(o):
    bpy.context.view_layer.objects.active = o
    for m in list(o.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)

def ellipsoid(name, ctr, scale, rot=(0, 0, 0), sub=3, rough=0.0, seed=0.0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0)
    for v in bm.verts:
        p = v.co.copy()
        if rough:
            n = noise.fractal(p * 1.3 + Vector((seed, seed * 1.7, seed * 0.3)), 0.6, 2.2, 4)
            p *= 1 + rough * n
        v.co = p
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    o.scale = scale; o.rotation_euler = rot; o.location = ctr
    return o

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join(); o = bpy.context.view_layer.objects.active; o.name = name
    return o

def remesh(o, size):
    m = o.modifiers.new('rm', 'REMESH'); m.mode = 'VOXEL'; m.voxel_size = size; apply_mods(o)

def boolean(o, cutter, op='DIFFERENCE'):
    m = o.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.object = cutter; m.solver = 'MANIFOLD'
    apply_mods(o); bpy.data.objects.remove(cutter)

# ---------------------------------------------------------------- 峰群
HALF_X, HALF_Z = 19.0, 6.2
def profile(x):  # 中间高、两端低的山势
    return max(0.0, 1 - (abs(x) / (HALF_X + 3)) ** 1.6)

stones = []
for i in range(95):  # 主峰：瘦高竖向湖石（“瘦”），彼此倚靠
    x = random.uniform(-HALF_X + 1, HALF_X - 1); z = random.uniform(-HALF_Z + 1.4, HALF_Z - 1.4)
    h = (1.4 + 6.6 * profile(x)) * random.uniform(0.55, 1.08)
    w = random.uniform(0.7, 1.35)
    stones.append(ellipsoid('pk', B(x, h * 0.5 - 0.7, z), (w, w * random.uniform(0.6, 1.0), h * 0.6),
                            (random.uniform(-.22, .22), random.uniform(-.22, .22), random.uniform(0, 6.3)),
                            rough=0.55, seed=i * 3.1))
for i in range(55):  # 基座与过渡石（较扁）
    x = random.uniform(-HALF_X, HALF_X); z = random.uniform(-HALF_Z, HALF_Z)
    if abs(z) > HALF_Z * (0.55 + 0.45 * profile(x)): continue
    s = random.uniform(1.0, 2.2) * (0.5 + 0.6 * profile(x))
    stones.append(ellipsoid('bs', B(x, s * 0.2 - 0.4, z), (s * 1.2, s * 0.9, s * 0.65),
                            (0, 0, random.uniform(0, 6.3)), rough=0.5, seed=i * 7.3 + 100))
for i in range(30):  # 峰顶悬挑、斜出（“或如鬼怪，或如猛兽”）
    x = random.uniform(-12, 12); z = random.uniform(-3.5, 3.5)
    top = (1.4 + 6.6 * profile(x)) * 0.85
    stones.append(ellipsoid('ov', B(x, top + random.uniform(-0.8, 0.3), z),
                            (random.uniform(0.9, 1.7), random.uniform(0.45, 0.8), random.uniform(0.35, 0.65)),
                            (random.uniform(-.7, .7), random.uniform(-.7, .7), random.uniform(0, 6.3)),
                            rough=0.6, seed=i * 5.7 + 300))
rock = join(stones, 'CZ_湖石')
remesh(rock, 0.14)

# 竖向流水纹（湖石“皱”）：沿法线做纵向拉长的噪声位移
def streak_displace(o, amp):
    me = o.data; me.calc_loop_triangles() if hasattr(me, 'calc_loop_triangles') else None
    bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    for v in bm.verts:
        c = v.co
        n = noise.fractal(Vector((c.x * 0.75, c.y * 0.75, c.z * 0.16)), 0.65, 2.3, 4)
        g = noise.noise(Vector((c.x * 2.6, c.y * 2.6, c.z * 0.5)))
        v.co = c + v.normal * (amp * n + 0.12 * g)
    bm.to_mesh(me); bm.free()
streak_displace(rock, 0.5)
# 风化坑：Voronoi 位移（向内），形成湖石“漏、透”的蜂窝面
tex = bpy.data.textures.new('pits', 'VORONOI'); tex.noise_scale = 0.5; tex.distance_metric = 'DISTANCE'
d = rock.modifiers.new('pits', 'DISPLACE'); d.texture = tex; d.texture_coords = 'GLOBAL'; d.strength = -0.5; d.mid_level = 0.62
apply_mods(rock)
remesh(rock, 0.12)

# ---------------------------------------------------------------- 石洞（可穿行）
# 前口朝园门（网页 +z），弯曲穿到背面；净高约 2.5 m、净宽约 2.2 m。
path = [(-5.0, 8.5), (-5.6, 5.0), (-7.4, 2.2), (-8.6, -0.6), (-8.0, -3.4), (-9.4, -6.0), (-10.2, -9.0)]
def sample(pts, step=0.35):
    out = []
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, z1 - z0); n = max(1, int(L / step))
        out += [(x0 + (x1 - x0) * t / n, z0 + (z1 - z0) * t / n) for t in range(n)]
    return out + [pts[-1]]
cave = [ellipsoid('cv', B(x, 0.9, z), (1.15, 1.15, 1.75), sub=2, rough=0.12, seed=k) for k, (x, z) in enumerate(sample(path))]
cutter = join(cave, 'cave'); remesh(cutter, 0.12)
boolean(rock, cutter)
CAVE_PTS = sample(path, 0.25)

# ---------------------------------------------------------------- 孔窍（透）
holes = []
for i in range(34):
    x = random.uniform(-14, 14); top = (1.6 + 6.0 * profile(x)) * 0.85
    if top < 2.6: continue
    y = random.uniform(1.9, top - 0.4); z = random.uniform(-3.0, 3.0)
    r = random.uniform(0.28, 0.75)
    holes.append(ellipsoid('h', B(x, y, z), (r, r * random.uniform(0.8, 1.3), 3.6 * random.uniform(0.6, 1.0)),
                           (random.uniform(-.6, .6) + math.pi / 2, 0, random.uniform(-.8, .8)), sub=2, rough=0.2, seed=i))
if holes:
    hc = join(holes, 'holes'); remesh(hc, 0.1); boolean(rock, hc)

# 底部切平在地面下 0.8 m（网页地形填满洞底）
bpy.ops.mesh.primitive_cube_add(size=1, location=B(0, -5.8, 0)); cut = bpy.context.object; cut.scale = (60, 30, 10)
bpy.ops.object.transform_apply(scale=True); boolean(rock, cut)

# 苔藓：在减面前按面分配（边缘更细碎），朝上的面成斑
rock.data.materials.clear(); rock.data.materials.append(M_ROCK); rock.data.materials.append(M_MOSS)
for p in rock.data.polygons:
    c = p.center; up = p.normal.z
    patch = noise.noise(c * 0.6) + 0.5 * noise.noise(c * 2.1) + 0.25 * noise.noise(c * 6.0)
    p.material_index = 1 if (up > 0.55 and patch > -0.1) or (up > 0.88 and patch > -0.6) else 0
tris = sum(len(p.vertices) - 2 for p in rock.data.polygons)
dec = rock.modifiers.new('dec', 'DECIMATE'); dec.ratio = min(1.0, 110000 / tris); apply_mods(rock)
for p in rock.data.polygons: p.use_smooth = True
link(rock, C_ROCK)

# ---------------------------------------------------------------- 碰撞框 + 松树位置
dg = bpy.context.evaluated_depsgraph_get()
bvh = BVHTree.FromObject(rock, dg)
def top_at(x, z):
    hit = bvh.ray_cast(B(x, 30, z), Vector((0, 0, -1)), 40)
    return None if hit[0] is None else hit[0].z
def ceil_at(x, z):  # 从洞底往上第一处石面；若起点在石头里（命中面朝上）返回 'solid'
    hit = bvh.ray_cast(B(x, 0.05, z), Vector((0, 0, 1)), 30)
    if hit[0] is None: return None
    return 'solid' if hit[1].z > 0 else hit[0].z
cells = {}
STEP = 0.8
for ix in range(int(-(HALF_X + 4) / STEP), int((HALF_X + 4) / STEP) + 1):
    for iz in range(int(-(HALF_Z + 4) / STEP), int((HALF_Z + 4) / STEP) + 1):
        x, z = ix * STEP, iz * STEP
        t = top_at(x, z)
        if t is None or t < 0.35: continue
        c = ceil_at(x, z)
        bot = c if (c not in (None, 'solid') and c > 2.0) else -0.8   # 洞顶（高于 2 m）不挡人
        cells[(ix, iz)] = (round(t * 4) / 4, round(bot * 4) / 4)
boxes, used = [], set()
for (ix, iz), (t, b) in sorted(cells.items()):
    if (ix, iz) in used: continue
    j = ix
    while (j + 1, iz) in cells and cells[(j + 1, iz)] == (t, b) and (j + 1, iz) not in used and j - ix < 6: j += 1  # 每段≤5.6 m，免得被当成院墙（WALLSEG）
    for k in range(ix, j + 1): used.add((k, iz))
    cx = (ix + j) / 2 * STEP; hx = (j - ix + 1) * STEP / 2
    boxes.append([round(cx, 2), round(iz * STEP, 2), round(hx, 2), STEP / 2, t, b])
trees = []
for x, z in [(-11.5, -1.5), (4.0, -3.0), (12.5, 1.0), (-2.0, 2.4)]:
    t = top_at(x, z)
    if t: trees.append([x, z, round(t - 0.2, 2)])

# ---------------------------------------------------------------- 藤萝：从峰顶外沿垂下
vine_bm, leaf_bm = bmesh.new(), bmesh.new()
def leaf(bm, p, n, s):
    t = n.cross(Vector((0, 0, 1)));
    if t.length < 1e-3: t = Vector((1, 0, 0))
    t.normalize(); u = n.cross(t)
    a = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 0)).normalized() if random.random() < .5 else t
    vs = [bm.verts.new(p + n * 0.03 + (a * math.cos(k) + u * math.sin(k)) * s * (1 if k % math.pi else 0.35)) for k in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    bm.faces.new(vs)
made = 0
for _ in range(400):
    if made >= 26: break
    x = random.uniform(-13, 13); z = random.choice([-1, 1]) * random.uniform(2.5, 5.5)
    t = top_at(x, z)
    if not t or t < 2.5: continue
    # 沿外侧面往下贴着石面走
    p = B(x, t, z); out = Vector((0, -1 if z > 0 else 1, 0)) * -1
    pts = []
    for k in range(int(random.uniform(8, 16))):
        q = p + Vector((random.uniform(-.08, .08), 0, -0.22 * k))
        hit = bvh.ray_cast(q + out * 1.5, -out, 3.0)
        if hit[0] is None: break
        pts.append((hit[0] + hit[1] * 0.04, hit[1]))
    if len(pts) < 5: continue
    made += 1
    prev = None
    for (pp, nn) in pts:
        ring = [vine_bm.verts.new(pp + Vector((math.cos(a) * 0.025, math.sin(a) * 0.025, 0))) for a in (0, 2.1, 4.2)]
        if prev:
            for k in range(3): vine_bm.faces.new((prev[k], prev[(k + 1) % 3], ring[(k + 1) % 3], ring[k]))
        prev = ring
        for _ in range(3): leaf(leaf_bm, pp + Vector((random.uniform(-.15, .15), random.uniform(-.15, .15), random.uniform(-.1, .1))), nn, random.uniform(0.07, 0.13))
for nm, bm, m in (('CZ_藤萝_vine', vine_bm, M_VINE), ('CZ_藤萝_leaf', leaf_bm, M_LEAF)):
    me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free(); me.materials.append(m)
    o = bpy.data.objects.new(nm, me); C_GREEN.objects.link(o)

# ---------------------------------------------------------------- 镜面白石（宝玉题「曲径通幽」）
# 立在正面山脚前的一块白石，正面磨平作“镜面”，下垫一块卧石。
fx = 2.5
front = None
for zz in [k * 0.1 for k in range(90, -10, -1)]:   # 从正面往里找贴地石面
    hit = bvh.ray_cast(B(fx, 0.6, zz + 0.01), Vector((0, 1, 0)), 0.3)  # Blender +Y = 网页 -z
    if hit[0] is not None:
        front = -hit[0].y; break
front = (front if front is not None else 5.0) + 0.9
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:   # 不规则石板：四角高低错落，背面鼓出
    x, y, z = v.co
    v.co = Vector((x * 2.5 * (1 + 0.08 * noise.noise(v.co * 3)), y * (0.32 if y < 0 else 0.55), z * 1.6 + 0.12 * noise.noise(v.co * 5 + Vector((1, 2, 3)))))
me = bpy.data.meshes.new('CZ_镜面白石_匾底'); bm.to_mesh(me); bm.free()
mirror = bpy.data.objects.new('CZ_镜面白石_匾底', me); C_STONE.objects.link(mirror)
mirror.location = B(fx, 1.25, front); mirror.rotation_euler = (0, 0, math.radians(-4))
bev = mirror.modifiers.new('bev', 'BEVEL'); bev.width = 0.06; bev.segments = 2; apply_mods(mirror)
mirror.data.materials.append(M_MARBLE)
base = ellipsoid('CZ_镜面白石_卧石', B(fx, 0.15, front + 0.05), (1.9, 0.9, 0.5), (0, 0, 0.1), sub=3, rough=0.4, seed=77)
bpy.context.view_layer.objects.active = base; bpy.ops.object.select_all(action='DESELECT'); base.select_set(True)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
base.data.materials.append(M_ROCK); link(base, C_ROCK)
for p in base.data.polygons: p.use_smooth = True
# 白石也挡人
boxes.append([fx, round(front, 2), 1.3, 0.35, 2.05, -0.5])

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(REPO, 'blender', 'cuizhang.blend'), compress=True)

colp = os.path.join(REPO, 'models', 'b', 'col.json')
col = json.load(open(colp, encoding='utf-8'))
col['cuizhang'] = boxes; col['cuizhang_trees'] = trees
json.dump(col, open(colp, 'w', encoding='utf-8'), ensure_ascii=False)
print('CUIZHANG tris', sum(len(p.vertices) - 2 for p in rock.data.polygons), 'boxes', len(boxes), 'vines', made, 'front', round(front, 2), 'trees', trees)
