"""大观楼室内：顾恩思义殿（正殿）+ 缀锦阁 / 含芳阁底层（坐标与 blender/daguan.blend 相同）。
用法：flock /tmp/coljson.lock python3 blender/scripts/interiors/build_daguan.py
外壳开门：先跑 blender/scripts/sites/daguan_doors.py（正殿明间、两阁底层明间隔扇已剪去，殿内/阁内“室内暗”黑板已删）。

  第十八回：省亲别墅正殿，匾「顾恩思义」，对联「天地启宏慈，赤子苍头同感戴；古今垂旷典，九州万国被恩荣。」
    殿内：宝座居中靠后（地平上）、屏风、香几香炉、仙鹤烛台一对、宫灯、宫扇。殿心留空（宴席大桌由游戏另放）。
  第四十回：刘姥姥一行在缀锦阁底下吃酒，凤姐命人把楼上的围屏、桌椅、大小花灯之类搬下来——
    缀锦阁底层：沿墙堆着折起的围屏、高几、大小花灯，靠东墙一道楼梯上楼；阁心留空。
  含芳阁（西）：镜像楼梯，沿墙条案、椅、灯，阁心留空。

房间（Blender 坐标）：
  正殿：x ±14.3，y 15.2…26.6，地 z=2.11（金砖面 2.122），顶 7.24（天花）。明间门 x ±2.17、y≈14.8。
  缀锦阁底层：x 28.7…37.28，y 15.35…22.78，地 z=0.9，顶（楼板底）5.6。明间门 x 31.64…34.36、y≈15。
  含芳阁底层：x 取负（镜像）。
Tripo 占位块：材质一律 'TRIPO占位'（网页隐藏并在原处放 Tripo 模型），带碰撞。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

new_file()
K = Kit('daguan')
TAN, RED, GOLD, LI = '紫檀', '朱漆', '描金', '花梨'
TRIPO = []


def tripo(name, cx, cy, z0, sx, sy, sz, face):
    """Tripo 雕塑件占位块（材质 TRIPO占位，带碰撞）。"""
    K.box('TRIPO占位', cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z0 + sz, col=True)
    TRIPO.append((name, round(cx, 2), round(cy, 2), round(z0, 3), sx, sy, sz, face))


# ============================================================ 顾恩思义殿
Z0 = 2.11
ZF = Z0 + 0.012
XL, XR, YF, YB, ZC = -14.3, 14.3, 15.2, 26.6, 7.24
K.box('金砖', XL, YF, Z0, XR, YB, ZF)
K.ceiling(XL - 0.03, YF - 0.03, XR + 0.03, YB + 0.03, ZC, cell=1.2)

# ---- 明间四扇隔扇门敞开，向殿内（+y）折到门框两侧（朱漆，与外壳同色） ----
for x_h, sgn in ((-2.12, 1), (2.12, -1)):
    for k in range(2):
        with K.at(x_h + sgn * 0.065 * k, 14.9, Z0 + 0.19, 90):
            K.door_leaf(RED, 1.07, 3.86, t=0.05)

# ---- 甬道红毡：门口到地平前 ----
K.carpet('红毡', -1.2, 15.4, 1.2, 21.3, ZF)

# ---- 地平（宝座台）：紫檀须弥座式，前出两级踏跺 ----
DX, DY0, DY1, DH = 3.3, 22.6, 26.2, 0.45
K.box(TAN, -DX, DY0, ZF, DX, DY1, ZF + DH - 0.06, col=True)
K.box(GOLD, -DX - 0.02, DY0 - 0.02, ZF + 0.12, DX + 0.02, DY1 + 0.02, ZF + 0.16)       # 腰线描金
K.box(TAN, -DX - 0.04, DY0 - 0.04, ZF + DH - 0.06, DX + 0.04, DY1 + 0.04, ZF + DH)       # 面
K.carpet('红毡', -DX + 0.1, DY0 + 0.1, DX - 0.1, DY1 - 0.1, ZF + DH)
for i, (dy, h) in enumerate(((0.62, 0.15), (0.31, 0.3))):                                 # 踏跺
    K.box(TAN, -1.3, DY0 - dy, ZF, 1.3, DY0 - dy + 0.31, ZF + h, col=True)
    K.box(GOLD, -1.3, DY0 - dy - 0.005, ZF + h - 0.02, 1.3, DY0 - dy + 0.005, ZF + h)
ZD = ZF + DH + 0.01

# ---- 宝座（Tripo）居中靠后，面朝殿门（−Y） ----
tripo('宝座', 0.0, 24.75, ZD, 1.7, 1.15, 1.75, '-Y')
# 脚踏
K.box(TAN, -0.55, 23.85, ZD, 0.55, 24.15, ZD + 0.14, col=True)
K.box('锦缎黄', -0.5, 23.88, ZD + 0.14, 0.5, 24.12, ZD + 0.16)

# ---- 屏风：五扇紫檀描金框、画绢心，立在宝座后 ----
with K.at(0, 25.85, ZD):
    K.screen(TAN, 4.6, 3.1, panels=5, silk='画绢', fold=0)
    K.box(GOLD, -2.32, -0.04, 3.1, 2.32, 0.04, 3.16)
    for i in range(9):                       # 屏帽描金云头
        K.sph(GOLD, -2.0 + i * 0.5, 0, 3.22, 0.12, 0.03, 0.08, seg=8)

# ---- 宫扇一对：宝座两侧、屏风前 ----
for sx in (-1, 1):
    x, y = sx * 1.55, 25.45
    K.cyl(TAN, x, y, ZD, ZD + 0.08, 0.2, seg=10)
    K.cyl(TAN, x, y, ZD, ZD + 2.55, 0.025, seg=8)
    K.sph(GOLD, x, y, ZD + 2.55, 0.05, seg=8)
    K.sph('锦缎黄', x, y - 0.02, ZD + 2.95, 0.46, 0.025, 0.52, seg=18)        # 扇面（团扇式）
    K.sph(GOLD, x, y - 0.03, ZD + 2.95, 0.5, 0.012, 0.56, seg=18)             # 描金边
    K.sph('锦缎', x, y - 0.05, ZD + 2.95, 0.16, 0.01, 0.18, seg=12)           # 团花
    K.col(x - 0.2, y - 0.2, ZD, x + 0.2, y + 0.2, ZD + 2.5)

# ---- 香几 + 香炉（Tripo）：地平前当中 ----
HX, HY = 0.0, 21.75
K.lathe(TAN, HX, HY, ZF, [(0.28, 0), (0.3, 0.05), (0.18, 0.12), (0.12, 0.2), (0.1, 0.78), (0.3, 0.84), (0.34, 0.9), (0.34, 0.94), (0.0, 0.94)], seg=12)
for i in range(4):
    a = math.pi / 4 + i * math.pi / 2
    K.rod(TAN, (HX + 0.27 * math.cos(a), HY + 0.27 * math.sin(a), ZF + 0.88), (HX + 0.3 * math.cos(a), HY + 0.3 * math.sin(a), ZF + 0.05), 0.025, seg=6)
K.col(HX - 0.34, HY - 0.34, ZF, HX + 0.34, HY + 0.34, ZF + 0.94)
tripo('香炉', HX, HY, ZF + 0.94, 0.5, 0.5, 0.6, '-Y')

# ---- 仙鹤烛台一对（Tripo）：地平前两侧 ----
for sx in (-1, 1):
    tripo('仙鹤烛台' + ('西' if sx < 0 else '东'), sx * 3.75, 22.2, ZF, 0.6, 0.7, 1.9, '-Y')

# ---- 匾「顾恩思义」：屏风上方后墙 ----
K.box(TAN, -1.75, 26.48, 6.05, 1.75, 26.6, 7.08)
K.box(GOLD, -1.68, 26.45, 6.12, 1.68, 26.5, 7.01)
K.box('顾恩思义匾', -1.56, 26.43, 6.2, 1.56, 26.46, 6.93)
# ---- 对联：屏风两侧后墙（上联在东＝观者右手，下联在西） ----
for sx, m in ((1, '殿联上'), (-1, '殿联下')):
    x = sx * 3.55
    K.box(TAN, x - 0.3, 26.48, 2.75, x + 0.3, 26.6, 6.55)
    K.box(GOLD, x - 0.26, 26.45, 2.79, x + 0.26, 26.5, 6.51)
    K.box(m, x - 0.22, 26.43, 2.84, x + 0.22, 26.46, 6.46)

# ---- 两次间：靠后墙条案、瓶、炉；落地宫灯 ----
for sx in (-1, 1):
    with K.at(sx * 6.0, 26.25, ZF):
        K.qiaotou(TAN, 2.4, 0.5, 0.92)
        K.vase('青花', -0.75, 0, 0.92, 0.5, 'meiping')
        K.vase('青花', 0.75, 0, 0.92, 0.5, 'meiping')
        K.ding('铜', 0, 0, 0.92, 0.3)
    for y in (17.2, 21.0):
        K.candle_stand(sx * 5.4, y, ZF, h=1.7)
        K.col(sx * 5.4 - 0.18, y - 0.18, ZF, sx * 5.4 + 0.18, y + 0.18, ZF + 1.7)
# ---- 梢间、尽间：靠墙一对宝座式扶手椅夹几（陪坐）、大瓶 ----
for sx in (-1, 1):
    for y in (18.2, 22.0):
        with K.at(sx * 12.9, y, ZF, 90 if sx < 0 else -90):
            K.chair(TAN, 'guanmao', cushion='锦缎黄')
    with K.at(sx * 12.9, 20.1, ZF):
        K.table(TAN, 0.55, 0.55, 0.78, top=0.04, leg=0.05, apron=0.06)
        K.vase('粉彩', 0, 0, 0.78, 0.36, 'yuhuchun')
    K.vase('青花', sx * 13.7, 25.9, ZF, 1.1, 'guan')
    K.col(sx * 13.7 - 0.22, 25.68, ZF, sx * 13.7 + 0.22, 26.12, ZF + 1.1)
    K.vase('青花', sx * 13.7, 15.85, ZF, 1.1, 'guan')
    K.col(sx * 13.7 - 0.22, 15.63, ZF, sx * 13.7 + 0.22, 16.07, ZF + 1.1)

# ---- 宫灯：天花下垂挂 ----
for x, y in ((-4.2, 18.6), (4.2, 18.6), (-4.2, 23.4), (4.2, 23.4), (-9.2, 20.9), (9.2, 20.9), (-12.6, 20.9), (12.6, 20.9), (0, 18.4)):
    K.lantern(x, y, ZC - 0.05, drop=1.1)


# ============================================================ 缀锦阁 / 含芳阁 底层
GZ = 0.9
GZC = 5.6
GY0, GY1 = 15.35, 22.78


def pavilion(sx, east):
    """sx=+1 缀锦阁（东），−1 含芳阁（西）；局部用 X(u) = sx*u，u∈[28.7, 37.28]。"""
    X = lambda u: sx * u
    def bx(m, u0, y0, z0, u1, y1, z1, col=False):
        a, b = sorted((X(u0), X(u1)))
        K.box(m, a, y0, z0, b, y1, z1, col)
    def cl(u0, y0, z0, u1, y1, z1):
        a, b = sorted((X(u0), X(u1)))
        K.col(a, y0, z0, b, y1, z1)
    bx('金砖', 28.7, GY0, GZ, 37.28, GY1, GZ + 0.012)
    zf = GZ + 0.012
    # 走马板：外壳墙只砌到 4.0，墙顶到楼板底（5.6）之间是空的（原来靠“室内暗”板挡），这里四面封上
    bx('赭墙', 28.69, GY0 - 0.04, 3.98, 28.75, GY1 + 0.02, GZC)
    bx('赭墙', 37.25, GY0 - 0.04, 3.98, 37.31, GY1 + 0.02, GZC)
    bx('赭墙', 28.69, GY1 - 0.02, 3.98, 37.31, GY1 + 0.04, GZC)
    bx('赭墙', 28.69, 15.31, 4.0, 37.31, 15.37, GZC)
    for u in (28.75, 37.25):
        bx(RED, u - 0.03, GY0, 3.95, u + 0.03, GY1, 4.05)
    # 明间四扇隔扇门敞开，贴两侧门框
    for u_h, s in ((31.66, 1), (34.34, -1)):
        for k in range(2):
            with K.at(X(u_h + s * 0.065 * k), 15.1, GZ + 0.2, 90):
                K.door_leaf(RED, 0.68, 2.2, t=0.045)
    # ---- 楼梯：贴“外”侧山墙（u 35.95…37.25），自南向北上，上段没入楼井 ----
    U0, U1 = 35.95, 37.25
    N, RISE, RUN, YS = 18, (GZC - GZ) / 18, 0.27, 17.0
    for i in range(N):
        z = GZ + (i + 1) * RISE
        y = YS + i * RUN
        bx(LI, U0 + 0.06, y, z - 0.04, U1, y + RUN + 0.02, z)                       # 踏板
        bx(LI, U0 + 0.06, y - 0.005, z - RISE, U1, y + 0.02, z - 0.04)              # 踢板
        if i < 9:                                                                    # 下半段可走
            cl(U0 + 0.06, y, z - 0.3, U1, y + RUN, z)
    ytop = YS + N * RUN
    # 斜梁（朱漆），外侧扶手、望柱
    for u in (U0, U1 - 0.02):
        a, b = sorted((X(u), X(u + 0.06 if u == U0 else u + 0.02)))
        K.bar(RED, ((a + b) / 2, YS - 0.1, GZ + 0.05), ((a + b) / 2, ytop, GZC - 0.05), 0.07 if u == U0 else 0.03, 0.22)
    for i in range(0, N + 1, 3):
        y = YS + i * RUN
        z = GZ + i * RISE
        K.box(RED, X(U0) - 0.03, y - 0.03, z, X(U0) + 0.03, y + 0.03, min(z + 0.95, GZC))
    K.bar(RED, (X(U0), YS, GZ + 0.95), (X(U0), ytop, GZC + 0.95), 0.05, 0.05)
    cl(U0 - 0.06, YS + 0.6, GZ, U0 + 0.02, GY1, GZ + 4.5)                         # 扶手侧挡
    cl(U0 - 0.06, YS + 9 * RUN, GZ, U1, GY1, GZC)                                  # 上半段（不可走）
    # 楼井：楼板底开口（黑），围一圈朱漆边
    yw = YS + 9.5 * RUN
    bx('daguan_室内暗', U0 - 0.05, yw, GZC - 0.02, 37.28, GY1, GZC - 0.005)
    bx(RED, U0 - 0.12, yw - 0.07, GZC - 0.12, U0 - 0.05, GY1, GZC - 0.005)
    bx(RED, U0 - 0.12, yw - 0.07, GZC - 0.12, 37.28, yw, GZC - 0.005)
    # 楼梯下封板
    bx(RED, U1 - 0.02, YS, GZ, U1, ytop, GZ + 0.25)

    if east:
        # ---- 缀锦阁：凤姐命人把楼上的围屏、桌椅、大小花灯搬下来 ----
        # 西（内）侧山墙：两架折起的大围屏
        with K.at(X(29.05), 19.4, zf, 90 if sx > 0 else -90):
            K.screen(TAN, 3.4, 2.6, panels=6, silk='山水图', fold=32)
        with K.at(X(29.25), 16.6, zf, 90 if sx > 0 else -90):
            K.screen(TAN, 1.8, 2.2, panels=4, silk='画绢', fold=40)
        # 两扇卸下的围屏平摞在地（叠放）
        for k in range(3):
            bx(TAN, 29.2 + k * 0.02, 21.25, zf + k * 0.06, 31.1 - k * 0.02, 22.15, zf + k * 0.06 + 0.055)
            bx('画绢', 29.4 + k * 0.02, 21.35, zf + k * 0.06 + 0.055, 30.9 - k * 0.02, 22.05, zf + k * 0.06 + 0.06)
        cl(29.2, 21.25, zf, 31.1, 22.15, zf + 0.2)
        # 北墙：一排高几，几上小花灯
        for u in (31.6, 32.4, 33.2):
            with K.at(X(u), 22.4, zf):
                K.table(TAN, 0.42, 0.42, 1.1, top=0.03, leg=0.035, apron=0.05, stretch=True)
                K.lathe('紫檀', 0, 0, 1.1, [(0.1, 0), (0.1, 0.03), (0.03, 0.05), (0.03, 0.12)], seg=8)
                K.lathe('窗纸', 0, 0, 1.22, [(0.07, 0), (0.15, 0.08), (0.15, 0.26), (0.07, 0.34)], seg=10)
                K.sph('锦缎', 0, 0, 1.58, 0.03, seg=6)
        # 北墙东段：条桌一张，上摞椅子两把（倒扣），桌前大花灯两盏（落地）
        with K.at(X(34.4), 22.35, zf):
            K.table(LI, 1.3, 0.55, 0.85, top=0.04, leg=0.05, apron=0.06)
            with K.at(-0.32, 0, 0.85):
                K.box('锦缎黄', -0.25, -0.2, 0, 0.25, 0.2, 0.05)
            with K.at(0.32, 0, 0.85):
                K.lathe('窗纸', 0, 0, 0, [(0.1, 0), (0.2, 0.1), (0.2, 0.3), (0.1, 0.4)], seg=10)
        for u in (29.3,):
            K.candle_stand(X(u), 15.9, zf, h=1.6)
            cl(u - 0.18, 15.72, zf, u + 0.18, 16.08, zf + 1.6)
        # 落地走马灯（大花灯）一盏
        with K.at(X(30.0), 20.6, zf):
            K.lathe(TAN, 0, 0, 0, [(0.25, 0), (0.25, 0.05), (0.05, 0.1), (0.04, 0.9)], seg=8)
            K.lathe('窗纸', 0, 0, 0.9, [(0.15, 0), (0.32, 0.12), (0.34, 0.45), (0.3, 0.62), (0.12, 0.7)], seg=12)
            K.lathe('锦缎', 0, 0, 1.6, [(0.14, 0), (0.18, 0.04), (0.0, 0.1)], seg=12)
            for i in range(8):
                a = i * math.pi / 4
                K.rod('锦缎', (0.33 * math.cos(a), 0.33 * math.sin(a), 1.5), (0.35 * math.cos(a), 0.35 * math.sin(a), 1.15), 0.008, seg=4)
        cl(29.7, 20.3, zf, 30.3, 20.9, zf + 1.7)
        # 悬挂花灯
        for u, y in ((31.6, 18.0), (33.8, 18.0), (31.6, 20.4), (33.8, 20.4)):
            K.lantern(X(u), y, GZC - 0.02, drop=0.45)
    else:
        # ---- 含芳阁：素一些，沿墙条案、对椅、花瓶、宫灯 ----
        with K.at(X(29.05), 19.0, zf, 90 if sx > 0 else -90):
            K.qiaotou(TAN, 2.2, 0.48, 0.9)
            K.vase('青花', 0.6, 0, 0.9, 0.42, 'meiping')
            K.penjing(-0.5, 0, 0.9, 0.42)
        with K.at(X(28.71), 19.0, 0, -90 if sx > 0 else 90):
            K.scroll(0, 0, 4.0, 1.0, 1.7, face=-1, paint='山水图')
        for y in (17.1, 20.9):
            with K.at(X(29.4), y, zf, 90 if sx > 0 else -90):
                K.chair(TAN, 'guanmao', cushion='锦缎')
        with K.at(X(33.0), 22.4, zf):
            K.table(TAN, 0.42, 0.42, 1.0, top=0.03, leg=0.035, apron=0.05, stretch=True)
            K.vase('粉彩', 0, 0, 1.0, 0.34, 'danping', flowers=6, fcol='花红')
        K.candle_stand(X(29.3), 15.9, zf, h=1.6)
        cl(29.12, 15.72, zf, 29.48, 16.08, zf + 1.6)
        for u, y in ((31.8, 18.6), (33.8, 20.4)):
            K.lantern(X(u), y, GZC - 0.02, drop=0.45)


pavilion(1, True)
pavilion(-1, False)

for t in TRIPO:
    print('TRIPO', t)
save_and_export(K)
