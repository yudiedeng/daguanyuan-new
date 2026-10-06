"""蘅芜苑室内（第四十回；参照 references/…/图03-1 蘅芜苑内景）。
用法：python3 blender/scripts/interiors/build_hengwu.py

  第四十回：及进了房屋，雪洞一般，一色玩器全无，案上只有一个土定瓶中供着数枝菊花，并两部书，
  茶奁茶杯而已。床上只吊着青纱帐幔，衾褥也十分朴素。

清厦（Blender 坐标）：地面 z=0.75，室内 x ±7.95、y 4.68…10.32；五间，檐柱 x=±1.8、±5.1、±8.1。
外壳改动（tools/glb_cut.mjs）：剪去前檐明间四扇隔扇，这里重做：两边两扇关着，中间两扇向里半开。
原碰撞把整座台明当成 1.71 m 高的实块（取了石作的包围盒），这里换成真实的 0.75 m 台面。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

Z0 = 0.75
ZC = 3.72
X1, Y0, Y1 = 7.95, 4.68, 10.32
new_file()
K = Kit('hengwu')
WOOD = '花梨'

K.box('金砖地', -X1, Y0, Z0, X1, Y1, Z0 + 0.01)   # 室内墁金砖：深灰、油亮（网页材质 金砖地，不带户外方砖的青苔风化）
# “雪洞一般”：四壁、顶棚一色白
# 顶上：素作井口天花——花梨木支条方格，白板，不描金不彩画（原来是一整块平板）
K.ceiling(-X1 + 0.05, Y0 + 0.05, X1 - 0.05, Y1 - 0.05, ZC, cell=0.62, frame=WOOD, panel='雪洞白', dot=None)
for sx in (-1, 1):
    K.wall_finish((sx * (X1 - 0.05), Y0), (sx * (X1 - 0.05), Y1), Z0, ZC, (-sx, 0), dado=0.12, wood=WOOD, plaster='雪洞白')   # 往里让 5 cm，盖住外壳槛墙压顶石探进来的边
K.wall_finish((-X1, Y1 - 0.05), (X1, Y1 - 0.05), Z0, ZC, (0, -1), dado=0.12, wood=WOOD, plaster='雪洞白')
# 前檐窗下的槛墙内侧也贴白灰、木踢脚（原来露着外壳的青砖，和另三面墙不一样）
for sx in (-1, 1):
    K.wall_finish((sx * X1, Y0 + 0.05), (sx * 1.66, Y0 + 0.05), Z0, 1.71, (0, 1), dado=0.12, wood=WOOD, plaster='雪洞白')

# ---- 入口：明间隔扇四扇——两边两扇关着，中间两扇向里半开（原来做成全开推到两边，从外面看像没有门） ----
for sx in (-1, 1):
    with K.at(sx * 0.81, 4.75, Z0 + 0.05, 0 if sx > 0 else 180):     # 边扇：0.81…1.61，关着
        K.door_leaf('绿漆', 0.8, 2.75, t=0.05)
    with K.at(sx * 0.81, 4.75, Z0 + 0.05, 105 if sx > 0 else 75):    # 中扇：从 ±0.81 处的门轴向里开 75°
        K.door_leaf('绿漆', 0.8, 2.75, t=0.05)

# ---- 前檐槛窗、横披：外壳只有外面一层窗纸，从屋里看是一片白板。里面补一层方格棂（细木条贴在纸里侧） ----
SASH = [(-7.892, -7.333), (-7.217, -6.658), (-6.543, -5.983), (-5.867, -5.308), (-4.893, -4.258), (-4.143, -3.508), (-3.392, -2.758), (-2.642, -2.007)]
TRAN = [(-7.93, -7.07), (-7.03, -6.17), (-6.131, -5.27), (-4.93, -3.97), (-3.929, -2.97), (-2.93, -1.97)]
PY = 4.545        # 窗纸在 y≈4.53，棂条贴在里侧


def grille(x0, x1, z0, z1, cell=0.1, bar=0.012, edge=0.03):
    K.box(WOOD, x0, PY, z0, x1, PY + 0.03, z0 + edge)          # 仔边
    K.box(WOOD, x0, PY, z1 - edge, x1, PY + 0.03, z1)
    K.box(WOOD, x0, PY, z0, x0 + edge, PY + 0.03, z1)
    K.box(WOOD, x1 - edge, PY, z0, x1, PY + 0.03, z1)
    nx = max(2, round((x1 - x0) / cell)); nz = max(2, round((z1 - z0) / cell))
    for i in range(1, nx):
        x = x0 + (x1 - x0) * i / nx
        K.box(WOOD, x - bar / 2, PY, z0, x + bar / 2, PY + 0.018, z1)
    for k in range(1, nz):
        z = z0 + (z1 - z0) * k / nz
        K.box(WOOD, x0, PY, z - bar / 2, x1, PY + 0.018, z + bar / 2)


for sx in (-1, 1):
    for a, b in SASH:
        grille(min(sx * a, sx * b), max(sx * a, sx * b), 2.014, 3.077)
    for a, b in TRAN:
        grille(min(sx * a, sx * b), max(sx * a, sx * b), 3.252, 3.55, cell=0.098)
for a, b in [(-1.63, -0.57), (-0.53, 0.53), (0.57, 1.63)]:      # 门上横披
    grille(a, b, 3.252, 3.55, cell=0.098)

# ---- 家具：Tripo 精细模型，摆在网页 index.html 的 PROPS.hengwu_in（tools/props.json 的 hw_*）。这里只留碰撞 ----
# 明间：条案一张、官帽椅两把（“一色玩器全无”）
K.col(-1.1, 9.7, Z0, 1.1, 10.2, Z0 + 0.86)
for sx in (-1, 1): K.col(sx * 0.7 - 0.3, 8.8, Z0, sx * 0.7 + 0.3, 9.4, Z0 + 1.0)
# ---- 东间：卧室兼书案。碧纱（素纸）槅扇相隔 ----
with K.at(1.8, (Y0 + Y1) / 2, Z0, -90):
    K.lattice_partition(WOOD, Y1 - Y0, ZC - Z0 - 0.12, paper='窗纸', door=(1.0, 2.2), step=0.085, bar=0.011)   # 门在 y 5.1…6.3；细棂密格
K.col(6.2, 7.35, Z0, 7.7, 9.45, Z0 + 2.3)            # 床（青纱帐幔）
with K.at(5.95, 8.4, Z0, -90):
    K.box(WOOD, -0.8, -0.18, 0, 0.8, 0.18, 0.13, col=True)        # 脚踏
K.col(3.4, 5.0, Z0, 4.8, 5.6, Z0 + 0.82)             # 书案：案上土定瓶供菊花、两部书、茶奁茶杯
K.col(3.8, 5.7, Z0, 4.4, 6.25, Z0 + 1.0)             # 圈椅
K.candle_stand(2.4, 9.8, Z0)

# ---- 西间：空空一张素榻 ----
K.col(-6.5, 9.4, Z0, -4.5, 10.2, Z0 + 0.6)
with K.at(-1.8, (Y0 + Y1) / 2, Z0, 90):
    for sx in (-1, 1):       # 落地罩两腿下的木墩（须弥墩），不让格棂直接戳地
        K.box(WOOD, sx * (Y1 - Y0) / 2 - (0.62 if sx > 0 else 0), -0.05, 0, sx * (Y1 - Y0) / 2 + (0 if sx > 0 else 0.62), 0.05, 0.32)
        K.box(WOOD, sx * (Y1 - Y0) / 2 - (0.64 if sx > 0 else 0), -0.055, 0.32, sx * (Y1 - Y0) / 2 + (0 if sx > 0 else 0.64), 0.055, 0.36)
    K.luodizhao(WOOD, Y1 - Y0, ZC - Z0 - 0.02, shape='arch', t=0.06, carve=False, step=0.09, bw=0.012, kazi=False, ring=0.06)   # 素作：细方格棂，不嵌卡子花、不描金

# ---- 外廊细部（外壳 hengwu.blend 只有光柱子、方墩柱础）：倒挂楣子 + 花牙子、鼓镜柱础 ----
# 檐柱：前后檐 y=3.1 / 11.9，x ±9.5 ±8.1 ±5.1 ±1.8；两山 x=±9.5，y 3.1 4.5 7.5 10.5 11.9。额枋底 z=3.69，柱径 0.3
CR = 0.15
ZT = 3.69
MZ = 0.4          # 楣子高


def meizi(L):
    """倒挂楣子（灯笼框）：局部 x ∈ [-L/2, L/2]，挂在额枋下 z ∈ [ZT-MZ, ZT]，面在 y=0。两端各一只透雕花牙子。"""
    zb, f, t, d, b = ZT - MZ, 0.045, 0.05, 0.1, 0.028
    x0, x1 = -L / 2, L / 2
    K.box('绿漆', x0, -t / 2, ZT - f, x1, t / 2, ZT)
    K.box('绿漆', x0, -t / 2, zb, x1, t / 2, zb + f)
    for xa, xb in ((x0, x0 + f), (x1 - f, x1)):
        K.box('绿漆', xa, -t / 2, zb, xb, t / 2, ZT)
    ix0, ix1, iz0, iz1 = x0 + d, x1 - d, zb + d, ZT - d          # 里圈“灯笼框”
    for xa, xb in ((ix0, ix0 + b), (ix1 - b, ix1)):
        K.box('绿漆', xa, -0.018, iz0, xb, 0.018, iz1)
    for za, zb_ in ((iz0, iz0 + b), (iz1 - b, iz1)):
        K.box('绿漆', ix0, -0.018, za, ix1, 0.018, zb_)
    n = max(2, round((ix1 - ix0) / 0.42))                         # 外框—里圈之间的短“卡子”
    for i in range(n + 1):
        x = ix0 + (ix1 - ix0) * (i + 0.5) / (n + 1)
        K.box('绿漆', x - b / 2, -0.018, zb + f, x + b / 2, 0.018, iz0)
        K.box('绿漆', x - b / 2, -0.018, iz1, x + b / 2, 0.018, ZT - f)
    for xa in (x0 + f, ix1):
        K.box('绿漆', xa, -0.018, (iz0 + iz1) / 2 - b / 2, xa + d - f, 0.018, (iz0 + iz1) / 2 + b / 2)
    m = max(2, round((ix1 - ix0) / 0.16))                         # 里圈竖棂
    for i in range(1, m):
        x = ix0 + (ix1 - ix0) * i / m
        K.box('绿漆', x - 0.009, -0.012, iz0, x + 0.009, 0.012, iz1)
    for sx in (-1, 1):                                            # 花牙子：三角透雕，中间一个圆孔
        e, a = sx * L / 2, 0.34
        out = [(e, zb)] + [(e - sx * a * math.cos(math.pi / 2 * k / 8), zb - a * math.sin(math.pi / 2 * k / 8)) for k in range(9)]
        cx, cz = e - sx * a * 0.3, zb - a * 0.3
        hole = [(cx + 0.055 * math.cos(2 * math.pi * k / 12), cz + 0.055 * math.sin(2 * math.pi * k / 12)) for k in range(12)]
        K.poly_panel('枋绿', out, [hole], 0.035)


XS = (-9.5, -8.1, -5.1, -1.8, 1.8, 5.1, 8.1, 9.5)
YS = (3.1, 4.5, 7.5, 10.5, 11.9)
for yr in (3.1, 11.9):
    for a, b in zip(XS, XS[1:]):
        if yr < 5 and a == -1.8:
            continue                       # 前檐明间：外壳已有雀替，留空做门口
        with K.at((a + b) / 2, yr, 0, 0):
            meizi(b - a - 2 * CR)
for xr in (-9.5, 9.5):
    for a, b in zip(YS, YS[1:]):
        with K.at(xr, (a + b) / 2, 0, 90):
            meizi(b - a - 2 * CR)
# 鼓镜柱础：外壳只有两层方墩（0.75…0.93），柱脚再加一圈微鼓的“鼓镜”
for x in XS:
    for y in YS:
        if abs(x) < 9 and 4 < y < 11:
            continue
        K.lathe('青石', x, y, 0.87, [(0.205, 0.0), (0.222, 0.035), (0.215, 0.07), (0.17, 0.095), (0.158, 0.1)], seg=20)

# ---- 外壳碰撞 ----
W = [
    [-10.32, 2.28, -0.01, 10.32, 12.73, Z0, False],          # 台明（真实高度）
    [-1.7, 1.02, -0.01, 1.7, 2.3, 0.15, False], [-1.7, 1.34, -0.01, 1.7, 2.3, 0.30, False],   # 前檐踏跺
    [-1.7, 1.66, -0.01, 1.7, 2.3, 0.45, False], [-1.7, 1.98, -0.01, 1.7, 2.3, 0.60, False],
    [-8.31, 4.32, Z0, -1.66, 4.75, ZC, False],                # 前檐槛墙+槛窗
    [1.66, 4.32, Z0, 8.31, 4.75, ZC, False],
    [-8.31, 10.25, Z0, 8.31, 10.71, ZC, False],               # 后檐
    [-8.31, 4.32, Z0, -X1, 10.71, ZC, False],
    [X1, 4.32, Z0, 8.31, 10.71, ZC, False],
    [-8.31, 4.32, ZC, 8.31, 10.71, ZC + 0.6, False],          # 顶（挡相机）
    [-1.66, 4.32, Z0 + 2.85, 1.66, 4.75, ZC, False],          # 门上横披
    [-1.66, 4.68, Z0, -0.81, 4.82, Z0 + 2.85, False], [0.81, 4.68, Z0, 1.66, 4.82, Z0 + 2.85, False],   # 两扇关着的边扇
]


def solid(b):
    lx, lz, hx, hz, top, bot = b
    if abs(lx) < 0.5 and -8 < lz < -6.5 and 7.5 < hx < 10 and 2.5 < hz < 5 and top < 4.5:
        return True                                           # 清厦实心块
    return abs(lx) < 0.5 and abs(lz + 6.77) < 0.1 and hx > 10 and abs(top - 1.71) < 0.05   # 台明误高


save_and_export(K, shell_cols_filter=solid, extra_cols=W)
