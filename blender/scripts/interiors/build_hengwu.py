"""蘅芜苑室内（第四十回；参照 references/…/图03-1 蘅芜苑内景）。
用法：python3 blender/scripts/interiors/build_hengwu.py

  第四十回：及进了房屋，雪洞一般，一色玩器全无，案上只有一个土定瓶中供着数枝菊花，并两部书，
  茶奁茶杯而已。床上只吊着青纱帐幔，衾褥也十分朴素。

清厦（Blender 坐标）：地面 z=0.75，室内 x ±7.95、y 4.68…10.32；五间，檐柱 x=±1.8、±5.1、±8.1。
外壳改动（tools/glb_cut.mjs）：剪去前檐明间四扇隔扇（此处做成全开）。
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

K.box('方砖地', -X1, Y0, Z0, X1, Y1, Z0 + 0.01)
# “雪洞一般”：四壁、顶棚一色白
K.box('白灰墙', -X1, Y0, ZC, X1, Y1, ZC + 0.04)
for sx in (-1, 1):
    K.wall_finish((sx * X1, Y0), (sx * X1, Y1), Z0, ZC, (-sx, 0), dado=0.12, wood=WOOD)
K.wall_finish((-X1, Y1), (X1, Y1), Z0, ZC, (0, -1), dado=0.12, wood=WOOD)

# ---- 入口：明间隔扇四扇全开 ----
for sx in (-1, 1):
    for k in range(2):
        x = sx * (1.62 + k * 0.8)
        with K.at(x, 4.75 + k * 0.07, Z0 + 0.05, 0 if sx > 0 else 180):
            K.door_leaf('绿漆', 0.8, 2.75, t=0.05)

# ---- 明间：一色玩器全无，只两把椅一张几 ----
with K.at(0, 9.95, Z0):
    K.qiaotou(WOOD, 2.2, 0.5, 0.86)
for sx in (-1, 1):
    with K.at(sx * 0.7, 9.1, Z0):
        K.chair(WOOD, 'guanmao', cushion='素绸')
with K.at(0, 9.1, Z0):
    K.table(WOOD, 0.5, 0.45, 0.74)

# ---- 东间：卧室兼书案。碧纱（素纸）槅扇相隔 ----
with K.at(1.8, (Y0 + Y1) / 2, Z0, -90):
    K.lattice_partition(WOOD, Y1 - Y0, ZC - Z0 - 0.12, paper='窗纸', door=(1.0, 2.2))   # 门在 y 5.1…6.3
with K.at(6.95, 8.4, Z0, -90):
    K.bed(WOOD, w=2.1, d=1.5, H=2.3, curtain='青纱', quilt='素绸', pillow='白布', frieze=WOOD)
with K.at(5.95, 8.4, Z0, -90):
    K.box(WOOD, -0.8, -0.18, 0, 0.8, 0.18, 0.13, col=True)        # 脚踏
# 案上只有土定瓶供菊花、两部书、茶奁茶杯
with K.at(4.1, 5.3, Z0):
    K.table(WOOD, 1.4, 0.6, 0.82)
    K.vase('土定', -0.45, 0.05, 0.82, 0.36, 'guan', flowers=7, fcol='菊黄')
    K.box('书函', 0.05, -0.12, 0.82, 0.32, 0.12, 0.87)
    K.box('书页', 0.06, -0.125, 0.825, 0.31, -0.11, 0.865)
    K.box('书函', 0.08, -0.1, 0.87, 0.3, 0.1, 0.915)
    K.box('书页', 0.09, -0.105, 0.875, 0.29, -0.09, 0.91)
    K.box(WOOD, 0.4, -0.08, 0.82, 0.6, 0.08, 0.95)                 # 茶奁
    for i in range(2):
        K.lathe('瓷白', 0.45 + i * 0.12, 0.18, 0.82, [(0.015, 0), (0.03, 0.02), (0.035, 0.045)], seg=10, cap=False)
with K.at(4.1, 5.95, Z0, 180):
    K.chair(WOOD, 'quan', cushion='素绸')
K.candle_stand(2.4, 9.8, Z0)

# ---- 西间：空空一张素榻 ----
with K.at(-5.5, 9.8, Z0):
    K.kang(WOOD, 2.0, 0.8, mat_cushion='素绸', back=0.3)
with K.at(-1.8, (Y0 + Y1) / 2, Z0, 90):
    K.luodizhao(WOOD, Y1 - Y0, ZC - Z0 - 0.02, shape='arch', t=0.06, carve=False)

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
]


def solid(b):
    lx, lz, hx, hz, top, bot = b
    if abs(lx) < 0.5 and -8 < lz < -6.5 and 7.5 < hx < 10 and 2.5 < hz < 5 and top < 4.5:
        return True                                           # 清厦实心块
    return abs(lx) < 0.5 and abs(lz + 6.77) < 0.1 and hx > 10 and abs(top - 1.71) < 0.05   # 台明误高


save_and_export(K, shell_cols_filter=solid, extra_cols=W)
