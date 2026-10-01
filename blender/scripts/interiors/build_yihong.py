"""怡红院室内（第十七回、第四十一回；布局参照 references/…/图01-1 怡红院室内空间格局、图01-2 镜壁示意）。
用法：python3 blender/scripts/interiors/build_yihong.py
外壳开门：node tools/glb_cut.mjs（见 blender/README.md「室内」），本脚本只生成室内陈设与碰撞。

  第十七回：只见这几间房内收拾的与别处不同，竟分不出间隔来的。原来四面皆是雕空玲珑木板……
  一槅一槅，或贮书，或设鼎，或安置笔砚，或供设瓶花，或安放盆景。其槅式样，或圆或方，或葵花蕉叶，
  或连环半璧……且满墙皆是随依古董玩器之形抠成的槽子……转过两层纱厨锦槅，果得一门出去。
  第四十一回：迎面一个女孩儿满面含笑迎了出来……原来是一幅画儿……地下踩的砖，皆是碧绿凿花……
  只见一面大镜子……那镜子原是西洋机括，可以开合……又见一副最精致的床帐。

布局（图01-1）：抱厦两头各一榻；正房西头为宝玉卧室（填漆床、暖阁），由多宝格镜壁上的大穿衣镜门进出；
明间居中；东头一间为书房（书架、小门）；明间与东间之间立屏风。
房屋（Blender 坐标）：地面 z=0.80。抱厦 x±7.85、y 4.95–7.84；正房 x±7.65、y 8.16–15.20。
正房前檐柱 y=8，x=±8、±5、±1.8；原有五块木板隔断已由 glb_cut 剪去。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

Z0 = 0.80
new_file()
K = Kit('yihong')
WOOD = '紫檀'
H = 5.2 - Z0          # 隔断到额枋下皮
XG = 7.64             # 山墙内皮（略让出砖台）
YB = 15.19            # 后墙内皮

# ---- 地面：碧绿凿花砖（网页里贴团花） ----
K.box('碧绿凿花砖', -XG, 4.95, Z0, XG, YB, Z0 + 0.012)

# ---- 入口：抱厦明间四扇隔扇门向内敞开 ----
LH = 3.05 - 0.98
for sx in (-1, 1):
    for k in range(2):
        x = sx * (1.62 + k * 0.8)
        with K.at(x, 5.06 + k * 0.07, 0.98, 0 if sx > 0 else 180):
            K.door_leaf('朱漆', 0.8, LH, t=0.05)
K.box('朱漆', -1.62, 4.88, Z0, 1.62, 4.98, Z0 + 0.08)

# ---- 正房前檐（y=8）五间 ----
#  西梢 多宝格 | 西次 板壁（迎面那幅“女孩儿”画） | 明间 圆光罩 | 东次 八方罩 | 东梢 多宝格
bays = [(-7.84, -5.16), (-4.84, -1.96), (-1.64, 1.64), (1.96, 4.84), (5.16, 7.84)]
for i, (a, b) in enumerate(bays):
    cx, w = (a + b) / 2, b - a
    with K.at(cx, 8.0, Z0):
        if i in (0, 4):
            K.duobaoge(WOOD, w, 0.36, 3.0, seed=11 + i, back=False)
            K.box(WOOD, -w / 2, -0.05, 3.0, w / 2, 0.05, 3.06)
            with K.at(0, 0, 3.06):
                K.lattice_partition(WOOD, w, H - 3.06 - 0.12, paper='碧纱')
        elif i == 1:
            K.box(WOOD, -w / 2, -0.06, 0, w / 2, 0.06, H, col=True)               # 板壁
            K.box('白灰墙', -w / 2 + 0.08, -0.07, 0.9, w / 2 - 0.08, -0.06, H - 0.1)
            K.box(WOOD, -w / 2 + 0.05, -0.08, 0.86, w / 2 - 0.05, -0.06, 0.92)
            K.scroll(0, -0.07, 3.55, 1.25, 2.55, face=-1, mount='绫裱', paint='美人画')
        elif i == 2:
            K.luodizhao(WOOD, w, H, shape='round', t=0.1)
        else:
            K.luodizhao(WOOD, w, H, shape='oct', t=0.08)

# ---- 西头：卧室。东界镜壁（x=-5.0）：多宝格 + 大穿衣镜门 + 多宝格，上为横披 ----
XP = -5.0
for (y0, y1, seed) in ((8.2, 10.0, 21), (11.3, YB, 23)):
    with K.at(XP, (y0 + y1) / 2, Z0, 90):            # 正面朝东（明间）
        K.duobaoge(WOOD, y1 - y0, 0.36, 3.0, seed=seed, back=False)
        K.box(WOOD, -(y1 - y0) / 2, -0.19, 0.0, (y1 - y0) / 2, 0.19, 0.75)        # 下为柜门裙板
        for k in range(int((y1 - y0) / 0.6)):
            x = -(y1 - y0) / 2 + 0.3 + k * 0.6
            K.box('画绢', x - 0.24, -0.2, 0.1, x + 0.24, -0.19, 0.65)
    with K.at(XP, (y0 + y1) / 2, Z0 + 3.0, 90):
        K.lattice_partition(WOOD, y1 - y0, H - 3.0 - 0.12, paper='碧纱')
# 镜门：门轴在南框 y=10.05，关上时镜面朝东；向卧室推开 45°（“西洋机括，可以开合”）
with K.at(XP, 10.05, Z0, 90 + 45):
    with K.at(0.6, 0, 0):
        K.mirror(WOOD, w=1.2, h=2.5, frame=0.12, stand=False, col=False, glass='穿衣镜', oval=True)
K.col(XP - 0.45, 10.05, Z0, XP, 10.5, Z0 + 2.6)
K.col(XP - 0.85, 10.45, Z0, XP - 0.4, 10.9, Z0 + 2.6)
with K.at(XP, 10.65, Z0 + 2.6, 90):
    K.lattice_partition(WOOD, 1.3, H - 2.6 - 0.12, paper='碧纱')

# 宝玉的床（填漆床）：靠西山墙，床口朝东
with K.at(-6.75, 12.7, Z0, 90):
    K.bed('朱漆', w=2.3, d=1.65, H=2.45, curtain='锦帐', quilt='锦缎', pillow='锦缎黄', frieze='描金')
with K.at(-5.75, 12.7, Z0, 90):
    K.box(WOOD, -1.0, -0.2, 0, 1.0, 0.2, 0.14, col=True)                          # 脚踏
with K.at(-5.95, 14.75, Z0):                                                    # 熏笼
    K.lathe('铜', 0, 0, 0, [(0.2, 0), (0.28, 0.25), (0.3, 0.42), (0.26, 0.48)], seg=18)
    for i in range(10):
        a = 2 * math.pi * i / 10
        K.rod('铜', (0.27 * math.cos(a), 0.27 * math.sin(a), 0.48), (0.12 * math.cos(a), 0.12 * math.sin(a), 0.75), 0.008, seg=4)
    K.col(-0.3, -0.3, 0, 0.3, 0.3, 0.75)
# 暖阁（卧室南头）：炕 + 炕桌，碧纱橱相隔
with K.at(-6.3, 8.75, Z0):
    K.kang(WOOD, 2.0, 0.85, mat_cushion='锦缎', back=0.35)
with K.at(-6.3, 9.9, Z0):
    K.lattice_partition(WOOD, 2.5, 2.6, paper='碧纱', door=(0.4, 1.25))
with K.at(-7.3, 11.0, Z0, 90):                                                  # 镜台
    K.table(WOOD, 0.8, 0.45, 0.8)
    with K.at(0, 0.12, 0.8):
        K.mirror('紫檀', w=0.42, h=0.5, frame=0.04, stand=False, col=False)
    K.vase('粉彩', -0.3, 0.05, 0.8, 0.2, 'danping', flowers=3, fcol='花红')
with K.at(-6.75, 11.0, Z0):
    K.stool('锦缎', top='描金')

# ---- 明间：罗汉床、一对圈椅茶几、红毡、横披对联 ----
K.carpet('红毡', -3.6, 9.2, 3.0, 14.4, Z0 + 0.012)
with K.at(0, 14.72, Z0):
    K.kang(WOOD, 2.4, 0.95, mat_cushion='锦缎')
    with K.at(0, 0.02, 0.45 + 0.06 + 0.3):
        K.teaset(0.15, 0.0, 0)
with K.at(0, YB, 0):
    K.box('紫檀', -1.6, -0.04, Z0 + 2.15, 1.6, 0.0, Z0 + 2.95)
    K.box('横披', -1.5, -0.05, Z0 + 2.22, 1.5, -0.03, Z0 + 2.88)
    for sx in (-1, 1):
        K.scroll(sx * 2.05, -0.01, Z0 + 3.4, 0.42, 2.3, face=-1, mount='绫裱', paint='书页')
for sx in (-1, 1):
    for yy in (11.0, 12.9):
        with K.at(sx * 2.3 - (0.4 if sx > 0 else 0), yy, Z0, 90 if sx < 0 else -90):
            K.chair(WOOD, 'quan', cushion='锦缎')
    with K.at(sx * 2.35 - (0.4 if sx > 0 else 0), 11.95, Z0):
        K.table(WOOD, 0.45, 0.45, 0.72)
        K.vase('青花', 0, 0, 0.72, 0.28, 'meiping')
# 明间与东间之间的屏风
with K.at(3.45, 12.2, Z0, 90):
    K.screen(WOOD, 2.6, 2.3, panels=4, silk='画绢', fold=12)
for (x, y) in ((-2.6, 10.2), (1.6, 10.2), (-2.6, 13.6), (1.6, 13.6)):
    K.lantern(x, y, 5.55, drop=0.7)
K.lantern(0, 6.4, 4.1, drop=0.25)

# ---- 东头：书房（书架、书案、满墙古董槽子） ----
for y in (9.0, 10.05, 11.1, 14.0):
    with K.at(XG - 0.22, y, Z0, -90):
        K.shelf(WOOD, 1.0, 0.42, 2.6, rows=6, fill=0.9)
with K.at(XG, 12.55, Z0, -90):                                                  # 嵌墙槽子板
    K.box(WOOD, -0.75, 0.0, 0.9, 0.75, 0.06, 3.4)
    K.box('黑漆', -0.62, -0.015, 1.25, 0.62, 0.0, 1.4)
    K.box('黑漆', -0.6, -0.035, 1.28, 0.55, -0.015, 1.37)                         # 琴
    K.box('描金', 0.43, -0.04, 1.29, 0.53, -0.02, 1.36)
    K.box('黑漆', -0.12, -0.015, 1.7, 0.12, 0.0, 2.5)
    K.vase('青瓷', 0, -0.06, 1.75, 0.6, 'danping')                                # 悬瓶
    K.box('黑漆', 0.42, -0.015, 1.6, 0.5, 0.0, 2.9)
    K.bar('铜', (0.46, -0.03, 1.65), (0.46, -0.03, 2.85), 0.03, 0.01)            # 剑
    K.box('黑漆', -0.6, -0.015, 1.7, -0.28, 0.0, 2.3)
    K.box('画绢', -0.57, -0.03, 1.78, -0.31, -0.015, 2.22)                        # 桌屏
    K.col(-0.75, -0.05, 0, 0.75, 0.06, 3.4)
with K.at(5.95, 12.5, Z0, 90):
    K.qiaotou(WOOD, 1.7, 0.6, 0.84)
    K.study_set(0.1, 0.02, 0.84, 0)
    K.vase('青瓷', -0.65, 0.1, 0.84, 0.3, 'gu', flowers=4, fcol='花白')
with K.at(5.3, 12.5, Z0, 90):
    K.chair(WOOD, 'guanmao', cushion='锦缎')
K.candle_stand(5.4, 9.6, Z0)
K.lantern(6.3, 11.8, 5.55, drop=0.7)
# 东间与明间：落地罩（开敞）
with K.at(5.0, (8.16 + YB) / 2, Z0, 90):
    K.luodizhao(WOOD, YB - 8.16, H, shape='arch', t=0.07)

# ---- 抱厦：两头各一榻、花几盆景、地毡 ----
K.carpet('红毡', -1.8, 5.3, 1.8, 7.6, Z0 + 0.012)
for sx in (-1, 1):
    with K.at(sx * 6.55, 6.45, Z0, -90 * sx):
        K.kang(WOOD, 2.2, 0.85, mat_cushion='锦缎', back=0.3)
    with K.at(sx * 3.4, 7.45, Z0):
        K.table(WOOD, 0.45, 0.45, 0.95, stretch=True)
        K.penjing(0, 0, 0.95, 0.42)

# ---- 天花、墙面 ----
K.ceiling(-XG, 8.16, XG, YB, 5.55, cell=0.64)
K.ceiling(-7.84, 5.02, 7.84, 7.9, 4.06, cell=0.64)
for sx in (-1, 1):
    K.wall_finish((sx * XG, 8.16), (sx * XG, YB), Z0, 5.5, (-sx, 0))
K.wall_finish((-XG, YB), (XG, YB), Z0, 5.5, (0, -1), dado=0.95)

# ---- 外壳碰撞：抱厦/正房墙体（实心块已去） ----
W = []
W.append([-8.0, 4.85, Z0, -1.66, 5.0, 4.1, False])
W.append([1.66, 4.85, Z0, 8.0, 5.0, 4.1, False])
for sx in (-1, 1):
    W.append([min(sx * 7.84, sx * 8.0), 4.9, Z0, max(sx * 7.84, sx * 8.0), 7.9, 4.1, False])
    W.append([min(sx * XG, sx * 8.31), 7.65, Z0, max(sx * XG, sx * 8.31), 15.85, 5.8, False])
W.append([-8.0, YB, Z0, 8.0, 15.8, 5.8, False])
W.append([-8.0, 3.0, 4.1, 8.0, 7.95, 4.7, False])     # 抱厦顶连前廊（挡相机）
W.append([-8.0, 7.95, 5.55, 8.0, 15.5, 6.2, False])   # 正房顶
for x in (-8, -5, -1.8, 1.8, 5, 8):
    for y in (4.0, 4.9, 8.0):
        W.append([x - 0.16, y - 0.16, Z0, x + 0.16, y + 0.16, 4.1 if y < 8 else 5.6, False])


def solid_hall(b):
    lx, lz, hx, hz, top, bot = b
    return abs(lx) < 1 and -13 < lz < -5 and hx > 7 and hz > 1 and bot > 0.75 and top - bot > 1.0


save_and_export(K, shell_cols_filter=solid_hall, extra_cols=W)
