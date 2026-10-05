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

# ---- 家具：Tripo 精细模型，摆在网页 index.html 的 PROPS.hengwu_in（tools/props.json 的 hw_*）。这里只留碰撞 ----
# 明间：条案一张、官帽椅两把（“一色玩器全无”）
K.col(-1.1, 9.7, Z0, 1.1, 10.2, Z0 + 0.86)
for sx in (-1, 1): K.col(sx * 0.7 - 0.3, 8.8, Z0, sx * 0.7 + 0.3, 9.4, Z0 + 1.0)
# ---- 东间：卧室兼书案。碧纱（素纸）槅扇相隔 ----
with K.at(1.8, (Y0 + Y1) / 2, Z0, -90):
    K.lattice_partition(WOOD, Y1 - Y0, ZC - Z0 - 0.12, paper='窗纸', door=(1.0, 2.2))   # 门在 y 5.1…6.3
K.col(6.2, 7.35, Z0, 7.7, 9.45, Z0 + 2.3)            # 床（青纱帐幔）
with K.at(5.95, 8.4, Z0, -90):
    K.box(WOOD, -0.8, -0.18, 0, 0.8, 0.18, 0.13, col=True)        # 脚踏
K.col(3.4, 5.0, Z0, 4.8, 5.6, Z0 + 0.82)             # 书案：案上土定瓶供菊花、两部书、茶奁茶杯
K.col(3.8, 5.7, Z0, 4.4, 6.25, Z0 + 1.0)             # 圈椅
K.candle_stand(2.4, 9.8, Z0)

# ---- 西间：空空一张素榻 ----
K.col(-6.5, 9.4, Z0, -4.5, 10.2, Z0 + 0.6)
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
    [-1.66, 4.68, Z0, -0.81, 4.82, Z0 + 2.85, False], [0.81, 4.68, Z0, 1.66, 4.82, Z0 + 2.85, False],   # 两扇关着的边扇
]


def solid(b):
    lx, lz, hx, hz, top, bot = b
    if abs(lx) < 0.5 and -8 < lz < -6.5 and 7.5 < hx < 10 and 2.5 < hz < 5 and top < 4.5:
        return True                                           # 清厦实心块
    return abs(lx) < 0.5 and abs(lz + 6.77) < 0.1 and hx > 10 and abs(top - 1.71) < 0.05   # 台明误高


save_and_export(K, shell_cols_filter=solid, extra_cols=W)
