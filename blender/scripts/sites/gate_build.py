# 大观园正门（第十七回）：
#   “只见正门五间，上面桶瓦泥鳅脊；那门栏窗槅，皆是细雕新鲜花样，并无朱粉涂饰；一色水磨群墙，下面白石台矶，凿成西番草花样。
#    左右一望，皆雪白粉墙，下面虎皮石，随势砌去，果然不落富丽俗套。”
# 照此建：
#   五开间（面阔 18 米），卷棚顶（泥鳅脊：前后坡在顶上圆弧相接、不起正脊），屋面一垄垄筒瓦从前檐翻过顶到后檐，檐口勾头滴水；
#   柱、枋、门、槅扇、槛窗全是本色楠木，不施朱漆彩画；明间两扇板门敞开，次间四扇槅扇、梢间槛窗，格心“灯笼锦”细棂嵌卡子花；
#   梢间槛墙和两山墙“一色水磨”青砖；台基、门外台阶和月台用白石，台帮、栏板面上凿西番草（卷草）纹。
# 坐标：原点在台基外地面中心（网页 Z.gate，世界 (0, 6.765, 120)），three 局部坐标 x 向东、y 向上、z 向园外（南）。
# 门外台阶按实测地面（index.html 的 height()）逐级随势而下，到园外街面。
# 用法：python3 blender/scripts/sites/gate_build.py /tmp/gate.glb [存 .blend]
#       node blender/scripts/web/pack_glb.mjs /tmp/gate.glb models/b/gate.wasm
#   碰撞框写进 models/b/col.json["gate"]。
import bpy, bmesh, json, math, os, sys
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
DST = ARGS[0]
BLEND = ARGS[1] if len(ARGS) > 1 else None
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# ---------------------------------------------------------------- 尺寸
BAY = 3.6                      # 开间
XS = [-9.0, -5.4, -1.8, 1.8, 5.4, 9.0]   # 柱位
ZROW = (-3.3, 0.0, 3.3)        # 后檐柱、中柱（门槅所在）、前檐柱
PH = 0.9                       # 台基高
PX, PZ = 10.18, 4.72           # 台基半宽、半深
CH = 4.3                       # 柱高（台基面起）
CR = 0.19                      # 柱半径
EAVE_Z = 4.95                  # 檐口离中线
EAVE_X = 11.25                 # 两山出檐
EAVE_Y = PH + CH + 0.25        # 檐口高
TOP_Y = PH + CH + 2.75         # 卷棚顶高
TOP_R = 0.75                   # 顶上圆弧半宽

# 门外地面（相对台基外地面 0）：z → y，取自网页 height(0, 120+z) − 6.765
GROUND = [(7.5, 0.0), (8, -0.02), (9, -0.09), (10, -0.21), (11, -0.41), (12, -0.62), (13, -1.05), (14, -1.27), (15, -1.5),
          (16, -2.0), (17, -2.29), (18, -2.57), (19, -2.86), (20, -3.43), (21, -3.7), (22, -3.96), (23, -4.21), (24, -4.7),
          (25, -4.92), (26, -5.12), (27, -5.5), (28, -5.7), (29, -5.86), (30, -5.99), (31, -6.12), (32, -6.12), (34, -6.13)]


def ground(z):
    for (z0, y0), (z1, y1) in zip(GROUND, GROUND[1:]):
        if z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / (z1 - z0)
    return GROUND[0][1] if z < GROUND[0][0] else GROUND[-1][1]


# ---------------------------------------------------------------- 网格积累（three 坐标 → Blender：(x, -z, y)）
class Part:
    def __init__(self, mat):
        self.mat, self.v, self.f, self.uv = mat, [], [], []

    def quad(self, a, b, c, d, uv=None):
        i = len(self.v)
        self.v += [a, b, c, d]
        self.f.append((i, i + 1, i + 2, i + 3))
        self.uv.append(uv or [(0, 0), (1, 0), (1, 1), (0, 1)])

    def poly(self, pts, uv=None):
        i = len(self.v)
        self.v += pts
        self.f.append(tuple(range(i, i + len(pts))))
        self.uv.append(uv or [(0, 0)] * len(pts))


PARTS = {}


def P(name, mat):
    if name not in PARTS:
        PARTS[name] = Part(mat)
    return PARTS[name]


def box(part, x0, x1, y0, y1, z0, z1):
    """轴对齐方盒（six faces，外法向）。"""
    a = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1), (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (3, 0, 4, 7)):
        part.quad(*[a[k] for k in f])


def obox(part, c, half, axis_x, y0, y1):
    """水平朝向任意的方盒：中心 c=(x,z)、半宽 half=(hx,hz)、局部 x 轴方向 axis_x=(ux,uz)。"""
    ux, uz = axis_x
    vx, vz = -uz, ux
    cs = [(c[0] + sx * half[0] * ux + sz * half[1] * vx, c[1] + sx * half[0] * uz + sz * half[1] * vz)
          for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    a = [(x, y0, z) for x, z in cs] + [(x, y1, z) for x, z in cs]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        part.quad(*[a[k] for k in f])


def cyl(part, x, z, y0, y1, r, n=16):
    for k in range(n):
        a0, a1 = k / n * math.tau, (k + 1) / n * math.tau
        p0, p1 = (x + r * math.cos(a0), z + r * math.sin(a0)), (x + r * math.cos(a1), z + r * math.sin(a1))
        part.quad((p0[0], y0, p0[1]), (p1[0], y0, p1[1]), (p1[0], y1, p1[1]), (p0[0], y1, p0[1]))
    part.poly([(x + r * math.cos(k / n * math.tau), y1, z + r * math.sin(k / n * math.tau)) for k in range(n)][::-1])


def band_xfc(part, x0, x1, y0, y1, z, out, u_per_m=1 / 2.48):
    """西番草浮雕带：竖直面，UV 横向按米数铺（贴图 4:1，0.62 米高一个循环）。out=+1 朝 +z，-1 朝 −z。"""
    L = x1 - x0
    u = L * u_per_m * 0.62 / (y1 - y0) if False else L / ((y1 - y0) * 4)
    if out > 0:
        part.quad((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), [(0, 0), (u, 0), (u, 1), (0, 1)])
    else:
        part.quad((x1, y0, z), (x0, y0, z), (x0, y1, z), (x1, y1, z), [(0, 0), (u, 0), (u, 1), (0, 1)])


def band_xfc_side(part, z0, z1, y0, y1, x, out):
    L = z1 - z0
    u = L / ((y1 - y0) * 4)
    if out > 0:
        part.quad((x, y0, z1), (x, y0, z0), (x, y1, z0), (x, y1, z1), [(0, 0), (u, 0), (u, 1), (0, 1)])
    else:
        part.quad((x, y0, z0), (x, y0, z1), (x, y1, z1), (x, y1, z0), [(0, 0), (u, 0), (u, 1), (0, 1)])


COL = []   # col.json：[lx, lz, hx, hz, top, bot, walk]


def colbox(x0, x1, z0, z1, top, bot, walk=0):
    COL.append([round((x0 + x1) / 2, 3), round((z0 + z1) / 2, 3), round((x1 - x0) / 2, 3), round((z1 - z0) / 2, 3), round(top, 3), round(bot, 3)] + ([1] if walk else []))


# ================================================================ 台基（白石台矶）
marble = P('台基_汉白玉', '汉白玉')
xfc = P('台基_西番草', '西番草')
pave = P('台基_方砖', '方砖地')
# 土衬（下）、台帮、阶条石（上，略出）
box(marble, -PX - 0.08, PX + 0.08, -0.6, 0.12, -PZ - 0.08, PZ + 0.08)
box(marble, -PX, PX, 0.12, PH - 0.14, -PZ, PZ)
box(marble, -PX - 0.05, PX + 0.05, PH - 0.14, PH, -PZ - 0.05, PZ + 0.05)
# 台帮四面凿西番草（浮雕面略凸 1 厘米）
for s in (-1, 1):
    band_xfc(xfc, -PX + 0.25, PX - 0.25, 0.2, PH - 0.22, s * (PZ + 0.012), s)
    band_xfc_side(xfc, -PZ + 0.25, PZ - 0.25, 0.2, PH - 0.22, s * (PX + 0.012), s)
# 台面方砖
pave.quad((-PX + 0.3, PH + 0.002, PZ - 0.3), (PX - 0.3, PH + 0.002, PZ - 0.3), (PX - 0.3, PH + 0.002, -PZ + 0.3), (-PX + 0.3, PH + 0.002, -PZ + 0.3))
colbox(-PX, PX, -PZ, PZ, PH, -1.5, 1)

# 前后台阶（明间 + 两次间宽，三级）与垂带
for s in (-1, 1):
    w = 3.4
    for k in range(3):
        y1 = PH - 0.3 * (k + 1) + 0.3
        z0 = s * (PZ + 0.35 * k)
        z1 = s * (PZ + 0.35 * (k + 1))
        box(marble, -w, w, -0.4, y1, min(z0, z1), max(z0, z1))
        colbox(-w, w, min(z0, z1), max(z0, z1), y1, -1.0, 1)
    for sx in (-1, 1):   # 垂带：斜边石
        zz = s * (PZ + 1.05)
        x0 = sx * w
        part = marble
        a, b = (x0, PH, s * PZ), (x0 + sx * 0.32, PH, s * PZ)
        c, d = (x0 + sx * 0.32, 0.0, zz), (x0, 0.0, zz)
        top = [(x0, PH + 0.02, s * PZ), (x0 + sx * 0.32, PH + 0.02, s * PZ), (x0 + sx * 0.32, 0.02, zz), (x0, 0.02, zz)]
        part.poly(top if (s * sx) > 0 else top[::-1])
        for (p, q) in ((top[0], top[3]), (top[1], top[2])):
            part.poly([p, q, (q[0], -0.4, q[2]), (p[0], -0.4, p[2])] if s > 0 else [(p[0], -0.4, p[2]), (q[0], -0.4, q[2]), q, p])
        colbox(min(x0, x0 + sx * 0.32), max(x0, x0 + sx * 0.32), min(s * PZ, zz), max(s * PZ, zz), PH * 0.6, -1.0)

# ================================================================ 柱、柱础、枋、雀替（本色楠木）
wood = P('木作_楠木', '本色楠木')
base_stone = P('柱础_青石', '青石')
for x in XS:
    for z in ZROW:
        cyl(wood, x, z, PH, PH + CH, CR, 18)
        cyl(base_stone, x, z, PH, PH + 0.16, CR + 0.12, 18)
        colbox(x - CR, x + CR, z - CR, z + CR, PH + CH, PH)
# 额枋（大、小两道）与平板枋
for z in ZROW:
    box(wood, XS[0] - 0.2, XS[-1] + 0.2, PH + CH - 0.62, PH + CH - 0.22, z - 0.16, z + 0.16)
    box(wood, XS[0] - 0.2, XS[-1] + 0.2, PH + CH - 1.02, PH + CH - 0.78, z - 0.12, z + 0.12)
    box(wood, XS[0] - 0.3, XS[-1] + 0.3, PH + CH - 0.22, PH + CH + 0.02, z - 0.2, z + 0.2)
# 由额垫板（两道额枋之间）
for z in ZROW:
    box(wood, XS[0], XS[-1], PH + CH - 0.78, PH + CH - 0.62, z - 0.06, z + 0.06)
# 前后檐柱到中柱的穿插枋、梁
for x in XS:
    for z0, z1 in ((ZROW[0], ZROW[1]), (ZROW[1], ZROW[2])):
        box(wood, x - 0.15, x + 0.15, PH + CH - 0.6, PH + CH - 0.2, z0, z1)
    box(wood, x - 0.18, x + 0.18, PH + CH + 0.02, PH + CH + 0.42, ZROW[0] - 0.4, ZROW[2] + 0.4)    # 大梁


def queti(part, x, z, sx, axis):
    """雀替：额枋下、柱两侧，卷草轮廓的木雕托（不施彩）。axis='x' 沿面阔方向伸出。"""
    L, H, T = 0.85, 0.42, 0.08
    yt = PH + CH - 1.02
    prof = []
    for k in range(13):
        t = k / 12
        prof.append((t * L, H * (1 - t) ** 1.6 * (0.75 + 0.25 * math.cos(t * 9.0))))
    pts = [(0, 0)] + [(px, -py) for px, py in prof] + [(L, 0)]
    for side in (-T / 2, T / 2):
        ring = [((x + sx * (CR + px)) if axis == 'x' else (x + side), yt + py, (z + side) if axis == 'x' else (z + sx * (CR + px))) for px, py in pts]
        part.poly(ring if (side > 0) == (sx > 0) else ring[::-1])
    for (a0, b0), (a1, b1) in zip(pts, pts[1:] + pts[:1]):
        q = []
        for (px, py), side in (((a0, b0), -T / 2), ((a1, b1), -T / 2), ((a1, b1), T / 2), ((a0, b0), T / 2)):
            q.append(((x + sx * (CR + px)) if axis == 'x' else (x + side), yt + py, (z + side) if axis == 'x' else (z + sx * (CR + px))))
        part.poly(q)


carve = P('木雕_楠木', '本色楠木')
for z in (ZROW[0], ZROW[2]):
    for i, x in enumerate(XS):
        for sx in (-1, 1):
            if (i == 0 and sx < 0) or (i == len(XS) - 1 and sx > 0):
                continue
            queti(carve, x, z, sx, 'x')

# ================================================================ 中线上的门、槅扇、槛窗、水磨群墙
paper = P('窗纸', '窗纸')
lat = P('棂心_楠木', '本色楠木')
brick = P('水磨砖', '水磨砖')
Y0 = PH                      # 门槛下皮
YT = PH + CH - 1.02          # 小额枋下皮
YM = PH + 3.15               # 中槛（门窗上口）


def lattice(part, x0, x1, y0, y1, z, w=0.022, d=0.035):
    """格心“灯笼锦”：外框一圈，里面井字分格，每格中心套一个小方框，四角用短棂连到外格；交点嵌卡子花。"""
    def bar(ax, ay, bx, by):
        if abs(ay - by) < 1e-6:
            box(part, min(ax, bx), max(ax, bx), ay - w, ay + w, z - d, z + d)
        else:
            box(part, ax - w, ax + w, min(ay, by), max(ay, by), z - d, z + d)
    box(part, x0, x1, y0, y0 + 0.05, z - d * 1.4, z + d * 1.4)
    box(part, x0, x1, y1 - 0.05, y1, z - d * 1.4, z + d * 1.4)
    box(part, x0, x0 + 0.05, y0, y1, z - d * 1.4, z + d * 1.4)
    box(part, x1 - 0.05, x1, y0, y1, z - d * 1.4, z + d * 1.4)
    nx = max(2, round((x1 - x0) / 0.26))
    ny = max(3, round((y1 - y0) / 0.26))
    cw, chh = (x1 - x0) / nx, (y1 - y0) / ny
    for i in range(nx):
        for j in range(ny):
            cx0, cy0 = x0 + i * cw, y0 + j * chh
            mx, my = cx0 + cw / 2, cy0 + chh / 2
            a, b = cw * 0.24, chh * 0.24
            # 中心小框
            bar(mx - a, my - b, mx + a, my - b); bar(mx - a, my + b, mx + a, my + b)
            bar(mx - a, my - b, mx - a, my + b); bar(mx + a, my - b, mx + a, my + b)
            # 十字短棂连到格边
            bar(mx, cy0, mx, my - b); bar(mx, my + b, mx, cy0 + chh)
            bar(cx0, my, mx - a, my); bar(mx + a, my, cx0 + cw, my)
            # 卡子花：小方块略凸
            box(part, mx - 0.03, mx + 0.03, my - b - 0.03, my - b + 0.03, z - d * 1.6, z + d * 1.6)
            box(part, mx - 0.03, mx + 0.03, my + b - 0.03, my + b + 0.03, z - d * 1.6, z + d * 1.6)


def geshan(x0, x1, z, leaves):
    """一间槅扇：分 leaves 扇，每扇上格心、下裙板（起线的木板）、中间绦环板。"""
    lw = (x1 - x0) / leaves
    for k in range(leaves):
        a, b = x0 + k * lw + 0.02, x0 + (k + 1) * lw - 0.02
        # 边梃、抹头
        box(wood, a, a + 0.07, Y0, YM, z - 0.05, z + 0.05)
        box(wood, b - 0.07, b, Y0, YM, z - 0.05, z + 0.05)
        for y in (Y0, Y0 + 0.75, Y0 + 0.95, YM - 0.07):
            box(wood, a, b, y, y + 0.07, z - 0.05, z + 0.05)
        # 裙板（起凸）与绦环板
        box(wood, a + 0.07, b - 0.07, Y0 + 0.07, Y0 + 0.75, z - 0.025, z + 0.025)
        box(carve, a + 0.16, b - 0.16, Y0 + 0.18, Y0 + 0.64, z - 0.04, z + 0.04)
        box(carve, a + 0.12, b - 0.12, Y0 + 0.82, Y0 + 0.9, z - 0.035, z + 0.035)
        lattice(lat, a + 0.07, b - 0.07, Y0 + 1.02, YM - 0.07, z)
        paper.quad((a + 0.07, Y0 + 1.02, z - 0.045), (b - 0.07, Y0 + 1.02, z - 0.045), (b - 0.07, YM - 0.07, z - 0.045), (a + 0.07, YM - 0.07, z - 0.045))
    colbox(x0, x1, z - 0.1, z + 0.1, YT, Y0)


def kanchuang(x0, x1, z):
    """梢间：下水磨群墙（槛墙），上槛窗四扇。"""
    yw = Y0 + 0.95
    box(brick, x0 + CR, x1 - CR, Y0, yw, z - 0.22, z + 0.22)
    box(marble, x0 + CR - 0.02, x1 - CR + 0.02, yw, yw + 0.06, z - 0.26, z + 0.26)   # 槛墙压面石
    lw = (x1 - x0 - 2 * CR) / 4
    for k in range(4):
        a, b = x0 + CR + k * lw + 0.02, x0 + CR + (k + 1) * lw - 0.02
        box(wood, a, a + 0.07, yw + 0.06, YM, z - 0.05, z + 0.05)
        box(wood, b - 0.07, b, yw + 0.06, YM, z - 0.05, z + 0.05)
        for y in (yw + 0.06, YM - 0.07):
            box(wood, a, b, y, y + 0.07, z - 0.05, z + 0.05)
        lattice(lat, a + 0.07, b - 0.07, yw + 0.13, YM - 0.07, z)
        paper.quad((a + 0.07, yw + 0.13, z - 0.045), (b - 0.07, yw + 0.13, z - 0.045), (b - 0.07, YM - 0.07, z - 0.045), (a + 0.07, YM - 0.07, z - 0.045))
    colbox(x0, x1, z - 0.25, z + 0.25, YT, Y0)


zc = ZROW[1]
# 中槛以上走马板（木板）、各间门框
for i in range(5):
    x0, x1 = XS[i] + CR, XS[i + 1] - CR
    box(wood, x0, x1, YM, YM + 0.12, zc - 0.08, zc + 0.08)                # 中槛
    box(wood, x0, x1, YM + 0.12, YT, zc - 0.04, zc + 0.04)                # 走马板
    box(wood, x0, x0 + 0.1, Y0, YM, zc - 0.08, zc + 0.08)                 # 抱框
    box(wood, x1 - 0.1, x1, Y0, YM, zc - 0.08, zc + 0.08)
# 明间：板门两扇向里敞开、门槛、门枕石与抱鼓石、门簪
x0, x1 = XS[2] + CR + 0.1, XS[3] - CR - 0.1
box(wood, x0, x1, Y0, Y0 + 0.28, zc - 0.1, zc + 0.1)                      # 门槛
colbox(x0, x1, zc - 0.1, zc + 0.1, Y0 + 0.28, Y0, 1)
lw = (x1 - x0) / 2
for sx, xh in ((-1, x0), (1, x1)):
    # 门扇：门轴在 xh，关着时朝明间中线伸；向里（−z）开到约 80°
    ang = math.radians(80)
    d = (-sx * math.cos(ang), -math.sin(ang))
    nrm = (d[1], -d[0]) if sx < 0 else (-d[1], d[0])          # 门扇朝园外那一面的法向
    hz = zc - 0.12
    obox(wood, (xh + d[0] * lw / 2, hz + d[1] * lw / 2), (lw / 2, 0.045), d, Y0 + 0.28, YM - 0.02)
    for r in range(5):          # 门钉 5×5（本色铁）
        for c in range(5):
            t = (c + 0.5) / 5
            px, pz = xh + d[0] * lw * t, hz + d[1] * lw * t
            yy = Y0 + 0.6 + r * 0.48
            cyl(P('门钉_铁', '铁'), px + nrm[0] * 0.05, pz + nrm[1] * 0.05, yy - 0.03, yy + 0.03, 0.035, 8)
    # 门枕石 + 抱鼓石（白石，门外一侧）
    box(marble, xh - 0.22, xh + 0.22, Y0, Y0 + 0.36, zc - 0.5, zc + 0.6)
    drum = P('抱鼓石_汉白玉', '汉白玉')
    for k in range(20):
        a0, a1 = k / 20 * math.tau, (k + 1) / 20 * math.tau
        R, cy, cz = 0.42, Y0 + 0.36 + 0.5, zc + 0.3
        for (p, q) in (((math.cos(a0), math.sin(a0)), (math.cos(a1), math.sin(a1))),):
            drum.quad((xh - 0.13, cy + R * q[1], cz + R * q[0]), (xh + 0.13, cy + R * q[1], cz + R * q[0]), (xh + 0.13, cy + R * p[1], cz + R * p[0]), (xh - 0.13, cy + R * p[1], cz + R * p[0]))
        for side in (-0.13, 0.13):
            drum.poly([(xh + side, cy, cz), (xh + side, cy + R * math.sin(a0), cz + R * math.cos(a0)), (xh + side, cy + R * math.sin(a1), cz + R * math.cos(a1))][:: (1 if side > 0 else -1)])
    colbox(xh - 0.25, xh + 0.25, zc - 0.5, zc + 0.75, Y0 + 1.3, Y0)
for k in range(4):   # 门簪
    xx = x0 + (k + 0.5) * (x1 - x0) / 4
    cyl(carve, xx, zc + 0.1, YM + 0.0, YM + 0.18, 0.09, 12)
# 次间槅扇、梢间槛窗
geshan(XS[1] + CR, XS[2] - CR, zc, 4)
geshan(XS[3] + CR, XS[4] - CR, zc, 4)
kanchuang(XS[0], XS[1], zc)
kanchuang(XS[4], XS[5], zc)

# 两山墙：一色水磨砖（下肩到墀头），山尖上接卷棚山花
for sx in (-1, 1):
    x = sx * XS[-1]
    box(brick, min(x, x + sx * 0.6), max(x, x + sx * 0.6), PH, PH + CH + 0.1, ZROW[0] - 0.5, ZROW[2] + 0.5)
    colbox(min(x, x + sx * 0.6), max(x, x + sx * 0.6), ZROW[0] - 0.5, ZROW[2] + 0.5, PH + CH, PH)
    # 墀头：檐下挑出的砖垛
    for s in (-1, 1):
        z = s * (ZROW[2] + 0.5)
        box(brick, min(x, x + sx * 0.6) - 0.05, max(x, x + sx * 0.6) + 0.05, PH + CH - 0.6, PH + CH + 0.25, min(z, z + s * 0.35), max(z, z + s * 0.35))

# ================================================================ 卷棚顶（泥鳅脊）：筒瓦垄从前檐翻过顶到后檐
def prof(t):
    """屋面剖面：t∈[0,1] 从前檐到后檐，返回 (z, y)。两坡下凹（举折），顶上一段圆弧。"""
    zz = EAVE_Z * (1 - 2 * t)
    a = abs(zz)
    if a <= TOP_R:
        y = TOP_Y - (TOP_R - math.sqrt(max(0.0, TOP_R ** 2 - a ** 2))) * 0.55
    else:
        s = (a - TOP_R) / (EAVE_Z - TOP_R)
        y0 = TOP_Y - TOP_R * 0.55
        y = y0 - (y0 - EAVE_Y) * (s ** 1.45)
    return zz, y


NT = 40
PROF = [prof(i / NT) for i in range(NT + 1)]
# 屋面底层（板瓦面 / 望板），略低于筒瓦
under = P('屋面_板瓦', 'YH_灰瓦')
soffit = P('望板_楠木', '本色楠木')
for (z0, y0), (z1, y1) in zip(PROF, PROF[1:]):
    under.quad((-EAVE_X, y0 + 0.02, z0), (EAVE_X, y0 + 0.02, z0), (EAVE_X, y1 + 0.02, z1), (-EAVE_X, y1 + 0.02, z1))
    soffit.quad((-EAVE_X, y1 - 0.1, z1), (EAVE_X, y1 - 0.1, z1), (EAVE_X, y0 - 0.1, z0), (-EAVE_X, y0 - 0.1, z0))
# 筒瓦：每 0.27 米一垄，半圆截面，沿剖面走
tong = P('屋面_筒瓦', 'YH_灰瓦')
RT = 0.075
nrows = int(2 * EAVE_X / 0.27)
for r in range(nrows + 1):
    x = -EAVE_X + 0.06 + r * (2 * EAVE_X - 0.12) / nrows
    ring = [(math.cos(math.pi * k / 6), math.sin(math.pi * k / 6)) for k in range(7)]
    for (z0, y0), (z1, y1) in zip(PROF, PROF[1:]):
        for (c0, s0), (c1, s1) in zip(ring, ring[1:]):
            tong.quad((x + RT * c0, y0 + 0.02 + RT * s0, z0), (x + RT * c0, y1 + 0.02 + RT * s0, z1),
                      (x + RT * c1, y1 + 0.02 + RT * s1, z1), (x + RT * c1, y0 + 0.02 + RT * s1, z0))
    # 两端勾头（圆盘）、檐口滴水（三角垂片）
    for zz, yy, s in ((PROF[0][0], PROF[0][1], 1), (PROF[-1][0], PROF[-1][1], -1)):
        P('勾头滴水', 'YH_灰瓦').poly([(x + RT * 1.1 * math.cos(k / 12 * math.tau), yy + 0.02 + RT * 1.1 * math.sin(k / 12 * math.tau), zz + s * 0.01) for k in range(12)][:: s])
        xd = x + 0.135
        P('勾头滴水', 'YH_灰瓦').poly([(xd - 0.11, yy + 0.02, zz + s * 0.005), (xd + 0.11, yy + 0.02, zz + s * 0.005), (xd, yy - 0.12, zz + s * 0.03)][:: s])
# 檐椽：前后檐下露出的圆椽
rafter = P('檐椽_楠木', '本色楠木')
for s in (-1, 1):
    for r in range(int(2 * (XS[-1] + 0.3) / 0.3) + 1):
        x = -(XS[-1] + 0.3) + r * 0.3
        z0, z1 = s * (ZROW[2] + 0.2), s * (EAVE_Z - 0.12)
        y0 = PH + CH + 0.35
        y1 = EAVE_Y - 0.06
        n = 6
        for k in range(n):
            a0, a1 = k / n * math.tau, (k + 1) / n * math.tau
            rafter.quad((x + 0.05 * math.cos(a0), y0 + 0.05 * math.sin(a0), z0), (x + 0.05 * math.cos(a1), y0 + 0.05 * math.sin(a1), z0),
                        (x + 0.05 * math.cos(a1), y1 + 0.05 * math.sin(a1), z1), (x + 0.05 * math.cos(a0), y1 + 0.05 * math.sin(a0), z1))
# 山面：博缝板（楠木）沿屋面剖面、山花板封住屋面与山墙之间
for sx in (-1, 1):
    x = sx * (EAVE_X + 0.02)
    for (z0, y0), (z1, y1) in zip(PROF, PROF[1:]):
        q = [(x, y0 - 0.32, z0), (x, y1 - 0.32, z1), (x, y1 + 0.12, z1), (x, y0 + 0.12, z0)]
        wood.poly(q if sx > 0 else q[::-1])
    xin = sx * (XS[-1] + 0.3)
    pts = [(xin, PH + CH + 0.1, z) for z, _ in (PROF[0], PROF[-1])]
    gable = [(xin, y - 0.05, z) for z, y in PROF if abs(z) <= ZROW[2] + 0.5]
    if gable:
        poly = [(xin, PH + CH + 0.1, gable[0][2])] + gable + [(xin, PH + CH + 0.1, gable[-1][2])]
        brick.poly(poly if sx < 0 else poly[::-1])

# 匾：前檐下、明间额枋之上（字在网页里写）
plq = P('匾_匾底', '匾心')
box(plq, -1.35, 1.35, PH + CH - 1.0 + 0.0, PH + CH - 0.15, ZROW[2] + 0.17, ZROW[2] + 0.24)

# ================================================================ 门外：月台与白石台矶，随势而下
STW = 3.2                      # 台阶半宽
Z_TOP = PZ + 1.05              # 台基台阶落地处
Z_PLAT = 8.6                   # 月台外沿
Z_END = 31.6                   # 末级
step_m = P('台矶_汉白玉', '汉白玉')
rail = P('栏杆_汉白玉', '汉白玉')
rail_x = P('栏板_西番草', '西番草')
# 月台（白石墁地），外沿一道西番草
box(step_m, -STW - 0.5, STW + 0.5, -0.7, 0.0, Z_TOP, Z_PLAT)
colbox(-STW - 0.5, STW + 0.5, Z_TOP, Z_PLAT, 0.0, -1.5, 1)
# 逐级：踏步 0.48 米深，顶面按地面中线 +0.1，单调下降、每级高差 0.06–0.22
steps = []
z = Z_PLAT
yprev = 0.0
while z < Z_END - 1e-6:
    z1 = min(Z_END, z + 0.48)
    target = ground((z + z1) / 2) + 0.1
    y = max(min(yprev, target), yprev - 0.22)     # 不往上走，一级最多落 0.22
    if yprev - y < 0.06:
        y = yprev                                 # 落差太小就并成一段平台
    steps.append((z, z1, y))
    yprev = y
    z = z1
for (z0, z1, y) in steps:
    box(step_m, -STW, STW, y - 0.16 - 0.5, y, z0, z1 + 0.02)
    colbox(-STW, STW, z0, z1, y, y - 1.5, 1)
# 垂带石与栏杆：两侧，望柱每 ~2.4 米，栏板面凿西番草
for sx in (-1, 1):
    xa, xb = sx * STW, sx * (STW + 0.4)
    lo, hi = min(xa, xb), max(xa, xb)
    pts = [(Z_TOP, 0.0), (Z_PLAT, 0.0)] + [((z0 + z1) / 2, y) for z0, z1, y in steps] + [(Z_END, steps[-1][2])]
    for (za, ya), (zb, yb) in zip(pts, pts[1:]):
        q = [(lo, ya + 0.12, za), (hi, ya + 0.12, za), (hi, yb + 0.12, zb), (lo, yb + 0.12, zb)]
        step_m.poly(q[::-1])
        for xx in (lo, hi):
            q = [(xx, ya + 0.12, za), (xx, yb + 0.12, zb), (xx, min(ya, yb) - 0.9, zb), (xx, min(ya, yb) - 0.9, za)]
            step_m.poly(q if (xx == hi) else q[::-1])
    # 望柱、栏板
    posts = [pts[0]]
    acc = 0
    for (za, ya), (zb, yb) in zip(pts, pts[1:]):
        acc += zb - za
        if acc >= 2.3:
            posts.append((zb, yb))
            acc = 0
    if posts[-1][0] < Z_END - 0.5:
        posts.append(pts[-1])
    xm = sx * (STW + 0.2)
    for zp, yp in posts:
        box(rail, xm - 0.11, xm + 0.11, yp + 0.12, yp + 1.12, zp - 0.11, zp + 0.11)
        # 柱头：仰覆莲（两层圆盘）+ 宝珠
        cyl(rail, xm, zp, yp + 1.12, yp + 1.2, 0.13, 12)
        for k in range(8):
            a0, a1 = k / 8 * math.pi, (k + 1) / 8 * math.pi
            r0, r1 = 0.12 * math.sin(a0), 0.12 * math.sin(a1)
            y0_, y1_ = yp + 1.2 + 0.12 - 0.12 * math.cos(a0), yp + 1.2 + 0.12 - 0.12 * math.cos(a1)
            for m in range(10):
                b0, b1 = m / 10 * math.tau, (m + 1) / 10 * math.tau
                rail.quad((xm + r0 * math.cos(b0), y0_, zp + r0 * math.sin(b0)), (xm + r0 * math.cos(b1), y0_, zp + r0 * math.sin(b1)),
                          (xm + r1 * math.cos(b1), y1_, zp + r1 * math.sin(b1)), (xm + r1 * math.cos(b0), y1_, zp + r1 * math.sin(b0)))
        colbox(xm - 0.12, xm + 0.12, zp - 0.12, zp + 0.12, yp + 1.3, yp)
    for (za, ya), (zb, yb) in zip(posts, posts[1:]):
        za_, zb_ = za + 0.11, zb - 0.11
        # 栏板：下 0.15 起，高 0.75，厚 0.1；两面凿西番草
        for side in (-1, 1):
            xx = xm + side * 0.05
            q = [(xx, ya + 0.27, za_), (xx, yb + 0.27, zb_), (xx, yb + 0.87, zb_), (xx, ya + 0.87, za_)]
            u = (zb_ - za_) / (0.6 * 4)
            rail_x.poly(q if side > 0 else q[::-1], [(0, 0), (u, 0), (u, 1), (0, 1)] if side > 0 else [(0, 1), (u, 1), (u, 0), (0, 0)])
        # 扶手（寻杖）与地栿
        for y0_, y1_ in ((0.87, 0.97), (0.12, 0.27)):
            q = [(xm - 0.07, ya + y1_, za_), (xm + 0.07, ya + y1_, za_), (xm + 0.07, yb + y1_, zb_), (xm - 0.07, yb + y1_, zb_)]
            rail.poly(q[::-1])
            for xx in (xm - 0.07, xm + 0.07):
                q = [(xx, ya + y0_, za_), (xx, yb + y0_, zb_), (xx, yb + y1_, zb_), (xx, ya + y1_, za_)]
                rail.poly(q if xx > xm else q[::-1])
        L = math.hypot(zb_ - za_, yb - ya)
        colbox(xm - 0.08, xm + 0.08, za_, zb_, max(ya, yb) + 1.0, min(ya, yb))
# 月台两侧栏杆（接到台基角）
for sx in (-1, 1):
    xm = sx * (STW + 0.2)
    colbox(xm - 0.08, xm + 0.08, Z_TOP, Z_PLAT, 1.0, -0.5)
# 末级外：一块落地踏石，接园外街面
box(step_m, -STW - 0.4, STW + 0.4, steps[-1][2] - 0.6, steps[-1][2] - 0.02, Z_END, Z_END + 0.6)

# ================================================================ 生成对象、导出
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
mats = {}
coll = bpy.context.scene.collection
ntri = 0
for name, part in PARTS.items():
    if not part.f:
        continue
    me = bpy.data.meshes.new('ZM_' + name)
    me.from_pydata([(x, -z, y) for x, y, z in part.v], [], part.f)
    uvl = me.uv_layers.new(name='UVMap')
    for poly, uvs in zip(me.polygons, part.uv):
        for li, uv in zip(poly.loop_indices, uvs):
            uvl.data[li].uv = uv
    me.validate()
    me.update()
    mn = 'M_' + part.mat
    if mn not in mats:
        m = bpy.data.materials.new(mn)
        m.use_nodes = True
        mats[mn] = m
    me.materials.append(mats[mn])
    ob = bpy.data.objects.new('ZM_' + name, me)
    coll.objects.link(ob)
    ntri += sum(len(p.vertices) - 2 for p in me.polygons)
print('parts', len(PARTS), 'tris', ntri, 'steps', len(steps), 'step y', [round(s[2], 2) for s in steps[::6]])
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.export_scene.gltf(filepath=DST, export_format='GLB', export_yup=True, export_apply=True, export_texcoords=True,
                          export_normals=True, export_materials='EXPORT')
colp = os.path.join(REPO, 'models', 'b', 'col.json')
C = json.load(open(colp))
C['gate'] = COL
json.dump(C, open(colp, 'w'), ensure_ascii=False, separators=(',', ':'))
print('->', DST, 'col', len(COL))
