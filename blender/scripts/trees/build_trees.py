"""稻香村「桑、榆、槿、柘，编就两溜青篱」——用 Blender 程序化生成四种树，格式与 models/t 里现有精品树一致。

每个树种产出三样：
  tex/leaf_<sp>_c.png / _a.png   叶片卡（一段带叶小枝，Cycles 俯视正交渲染：颜色 + 透明度）
  models/t/<sp>_1.wasm           树模型（glb）：<sp>_bark 树皮管 + <sp>_leaf 叶片卡四边形，地面在 y=0，单位米
  tex/imp_<sp>1.png + imp.json   远景替身（侧视正交渲染，256×512）

用法：python3 blender/scripts/trees/build_trees.py [sang yu mujin zhe] [--preview]
  --preview：另在 /tmp 渲一张带天空的整树预览，便于检查形态。

依据（第十七回原文与植物形态）：
  桑 Morus alba      乔木，叶卵形、基部心形、粗锯齿，常有三裂叶，嫩绿有光泽
  榆 Ulmus pumila    乔木，早春先叶开花结实，枝上簇生一团团圆形翅果（榆钱），叶小椭圆、有锯齿
  槿 Hibiscus syriacus  灌木，多干丛生，叶菱状卵形、常三浅裂、缘有粗齿，深绿
  柘 Maclura tricuspidata 小乔木/灌木，枝有硬刺，叶卵形至倒卵形、全缘、偶三裂，深绿有光泽
"""
import bpy, bmesh, sys, os, json, math, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TEX = os.path.join(ROOT, 'tex')
OUT_T = os.path.join(ROOT, 'models', 't')
ARGS = [a for a in sys.argv[1:] if not a.startswith('--') and not a.endswith('.py')]
PREVIEW = '--preview' in sys.argv
ALL = ['sang', 'yu', 'mujin', 'zhe']
SPECIES = [a for a in ARGS if a in ALL] or ALL


# ---------------------------------------------------------------- 通用
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False
    sc.cycles.transparent_max_bounces = 256   # 叶卡层层叠叠，透明反弹不够会出黑块
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.62, 0.66, 0.70, 1); bg.inputs[1].default_value = 1.2
    return sc


def sun(rot, strength=3.2, color=(1, 0.97, 0.92)):
    d = bpy.data.lights.new('sun', 'SUN'); d.energy = strength; d.color = color; d.angle = math.radians(8)
    o = bpy.data.objects.new('sun', d); o.rotation_euler = rot; bpy.context.scene.collection.objects.link(o)


def mat_color_attr(name, rough=0.55, sss=0.0, bump=0.15, spec=0.4):
    """颜色来自顶点色属性 col；叶片加一点噪声凹凸当叶脉质感。"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    p = N['Principled BSDF']
    a = N.new('ShaderNodeVertexColor'); a.layer_name = 'col'
    L.new(a.outputs['Color'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = rough
    p.inputs['Specular IOR Level'].default_value = spec
    if sss:
        p.inputs['Subsurface Weight'].default_value = sss
    if bump:
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 140; nz.inputs['Detail'].default_value = 4
        b = N.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump
        L.new(nz.outputs['Fac'], b.inputs['Height']); L.new(b.outputs['Normal'], p.inputs['Normal'])
    return m


def mesh_obj(name, verts, faces, cols=None, mat=None):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    if cols is not None:
        ca = me.color_attributes.new('col', 'FLOAT_COLOR', 'POINT')
        for i, c in enumerate(cols): ca.data[i].color = (c[0], c[1], c[2], 1)
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    if mat: me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return o


def tube(path, radii, sides, verts, faces, cols=None, col=None, uvs=None, v0=0.0):
    """沿折线生成管子（平行移动标架）；返回终点的累计长度。"""
    n = len(path)
    t0 = (path[1] - path[0]).normalized()
    up = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nx = t0.cross(up).normalized()
    base = len(verts); acc = v0; prev_t = t0
    for i in range(n):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        if i:
            acc += (path[i] - path[i - 1]).length
            q = prev_t.rotation_difference(t); nx = q @ nx
        prev_t = t
        ny = t.cross(nx).normalized(); nx = ny.cross(t).normalized()
        for k in range(sides + 1):
            a = 2 * math.pi * k / sides
            verts.append(path[i] + radii[i] * (math.cos(a) * nx + math.sin(a) * ny))
            if cols is not None: cols.append(col)
            if uvs is not None: uvs.append((k / sides, acc * 0.45))
    for i in range(n - 1):
        for k in range(sides):
            a = base + i * (sides + 1) + k; b = a + sides + 1
            faces.append((a, a + 1, b + 1, b))
    return acc


# ---------------------------------------------------------------- 叶形
def sawtooth(x):
    return x - math.floor(x)


def leaf_profile(kind, rng):
    """返回 (宽度函数 w(t), 基部下垂 dy(t), 锯齿数, 齿深)。t: 0=叶基 1=叶尖，叶长 1。"""
    if kind == 'sang':
        lobed = rng.random() < 0.12
        def w(t):
            v = 0.40 * math.sin(math.pi * min(t, 0.999)) ** 0.75 * (1 - 0.30 * t)
            if lobed:
                v += 0.16 * math.exp(-((t - 0.42) / 0.09) ** 2) - 0.17 * math.exp(-((t - 0.6) / 0.06) ** 2)
            return max(v, 0.0)
        return w, (lambda t: -0.14 * math.sin(math.pi * min(t / 0.3, 1)) if t < 0.3 else 0.0), 18, 0.05
    if kind == 'mujin':
        def w(t):
            v = 0.30 * math.sin(math.pi * min(t, 0.999)) ** 0.9 * (1 - 0.15 * t)
            v += 0.14 * math.exp(-((t - 0.45) / 0.1) ** 2) - 0.10 * math.exp(-((t - 0.63) / 0.06) ** 2)
            return max(v, 0.0)
        return w, (lambda t: 0.0), 9, 0.05
    if kind == 'zhe':
        lobed = rng.random() < 0.15
        def w(t):
            v = 0.27 * math.sin(math.pi * min(t, 0.999)) ** 0.65 * (0.8 + 0.4 * t) * (1 - 0.25 * t ** 3)
            if lobed:
                v += 0.12 * math.exp(-((t - 0.55) / 0.08) ** 2)
            return max(v, 0.0)
        return w, (lambda t: 0.0), 0, 0.0
    if kind == 'yuleaf':
        return (lambda t: 0.26 * math.sin(math.pi * min(t, 0.999)) ** 0.8), (lambda t: 0.0), 12, 0.03
    if kind == 'samara':   # 榆钱：近圆形薄翅，顶端有一小缺口
        def w(t):
            v = 0.5 * math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2))
            if t > 0.9: v *= 0.75 + 2.5 * (t - 0.9)
            return v
        return w, (lambda t: 0.0), 0, 0.0
    raise ValueError(kind)


def add_leaf(V, F, C, kind, base, d, side, L, rng, col, fold=0.12, droop=0.15, rows=12):
    """在 base 处长一片叶：主脉沿 d（单位向量，大致在卡片平面），side 为叶面内的横向，L 叶长。"""
    w, dy, nteeth, tooth = leaf_profile(kind, rng)
    nrm = d.cross(side).normalized()
    if nrm.z < 0: nrm = -nrm
    idx0 = len(V); n = rows
    for i in range(n + 1):
        t = i / n
        ww = w(t)
        for s in (-1, 0, 1):
            x = s * ww
            if s and nteeth and 0.08 < t < 0.97:
                x += s * tooth * sawtooth(t * nteeth) * min(1, ww * 6)
            y = t + (dy(t) if s else 0.0)
            z = fold * abs(x) - droop * t * t
            p = base + L * (y * d + x * side + z * nrm)
            V.append(p)
            k = 1.0 + (0.12 if s == 0 else 0.0) - 0.08 * t
            C.append((col[0] * k, col[1] * k, col[2] * k))
    for i in range(n):
        a = idx0 + i * 3
        F.append((a, a + 1, a + 4, a + 3)); F.append((a + 1, a + 2, a + 5, a + 4))


def twig_card(sp):
    """在 XY 平面（卡片平面，枝基在 (0,0)，向 +Y 生长，宽 1 高 1）里摆一段带叶小枝，俯视渲染。"""
    sc = reset(); rng = random.Random({'sang': 11, 'yu': 23, 'mujin': 37, 'zhe': 41}[sp])
    leafm = mat_color_attr('leaf', rough={'sang': 0.42, 'zhe': 0.35}.get(sp, 0.55), sss=0.0, bump=0.12)
    barkm = mat_color_attr('twig', rough=0.8, bump=0.3, spec=0.2)
    TV, TF, TC = [], [], []
    LV, LF, LC = [], [], []
    twig_col = {'sang': (0.33, 0.27, 0.2), 'yu': (0.30, 0.24, 0.19), 'mujin': (0.36, 0.33, 0.26), 'zhe': (0.32, 0.25, 0.18)}[sp]

    def stem(p0, d0, length, r0, nseg=14, bend=0.0, zig=0.0):
        pts, rad = [], []; p = p0.copy(); d = d0.normalized()
        for i in range(nseg + 1):
            pts.append(p.copy()); rad.append(r0 * (1 - 0.7 * i / nseg))
            ang = bend / nseg + (zig * (1 if i % 2 else -1) if zig else 0) + rng.uniform(-0.06, 0.06)
            d = Matrix.Rotation(ang, 3, 'Z') @ d
            p = p + d * (length / nseg)
        tube(pts, rad, 6, TV, TF, TC, twig_col)
        return pts

    def green(base, var=0.06):
        return tuple(max(0, c * (1 + rng.uniform(-var, var))) for c in base)

    if sp in ('sang', 'mujin', 'zhe'):
        L = {'sang': 0.115, 'mujin': 0.085, 'zhe': 0.08}[sp]
        gcol = {'sang': (0.075, 0.19, 0.03), 'mujin': (0.045, 0.11, 0.025), 'zhe': (0.04, 0.095, 0.02)}[sp]
        main = stem(Vector((0, 0, 0)), Vector((0.05, 1, 0)), 0.92, 0.012, bend=0.25, zig=0.08 if sp == 'zhe' else 0)
        shoots = [main]
        for frac, ang, ln in [(0.18, 0.8, 0.4), (0.32, -0.75, 0.42), (0.46, 0.7, 0.38), (0.6, -0.7, 0.32), (0.74, 0.65, 0.24)]:
            i = int(frac * (len(main) - 1)); d = (main[i + 1] - main[i]).normalized()
            shoots.append(stem(main[i], Matrix.Rotation(ang, 3, 'Z') @ d, ln, 0.007, nseg=8, bend=-0.3 * math.copysign(1, ang),
                               zig=0.1 if sp == 'zhe' else 0))
        for si, pts in enumerate(shoots):
            nodes = 14 if si == 0 else 8
            for j in range(nodes):
                f = 0.12 + 0.86 * j / (nodes - 1) if si == 0 else 0.15 + 0.85 * j / (nodes - 1)
                i = min(int(f * (len(pts) - 1)), len(pts) - 2)
                p = pts[i]; d = (pts[i + 1] - pts[i]).normalized()
                sgn = 1 if j % 2 else -1
                ld = Matrix.Rotation(sgn * rng.uniform(0.6, 1.1), 3, 'Z') @ d
                ld = (ld + Vector((0, 0, rng.uniform(-0.25, 0.35)))).normalized()
                side = ld.cross(Vector((0, 0, 1))).normalized()
                side = Matrix.Rotation(rng.uniform(-0.35, 0.35), 3, ld) @ side
                pet = 0.035 if sp != 'zhe' else 0.02
                pb = p + ld * pet
                tube([p, pb], [0.0035, 0.003], 4, TV, TF, TC, (0.32, 0.42, 0.18))
                s = L * rng.uniform(0.75, 1.1) * (0.75 if si and j == nodes - 1 else 1)
                add_leaf(LV, LF, LC, sp, pb, ld, side, s, rng, green(gcol), fold=0.18, droop=rng.uniform(0.05, 0.25))
                if sp == 'zhe' and j % 2 == 0:   # 柘：节上硬刺
                    td = Matrix.Rotation(-sgn * 0.9, 3, 'Z') @ d
                    tube([p, p + td * 0.045], [0.004, 0.0004], 4, TV, TF, TC, (0.26, 0.2, 0.15))
            # 枝端嫩叶
            p = pts[-1]; d = (pts[-1] - pts[-2]).normalized()
            add_leaf(LV, LF, LC, sp, p, d, d.cross(Vector((0, 0, 1))).normalized(), L * 0.5, rng,
                     tuple(min(1, c * 1.35) for c in gcol), fold=0.3)
    else:   # 榆：枝上一团团榆钱 + 枝端几片小叶
        main = stem(Vector((0, 0, 0)), Vector((-0.04, 1, 0)), 0.9, 0.011, bend=-0.2)
        shoots = [main]
        for frac, ang, ln in [(0.25, 0.8, 0.4), (0.45, -0.85, 0.42), (0.65, 0.75, 0.32), (0.8, -0.7, 0.2)]:
            i = int(frac * (len(main) - 1)); d = (main[i + 1] - main[i]).normalized()
            shoots.append(stem(main[i], Matrix.Rotation(ang, 3, 'Z') @ d, ln, 0.006, nseg=8, bend=0.3 * math.copysign(1, ang)))
        for si, pts in enumerate(shoots):
            nodes = 8 if si == 0 else 4
            for j in range(nodes):
                f = 0.1 + 0.75 * j / (nodes - 1)
                i = min(int(f * (len(pts) - 1)), len(pts) - 2); c0 = pts[i]
                for k in range(rng.randint(9, 16)):   # 一簇榆钱
                    a = rng.uniform(0, 2 * math.pi); r = rng.uniform(0.004, 0.03)
                    p = c0 + Vector((math.cos(a) * r, math.sin(a) * r, rng.uniform(0, 0.02)))
                    dd = Vector((math.cos(a), math.sin(a), rng.uniform(-0.2, 0.9))).normalized()
                    side = dd.cross(Vector((0, 0, 1))).normalized()
                    if side.length < 0.1: side = Vector((1, 0, 0))
                    col = green((0.28, 0.36, 0.09), 0.1)
                    add_leaf(LV, LF, LC, 'samara', p, dd, side, rng.uniform(0.026, 0.036), rng, col, fold=0.05, droop=0.0, rows=6)
            p = pts[-1]; d = (pts[-1] - pts[-2]).normalized()
            for k, a in enumerate((-0.7, 0.0, 0.7)):
                ld = Matrix.Rotation(a, 3, 'Z') @ d
                add_leaf(LV, LF, LC, 'yuleaf', p, ld, ld.cross(Vector((0, 0, 1))).normalized(), 0.065 * (1.2 if k == 1 else 1), rng,
                         green((0.13, 0.27, 0.05)), fold=0.15)
    mesh_obj('twig', TV, TF, TC, barkm)
    mesh_obj('leaves', LV, LF, LC, leafm)
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; cam.ortho_scale = 1.0
    co = bpy.data.objects.new('c', cam); co.location = (0, 0.5, 3); sc.collection.objects.link(co); sc.camera = co
    bpy.context.scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.7
    sun((math.radians(28), math.radians(-18), 0), 1.8)
    sc.render.resolution_x = sc.render.resolution_y = 512
    raw = f'/tmp/leafcard_{sp}.png'; sc.render.filepath = raw
    bpy.ops.render.render(write_still=True)
    split_card(raw, os.path.join(TEX, f'leaf_{sp}_c.png'), os.path.join(TEX, f'leaf_{sp}_a.png'))


def read_png(path):
    im = bpy.data.images.load(path); w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4); bpy.data.images.remove(im); return a


def write_png(path, arr, mode):
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    if mode == 'BW': rgba[..., :3] = arr[..., None] if arr.ndim == 2 else arr[..., :1]
    else: rgba[..., :arr.shape[2]] = arr
    im = bpy.data.images.new('o', w, h, alpha=(mode == 'RGBA'))
    im.pixels = rgba.ravel()
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)


def bleed(rgb, a, it=24):
    """把不透明处的颜色向透明处扩散，避免 mipmap/alphaTest 时叶缘发黑。"""
    rgb = rgb.copy(); m = (a > 0.5).astype(np.float32)
    for _ in range(it):
        acc = np.zeros_like(rgb); cnt = np.zeros_like(m)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(rgb * m[..., None], dy, 0), dx, 1); cnt += np.roll(np.roll(m, dy, 0), dx, 1)
        new = (m == 0) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][..., None]; m = np.maximum(m, new.astype(np.float32))
    rgb[m == 0] = rgb[m > 0].mean(0) if (m > 0).any() else 0.2
    return rgb


def split_card(raw, cpath, apath):
    px = read_png(raw); a = px[..., 3]
    rgb = np.where(a[..., None] > 1e-3, px[..., :3] / np.maximum(a[..., None], 1e-3), 0)   # 反预乘
    rgb = bleed(np.clip(rgb, 0, 1), a)
    write_png(cpath, rgb, 'RGB'); write_png(apath, a, 'BW')
    print('card', os.path.basename(cpath))


# ---------------------------------------------------------------- 树
SPEC = {
    # H 树高；trunk 主干占比；r0 基径；kids 各级分枝数；ang 分枝角；card 叶卡边长；stems 丛生干数
    'sang':  dict(H=6.5, trunk=0.38, r0=0.11, kids=(6, 4, 3), ang=(52, 48, 40), lens=(0.62, 0.5, 0.4), gn=0.16, up=0.05,
                  card=1.3, cards=4, stems=1, crown_flat=0.85),
    'yu':    dict(H=9.0, trunk=0.4, r0=0.14, kids=(8, 5, 3), ang=(40, 52, 45), lens=(0.55, 0.5, 0.42), gn=0.12, up=0.0,
                  card=1.55, cards=4, stems=1, crown_flat=1.0, droop=0.05),
    'mujin': dict(H=2.6, trunk=0.04, r0=0.035, kids=(5, 3, 0), ang=(22, 38, 0), lens=(0.6, 0.45, 0), gn=0.1, up=0.08,
                  card=0.62, cards=3, stems=6, crown_flat=0.55),
    'zhe':   dict(H=3.8, trunk=0.2, r0=0.06, kids=(6, 4, 2), ang=(50, 55, 50), lens=(0.6, 0.5, 0.42), gn=0.2, up=0.04,
                  card=0.85, cards=3, stems=1, crown_flat=0.9),
}


def build_tree(sp, seed=1):
    S = SPEC[sp]; rng = random.Random(seed * 101 + len(sp))
    BV, BF, BU = [], [], []
    cards = []   # (pos, dir)
    levels = sum(1 for k in S['kids'] if k) + 1

    def grow(p0, d0, length, r, lvl):
        nseg = max(3, int(length / 0.35)) if lvl == 0 else max(3, int(length / 0.3))
        pts, rad = [p0.copy()], [r * (1.25 if lvl == 0 else 1)]
        p = p0.copy(); d = d0.normalized()
        for i in range(nseg):
            g = S['gn'] * (0.25 if lvl == 0 and S['stems'] == 1 else 1)   # 主干基本直立，枝条才弯曲
            d = (d + Vector((rng.gauss(0, g), rng.gauss(0, g), rng.gauss(0, g * 0.5) + (0.08 if lvl == 0 else S['up']) - S.get('droop', 0) * lvl))).normalized()
            p = p + d * (length / nseg); pts.append(p.copy())
            rad.append(r * (1 - 0.82 * (i + 1) / nseg) + 0.004)
        tube(pts, rad, [9, 6, 5, 4][min(lvl, 3)], BV, BF, uvs=BU)
        kids = S['kids'][lvl] if lvl < len(S['kids']) else 0
        if kids:
            start = S['trunk'] if lvl == 0 else 0.25
            for k in range(kids):
                f = start + (1 - start) * (k + 0.5) / kids * 0.92
                i = min(int(f * nseg), nseg - 1)
                pd = (pts[i + 1] - pts[i]).normalized()
                az = k * 2.39996 + rng.uniform(-0.4, 0.4)
                perp = pd.cross(Vector((0, 0, 1)) if abs(pd.z) < 0.95 else Vector((1, 0, 0))).normalized()
                perp = Quaternion(pd, az) @ perp
                ang = math.radians(S['ang'][lvl] * rng.uniform(0.8, 1.2))
                cd = (pd * math.cos(ang) + perp * math.sin(ang)).normalized()
                cd.z *= S['crown_flat']
                cl = length * S['lens'][lvl] * rng.uniform(0.8, 1.15) * (1.15 - 0.4 * f if lvl == 0 else 1)
                grow(pts[i], cd, cl, rad[i] * 0.62, lvl + 1)
        if lvl == levels - 1 or not kids:
            n = S['cards'] if lvl else 2
            for k in range(n):
                f = 0.35 + 0.65 * (k + 1) / n
                i = min(int(f * nseg), nseg - 1)
                cards.append((pts[i], (pts[min(i + 1, nseg)] - pts[i]).normalized()))
            cards.append((pts[-1], (pts[-1] - pts[-2]).normalized()))

    H = S['H']
    for s in range(S['stems']):
        if S['stems'] == 1:
            p0 = Vector((0, 0, 0)); d0 = Vector((rng.gauss(0, 0.04), rng.gauss(0, 0.04), 1))
        else:
            a = s * 2.39996 + rng.uniform(-0.3, 0.3); rr = rng.uniform(0.02, 0.14)
            p0 = Vector((math.cos(a) * rr, math.sin(a) * rr, 0))
            d0 = Vector((math.cos(a) * 0.32, math.sin(a) * 0.32, 1))
        L0 = H * (0.82 if S['stems'] == 1 else rng.uniform(0.7, 0.92))
        grow(p0 - Vector((0, 0, 0.05)), d0, L0, S['r0'], 0)

    # 叶卡：枝基在卡片下边中点，卡片竖向沿枝方向并带一点外翻；法线偏向树冠外侧，光照更柔
    LV, LF, LUV, LN = [], [], [], []
    cen = Vector((0, 0, 0)); [cen.__iadd__(p) for p, _ in cards]; cen /= max(1, len(cards))
    cen.z = max(cen.z, H * 0.55)
    for p, d in cards:
        out = (p - cen); out.z *= 0.6; out = out.normalized() if out.length > 1e-3 else Vector((0, 0, 1))
        up = (d * 0.55 + out * 0.45 + Vector((0, 0, 0.25))).normalized()
        roll = rng.uniform(0, math.pi)
        side = up.cross(Vector((0, 0, 1)) if abs(up.z) < 0.95 else Vector((1, 0, 0))).normalized()
        side = Quaternion(up, roll) @ side
        s = S['card'] * rng.uniform(0.85, 1.15)
        q = [p - side * s / 2, p + side * s / 2, p + side * s / 2 + up * s, p - side * s / 2 + up * s]
        b = len(LV); LV += q; LF.append((b, b + 1, b + 2, b + 3)); LUV += [(0, 0), (1, 0), (1, 1), (0, 1)]
        fn = side.cross(up).normalized()
        if fn.dot(out) < 0: fn = -fn
        nn = (fn * 0.35 + out * 0.65).normalized()
        LN += [nn] * 4

    bark = mesh_obj(f'{sp}_bark', BV, BF)
    uvl = bark.data.uv_layers.new(name='UV')
    for poly in bark.data.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = BU[bark.data.loops[li].vertex_index]
    leaf = mesh_obj(f'{sp}_leaf', LV, LF)
    uvl = leaf.data.uv_layers.new(name='UV')
    for poly in leaf.data.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = LUV[leaf.data.loops[li].vertex_index]
    leaf.data.normals_split_custom_set_from_vertices([tuple(n) for n in LN])
    print(sp, 'bark verts', len(BV), 'cards', len(cards))
    return bark, leaf


def tree_materials(sp, bark, leaf):
    bm = bpy.data.materials.new('bark'); bm.use_nodes = True; N = bm.node_tree.nodes; L = bm.node_tree.links
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, 'bark_c.jpg'))
    L.new(t.outputs['Color'], N['Principled BSDF'].inputs['Base Color']); N['Principled BSDF'].inputs['Roughness'].default_value = 0.9
    bark.data.materials.append(bm)
    lm = bpy.data.materials.new('leafcard'); lm.use_nodes = True; N = lm.node_tree.nodes; L = lm.node_tree.links
    c = N.new('ShaderNodeTexImage'); c.image = bpy.data.images.load(os.path.join(TEX, f'leaf_{sp}_c.png'))
    a = N.new('ShaderNodeTexImage'); a.image = bpy.data.images.load(os.path.join(TEX, f'leaf_{sp}_a.png')); a.image.colorspace_settings.name = 'Non-Color'
    p = N['Principled BSDF']; L.new(c.outputs['Color'], p.inputs['Base Color']); L.new(a.outputs['Color'], p.inputs['Alpha'])
    p.inputs['Roughness'].default_value = 0.6
    leaf.data.materials.append(lm)


def export_glb(sp, bark, leaf):
    for o in bpy.context.scene.objects: o.select_set(o in (bark, leaf))
    tmp = f'/tmp/{sp}_1.glb'
    bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB', use_selection=True, export_materials='NONE',
                              export_yup=True, export_texcoords=True, export_normals=True, export_apply=True)
    os.replace(tmp, os.path.join(OUT_T, f'{sp}_1.wasm'))
    print('model', f'models/t/{sp}_1.wasm', os.path.getsize(os.path.join(OUT_T, f'{sp}_1.wasm')) // 1024, 'KB')


def render_impostor(sp, bark, leaf):
    sc = bpy.context.scene
    # 现有替身都是平光的本色（光照交给网页），这里把材质换成自发光，只留一点点明暗
    for o in (bark, leaf):
        nt = o.data.materials[0].node_tree; N = nt.nodes; L = nt.links; p = N['Principled BSDF']
        em = N.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 0.82
        L.new(p.inputs['Base Color'].links[0].from_socket, em.inputs['Color'])
        out = N['Material Output']
        if o is leaf:
            tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
            L.new(p.inputs['Alpha'].links[0].from_socket, mx.inputs['Fac'])
            L.new(tr.outputs[0], mx.inputs[1]); L.new(em.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs['Surface'])
        else:
            L.new(em.outputs[0], out.inputs['Surface'])
    pts = [o.matrix_world @ v.co for o in (bark, leaf) for v in o.data.vertices]
    x0 = min(p.x for p in pts); x1 = max(p.x for p in pts); z1 = max(p.z for p in pts)
    y0 = min(p.y for p in pts); y1 = max(p.y for p in pts)
    zmin = -0.02; size = max(x1 - x0, y1 - y0, z1 - zmin) * 1.04
    cx = (x0 + x1) / 2
    cam = bpy.data.cameras.new('ic'); cam.type = 'ORTHO'; cam.ortho_scale = size
    co = bpy.data.objects.new('ic', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (cx, -50, zmin + size / 2); co.rotation_euler = (math.radians(90), 0, 0)
    sun((math.radians(55), 0, math.radians(-30)), 2.6)
    sc.render.resolution_x = sc.render.resolution_y = 512; sc.cycles.samples = 64
    raw = f'/tmp/imp_{sp}.png'; sc.render.filepath = raw
    sc.render.image_settings.color_mode = 'RGBA'
    bpy.ops.render.render(write_still=True)
    px = read_png(raw)[:, ::2]          # 横向压一半：256×512，与现有替身同规格（网页里按 x0..x1 拉回）
    a = px[..., 3:]; rgb = np.where(a > 1e-3, px[..., :3] / np.maximum(a, 1e-3), 0)
    rgb = bleed(np.clip(rgb, 0, 1), a[..., 0], it=6)
    write_png(os.path.join(TEX, f'imp_{sp}1.png'), np.concatenate([rgb, a], 2), 'RGBA')
    ip = os.path.join(TEX, 'imp.json'); J = json.load(open(ip))
    J[f'{sp}1'] = {'x0': round(cx - size / 2, 2), 'x1': round(cx + size / 2, 2), 'h': round(size, 2), 'zmin': zmin}
    json.dump(J, open(ip, 'w'), separators=(',', ':'))
    print('impostor', f'imp_{sp}1', J[f'{sp}1'])


def preview(sp):
    sc = bpy.context.scene; sc.render.film_transparent = False
    S = SPEC[sp]; H = S['H']
    cam = bpy.data.cameras.new('pv'); cam.lens = 35
    co = bpy.data.objects.new('pv', cam); sc.collection.objects.link(co); sc.camera = co
    co.location = (H * 1.3, -H * 1.6, H * 0.45); co.rotation_euler = (math.radians(88), 0, math.radians(39))
    bpy.ops.mesh.primitive_plane_add(size=H * 6)
    sc.render.resolution_x = 640; sc.render.resolution_y = 640; sc.cycles.samples = 32
    sc.render.filepath = f'/tmp/preview_{sp}.png'; bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(bpy.context.active_object); sc.render.film_transparent = True
    for o in [o for o in sc.objects if o.type == 'LIGHT']: bpy.data.objects.remove(o)


for sp in SPECIES:
    twig_card(sp)
    reset()
    bark, leaf = build_tree(sp)
    tree_materials(sp, bark, leaf)
    export_glb(sp, bark, leaf)
    if PREVIEW: preview(sp)
    render_impostor(sp, bark, leaf)
