# 园路 3D 化（第十七回“石子甬路”）：按 blender/data/lu_<名>.json 的横断面取样，在 Blender 里建一条真的路——
#   两侧条石路牙（每块长短不一、留缝、往下埋）、路牙内青砖立砌一圈、路心卵石拼花街（斜方格，格心嵌一朵暖黄石子）；
#   路面贴着网页里看得见的地形网格走，桥面、石磴两段跳过（那里另有桥、台阶），岔口那一侧不立路牙、不镶砖，好让支路接进来。
#   颜色全用顶点色，不用贴图。每 12 米切一块：<名>_<k>_base（灰浆底、砖、路牙，远近都显示）和 <名>_<k>_peb（卵石，网页只在近处显示）。
# 用法：python3 blender/scripts/sites/paths_build.py blender/data/lu_zhou.json /tmp/lu_zhou.glb [存 .blend 的路径]
#       node blender/scripts/web/pack_lu.mjs /tmp/lu_zhou.glb models/b/lu_zhou.wasm
import bpy, json, math, random, sys

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
src, dst = ARGS[0], ARGS[1]
blend = ARGS[2] if len(ARGS) > 2 else None
D = json.load(open(src))
rows, OFF, W = D['rows'], D['off'], D['w']
HW = W / 2
NAME = src.rsplit('lu_', 1)[-1].split('.')[0]
rnd = random.Random(1717)

CURB_W, CURB_UP, CURB_DOWN = 0.16, 0.06, 0.25      # 路牙宽、高出地面、埋深
BRICK_W, BRICK_T, BRICK_UP = 0.24, 0.055, 0.045    # 立砖横着砌：宽（横向）、厚（顺路方向）、顶面高出地面
BED_UP = 0.03                                      # 灰浆底面
PEB = 0.095                                        # 卵石间距
CHUNK = 48                                         # 每块行数（0.25 米一行 → 12 米）


def ground(r, o):
    """第 r 行、横向偏移 o 处的地面高（在取样点之间线性插）。"""
    y = r['y']
    t = (o - OFF[0]) / (OFF[-1] - OFF[0]) * (len(OFF) - 1)
    i = max(0, min(len(OFF) - 2, int(math.floor(t))))
    f = t - i
    return y[i] * (1 - f) + y[i + 1] * f


def at(r, s, o):
    """行 r 往前 s 米、横向 o 米处的 (x, z)（three 坐标）。"""
    nx, nz = -r['tz'], r['tx']
    return r['x'] + r['tx'] * s + nx * o, r['z'] + r['tz'] * s + nz * o


def ok(r):
    return not r['wet'] and not r['steep']


class Part:
    def __init__(self):
        self.v, self.f, self.c = [], [], []

    def add(self, verts, faces, col):
        b = len(self.v)
        self.v += verts
        self.f += [tuple(i + b for i in fc) for fc in faces]
        lin = tuple(max(0.0, min(1.0, ch)) ** 2.2 for ch in col[:3]) + (1.0,)   # 下面颜色都按屏幕上看到的（sRGB）写，glTF 顶点色要线性值
        self.c += [lin] * len(verts)


def box_on(part, corners_xz, ybot, ytop, col, bevel=0.012):
    """四角（顺序：左后、右后、右前、左前，three 的 x,z）+ 底高 + 各角顶高 → 一块略带倒角的石块。"""
    (ax, az), (bx, bz), (cx, cz), (dx, dz) = corners_xz
    mx, mz = (ax + bx + cx + dx) / 4, (az + bz + cz + dz) / 4
    tops = ytop if isinstance(ytop, list) else [ytop] * 4
    shrink = lambda x, z, k: (x + (mx - x) * k, z + (mz - z) * k)
    vs = []
    for (x, z), t in zip(corners_xz, tops):
        vs.append((x, z, ybot))
    for (x, z), t in zip(corners_xz, tops):
        vs.append((x, z, t - bevel))
    for (x, z), t in zip(corners_xz, tops):
        sx, sz = shrink(x, z, 0.12)
        vs.append((sx, sz, t))
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
             (4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 10, 11)]
    # three (x, y↑, z) → Blender (x, -z, y)
    part.add([(x, -z, y) for (x, z, y) in vs], faces, col)


def jitter(c, k=0.08):
    m = 1 + rnd.uniform(-k, k)
    return (c[0] * m, c[1] * m, c[2] * m, 1.0)


def build_chunk(i0, i1):
    base, peb = Part(), Part()
    seg = [r for r in rows[i0:i1 + 1]]
    # ---- 灰浆底：横向 0.2 米一格，贴地
    across = [-(HW - CURB_W - BRICK_W) + k * 0.2 for k in range(int((2 * (HW - CURB_W - BRICK_W)) / 0.2) + 1)]
    across[-1] = HW - CURB_W - BRICK_W
    grid = []
    for r in seg:
        line = []
        for o in across:
            x, z = at(r, 0, o)
            line.append((x, -z, ground(r, o) + BED_UP))
        grid.append(line)
    for j in range(len(seg) - 1):
        if not (ok(seg[j]) and ok(seg[j + 1])):
            continue
        for k in range(len(across) - 1):
            vs = [grid[j][k], grid[j][k + 1], grid[j + 1][k + 1], grid[j + 1][k]]
            base.add(vs, [(0, 3, 2, 1)], jitter((0.47, 0.45, 0.41), 0.04))
    # ---- 两侧：青砖立砌 + 条石路牙（岔口那一侧空着）
    for sd, flag in ((-1, 'jl'), (1, 'jr')):
        # 立砖：顺路方向每 BRICK_T 一块
        acc = 0.0
        for j in range(len(seg) - 1):
            r, q = seg[j], seg[j + 1]
            if not (ok(r) and ok(q)) or r[flag] or q[flag]:
                continue
            step = math.hypot(q['x'] - r['x'], q['z'] - r['z'])
            s = 0.0
            while s < step - 1e-4:
                t = min(BRICK_T - 0.006, step - s)
                o0, o1 = sd * (HW - CURB_W - BRICK_W), sd * (HW - CURB_W)
                c = [at(r, s, o0), at(r, s, o1), at(r, s + t, o1), at(r, s + t, o0)]
                g = min(ground(r, o0), ground(r, o1))
                box_on(base, c, g - 0.12, g + BRICK_UP + rnd.uniform(-0.006, 0.006),
                       jitter((0.43, 0.42, 0.4), 0.07), bevel=0.006)
                s += BRICK_T
        # 路牙：每块 0.6–1.0 米，块间留 1 厘米缝
        j = 0
        while j < len(seg) - 1:
            if not ok(seg[j]) or seg[j][flag]:
                j += 1
                continue
            L = rnd.uniform(0.6, 1.0)
            n = max(1, round(L / 0.25))
            k = min(len(seg) - 1, j + n)
            while k > j and not all(ok(seg[m]) and not seg[m][flag] for m in range(j, k + 1)):
                k -= 1
            if k == j:
                j += 1
                continue
            r, q = seg[j], seg[k]
            o0, o1 = sd * (HW - CURB_W), sd * HW
            s1 = math.hypot(q['x'] - r['x'], q['z'] - r['z']) - 0.01
            # 曲线上的一块：用首尾两行各自的法向取角，块面跟着弯
            c = [at(r, 0.005, o0), at(r, 0.005, o1), at(q, -0.005, o1), at(q, -0.005, o0)]
            tops = [ground(r, o0) + CURB_UP, ground(r, o1) + CURB_UP, ground(q, o1) + CURB_UP, ground(q, o0) + CURB_UP]
            g = min(tops) - CURB_UP - CURB_DOWN
            box_on(base, c, g, tops, jitter((0.56, 0.55, 0.52), 0.09), bevel=0.02)
            j = k
    # ---- 卵石：路心按 PEB 间距错行排，斜方格花街
    inner = HW - CURB_W - BRICK_W - 0.03
    for j in range(len(seg) - 1):
        r, q = seg[j], seg[j + 1]
        if not (ok(r) and ok(q)):
            continue
        step = math.hypot(q['x'] - r['x'], q['z'] - r['z'])
        s0 = r.get('_s', 0.0)
        s = (math.ceil(s0 / PEB) * PEB) - s0
        while s < step:
            u = s0 + s                               # 顺路总米数
            row_i = int(round(u / PEB))
            shift = (PEB / 2) if row_i % 2 else 0.0
            o = -inner + shift
            while o <= inner:
                # 花街：斜方格（格距 0.6 米）深色石子拼线；格心一朵暖黄
                a, b = (u + o) / 0.6, (u - o) / 0.6
                da, db = abs(a - round(a)), abs(b - round(b))
                ca, cb = (a - math.floor(a)) - 0.5, (b - math.floor(b)) - 0.5
                if da < 0.11 or db < 0.11:
                    col = jitter((0.34, 0.33, 0.31), 0.12)
                elif math.hypot(ca, cb) < 0.16:
                    col = jitter((0.64, 0.53, 0.38), 0.08)
                else:
                    col = jitter((0.58, 0.56, 0.52), 0.07)
                x, z = at(r, s + rnd.uniform(-0.01, 0.01), o + rnd.uniform(-0.01, 0.01))
                f = s / step
                gy = ground(r, o) * (1 - f) + ground(q, o) * f + BED_UP
                pebble(peb, x, z, gy, col, math.atan2(r['tx'], r['tz']))
                o += PEB
            s += PEB
    return base, peb


def pebble(part, x, z, y, col, ang):
    """一颗卵石：六边形底、一圈腰、一个顶点（18 个三角），长圆、顺路斜放。"""
    lx = PEB * rnd.uniform(0.40, 0.52)
    lz = lx * rnd.uniform(0.62, 0.85)
    h = PEB * rnd.uniform(0.16, 0.24)   # 大半埋在灰浆里，只露个圆顶
    a0 = ang + rnd.uniform(-0.5, 0.5)
    ca, sa = math.cos(a0), math.sin(a0)
    vs = []
    for ring, (k, hh) in enumerate(((1.0, -0.01), (0.7, h * 0.72))):
        for m in range(6):
            t = m / 6 * math.tau
            ex, ez = math.cos(t) * lx * k, math.sin(t) * lz * k
            vx, vz = x + ex * ca + ez * sa, z - ex * sa + ez * ca
            vs.append((vx, -vz, y + hh))
    vs.append((x, -z, y + h))
    faces = [(m, (m + 1) % 6, 6 + (m + 1) % 6, 6 + m) for m in range(6)] + [(6 + m, 6 + (m + 1) % 6, 12) for m in range(6)]
    part.add(vs, faces, col)


# 顺路累计米数（花街图案连续）
acc = 0.0
for i, r in enumerate(rows):
    if i:
        acc += math.hypot(r['x'] - rows[i - 1]['x'], r['z'] - rows[i - 1]['z'])
    r['_s'] = acc

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
mat = bpy.data.materials.new('M_lu')
mat.use_nodes = True
coll = bpy.context.scene.collection
nt = 0
for ci, i0 in enumerate(range(0, len(rows) - 1, CHUNK)):
    i1 = min(len(rows) - 1, i0 + CHUNK)
    for part, tag in zip(build_chunk(i0, i1), ('base', 'peb')):
        if not part.f:
            continue
        me = bpy.data.meshes.new(f'lu_{NAME}_{ci}_{tag}')
        me.from_pydata(part.v, [], part.f)
        attr = me.color_attributes.new('Col', 'FLOAT_COLOR', 'CORNER')
        for poly in me.polygons:
            for li in poly.loop_indices:
                attr.data[li].color = part.c[me.loops[li].vertex_index]
        me.materials.append(mat)
        if tag == 'peb':
            me.shade_smooth()    # 卵石圆润，不要一颗颗的棱面
        ob = bpy.data.objects.new(me.name, me)
        coll.objects.link(ob)
        nt += sum(len(p.vertices) - 2 for p in me.polygons)
print('chunks', ci + 1, 'tris', nt)
if blend:
    bpy.ops.wm.save_as_mainfile(filepath=blend)
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_yup=True, export_apply=False,
                          export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_normals=True,
                          export_texcoords=False, export_materials='EXPORT')
print('->', dst)
