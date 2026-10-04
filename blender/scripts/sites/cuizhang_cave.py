"""翠嶂凿石洞「曲径通幽」（在 blender/cuizhang.blend 上就地修改，可重复执行）。
第十七回：贾政进园门，迎面翠嶂，山上镜面白石；「说着，进入石洞来。只见佳木茏葱，奇花闪灼，
一带清流，从花木深处曲折泻于石隙之下」。

用法（仓库根目录）：
  flock /tmp/coljson.lock python3 blender/scripts/sites/cuizhang_cave.py
  cd blender/scripts/web && python3 export_glb.py ../../cuizhang.blend /tmp/cz.glb \
      && node pack_glb.mjs /tmp/cz.glb ../../../models/b/cuizhang.wasm ../../../models/b/cuizhang.wasm

做法：
  1. 第一次运行时把 CZ_湖石 / CZ_藤萝_vine / CZ_藤萝_leaf 的原网格另存为 *__原（fake user，不导出）；
     以后每次都从原网格重来，所以可重复执行。
  2. 沿一条轻微 S 形的中心线 PATH（网页局部 x,z，从南口到北口）扫掠一个不规则拱形截面作切刀，
     EXACT 布尔把 CZ_湖石 凿穿（切刀底到地下 0.9 m，网页地形填洞底）。
  3. 内衬 CZ_石洞_衬（M_太湖石）：比切刀大 3 cm 的闭合厚壳（内壁面朝洞内、外壁面朝外、两端封口），
     石块之间的缝、山腹里原有的天井处由它封住，从洞里看不到天空、模型背面。
     洞底 CZ_石洞_地（M_苔地），局部高 FLOOR_Y。
  4. 挡路的藤萝叶、藤蔓剪掉。
  5. 重新生成 col.json['cuizhang']（0.2 m 格，跳过藤萝/洞底；洞道附近按「点在石头里」精确判定，
     其余照旧「上方有石就挡」）。洞里不出任何碰撞框（地坪就是地形）。
坐标：Blender X = 网页局部 x，Blender Y = −网页局部 z，Blender Z = 高。园门在南（网页 +z）。
"""
import bpy, bmesh, math, os, json
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', 'cuizhang.blend'))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))

# 洞中心线（网页局部 x, z），从南（园门）到北（沁芳溪）。南口在镜面白石西侧，先西偏、再折回东北出洞。
PATH = [(-0.9, 9.6), (-0.9, 7.2), (-1.35, 5.0), (-2.45, 3.0), (-2.7, 1.2), (-2.05, -0.5),
        (-1.05, -2.0), (-0.55, -3.6), (-0.5, -5.5), (-0.5, -9.6)]
W = 0.80          # 洞半宽基数（洞壁再向外随机 0–0.22 m）→ 洞宽 1.6–2.0，均约 1.75
VS, H = 1.45, 1.2  # 拱脚高、拱高 → 拱顶约 2.6–2.9 m（随机 −0.05…+0.31）
FLOOR_Y = 0.08    # 洞底（网页局部 y）
STEP = 0.25       # 扫掠步长

bpy.ops.wm.open_mainfile(filepath=SRC)
O, ME, MA = bpy.data.objects, bpy.data.meshes, bpy.data.materials
col_rock = bpy.data.collections['CZ_山石']

# ---- 复位到原网格（可重复执行） ----
for o in [o for o in O if o.name.startswith('CZ_石洞_')]:
    bpy.data.objects.remove(o, do_unlink=True)
for nm in ('CZ_湖石', 'CZ_藤萝_vine', 'CZ_藤萝_leaf'):
    o = O[nm]; key = nm + '__原'
    if ME.get(key) is None:
        m = o.data.copy(); m.name = key; m.use_fake_user = True
    else:
        old = o.data; o.data = ME[key].copy(); o.data.name = nm
        if old.users == 0: ME.remove(old)
for m in [m for m in ME if m.users == 0 and not m.use_fake_user]:
    ME.remove(m)


def B(x, y, z):
    return Vector((x, -z, y))


# ---------------------------------------------------------------- 中心线
def catmull(pts, step):
    P = [Vector((x, -z, 0)) for x, z in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(40):
            t = k / 40
            dense.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    dense.append(P[-2])
    out, acc = [dense[0]], 0.0           # 等距重采样
    for a, b in zip(dense, dense[1:]):
        acc += (b - a).length
        if acc >= step: out.append(b); acc = 0.0
    if (out[-1] - dense[-1]).length > step * 0.4: out.append(dense[-1])
    else: out[-1] = dense[-1]
    return out

CEN = catmull(PATH, STEP)
UP = Vector((0, 0, 1))
TAN = []
for i in range(len(CEN)):
    a, b = CEN[max(0, i - 1)], CEN[min(len(CEN) - 1, i + 1)]
    TAN.append((b - a).normalized())
LAT = [t.cross(UP).normalized() for t in TAN]   # 洞的右手侧（沿前进方向）


def nz(p, f=1.0, seed=0.0):
    q = p * f + Vector((seed, seed * 0.7, seed * 1.3))
    return max(-1.0, min(1.0, 0.75 * noise.noise(q) + 0.45 * noise.noise(q * 2.7 + Vector((5.1, 1.3, 2.2)))))


WALL_V = [0.3, 0.75, 1.15]
NARCH = 16

def profile(i, vb, off, outer=0.0):
    """第 i 站截面：从左墙底 → 拱 → 右墙底的点列（世界坐标）。off：在不规则面基础上再外扩；
    outer>0：外壳额外的起伏量。"""
    c, n = CEN[i], LAT[i]
    pts2 = [(-1, v) for v in [vb] + WALL_V + [VS]]
    pts2 += [(math.cos(math.pi * (1 - k / NARCH)), None, k) for k in range(1, NARCH)]
    pts2 += [(1, v) for v in [VS] + WALL_V[::-1] + [vb]]
    out = []
    for e in pts2:
        if e[1] is None:                      # 拱
            th = math.pi * (1 - e[2] / NARCH)
            u, v = W * math.cos(th), VS + H * math.sin(th)
            dn = Vector((math.cos(th) / W, math.sin(th) / H)).normalized()
        else:
            u, v = e[0] * W, e[1]; dn = Vector((e[0], 0.0))
        base = c + n * u + UP * max(v, 0.0)
        r = nz(base, 1.1); bump = max(0.0, nz(base, 2.6, 3.3))   # 低频起伏 + 高频凸凹（只向外）
        if e[1] is not None and v <= VS:
            d = 0.07 + 0.07 * r + 0.08 * bump          # 洞壁只向外：0–0.22
        else:
            d = 0.05 + 0.10 * r + 0.16 * bump          # 拱：−0.05…+0.31（拱顶 2.6 m 以上，参差）
        d += off
        if outer: d += outer * (0.6 + 0.4 * nz(base, 0.7, 9.0)) * (0.4 + 0.6 * max(0.0, dn.y))
        out.append(c + n * (u + dn.x * d) + UP * (v + dn.y * d))
    return out


def sweep(rings, name, mat, closed_ring=True, cap=True, smooth=True):
    bm = bmesh.new()
    R = [[bm.verts.new(p) for p in ring] for ring in rings]
    m = len(R[0])
    for a, b in zip(R, R[1:]):
        for k in range(m if closed_ring else m - 1):
            k2 = (k + 1) % m
            bm.faces.new((a[k], a[k2], b[k2], b[k]))
    if cap:
        for r in (R[0], R[-1]):
            bm.faces.new(r)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = ME.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = smooth
    o = O.new(name, me); col_rock.objects.link(o); me.materials.append(MA[mat])
    return o


# ---------------------------------------------------------------- 原岩 BVH（找洞口）
rock = O['CZ_湖石']
def bvh_of(objs):
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world)
        tm = ME.new('_tmp'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); ME.remove(tm)
    b = BVHTree.FromBMesh(bm); bm.free(); return b

bvh0 = bvh_of([rock])
covered = [bvh0.ray_cast(c + UP * 1.6, UP, 12)[0] is not None for c in CEN]   # 1.6 m 以上有石＝进了山（北麓矮苔坡不算）
ia = covered.index(True); ib = len(CEN) - 1 - covered[::-1].index(True)
# 洞口：内衬从上方见石处再往里 1 站开始（洞口边缘由布尔面收口）
ia, ib = ia + 1, ib - 1
print('stations', len(CEN), 'lining', ia, ib, 'south portal z', round(-CEN[ia].y, 2), 'north portal z', round(-CEN[ib].y, 2))

# ---------------------------------------------------------------- 1. 布尔凿洞
cutter = sweep([profile(i, -0.9, 0.0) for i in range(len(CEN))], 'CZ_石洞_cutter', 'M_太湖石')
md = rock.modifiers.new('cave', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.object = cutter
md.solver = 'EXACT'; md.material_mode = 'TRANSFER'; md.use_hole_tolerant = True
bpy.context.view_layer.objects.active = rock
bpy.ops.object.modifier_apply(modifier='cave')
bpy.data.objects.remove(cutter, do_unlink=True)
# 切出来的洞壁：材质一律太湖石（切面落在苔地上的也改回石）
mi = [m.name for m in rock.data.materials].index('M_太湖石')
bm = bmesh.new(); bm.from_mesh(rock.data)
def in_tube(p, pad=0.0, vmax=None):
    """点是否落在洞道（中心线附近 W+0.22+pad、高到拱顶+pad）"""
    best, bi = 1e9, 0
    for i, c in enumerate(CEN):
        d = (Vector((p.x, p.y, 0)) - c).length_squared
        if d < best: best, bi = d, i
    q = Vector((p.x, p.y, 0)) - CEN[bi]
    if abs(q.dot(TAN[bi])) > STEP: return False          # 超出两端
    u = abs(q.dot(LAT[bi])); z = p.z
    top = vmax if vmax is not None else VS + H + 0.31 + pad
    if z > top or z < -1.0: return False
    if z <= VS: return u <= W + 0.22 + pad
    t = (z - VS) / (H + 0.31 + pad)
    return u <= (W + 0.22 + pad) * math.sqrt(max(0.0, 1 - t * t))
n_m = 0
for f in bm.faces:
    if f.material_index != mi and in_tube(f.calc_center_median(), 0.03):
        f.material_index = mi; n_m += 1
bm.to_mesh(rock.data); bm.free()
print('cut faces re-material', n_m, 'rock faces', len(rock.data.polygons))

# ---------------------------------------------------------------- 2. 内衬厚壳 + 洞底
inner = [profile(i, -0.1, 0.03) for i in range(ia, ib + 1)]
def taper(i):        # 两头 4 站内外壳收薄，洞口不留一圈粗边
    k = min(i - ia, ib - i) / 4.0
    return 0.15 + 0.85 * min(1.0, k) ** 2
outer = [profile(i, -0.1, 0.04 + 0.26 * taper(i), outer=0.35 * taper(i)) for i in range(ia, ib + 1)]
rings = [a + b[::-1] for a, b in zip(inner, outer)]      # 闭合 U 形截面：内壁（左→右）+ 外壁（右→左）
bm = bmesh.new()
R = [[bm.verts.new(p) for p in r] for r in rings]
m = len(R[0]); half = len(inner[0])
for a, b in zip(R, R[1:]):
    for k in range(m):
        k2 = (k + 1) % m
        bm.faces.new((a[k], a[k2], b[k2], b[k]))
for r in (R[0], R[-1]):                                   # 两端封口：内外壁之间逐段四边形
    for k in range(half - 1):
        bm.faces.new((r[k], r[k + 1], r[m - 2 - k], r[m - 1 - k]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# 检查：内壁面法线应朝洞内（指向中心线）
me = ME.new('CZ_石洞_衬'); bm.to_mesh(me); bm.free()
lining = O.new('CZ_石洞_衬', me); col_rock.objects.link(lining); me.materials.append(MA['M_太湖石']); me.materials.append(MA['M_苔地'])
for p in me.polygons:   # 外壳露天朝上的面同山体一样长苔（与 build_cuizhang.py 同一套斑块噪声）
    p.use_smooth = True; c = p.center
    patch = noise.noise(c * 0.6) + 0.5 * noise.noise(c * 2.1) + 0.25 * noise.noise(c * 6.0)
    p.material_index = 1 if (p.normal.z > 0.55 and patch > -0.1) or (p.normal.z > 0.88 and patch > -0.6) else 0
c0 = CEN[(ia + ib) // 2]; bad = 0
for p in me.polygons:
    if (p.center - c0).length < 1.2 and abs((p.center - c0).dot(TAN[(ia + ib) // 2])) < 0.2:
        q = (c0 + UP * 1.3) - p.center
        if p.normal.dot(q) < 0: bad += 1
print('lining inner faces facing away (want 0):', bad)

# 洞底：两口外各伸 0.3 m
bm = bmesh.new(); rows = []
for i in range(max(0, ia - 1), min(len(CEN), ib + 2)):
    c, n = CEN[i], LAT[i]
    rows.append([bm.verts.new(c + n * (W * s * 1.12) + UP * FLOOR_Y) for s in (-1, -0.5, 0, 0.5, 1)])
for a, b in zip(rows, rows[1:]):
    for k in range(4): bm.faces.new((a[k], b[k], b[k + 1], a[k + 1]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    if f.normal.z < 0: f.normal_flip()
me = ME.new('CZ_石洞_地'); bm.to_mesh(me); bm.free()
floor = O.new('CZ_石洞_地', me); col_rock.objects.link(floor); me.materials.append(MA['M_苔地'])

# ---------------------------------------------------------------- 3. 剪掉挡路的藤萝
for nm in ('CZ_藤萝_leaf', 'CZ_藤萝_vine'):
    o = O[nm]; bm = bmesh.new(); bm.from_mesh(o.data)
    dead = [f for f in bm.faces if any(in_tube(o.matrix_world @ v.co, 0.25, vmax=3.1) for v in f.verts)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free(); print('cut', nm, len(dead))

# ---------------------------------------------------------------- 4. 碰撞框
bpy.context.view_layer.update()
solid_objs = [rock, lining, O['CZ_镜面白石_卧石'], O['CZ_镜面白石_匾底']]
bvh = bvh_of(solid_objs)
DIRS = [Vector((0, 0, 1)), Vector((1, 0.13, 0.05)).normalized(), Vector((-0.2, -1, 0.07)).normalized()]
def inside(p):
    v = 0
    for d in DIRS:
        h = bvh.ray_cast(p, d, 60)
        if h[0] is not None and h[1].dot(d) > 0: v += 1
    return v >= 2
def top_at(x, z):
    h = bvh.ray_cast(B(x, 30, z), Vector((0, 0, -1)), 40)
    return None if h[0] is None else h[0].z
def near_axis(x, z, r):
    p = Vector((x, -z, 0))
    return min((p - c).length for c in CEN) < r

G = 0.2                      # 洞道附近细格
X0, X1, Z0, Z1 = -20.6, 20.8, -8.6, 8.6
nx, nz_ = int(round((X1 - X0) / G)), int(round((Z1 - Z0) / G))
def blocked(x, z, fine):
    t = top_at(x, z)
    if t is None or t < 0.45: return None
    if fine:                     # 洞道附近：点在石头里才挡（洞顶、洞外悬石不算）
        blk = any(inside(B(x, y, z)) for y in (0.55, 0.95, 1.35, 1.75))
    else:                        # 其余照旧：上面有石就挡
        blk = t >= 0.55
    if not blk: return None
    return math.ceil(t * 2) / 2 if fine else math.ceil(t * 4) / 4   # 细格顶高取 0.5 m 一档，好合并
fine, coarse = {}, {}
for ix in range(0, nx + 1, 2):   # 0.4 格；格心离洞中心线 < 1.7 m 的拆成 4 个 0.2 格
    for iz in range(0, nz_ + 1, 2):
        x, z = X0 + (ix + 0.5) * G, Z0 + (iz + 0.5) * G
        if near_axis(x, z, 1.7):
            for a in (0, 1):
                for b in (0, 1):
                    t = blocked(X0 + (ix + a) * G, Z0 + (iz + b) * G, True)
                    if t is not None: fine[(ix + a, iz + b)] = t
        else:
            t = blocked(x, z, False)
            if t is not None: coarse[(ix // 2, iz // 2)] = t
def merge(cells, g, ox, oz, maxc):
    """同顶高的格子贪心合并成矩形（单框半边 ≤ maxc*g/2，免得被网页当成院墙 WALLSEG）"""
    out, used = [], set()
    for key in sorted(cells, key=lambda k: (k[1], k[0])):
        if key in used: continue
        ix, iz = key; t = cells[key]; j = ix
        while (j + 1, iz) in cells and cells[(j + 1, iz)] == t and (j + 1, iz) not in used and j + 1 - ix < maxc: j += 1
        k = iz
        while k + 1 - iz < maxc and all(cells.get((a, k + 1)) == t and (a, k + 1) not in used for a in range(ix, j + 1)): k += 1
        for a in range(ix, j + 1):
            for b in range(iz, k + 1): used.add((a, b))
        out.append([round(ox + (ix + j) / 2 * g, 2), round(oz + (iz + k) / 2 * g, 2), round((j - ix + 1) * g / 2, 2),
                    round((k - iz + 1) * g / 2, 2), t, -0.75])
    return out
boxes = merge(coarse, 2 * G, X0 + G / 2, Z0 + G / 2, 14) + merge(fine, G, X0, Z0, 28)
colp = os.path.join(REPO, 'models', 'b', 'col.json')
cj = json.load(open(colp, encoding='utf-8')); cj['cuizhang'] = boxes
with open(colp, 'w', encoding='utf-8') as f:
    json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))
print('col cuizhang boxes', len(boxes))
print('PATH_WEB', [(round(c.x, 2), round(-c.y, 2)) for c in CEN[::4]])
# 记下中心线与内衬起止站（网页局部 x,z），供检查脚本、带路途经点用
bpy.context.scene['cz_cave'] = json.dumps({'cen': [(round(c.x, 3), round(-c.y, 3)) for c in CEN], 'ia': ia, 'ib': ib,
                                           'W': W, 'VS': VS, 'H': H, 'floor': FLOOR_Y})

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
