"""藕香榭室内（第三十八回；坐标与 blender/ouxiang.blend 相同，原点在榭心）。
用法：flock /tmp/coljson.lock python3 blender/scripts/interiors/build_ouxiang.py
外壳：先跑 blender/scripts/sites/ouxiang_doors.py（删榭内旧条桌、重做碰撞）。南北明间隔扇门外壳里本来就敞开着。

  第三十八回：这藕香榭盖在池中，四面有窗，左右有曲廊可通，亦是跨水接岸，后面又有曲折竹桥暗接。……
  进入榭中，只见栏杆外另放着两张竹案，一个上面设着杯箸酒具，一个上头设着茶筅茶盂各色茶具。
  那边有两三个丫头煽风炉煮茶，这一边另外几个丫头也煽风炉烫酒呢。……柱上挂的黑漆嵌蚌的对子：
  芙蓉影破归兰桨，菱藕香深写竹桥。……上面一桌：贾母、薛姨妈、宝钗、黛玉、宝玉；东边一桌：史湘云、王夫人、
  迎、探、惜；西边靠门一小桌：李纨和凤姐的，虚设坐位，二人皆不敢坐，只在贾母王夫人两桌上伺候。
  （匾额「藕香榭」、黑漆嵌蚌对联外壳里都有，挂在南面明间檐柱上，字已刻好。）

方位：匾额朝南（Blender −Y），东 = +X，西 = −X，「上面」= 北（+Y）。
榭内：x ±4.66，y ±3.26，地 z=0.90；南北明间门 x ±0.73。南面廊（y −3.41…−4.71）接左右曲廊。
东、西面南次间（y −3.16…−0.14）在 ouxiang_doors.py 里剪开做门，左右曲廊由此进榭。
竹案：按「栏杆外」放在南面美人靠外的月台上（z=0.32），中间留出上岸到南门的路。
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

new_file()
K = Kit('ouxiang')
Z = 0.90
WD, LQ = '紫檀', '黑漆'
TRIPO = []


def tripo(name, cx, cy, z0, sx, sy, sz, face, desc):
    K.box('TRIPO占位', cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z0 + sz, col=True)
    TRIPO.append(dict(name='TRIPO_' + name, center=[round(cx, 3), round(cy, 3)], bottom_z=round(z0, 3),
                      size=[sx, sy, sz], front=face, prompt=desc))


CRAB = 'A round Chinese porcelain platter piled with steamed red hairy crabs, blue-and-white rim, Qing dynasty banquet style'
STOVE = 'A small Chinese clay tea brazier (fenglu) with a charcoal opening on the front and a small bronze kettle on top, rustic unglazed terracotta'


def place_setting(x, y, z, ang):
    """一份席面：小酒杯、姜醋碟、一双箸（ang：朝座位的方向，度）。"""
    a = math.radians(ang)
    cx, cy = x, y
    K.lathe('瓷白', cx, cy, z, [(0.02, 0), (0.03, 0.02), (0.033, 0.04)], seg=10, cap=False)      # 酒杯
    px, py = cx - math.sin(a) * 0.1, cy + math.cos(a) * 0.1
    K.lathe('青花', px, py, z, [(0.03, 0), (0.05, 0.012), (0.055, 0.018)], seg=10, cap=False)    # 姜醋碟
    qx, qy = cx + math.sin(a) * 0.1, cy - math.cos(a) * 0.1
    for d in (-0.012, 0.012):
        ox, oy = math.sin(a) * d, -math.cos(a) * d
        K.rod('黑漆', (qx + ox - math.cos(a) * 0.12, qy + oy - math.sin(a) * 0.12, z + 0.006),
              (qx + ox + math.cos(a) * 0.12, qy + oy + math.sin(a) * 0.12, z + 0.006), 0.004, seg=4)


def wine_pot(x, y, z, m='铜'):
    K.lathe(m, x, y, z, [(0.05, 0), (0.08, 0.04), (0.085, 0.12), (0.04, 0.2), (0.025, 0.24), (0.035, 0.26), (0.0, 0.27)], seg=14)
    K.rod(m, (x + 0.07, y, z + 0.08), (x + 0.16, y, z + 0.2), 0.01, seg=5)


def guihua(x, y):
    """香几上一瓶折枝桂花。"""
    with K.at(x, y, Z):
        K.table(WD, 0.42, 0.42, 0.82, top=0.03, leg=0.035, apron=0.05)
        K.vase('青花', 0, 0, 0.82, 0.38, 'meiping', flowers=16, fcol='菊黄')


def seat_stool(x, y):
    with K.at(x, y, Z):
        K.stool('青瓷', top='描金', h=0.46, r=0.19)


def seat_chair(x, y, rot):
    with K.at(x, y, Z, rot):
        K.chair(WD, 'quan', cushion='锦缎')


# ---------------- 地坪：方砖上铺一块红毡（上面一桌） ----------------
K.carpet('红毡', -1.6, -0.2, 1.6, 2.35, Z + 0.005)

# ---------------- 上面一桌（北）：贾母、薛姨妈、宝钗、黛玉、宝玉 ----------------
TX, TY = 0.0, 0.95
with K.at(TX, TY, Z):
    K.table(WD, 1.3, 0.9, 0.84, top=0.05, leg=0.06, apron=0.08)
H = Z + 0.84
seat_chair(TX - 0.35, TY + 0.72, 0)       # 贾母
seat_chair(TX + 0.35, TY + 0.72, 0)       # 薛姨妈
seat_stool(TX - 0.95, TY)                  # 宝钗
seat_stool(TX + 0.95, TY)                  # 宝玉
seat_stool(TX, TY - 0.7)                   # 黛玉
for (x, y, a) in ((TX - 0.35, TY + 0.28, -90), (TX + 0.35, TY + 0.28, -90), (TX - 0.5, TY, 0), (TX + 0.5, TY, 180), (TX, TY - 0.3, 90)):
    place_setting(x, y, H, a)
wine_pot(TX + 0.45, TY - 0.25, H, '铜')
tripo('螃蟹盘_上', TX, TY + 0.02, H, 0.42, 0.42, 0.14, '-Y', CRAB)

# ---------------- 东边一桌：湘云、王夫人、迎春、探春、惜春 ----------------
EX, EY = 3.05, 0.2
with K.at(EX, EY, Z):
    K.table(WD, 0.95, 0.95, 0.84, top=0.05, leg=0.06, apron=0.08)
seat_chair(EX, EY + 0.75, 0)               # 王夫人
seat_stool(EX - 0.75, EY)                  # 迎春
seat_stool(EX + 0.75, EY)                  # 探春
seat_stool(EX - 0.3, EY - 0.72)            # 惜春
seat_stool(EX + 0.35, EY - 0.72)           # 湘云（做东）
for (x, y, a) in ((EX, EY + 0.3, -90), (EX - 0.3, EY, 0), (EX + 0.3, EY, 180), (EX - 0.25, EY - 0.3, 90), (EX + 0.25, EY - 0.3, 90)):
    place_setting(x, y, H, a)
wine_pot(EX + 0.32, EY + 0.3, H, '铜')
tripo('螃蟹盘_东', EX, EY + 0.02, H, 0.38, 0.38, 0.14, '-Y', CRAB)

# ---------------- 西边靠门一小桌：李纨、凤姐（虚设坐位） ----------------
WX, WY = -2.1, -2.2
with K.at(WX, WY, Z):
    K.table(WD, 0.72, 0.72, 0.8, top=0.04, leg=0.05, apron=0.07)
seat_stool(WX - 0.62, WY)                  # 李纨
seat_stool(WX, WY + 0.62)                  # 凤姐
for (x, y, a) in ((WX - 0.2, WY, 0), (WX, WY + 0.2, -90)):
    place_setting(x, y, Z + 0.8, a)
tripo('螃蟹盘_西', WX + 0.08, WY - 0.08, Z + 0.8, 0.32, 0.32, 0.12, '-Y', CRAB)

# ---------------- 四角香几桂花瓶（「赏桂花」） ----------------
for x, y in ((-4.25, 2.85), (4.25, 2.85), (-3.55, -2.9), (3.55, -2.9)):
    guihua(x, y)

# ---------------- 栏杆外两张竹案（南面美人靠外的月台，地 z=0.32）：西案杯箸酒具，东案茶筅茶盂；外侧各一只风炉 ----------------
ZT = 0.32
BY = -5.45
for sx in (-1, 1):
    with K.at(sx * 3.2, BY, ZT):
        K.table('黄竹', 1.3, 0.62, 0.78, top=0.035, leg=0.045, apron=0.05, stretch=True)
        for k in range(9):                                       # 案面竹片缝
            x = -0.6 + k * 0.15
            K.box('湘妃竹', x - 0.008, -0.31, 0.78, x + 0.008, 0.31, 0.785)
BT = ZT + 0.785
# 西案：杯箸酒具
wine_pot(-3.6, BY + 0.05, BT, '铜')
wine_pot(-3.25, BY + 0.12, BT, '瓷白')
for i in range(6):
    K.lathe('瓷白', -3.0 + (i % 3) * 0.09, BY - 0.12 + (i // 3) * 0.1, BT, [(0.02, 0), (0.03, 0.02), (0.033, 0.04)], seg=10, cap=False)
for i in range(4):                                   # 一把箸
    K.rod('黑漆', (-3.8, BY - 0.22 + i * 0.012, BT + 0.006), (-3.55, BY - 0.22 + i * 0.012, BT + 0.006), 0.004, seg=4)
K.box('朱漆', -2.8, BY + 0.1, BT, -2.6, BY + 0.2, BT + 0.06)        # 箸匣
# 东案：茶筅、茶盂、各色茶具
K.teaset(3.2, BY, BT, m='紫砂', cups=4)
K.lathe('青瓷', 3.65, BY - 0.02, BT, [(0.05, 0), (0.09, 0.03), (0.1, 0.08), (0.085, 0.1)], seg=14, cap=False)   # 茶盂
K.lathe('竹竿', 2.8, BY - 0.12, BT, [(0.025, 0), (0.03, 0.04), (0.012, 0.06), (0.01, 0.13), (0.0, 0.13)], seg=10)  # 茶筅
K.lathe('青花', 3.72, BY + 0.18, BT, [(0.04, 0), (0.05, 0.08), (0.03, 0.12), (0.032, 0.14)], seg=12)              # 茶叶罐
# 风炉：煮茶（东）、烫酒（西）
tripo('风炉_西', -4.3, BY, ZT, 0.36, 0.36, 0.5, '+X', STOVE)
tripo('风炉_东', 4.3, BY, ZT, 0.36, 0.36, 0.5, '-X', STOVE)

# ---------------- 东、西侧门（接曲廊）：四扇隔扇敞开，折在室内贴两柱 ----------------
for sx in (-1, 1):
    for yh, s in ((-3.12, 1), (-0.18, -1)):
        for k in range(2):
            with K.at(sx * 4.72, yh + s * 0.06 * k, Z + 0.12, 180 if sx > 0 else 0):
                K.door_leaf('栗壳漆', 0.72, 2.3, t=0.05)

# ---------------- 宫灯 ----------------
for x, y in ((0.0, 1.0), (3.05, 0.2), (-2.6, 0.3), (0.0, -2.2)):
    K.lantern(x, y, 5.6, drop=1.3)

print('TRIPO', json.dumps(TRIPO, ensure_ascii=False))
save_and_export(K)
