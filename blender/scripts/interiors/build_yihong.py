"""怡红院室内（第十七回、第四十一回）。
用法：python3 blender/scripts/interiors/build_yihong.py
外壳开门：node tools/glb_cut.mjs（见 README「室内」一节），本脚本只生成室内陈设与碰撞。

  第十七回：只见这几间房内收拾的与别处不同，竟分不出间隔来的。原来四面皆是雕空玲珑木板……
  一槅一槅，或贮书，或设鼎，或安置笔砚，或供设瓶花，或安放盆景。其槅式样，或圆或方，或葵花蕉叶，
  或连环半璧……且满墙皆是随依古董玩器之形抠成的槽子……转过两层纱厨锦槅，果得一门出去。
  第四十一回：刘姥姥……迎面一个女孩儿满面含笑迎了出来……原来是一幅画儿……又见一副最精致的床帐……
  地下踩的砖，皆是碧绿凿花……刘姥姥掀帘进去，只见一面大镜子……那镜子原是西洋机括，可以开合。

房屋（Blender 坐标）：地面 z=0.80。抱厦 x±7.85、y 4.95–7.84；正房 x±7.69、y 8.16–15.20。
正房前檐柱 y=8，x=±8、±5、±1.8；原有五块木板隔断已由 glb_cut 剪去。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

Z0 = 0.80
new_file()
K = Kit('yihong')
WOOD = '紫檀'

# ---- 地面：碧绿凿花砖 ----
K.box('碧绿凿花砖', -7.68, 4.95, Z0, 7.68, 15.2, Z0 + 0.012)

# ---- 入口：抱厦明间四扇隔扇门向内敞开，贴在两侧槛窗内侧 ----
LH = 3.05 - 0.98
for sx in (-1, 1):
    for k in range(2):
        x = sx * (1.62 + k * 0.8)
        with K.at(x, 5.06 + k * 0.07, 0.98, 0 if sx > 0 else 180):
            K.door_leaf('朱漆', 0.8, LH, t=0.05)
K.box('朱漆', -1.62, 4.88, Z0, 1.62, 4.98, Z0 + 0.08)  # 门槛（低，可跨）

# ---- 正房前檐（y=8）五间：多宝格 | 碧纱橱 | 圆光罩 | 八方罩 | 多宝格 ----
H = 5.2 - Z0  # 隔断到额枋下皮
bays = [(-7.84, -5.16), (-4.84, -1.96), (-1.64, 1.64), (1.96, 4.84), (5.16, 7.84)]
for i, (a, b) in enumerate(bays):
    cx, w = (a + b) / 2, b - a
    with K.at(cx, 8.0, Z0):
        if i in (0, 4):
            K.duobaoge(WOOD, w, 0.36, 3.0, seed=11 + i, back=False)   # 无背板，两面通透
            K.box(WOOD, -w / 2, -0.05, 3.0, w / 2, 0.05, 3.06)
            with K.at(0, 0, 3.06):
                K.lattice_partition(WOOD, w, H - 3.06 - 0.12, paper='碧纱')
        elif i == 1:
            K.lattice_partition(WOOD, w, 3.0, paper='碧纱', door=(-0.48, 0.48))
            with K.at(0, 0, 3.0):
                K.luodizhao(WOOD, w, H - 3.0, shape='oct', t=0.06, carve=False)
        elif i == 2:
            K.luodizhao(WOOD, w, H, shape='round', t=0.1)
        else:
            K.luodizhao(WOOD, w, H, shape='oct', t=0.08)

# ---- 正房东间：宝玉卧室。西界一道隔断（x=5.0）：多宝格 + 穿衣镜门 + 多宝格 ----
XP = 5.0
for (y0, y1, seed) in ((8.2, 10.0, 21), (12.0, 15.2, 23)):
    with K.at(XP, (y0 + y1) / 2, Z0, -90):   # 局部 -Y → 世界 -X：正面朝西（正房明间）
        K.duobaoge(WOOD, y1 - y0, 0.36, 3.0, seed=seed, back=False)
    with K.at(XP, (y0 + y1) / 2, Z0 + 3.0, -90):
        K.lattice_partition(WOOD, y1 - y0, H - 3.0 - 0.12, paper='碧纱')
# 穿衣镜门：门轴在 y=11.95，关上时镜面朝西；向卧室推开 45°（刘姥姥“一推”即开，露出床帐）
with K.at(XP, 11.95, Z0, -90 + 45):
    with K.at(0.6, 0, 0):
        K.mirror(WOOD, w=1.2, h=2.45, stand=False, col=False, glass='穿衣镜')
K.col(XP, 11.45, Z0, XP + 0.45, 11.95, Z0 + 2.6)
K.col(XP + 0.4, 11.05, Z0, XP + 0.85, 11.5, Z0 + 2.6)
with K.at(XP, 11.0, Z0 + 2.75, -90):
    K.lattice_partition(WOOD, 2.0, H - 2.75 - 0.12, paper='碧纱')

# 宝玉的床：靠东山墙，床口朝西；锦笼纱罩
with K.at(6.75, 12.6, Z0, -90):
    K.bed(WOOD, w=2.3, d=1.65, H=2.45, curtain='锦帐', quilt='锦缎', pillow='锦缎黄', frieze='描金')
# 床前脚踏、熏笼、镜台、绣墩
with K.at(5.75, 12.6, Z0, -90):
    K.box(WOOD, -1.0, -0.2, 0, 1.0, 0.2, 0.14, col=True)
with K.at(6.4, 9.2, Z0):
    K.table(WOOD, 1.1, 0.5, 0.8)
    K.box(WOOD, -0.25, 0.0, 0.8, 0.25, 0.2, 0.86)
    with K.at(0, 0.12, 0.86):
        K.mirror('紫檀', w=0.42, h=0.5, frame=0.04, stand=False, col=False)
    K.vase('粉彩', -0.4, 0.05, 0.8, 0.2, 'danping', flowers=3, fcol='花红')
with K.at(6.4, 8.75, Z0):
    K.stool('锦缎', top='描金')
with K.at(5.9, 14.6, Z0):
    K.lathe('铜', 0, 0, 0, [(0.2, 0), (0.28, 0.25), (0.3, 0.42), (0.26, 0.48)], seg=18)  # 熏笼
    for i in range(10):
        a = 2 * math.pi * i / 10
        K.rod('铜', (0.27 * math.cos(a), 0.27 * math.sin(a), 0.48), (0.12 * math.cos(a), 0.12 * math.sin(a), 0.75), 0.008, seg=4)
    K.col(-0.3, -0.3, 0, 0.3, 0.3, 0.75)

# ---- 正房明间：罗汉床、一对圈椅茶几、红毡 ----
K.carpet('红毡', -3.6, 9.2, 3.6, 14.4, Z0 + 0.012)
with K.at(0, 14.7, Z0):
    K.kang(WOOD, 2.4, 0.95, mat_cushion='锦缎')
    with K.at(0, 0.02, 0.45 + 0.06 + 0.3):
        K.teaset(0.15, 0.0, 0)
for sx in (-1, 1):
    for yy in (11.0, 12.9):
        with K.at(sx * 2.3, yy, Z0, 90 if sx < 0 else -90):
            K.chair(WOOD, 'quan', cushion='锦缎')
    with K.at(sx * 2.35, 11.95, Z0):
        K.table(WOOD, 0.45, 0.45, 0.72)
        K.vase('青花', 0, 0, 0.72, 0.28, 'meiping')
# 明间四盏宫灯
for (x, y) in ((-2.6, 10.2), (2.6, 10.2), (-2.6, 13.6), (2.6, 13.6), (0, 6.4)):
    K.lantern(x, y, 5.55 if y > 8 else 4.1, drop=0.7 if y > 8 else 0.25)

# ---- 正房西间：书房。西山墙上那幅“女孩儿”画、古董槽子；书架、书案 ----
with K.at(-7.66, 11.7, Z0 + 3.3, 90):        # 贴西山墙，朝东
    K.scroll(0, 0, 0, 1.3, 2.5, face=-1, mount='绫裱', paint='美人画')
# 满墙古董槽子：一块嵌墙木板，槽里嵌琴、悬瓶、剑
with K.at(-7.69, 9.25, Z0, 90):
    K.box(WOOD, -0.85, -0.06, 0.9, 0.85, 0.0, 3.4)
    K.box('黑漆', -0.7, -0.07, 1.25, 0.7, -0.055, 1.4)           # 琴形槽
    K.box('黑漆', -0.68, -0.09, 1.28, 0.62, -0.07, 1.37)          # 琴
    K.box('描金', 0.5, -0.1, 1.29, 0.6, -0.08, 1.36)
    K.box('黑漆', -0.12, -0.07, 1.7, 0.12, -0.055, 2.5)
    K.vase('青瓷', 0, -0.12, 1.75, 0.6, 'danping')               # 悬瓶
    K.box('黑漆', 0.45, -0.07, 1.6, 0.53, -0.055, 2.9)
    K.bar('铜', (0.49, -0.09, 1.65), (0.49, -0.09, 2.85), 0.03, 0.01)  # 剑
    K.box('黑漆', -0.65, -0.07, 1.7, -0.3, -0.055, 2.3)
    K.box('画绢', -0.62, -0.09, 1.78, -0.33, -0.07, 2.22)         # 桌屏
    K.col(-0.85, -0.12, 0, 0.85, 0.0, 3.4)
for x in (-7.0, -6.0):
    with K.at(x, 14.95, Z0):
        K.shelf(WOOD, 0.95, 0.4, 2.3, rows=5)
with K.at(-6.0, 10.6, Z0, -90):
    K.qiaotou(WOOD, 1.9, 0.6, 0.84)
    K.study_set(0.1, 0.02, 0.84, 0)
    K.vase('青瓷', -0.75, 0.1, 0.84, 0.3, 'gu', flowers=4, fcol='花白')
with K.at(-6.75, 10.6, Z0, 90):
    K.chair(WOOD, 'guanmao', cushion='锦缎')
K.candle_stand(-5.3, 9.3, Z0)

# ---- 抱厦：自鸣钟、花几盆景、地毡 ----
K.carpet('红毡', -1.8, 5.3, 1.8, 7.6, Z0 + 0.012)
with K.at(-6.9, 7.45, Z0):
    K.box(WOOD, -0.35, -0.25, 0, 0.35, 0.25, 1.9, col=True)            # 钟柜
    K.box('描金', -0.3, -0.26, 1.2, 0.3, -0.25, 1.75)
    with K.at(0, -0.26, 1.47, 0):
        K.rod('瓷白', (0, 0, -0.2), (0, -0.01, -0.2), 0.2, seg=24)       # 钟面
        K.rod('墨', (0, -0.02, -0.2), (0.12, -0.02, -0.15), 0.006, seg=4)
        K.rod('墨', (0, -0.02, -0.2), (-0.03, -0.02, -0.05), 0.006, seg=4)
    K.lathe('描金', 0, 0, 1.9, [(0.3, 0), (0.18, 0.12), (0.05, 0.25), (0.0, 0.3)], seg=6)
for sx in (-1, 1):
    with K.at(sx * 3.4, 7.45, Z0):
        K.table(WOOD, 0.45, 0.45, 0.95, stretch=True)
        K.penjing(0, 0, 0.95, 0.42)
with K.at(6.6, 7.45, Z0):
    K.table(WOOD, 0.45, 0.45, 0.95, stretch=True)
    K.vase('青花', 0, 0, 0.95, 0.45, 'meiping', flowers=5, fcol='花红')

# ---- 天花、墙面 ----
K.ceiling(-7.69, 8.16, 7.69, 15.2, 5.55, cell=0.64)
K.ceiling(-7.84, 5.02, 7.84, 7.9, 4.06, cell=0.64)
for sx in (-1, 1):
    K.wall_finish((sx * 7.69, 8.16), (sx * 7.69, 15.2), Z0, 5.5, (-sx, 0))
K.wall_finish((-7.69, 15.24), (7.69, 15.24), Z0, 5.5, (0, -1), dado=0.95)
# 罗汉床上方：横披一幅、两侧对联
with K.at(0, 15.2, 0):
    K.box('紫檀', -1.6, -0.04, Z0 + 2.15, 1.6, 0.0, Z0 + 2.95)
    K.box('画心', -1.5, -0.05, Z0 + 2.22, 1.5, -0.03, Z0 + 2.88)
    for sx in (-1, 1):
        K.scroll(sx * 2.05, -0.01, Z0 + 3.3, 0.42, 2.3, face=-1, mount='绫裱', paint='书页')
with K.at(-7.69, 0, 0, 90):   # 西山墙另一侧：一幅山水
    pass

# ---- 外壳碰撞：抱厦/正房墙体（实心块已去） ----
W = []
W.append([-8.0, 4.85, Z0, -1.66, 5.0, 4.1, False])
W.append([1.66, 4.85, Z0, 8.0, 5.0, 4.1, False])
for sx in (-1, 1):
    W.append([min(sx * 7.84, sx * 8.0), 4.9, Z0, max(sx * 7.84, sx * 8.0), 7.9, 4.1, False])  # 抱厦两山槛窗
    W.append([min(sx * 7.69, sx * 8.31), 7.65, Z0, max(sx * 7.69, sx * 8.31), 15.85, 5.8, False])  # 正房山墙
W.append([-8.0, 4.9, 4.1, 8.0, 7.95, 4.7, False])     # 抱厦顶（挡相机）
W.append([-8.0, 7.95, 5.6, 8.0, 15.5, 6.2, False])    # 正房顶
for x in (-8, -5, -1.8, 1.8, 5, 8):                   # 檐柱（前檐、抱厦）
    for y in (4.0, 4.9, 8.0):
        W.append([x - 0.16, y - 0.16, Z0, x + 0.16, y + 0.16, 4.1 if y < 8 else 5.6, False])


def solid_hall(b):
    lx, lz, hx, hz, top, bot = b
    return abs(lx) < 1 and -13 < lz < -5 and hx > 7 and hz > 1 and bot > 0.75 and top - bot > 1.0


save_and_export(K, shell_cols_filter=solid_hall, extra_cols=W)
