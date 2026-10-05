"""蓼汀花溆的港洞（第十七回“忽闻水声潺湲，泻出石洞，上则萝薄垂引，下则落花浮荡”）。

整块山石用有向距离场（SDF）雕出来，再用 marching cubes 取面、Blender 减面：
  两岸石墩 + 洞顶横梁 + 峰顶几块立石，平滑相融；中间掏出可过船的拱洞（宽约 6.4 m、水面上高约 3 m）；
  再掏十几个穿透的孔窍（太湖石的“玲珑”），表面加两层噪声起伏。
藤萝的路径也在这里算：从石顶朝上的面出发，每下 0.15 m 把点吸回石面（离石 4 cm）；遇到洞顶下面这类朝下的面就离开石面直垂。

输出：
  models/b/huaxu.wasm    —— 港洞模型（局部坐标：原点在洞心水面，溪流顺 z 方向；材质 M_HW_玲珑石，网页三向贴石纹）
  models/b/hx_vines.json —— 藤萝路径 {D:[[dx,dz,x0,y0,z0,x1,y1,z1…]…]}（同 hw_vines.json 的 D），由 blender/scripts/web/hw_plants.py 烘成 models/b/hx_vines.wasm
用法：python3 blender/scripts/sites/huaxu_cave.py   （需要 pip install bpy scikit-image）
"""
import json, math, os, subprocess
import numpy as np
from skimage.measure import marching_cubes

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TMP = os.environ.get('TMPDIR', '/tmp')
rng = np.random.default_rng(1818)

# ---------------------------------------------------------------- 噪声（值噪声 + fbm，向量化）
LAT = rng.random((64, 64, 64)).astype(np.float32)
def vnoise(P):
    f = np.floor(P); t = P - f; t = t * t * (3 - 2 * t); i = f.astype(np.int64) & 63
    def L(dx, dy, dz): return LAT[(i[:, 0] + dx) & 63, (i[:, 1] + dy) & 63, (i[:, 2] + dz) & 63]
    x0 = L(0, 0, 0) * (1 - t[:, 0]) + L(1, 0, 0) * t[:, 0]; x1 = L(0, 1, 0) * (1 - t[:, 0]) + L(1, 1, 0) * t[:, 0]
    x2 = L(0, 0, 1) * (1 - t[:, 0]) + L(1, 0, 1) * t[:, 0]; x3 = L(0, 1, 1) * (1 - t[:, 0]) + L(1, 1, 1) * t[:, 0]
    y0 = x0 * (1 - t[:, 1]) + x1 * t[:, 1]; y1 = x2 * (1 - t[:, 1]) + x3 * t[:, 1]
    return (y0 * (1 - t[:, 2]) + y1 * t[:, 2]) * 2 - 1
def fbm(P, o=4):
    s, a, f = 0, 0.5, 1.0
    for _ in range(o): s = s + a * vnoise(P * f + 17.3 * f); a *= 0.5; f *= 2.03
    return s

# ---------------------------------------------------------------- 距离场
def sd_rbox(P, c, h, r):
    q = np.abs(P - c) - (np.array(h) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(axis=1), 0) - r
def sd_ell(P, c, r):
    q = (P - c) / r; k0 = np.linalg.norm(q, axis=1); k1 = np.linalg.norm(q / r, axis=1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-6)
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)
def smax(a, b, k): return -smin(-a, -b, k)

PEAKS = [((-3.2, 5.4, -1.0), (1.7, 1.9, 1.5)), ((2.4, 6.0, 0.6), (1.5, 2.3, 1.3)), ((5.6, 5.1, -1.6), (1.4, 1.6, 1.3)),
         ((-6.4, 4.6, 1.6), (1.6, 1.6, 1.5)), ((-0.6, 5.0, 2.0), (1.3, 1.3, 1.1)), ((7.2, 4.0, 1.8), (1.3, 1.5, 1.2))]
FLANK = [((-4.6, 0.2, -4.3), (1.1, 1.4, 1.0)), ((4.5, 0.0, -4.5), (1.0, 1.2, 0.9)), ((-4.8, 0.0, 4.4), (1.0, 1.1, 0.9)), ((4.7, 0.3, 4.3), (1.2, 1.5, 1.0))]
HOLES = []
for _ in range(16):   # 孔窍：多数顺 z 或 x 穿透，少数斜着
    c = np.array([rng.uniform(-8, 8), rng.uniform(2.8, 6.4), rng.uniform(-3.2, 3.2)])
    if abs(c[0]) < 3.6 and c[1] < 3.4: continue
    ax = rng.choice(3, p=[0.35, 0.15, 0.5]); r = np.full(3, rng.uniform(0.28, 0.75)); r[ax] *= rng.uniform(3, 6)
    HOLES.append((c, r))
def sdf(P):
    d = sd_rbox(P, np.array([-6.3, 1.0, 0]), (2.7, 3.0, 4.0), 1.2)
    d = smin(d, sd_rbox(P, np.array([6.3, 1.0, 0]), (2.7, 3.0, 4.0), 1.2), 0.8)
    d = smin(d, sd_rbox(P, np.array([0, 4.1, 0]), (8.4, 1.05, 3.7), 0.9), 1.0)
    for c, r in PEAKS: d = smin(d, sd_ell(P, np.array(c), np.array(r)), 0.9)
    for c, r in FLANK: d = smin(d, sd_ell(P, np.array(c), np.array(r)), 0.6)
    # 拱洞：下部方、上部半椭圆，顺 z 贯通
    ax = np.abs(P[:, 0]); y = P[:, 1]
    arch = np.where(y < 1.7, ax - 3.2, np.sqrt((ax / 3.2) ** 2 + ((y - 1.7) / 1.35) ** 2) * 1.6 - 1.6)
    arch = np.maximum(arch, -(y + 3.0))
    d = smax(d, -arch, 0.5)
    for c, r in HOLES: d = smax(d, -sd_ell(P, c, r), 0.35)
    d = d + 0.32 * fbm(P * 0.55) + 0.1 * fbm(P * 2.1, 3)
    return d

# ---------------------------------------------------------------- 取面
S = 0.12; xs = np.arange(-10.5, 10.5, S); ys = np.arange(-2.2, 9.0, S); zs = np.arange(-6.2, 6.2, S)
G = np.stack(np.meshgrid(xs, ys, zs, indexing='ij'), -1).reshape(-1, 3).astype(np.float32)
D = np.concatenate([sdf(G[i:i + 400000]) for i in range(0, len(G), 400000)]).reshape(len(xs), len(ys), len(zs))
D[:, 0, :] = 1  # 底面封口（埋在河床下）
verts, faces, _, _ = marching_cubes(D, 0.0, spacing=(S, S, S))
verts += np.array([xs[0], ys[0], zs[0]])
print('marching cubes', len(verts), len(faces))

# ---------------------------------------------------------------- 藤萝路径
def grad(P, e=0.03):
    g = np.zeros_like(P)
    for k in range(3):
        o = np.zeros(3); o[k] = e; g[:, k] = (sdf(P + o) - sdf(P - o)) / (2 * e)
    n = np.linalg.norm(g, axis=1, keepdims=True); return g / np.maximum(n, 1e-6)
# 挂点：石顶、石肩（法向朝上）且在 2.4 m 以上
fc = verts[faces].mean(axis=1); fn = np.cross(verts[faces[:, 1]] - verts[faces[:, 0]], verts[faces[:, 2]] - verts[faces[:, 0]])
fa = np.linalg.norm(fn, axis=1); fn = fn / np.maximum(fa[:, None], 1e-9)
cand = np.where((fn[:, 1] > 0.3) & (fc[:, 1] > 2.4))[0]; rng.shuffle(cand)
anchors = []
for i in cand:
    p = fc[i]
    if all(np.linalg.norm(p - a) > 0.38 for a in anchors): anchors.append(p)
    if len(anchors) >= 260: break
# 洞口檐下再加一排：沿两个洞口的拱顶外沿
for sz in (-1, 1):
    for x in np.arange(-5.6, 5.7, 0.3):
        p = np.array([x + rng.uniform(-.1, .1), 5.2, sz * 4.6])
        for _ in range(40):   # 从上往下找到石面
            if sdf(p[None])[0] < 0.05: break
            p = p - np.array([0, 0.1, 0])
        if p[1] > 2.2: anchors.append(p + np.array([0, 0, sz * 0.05]))
D_out = []
for a in anchors:
    p = np.array(a, dtype=np.float64); g = grad(p[None])[0]; h = np.array([g[0], 0, g[2]]); hl = np.linalg.norm(h)
    h = h / hl if hl > 0.1 else np.array([math.cos(rng.uniform(0, 6.28)), 0, math.sin(rng.uniform(0, 6.28))])
    L = rng.uniform(1.2, 4.5); pts = [p.copy()]; tot = 0; free = False
    while tot < L and p[1] > 0.25:
        q = p + np.array([0, -0.15, 0]) + np.array([-h[2], 0, h[0]]) * rng.uniform(-0.03, 0.03)
        if not free:
            for _ in range(3):
                d = sdf(q[None])[0]; gq = grad(q[None])[0]
                if gq[1] < -0.35 and d > -0.02: free = True; break      # 到了朝下的面（洞顶下、石檐下）：离开石面直垂
                q = q - gq * (d - 0.04)
            if not free:
                hh = np.array([gq[0], 0, gq[2]]); n = np.linalg.norm(hh)
                if n > 0.2: h = hh / n
        if free and sdf(q[None])[0] < 0.03: break                         # 直垂又碰到石头就停
        tot += np.linalg.norm(q - p); p = q; pts.append(p.copy())
    if len(pts) >= 3: D_out.append([round(float(h[0]), 2), round(float(h[2]), 2)] + [round(float(v), 2) for pt in pts for v in pt])
json.dump({'D': D_out}, open(os.path.join(ROOT, 'models', 'b', 'hx_vines.json'), 'w'))
print('vines', len(D_out), 'pts', sum((len(d) - 2) // 3 for d in D_out))

# ---------------------------------------------------------------- 建网格、减面、导出
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('HX_港洞')
me.from_pydata([(float(x), float(-z), float(y)) for x, y, z in verts], [], [(int(c), int(b), int(a)) for a, b, c in faces]); me.update()
ob = bpy.data.objects.new('HX_港洞', me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new('M_HW_玲珑石'); me.materials.append(mat)
bpy.context.view_layer.objects.active = ob; ob.select_set(True)
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False); bpy.ops.object.mode_set(mode='OBJECT')
md = ob.modifiers.new('dec', 'DECIMATE'); md.ratio = 70000 / len(faces)
bpy.ops.object.modifier_apply(modifier='dec')
for p in me.polygons: p.use_smooth = True
print('decimated tris', sum(len(p.vertices) - 2 for p in me.polygons))
dst = os.path.join(TMP, 'huaxu.glb')
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True, export_image_format='NONE', export_materials='EXPORT', export_yup=True)
subprocess.run(['node', os.path.join(ROOT, 'blender', 'scripts', 'web', 'pack_glb.mjs'), dst, os.path.join(ROOT, 'models', 'b', 'huaxu.wasm')], check=True, cwd=os.path.join(ROOT, 'blender', 'scripts', 'web'))
