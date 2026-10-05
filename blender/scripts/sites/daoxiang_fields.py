"""稻香村菜畦重做：「下面分畦列亩，佳蔬菜花，漫然无际」。

原模型里的菜畦是四块方方正正的「沙盘」：一圈凸起的硬边框，里面是光滑等宽的长条垄，作物是两种十字插片。
这里改为：
  1. 垄沟：垄面宽窄、高低、走向都略有起伏，土块颗粒、垄头参差、边缘缓缓落进地面，不再有硬边框。
     → models/b/daoxiang_tian.wasm（材质 M_田土，网页里沿用「田土」贴图），与 daoxiang 同一原点。
     原模型里的旧垄和边框用 tools/glb_cut.mjs 剪掉（命令见 blender/README.md）。
  2. 作物：三维小株，不再是插片——油菜（开黄花，即「菜花」）、青菜、葱，各有几种变体，顶点色上色。
     → models/p/crops.glb（节点 youcai_0.. / qingcai_0.. / cong_0..，地面在 y=0，单位米）
  3. 每一株的位置（顺着弯曲的垄）→ tex/crops_daoxiang.json，网页 buildCrops() 读来实例化。

用法：python3 blender/scripts/sites/daoxiang_fields.py [--preview]
坐标：Blender 坐标（Z 向上），即 daoxiang.blend 的局部坐标；网页里 x=X，z=−Y。
"""
import bpy, bmesh, sys, os, json, math, random
from mathutils import Vector, Matrix, Quaternion, noise

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
PREVIEW = '--preview' in sys.argv

# 四块菜畦（与原模型 菜畦_*_soil 同一范围）。al：垄的走向（沿 X 还是沿 Y）；crop：种什么
PLOTS = [
    dict(name='西南', x=(-26.0, -8.2), y=(-22.3, -9.0), al='x', crop=['youcai']),
    dict(name='南中', x=(-1.2, 11.5), y=(-22.3, -5.2), al='y', crop=['qingcai']),
    dict(name='东南', x=(12.5, 26.0), y=(-22.3, -5.2), al='y', crop=['cong', 'qingcai']),
    dict(name='东',   x=(16.5, 26.0), y=(-3.8, 9.4),   al='x', crop=['youcai']),
]
PITCH = 1.5          # 垄距
RIDGE_H = 0.22       # 垄高（垄面比沟底高）
BASE = 0.05          # 沟底高出原地面
CELL = 0.12          # 网格边长


def wob(k, u, seed):
    """第 k 条垄的中线在 u 处的横向偏移——让垄走得不那么笔直。"""
    return 0.11 * math.sin(0.42 * u + 1.7 * k + seed) + 0.05 * math.sin(1.37 * u + 0.9 * k + 2 * seed)


def plot_frame(P):
    """返回 (u0,u1, v0,v1, to_xy)：u 沿垄，v 横跨垄。"""
    if P['al'] == 'x':
        return P['x'][0], P['x'][1], P['y'][0], P['y'][1], (lambda u, v: (u, v))
    return P['y'][0], P['y'][1], P['x'][0], P['x'][1], (lambda u, v: (v, u))


def ridges(P):
    u0, u1, v0, v1, _ = plot_frame(P)
    n = int((v1 - v0 - 0.6) // PITCH)
    off = (v1 - v0 - (n - 1) * PITCH) / 2      # 居中
    return [v0 + off + k * PITCH for k in range(n)]


def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


def height(P, pi, u, v):
    u0, u1, v0, v1, _ = plot_frame(P)
    rng = random.Random(pi * 97)
    cs = ridges(P)
    # 离菜畦边缘的距离（向外为负），边线本身用噪声抖一抖
    edge = min(u - u0, u1 - u, v - v0, v1 - v) + 0.18 * noise.noise(Vector((u * 0.5, v * 0.5, pi * 3.1)))
    if edge < -0.85: return None
    h = BASE * sstep(-0.5, 0.0, edge)
    # 垄
    best = 0.0
    for k, c in enumerate(cs):
        d = abs(v - (c + wob(k, u, pi)))
        if d > 0.8: continue
        endu = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(k * 2.1 + pi))   # 垄头参差
        endv = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(k * 1.3 + pi * 2))
        taper = sstep(u0 + endu - 0.3, u0 + endu + 0.25, u) * sstep(u1 - endv + 0.3, u1 - endv - 0.25, u)
        hh = 0.85 + 0.15 * noise.noise(Vector((u * 0.35, k * 1.7, pi)))  # 垄高有起伏
        prof = sstep(0.6, 0.36, d)         # 垄面圆鼓，沟窄而陡
        best = max(best, RIDGE_H * hh * prof * taper)
    h += best * sstep(-0.1, 0.25, edge)
    # 土块：两层噪声
    q = Vector((u * 3.2, v * 3.2, pi * 7.0))
    h += 0.018 * noise.noise(q) + 0.008 * noise.noise(q * 3.1)
    h -= 0.03 * sstep(0.0, -0.5, edge)     # 外缘略低于原地面，好让地面把接缝盖住
    return h


def build_soil(P, pi):
    u0, u1, v0, v1, to_xy = plot_frame(P)
    M = 0.85   # 比原菜畦外扩：剪掉旧边框时连带剪掉的地面三角形要盖住
    nu = int((u1 - u0 + 2 * M) / CELL) + 1; nv = int((v1 - v0 + 2 * M) / CELL) + 1
    V, F, idx = [], [], {}
    for i in range(nu):
        for j in range(nv):
            u = u0 - M + i * CELL; v = v0 - M + j * CELL
            h = height(P, pi, u, v)
            if h is None: continue
            idx[i, j] = len(V); x, y = to_xy(u, v); V.append((x, y, h))
    for i in range(nu - 1):
        for j in range(nv - 1):
            q = [idx.get((i, j)), idx.get((i + 1, j)), idx.get((i + 1, j + 1)), idx.get((i, j + 1))]
            if None in q: continue
            F.append(tuple(q) if P['al'] == 'x' else tuple(reversed(q)))
    me = bpy.data.meshes.new('菜畦_' + P['name'] + '_soil'); me.from_pydata(V, [], F); me.update()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(o)
    return o


# ---------------------------------------------------------------- 作物
def lin(c):   # sRGB → 线性（glTF 顶点色是线性的）
    return tuple((x / 12.92) if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


class Mesh:
    def __init__(s): s.V, s.F, s.C = [], [], []

    def tube(s, pts, r0, r1, sides, col):
        n = len(pts); b = len(s.V)
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            a = t.orthogonal().normalized(); bb = t.cross(a)
            r = r0 + (r1 - r0) * i / (n - 1)
            for k in range(sides):
                th = 2 * math.pi * k / sides
                s.V.append(p + r * (math.cos(th) * a + math.sin(th) * bb)); s.C.append(col)
        for i in range(n - 1):
            for k in range(sides):
                a0 = b + i * sides + k; a1 = b + i * sides + (k + 1) % sides
                s.F.append((a0, a1, a1 + sides, a0 + sides))

    def leaf(s, base, d, side, L, W, prof, col, col_mid=None, fold=0.25, curl=0.0, rows=5):
        nrm = d.cross(side).normalized(); b = len(s.V)
        for i in range(rows + 1):
            t = i / rows; w = W * prof(t)
            # 叶片沿长度向下弯（curl），并沿主脉对折一点（fold）
            dd = (d * math.cos(curl * t) - nrm * math.sin(curl * t)).normalized()
            p = base + d * (L * t) - nrm * (L * curl * t * t * 0.5)
            for sgn in (-1, 0, 1):
                s.V.append(p + side * (sgn * w) + nrm * (fold * abs(sgn) * w))
                s.C.append(col_mid if (sgn == 0 and col_mid) else col)
        for i in range(rows):
            a = b + i * 3
            s.F.append((a, a + 1, a + 4, a + 3)); s.F.append((a + 1, a + 2, a + 5, a + 4))

    def star(s, c, nrm, r, col, k=4):
        """一朵小花：k 瓣的扁平星形。"""
        a = nrm.orthogonal().normalized(); bb = nrm.cross(a); b = len(s.V)
        s.V.append(c + nrm * 0.002); s.C.append(col)
        for i in range(2 * k):
            th = math.pi * i / k; rr = r if i % 2 == 0 else r * 0.7
            s.V.append(c + rr * (math.cos(th) * a + math.sin(th) * bb)); s.C.append(col)
        for i in range(2 * k):
            s.F.append((b, b + 1 + i, b + 1 + (i + 1) % (2 * k)))

    def obj(s, name):
        me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in s.V], [], s.F); me.update()
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        for i, c in enumerate(s.C): ca.data[i].color = (*c, 1)
        for p in me.polygons: p.use_smooth = True
        o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o


def jit(c, r, a=0.08):
    return tuple(max(0, x * (1 + r.uniform(-a, a))) for x in c)


LEAF_DARK = lin((0.24, 0.40, 0.20)); LEAF_BLUE = lin((0.30, 0.45, 0.30))
YELLOW = lin((0.98, 0.80, 0.10)); BUD = lin((0.62, 0.70, 0.20)); STEM = lin((0.36, 0.52, 0.24))


def youcai(seed):
    """油菜：抽薹开花。一根主茎、上部几根分枝，枝顶总状花序一团黄花，下部几片抱茎叶。约 0.8–1.0 m。"""
    r = random.Random(seed); m = Mesh()
    H = r.uniform(0.8, 1.0)
    lean = Vector((r.uniform(-0.08, 0.08), r.uniform(-0.08, 0.08), 1)).normalized()
    pts = [Vector((0, 0, 0)) + lean * (H * i / 5) + Vector((0.02 * math.sin(i + seed), 0, 0)) for i in range(6)]
    m.tube(pts, 0.009, 0.004, 4, jit(STEM, r))
    tips = [(pts[-1], (pts[-1] - pts[-2]).normalized(), 1.0)]
    for b in range(r.randint(2, 4)):
        f = r.uniform(0.5, 0.8); p0 = pts[0].lerp(pts[-1], f)
        az = b * 2.4 + r.uniform(-0.4, 0.4); d = Vector((math.cos(az) * 0.5, math.sin(az) * 0.5, 1)).normalized()
        L = H * (1 - f) * r.uniform(0.7, 1.0); p1 = p0 + d * L * 0.5 + Vector((0, 0, L * 0.1)); p2 = p0 + d * L + Vector((0, 0, L * 0.25))
        m.tube([p0, p1, p2], 0.005, 0.003, 4, jit(STEM, r)); tips.append((p2, (p2 - p1).normalized(), 0.75))
    for (p, d, sc) in tips:   # 花序：下部开花、顶上绿蕾
        n = int(26 * sc)
        for i in range(n):
            t = i / n; az = i * 2.4
            c = p - d * (0.08 * sc) * (1 - t) ** 1.5 + Vector((math.cos(az), math.sin(az), 0)) * (0.04 * math.sqrt(1 - t) + 0.006)
            if t > 0.86: m.star(c, (d + Vector((math.cos(az), math.sin(az), 0)) * 0.6).normalized(), 0.007, BUD, 3)
            else: m.star(c, (d * 0.8 + Vector((math.cos(az), math.sin(az), 0))).normalized(), r.uniform(0.01, 0.013), jit(YELLOW, r, 0.05), 2)   # 一朵花四个三角形，远看就是一点黄
    for i in range(r.randint(5, 7)):   # 叶：下大上小，长椭圆，抱茎
        f = 0.05 + 0.5 * i / 7; p = pts[0].lerp(pts[-1], f); az = i * 2.4 + r.uniform(-0.3, 0.3)
        d = Vector((math.cos(az), math.sin(az), r.uniform(0.3, 0.8))).normalized(); side = d.cross(Vector((0, 0, 1))).normalized()
        L = (0.26 - 0.3 * f) * r.uniform(0.85, 1.15)
        m.leaf(p, d, side, L, L * 0.28, lambda t: math.sin(math.pi * min(t, 0.98)) ** 0.7, jit(LEAF_BLUE, r), fold=0.3, curl=0.9)
    return m


def qingcai(seed):
    """青菜（小白菜）：莲座状，白绿色宽叶柄、深绿匙形叶片，约 0.2–0.28 m。"""
    r = random.Random(seed); m = Mesh(); n = r.randint(8, 11)
    PET = lin((0.80, 0.86, 0.66)); BL = lin((0.17, 0.33, 0.12))
    for i in range(n):
        az = i * 2.4 + r.uniform(-0.2, 0.2); inner = i / n
        tilt = 0.12 + 0.75 * (1 - inner) * r.uniform(0.8, 1.1)   # 外层叶更外翻，内层直立
        d = Vector((math.cos(az) * math.sin(tilt), math.sin(az) * math.sin(tilt), math.cos(tilt))).normalized()
        side = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < 0.99 else Vector((1, 0, 0))
        L = r.uniform(0.17, 0.25) * (0.75 + 0.25 * (1 - inner))
        prof = lambda t: (0.13 + 0.05 * t) if t < 0.42 else 0.3 * math.sin(math.pi * min(0.999, 0.5 + (t - 0.42) / 1.16)) ** 0.6 + 0.06
        m.leaf(Vector((0, 0, 0.01)), d, side, L, L, prof, jit(BL, r), col_mid=jit(lin((0.42, 0.58, 0.30)), r), fold=-0.25, curl=-0.35 * (1 - inner), rows=6)
        # 叶柄段改成白绿色
        for k in range(len(m.V) - 21, len(m.V) - 12): m.C[k] = jit(PET, r, 0.04)
    return m


def cong(seed):
    """葱：一丛六七根中空管状叶，略弯，约 0.35–0.5 m。"""
    r = random.Random(seed); m = Mesh(); G = lin((0.36, 0.55, 0.30)); W = lin((0.85, 0.88, 0.78))
    for i in range(r.randint(6, 8)):
        az = r.uniform(0, 2 * math.pi); L = r.uniform(0.32, 0.5); bend = r.uniform(0.05, 0.35)
        d = Vector((math.cos(az) * bend, math.sin(az) * bend, 1)).normalized()
        base = Vector((math.cos(az) * 0.01, math.sin(az) * 0.01, 0))
        pts = [base + d * (L * t / 4) + Vector((math.cos(az), math.sin(az), 0)) * (bend * 0.25 * L * (t / 4) ** 2) for t in range(5)]
        m.tube(pts[:2], 0.006, 0.006, 4, jit(W, r, 0.03)); m.tube(pts[1:], 0.006, 0.0015, 4, jit(G, r))
    return m


CROPS = {'youcai': (youcai, 3), 'qingcai': (qingcai, 3), 'cong': (cong, 2)}
SPACE = {'youcai': (0.3, 2), 'qingcai': (0.30, 2), 'cong': (0.16, 2)}    # 株距, 每垄几行


def place(P, pi):
    """沿垄排株；偶有缺苗。返回 [kind, variant, x, y, z, rot, scale]（Blender 坐标）。"""
    u0, u1, v0, v1, to_xy = plot_frame(P); r = random.Random(500 + pi); out = []
    for k, c in enumerate(ridges(P)):
        kind = P['crop'][k % len(P['crop'])]
        sp, lines = SPACE[kind]
        endu = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(k * 2.1 + pi)); endv = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(k * 1.3 + pi * 2))
        for ln in range(lines):
            dv = 0 if lines == 1 else (ln - 0.5) * 0.36
            u = u0 + endu + 0.25 + r.uniform(0, sp)
            while u < u1 - endv - 0.25:
                if r.random() > 0.06:
                    v = c + wob(k, u, pi) + dv + r.uniform(-0.04, 0.04)
                    x, y = to_xy(u + r.uniform(-0.04, 0.04), v)
                    h = height(P, pi, u, v) or 0.0
                    out.append([kind, r.randrange(CROPS[kind][1]), round(x, 3), round(y, 3), round(h - 0.01, 3),
                                round(r.uniform(0, 6.283), 2), round(r.uniform(0.85, 1.15), 2)])
                u += sp * r.uniform(0.85, 1.15)
    return out


# ---------------------------------------------------------------- 主流程
def export(objs, path, colors):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_yup=True,
              export_texcoords=False, export_normals=True)
    if colors:
        kw.update(export_vertex_color='ACTIVE', export_all_vertex_colors=False)
    kw['export_materials'] = 'NONE' if colors else 'EXPORT'
    bpy.ops.export_scene.gltf(**kw)


bpy.ops.wm.read_factory_settings(use_empty=True)
# 1 垄沟
soil_mat = bpy.data.materials.new('M_田土')
soils = []
for pi, P in enumerate(PLOTS):
    o = build_soil(P, pi); o.data.materials.append(soil_mat); soils.append(o)
    print('soil', P['name'], len(o.data.vertices))
raw = '/tmp/daoxiang_tian.glb'; export(soils, raw, False)
# 2 作物模型
bpy.ops.wm.read_factory_settings(use_empty=True)
objs = []
for kind, (fn, nv) in CROPS.items():
    for v in range(nv):
        o = fn(v * 31 + len(kind)).obj(f'{kind}_{v}'); objs.append(o)
        print('crop', o.name, len(o.data.polygons), 'faces')
export(objs, os.path.join(ROOT, 'models', 'p', 'crops.glb'), True)
# 3 株位
items = []
for pi, P in enumerate(PLOTS): items += place(P, pi)
json.dump({'fields': 'blender/scripts/sites/daoxiang_fields.py', 'items': items},
          open(os.path.join(ROOT, 'tex', 'crops_daoxiang.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
from collections import Counter
print('plants', len(items), Counter(i[0] for i in items))
print('NEXT: node blender/scripts/web/pack_glb.mjs', raw, 'models/b/daoxiang_tian.wasm')

if PREVIEW:
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    for i, o in enumerate(objs):
        o.location = ((i % 4) * 0.9 - 1.35, (i // 4) * 1.0, 0)
        mt = bpy.data.materials.new('vc'); mt.use_nodes = True; N = mt.node_tree.nodes
        a = N.new('ShaderNodeVertexColor'); a.layer_name = 'Col'; mt.node_tree.links.new(a.outputs[0], N['Principled BSDF'].inputs['Base Color'])
        o.data.materials.append(mt)
    d = bpy.data.lights.new('s', 'SUN'); d.energy = 3; so = bpy.data.objects.new('s', d); so.rotation_euler = (0.7, 0.2, 0.5); sc.collection.objects.link(so)
    cam = bpy.data.cameras.new('c'); cam.lens = 40; co = bpy.data.objects.new('c', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (0.0, -3.4, 1.6); co.rotation_euler = (math.radians(66), 0, 0)
    sc.render.resolution_x = 900; sc.render.resolution_y = 600; sc.render.filepath = '/tmp/crops_preview.png'
    bpy.ops.render.render(write_still=True)
