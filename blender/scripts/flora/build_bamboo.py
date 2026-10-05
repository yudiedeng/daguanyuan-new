"""竹（潇湘馆一带的“千百竿翠竹”）：Blender 建模，导出六株竹 models/t/zhu_<n>.wasm（弯度、根部斜出各不同） 和叶簇贴图 tex/zhu_spray.png。
用法：python3 blender/scripts/flora/build_bamboo.py --out /tmp/zhu      （需要 bpy；之后的打包见文末）

一、叶簇贴图：先在 Blender 里真把两枝竹叶簇建出来（一根下垂的小枝，两侧互生、梢头成扇，每簇约 35 片细长披针形叶，
    叶长 12–19 cm、宽 2.2–3.2 cm，深浅黄绿不一），用 Cycles 正交俯拍成透明底贴图（左右两半各一簇）。
二、竹株（约 10 m 高，网页按需要的高度缩放）：
    竹竿：上细下粗、顶上略弯，节间下短上长，每节一道竹节环；贴竹竿贴图（节环、节下白粉、竖纹），v 按节计；
    枝：生在约三成高以上的节上，左右交替，先斜上再下垂；
    叶：每根枝上挂三四簇“叶簇片”（两片十字交叉的四边形，贴上面的叶簇贴图），竿梢再一簇。
材质：zhu_culm（竿、枝）、zhu_leaf（叶簇片，网页里贴 tex/zhu_spray.png、alphaTest）。坐标：Blender Z 向上。
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector

OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/zhu'
os.makedirs(OUT, exist_ok=True)
SW, SH = 0.6, 0.45          # 一簇叶簇片的尺寸（米）：沿小枝 0.6，横向 0.45


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*col, 1)
    return m


def emit_mat(name, col):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*col, 1)
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def tube(bm, pts, radii, sides):
    """沿折线 pts 生成一根管（无端盖）。"""
    rings = []
    for i, p in enumerate(pts):
        a = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        t = a.normalized()
        ref = Vector((1, 0, 0)) if abs(t.x) < 0.9 else Vector((0, 1, 0))
        u = t.cross(ref).normalized()
        v = t.cross(u)
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            ring.append(bm.verts.new(p + (u * math.cos(th) + v * math.sin(th)) * radii[i]))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for k in range(sides):
            bm.faces.new((rings[i][k], rings[i][(k + 1) % sides], rings[i + 1][(k + 1) % sides], rings[i + 1][k]))


# ---------------- 一、叶簇贴图 ----------------
def leaf_outline(bm, base, ang, L, W):
    """平放在 XY 面上的一片披针形叶（叶柄在 base，朝 ang 方向）。"""
    d = Vector((math.cos(ang), math.sin(ang), 0))
    s = Vector((-math.sin(ang), math.cos(ang), 0))
    prof = [(0.0, 0.0), (0.08, 0.55), (0.25, 0.95), (0.45, 1.0), (0.65, 0.8), (0.82, 0.48), (0.94, 0.18), (1.0, 0.0)]
    left = [bm.verts.new(base + d * (L * f) + s * (W * 0.5 * w)) for f, w in prof]
    right = [bm.verts.new(base + d * (L * f) - s * (W * 0.5 * w)) for f, w in prof[1:-1]]
    ring = left + right[::-1]
    bm.faces.new(ring)


def spray_texture(path):
    clear()
    sc = bpy.context.scene
    greens = [(0.20, 0.34, 0.09), (0.27, 0.42, 0.12), (0.34, 0.48, 0.15), (0.42, 0.53, 0.18), (0.50, 0.56, 0.22), (0.16, 0.28, 0.08)]
    mats = [emit_mat('g%d' % i, c) for i, c in enumerate(greens)]
    twig = emit_mat('twig', (0.33, 0.36, 0.18))
    for half, seed in ((0, 5), (1, 9)):
        rnd = random.Random(seed)
        ox = half * SW
        bm = bmesh.new()
        tw = bmesh.new()
        # 小枝：从左端伸到 0.41，梢头叶扇不超出本半边（0.6）
        pts = [Vector((ox + 0.02 + 0.39 * t, 0.02 * math.sin(t * 3 + seed), 0)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
        tube(tw, pts, [0.004, 0.0035, 0.003, 0.0025, 0.002], 4)
        n_leaf = 0
        for k, t in enumerate((0.1, 0.18, 0.26, 0.34, 0.42, 0.5, 0.58, 0.66, 0.74, 0.82, 0.9)):
            p = pts[0] + (pts[-1] - pts[0]) * t
            for sgn in (1, -1):
                if rnd.random() < 0.1:
                    continue
                for extra in range(1 + (rnd.random() < 0.5)):
                    ang = sgn * rnd.uniform(0.45, 1.15) * (1 - 0.3 * t) + rnd.uniform(-0.15, 0.15)
                    leaf_outline(bm, p, ang, rnd.uniform(0.12, 0.19), rnd.uniform(0.022, 0.032))
                n_leaf += 1
        tip = pts[-1]
        for k in range(6):                                   # 梢头一扇
            ang = (k - 2.5) * 0.34 + rnd.uniform(-0.1, 0.1)
            leaf_outline(bm, tip, ang, rnd.uniform(0.12, 0.16), rnd.uniform(0.022, 0.03))
        me = bpy.data.meshes.new('spray%d' % half)
        bm.to_mesh(me); bm.free()
        for m in mats:
            me.materials.append(m)
        for i, poly in enumerate(me.polygons):
            poly.material_index = random.Random(seed * 100 + i).randrange(len(mats))
        o = bpy.data.objects.new('spray%d' % half, me)
        sc.collection.objects.link(o)
        me2 = bpy.data.meshes.new('twig%d' % half)
        tw.to_mesh(me2); tw.free()
        me2.materials.append(twig)
        sc.collection.objects.link(bpy.data.objects.new('twig%d' % half, me2))
    cam = bpy.data.cameras.new('cam')
    cam.type = 'ORTHO'
    cam.ortho_scale = 2 * SW
    co = bpy.data.objects.new('cam', cam)
    co.location = (SW, 0, 2)
    sc.collection.objects.link(co)
    sc.camera = co
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 16
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = 1024, 384
    sc.render.pixel_aspect_x = sc.render.pixel_aspect_y = 1
    sc.view_settings.view_transform = 'Standard'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('spray', path)


# ---------------- 竹竿贴图 ----------------
def culm_texture(path):
    """一节竹竿的贴图（v=0 是竹节，往上到下一节）：节处一道深色节环、节下一圈白粉、竖向细纤维纹、零星斑，越往上略黄。"""
    import numpy as np
    W, Hh = 128, 512
    r = np.random.default_rng(7)
    u = np.linspace(0, 1, W, endpoint=False)[None, :]
    v = np.linspace(0, 1, Hh)[:, None]
    base = np.array([0.30, 0.43, 0.17])
    fib = (np.sin(u * 2 * np.pi * 9 + r.uniform(0, 6)) * 0.5 + np.sin(u * 2 * np.pi * 23 + 1.3) * 0.3)
    fib = fib + r.normal(0, 0.35, (1, W))
    col = base[None, None, :] * (1 + 0.06 * fib[..., None])
    col = col * (1 + 0.1 * v[..., None]) + np.array([0.03, 0.02, -0.01]) * v[..., None]    # 越往上略黄
    blot = r.random((Hh // 64 + 1, W)).repeat(64, 0)[:Hh]                                   # 竖向的浅斑
    blot = np.convolve(blot.mean(0), np.ones(5) / 5, 'same')[None, :] * 0.5 + blot * 0.5
    col *= (1 - 0.07 * np.clip((blot - 0.6) * 3, 0, 1))[..., None]
    wax = np.exp(-((v - 0.07) / 0.05) ** 2)                                                # 节下白粉
    col = col * (1 - 0.45 * wax[..., None]) + np.array([0.62, 0.66, 0.58]) * 0.45 * wax[..., None]
    ring = np.exp(-((v - 0.012) / 0.008) ** 2) + np.exp(-((v - 0.995) / 0.006) ** 2)       # 节环
    col = col * (1 - 0.6 * np.clip(ring, 0, 1)[..., None]) + np.array([0.15, 0.17, 0.08]) * 0.6 * np.clip(ring, 0, 1)[..., None]
    img = bpy.data.images.new('culm', W, Hh)
    px = np.concatenate([np.clip(col, 0, 1), np.ones((Hh, W, 1))], axis=2)
    img.pixels = px.ravel().tolist()
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    print('culm', path)


def culm_tube(bm, uv, axis, nodes, rad, sides=6):
    """竹竿：每节一段，UV 的 v 按节计（第 i 节 i…i+1），u 绕一圈。"""
    rings = []
    for i in range(len(nodes) - 1):
        z0, z1 = nodes[i], nodes[i + 1]
        for zz, k in ((z0, 1.0), (z0 + 0.02, 1.1), ((z0 + z1) / 2, 0.98)):
            rings.append((axis(zz), rad(zz) * k, i + (zz - z0) / (z1 - z0)))
    rings.append((axis(nodes[-1]), 0.004, len(nodes) - 1))
    vs = []
    for p, r, v in rings:
        ring = [bm.verts.new(p + Vector((math.cos(2 * math.pi * k / sides), math.sin(2 * math.pi * k / sides), 0)) * r) for k in range(sides)]
        vs.append((ring, v))
    for (ra, va), (rb, vb) in zip(vs, vs[1:]):
        for k in range(sides):
            f = bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k]))
            for loop, (uu, vv) in zip(f.loops, ((k, va), (k + 1, va), (k + 1, vb), (k, vb))):
                loop[uv].uv = (uu / sides, vv)


# ---------------- 二、竹株 ----------------
def spray_card(bm, uv, base, d, droop, size, half):
    """叶簇片：两片十字交叉的四边形，从 base 沿 d 伸出、向下垂 droop；UV 取贴图左/右半。"""
    d = d.normalized()
    side = Vector((-d.y, d.x, 0)).normalized()
    fwd = (d + Vector((0, 0, -droop))).normalized()
    down = fwd.cross(side).normalized()
    L, W = SW * size, SH * size
    u0 = 0.5 * half
    for wv in (side, (side * 0.35 + down).normalized()):
        a = base + wv * (W * 0.5)
        b = base - wv * (W * 0.5)
        c = b + fwd * L
        e = a + fwd * L
        f = bm.faces.new((bm.verts.new(a), bm.verts.new(b), bm.verts.new(c), bm.verts.new(e)))
        for loop, (uu, vv) in zip(f.loops, ((0, 1), (0, 0), (1, 0), (1, 1))):
            loop[uv].uv = (u0 + 0.5 * uu, vv)


def bamboo(seed, H, bend=0.35, sbase=0.0):
    rnd = random.Random(seed)
    culm = bmesh.new()
    cuv = culm.loops.layers.uv.new('UVMap')
    lv = bmesh.new()
    uv = lv.loops.layers.uv.new('UVMap')
    nodes = [0.0]
    z = 0.0
    while z < H:
        f = z / H
        z += 0.18 + 0.32 * min(1.0, f * 2.2) * rnd.uniform(0.85, 1.15)
        nodes.append(min(z, H))
    lean = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)).normalized()
    def axis(z):
        f = z / H   # 梢头弯 bend（米/10 m），根部斜出 sbase（先往外斜、再直起来）
        return Vector((0, 0, z)) + lean * (bend * f ** 2.2 * H / 10 + sbase * min(f, 0.25) * 4 * H / 10)
    def rad(z):
        return 0.026 * (1 - 0.7 * z / H) + 0.005
    culm_tube(culm, cuv, axis, nodes, rad)
    side = rnd.uniform(0, 2 * math.pi)
    for z0 in nodes[1:-1]:
        f = z0 / H
        if f < 0.28:
            continue
        side += math.pi + rnd.uniform(-0.5, 0.5)
        for b in range(2 if f < 0.95 else 1):
            az = side + rnd.uniform(-0.45, 0.45) + b * rnd.uniform(0.5, 0.9)
            out = Vector((math.cos(az), math.sin(az), 0))
            Lb = (0.35 + 1.0 * math.sin(math.pi * min(1.0, (f - 0.28) / 0.72 * 0.85 + 0.15))) * rnd.uniform(0.75, 1.15) * H / 10
            up = rnd.uniform(0.55, 0.95)
            bp = [axis(z0) + out * (Lb * t) + Vector((0, 0, Lb * (up * t - 0.55 * t * t))) for t in (0, 1 / 3, 2 / 3, 1)]
            n0 = len(culm.faces)
            tube(culm, bp, [0.006, 0.0045, 0.003, 0.002], 3)
            culm.faces.ensure_lookup_table()
            for fi in range(n0, len(culm.faces)):
                for loop in culm.faces[fi].loops:
                    loop[cuv].uv = (0.5, 0.5)            # 枝：取贴图节间中部的绿
            for k, t in enumerate((0.25, 0.5, 0.75, 1.0) if Lb > 0.6 else (0.5, 1.0)):
                p = bp[0] + (bp[-1] - bp[0]) * t
                a2 = az + rnd.uniform(-0.9, 0.9)
                d = Vector((math.cos(a2), math.sin(a2), 0))
                spray_card(lv, uv, p, d, rnd.uniform(0.6, 1.3), rnd.uniform(0.75, 1.1), rnd.randrange(2))
    top = axis(H)
    for k in range(3):
        a = rnd.uniform(0, 2 * math.pi)
        spray_card(lv, uv, top - Vector((0, 0, 0.15 * k)), Vector((math.cos(a), math.sin(a), 0)), 0.9, 0.8, k % 2)
    return culm, lv


def leaf_mat(png, name='zhu_leaf'):
    """贴图材质（不贴的话导出后 UV 会被打包时当成无用属性删掉）。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes['Principled BSDF']
    im = nt.nodes.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(png)
    nt.links.new(im.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(im.outputs['Alpha'], bs.inputs['Alpha'])
    return m


def obj(name, bm, m):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    me.materials.append(m)
    return o


spray_texture(os.path.join(OUT, 'zhu_spray.png'))
culm_texture(os.path.join(OUT, 'zhu_culm.png'))
VARS = ((11, 10.0, 0.35, 0.0), (23, 10.6, 0.6, 0.15), (37, 9.4, 0.9, 0.0), (51, 8.5, 0.5, 0.25), (67, 11.2, 0.25, 0.1), (83, 9.8, 1.1, 0.2))
for n, (seed, H, bend, sbase) in enumerate(VARS, 1):
    clear()
    c, l = bamboo(seed, H, bend, sbase)
    obj('zhu_culm', c, leaf_mat(os.path.join(OUT, 'zhu_culm.png'), 'zhu_culm'))
    obj('zhu_leaf', l, leaf_mat(os.path.join(OUT, 'zhu_spray.png')))
    tris = sum(len(p.vertices) - 2 for o in bpy.data.objects for p in o.data.polygons)
    path = os.path.join(OUT, 'zhu_%d.glb' % n)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=True, export_texcoords=True, export_materials='EXPORT')
    print('zhu_%d' % n, 'H', H, 'tris', tris, path)

# 打包到网页（保留 UV、不减面；pack_prop 会把高度归一成 1 m，网页里按竹高缩放）：
#   node blender/scripts/web/pack_prop.mjs /tmp/zhu/zhu_1.glb models/t/zhu_1.wasm 99999   （2–6 同）
#   cp /tmp/zhu/zhu_spray.png /tmp/zhu/zhu_culm.png tex/
