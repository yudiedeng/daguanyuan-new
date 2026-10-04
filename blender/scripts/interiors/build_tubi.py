"""凸碧山庄室内（第七十五、七十六回中秋夜宴；坐标与 blender/tubi.blend 相同，网页 p=[80,Z.tubi.y,-129]）。
用法：flock /tmp/coljson.lock python3 blender/scripts/interiors/build_tubi.py
外壳开门：先跑 blender/scripts/sites/tubi_doors.py（明间四扇隔扇门已在外壳里删去），本脚本放敞开的门扇与陈设。

  第七十五回：贾母带领众人到山上的凸碧山庄。……凡桌椅形式皆是圆的，特取团圆之意。
  上面居中贾母坐下，左垂首贾赦、贾珍、贾琏、贾蓉，右垂首贾政、宝玉、贾环、贾兰，团团围坐。……
  （之前在嘉荫堂月台上：焚着斗香，秉着风烛，陈献着瓜饼及各色果品——这里的香案月供即取此意。）

凸碧堂（五开间，前廊）：室内 x −4.85…4.85，y −1.24（前金柱/门槛线）…3.09（后墙内皮），地坪 z=0.88；
  无内柱；明间门洞 x ±1.73，门槛顶 z 1.01。前廊 y −2.88…−1.30。
布置：
  当中一张大圆桌（直径 1.7），一圈九座：北面正中贾母圈椅，其余八只绣墩，南面（门口一侧）留 72° 的空当，
  进门就能直接走到桌边。圆桌后（北）一架八扇大围屏，屏上悬匾。东山墙下设香案供月（月供、香炉为 Tripo 占位，
  一对烛台），西山墙下翘头案供桂花。梁下宫灯三盏，围屏两侧羊角灯一对。明间四扇门向内折贴两侧门柱。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from kit import Kit, new_file, save_and_export

Z0 = 0.88                       # 地坪
XW, XE = -4.85, 4.85            # 山墙内皮
YS, YN = -1.24, 3.09            # 门槛线 / 后墙内皮
WOOD, TAN = '花梨', '紫檀'

new_file()
K = Kit('tubi')

TRIPO = []      # (名称, 中心x, 中心y, 底z, 长x, 宽y, 高z, 正面, 描述)


def tripo(name, cx, cy, z0, sx, sy, sz, face, desc):
    """Tripo 雕塑件占位块：材质一律 'TRIPO占位'（网页隐藏此材质的网格，在原位放 Tripo 模型）；带碰撞。"""
    K.box('TRIPO占位', cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z0 + sz, col=True)
    TRIPO.append((name, cx, cy, z0, sx, sy, sz, face, desc))


def round_table(x, y, R=0.85, h=0.82):
    """圆桌：圆面、束腰、牙板、五腿带托泥。"""
    K.cyl(WOOD, x, y, Z0 + h - 0.045, Z0 + h, R, seg=40)
    K.cyl(WOOD, x, y, Z0 + h - 0.075, Z0 + h - 0.045, R - 0.05, seg=40)
    K.cyl(TAN, x, y, Z0 + h - 0.16, Z0 + h - 0.075, R - 0.07, seg=40)
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 2
        lx, ly = x + (R - 0.13) * math.cos(a), y + (R - 0.13) * math.sin(a)
        K.rod(WOOD, (lx, ly, Z0 + 0.06), (lx, ly, Z0 + h - 0.1), 0.035, seg=8)
    # 圆环托泥
    for i in range(30):
        a0, a1 = 2 * math.pi * i / 30, 2 * math.pi * (i + 1) / 30
        r = R - 0.13
        K.bar(WOOD, (x + r * math.cos(a0), y + r * math.sin(a0), Z0 + 0.03), (x + r * math.cos(a1), y + r * math.sin(a1), Z0 + 0.03), 0.06, 0.05)
    K.col(x - R, y - R, Z0, x + R, y + R, Z0 + h)


def plate(x, y, z, r, m='瓷白'):
    K.lathe(m, x, y, z, [(r * 0.55, 0), (r * 0.6, 0.008), (r, 0.03), (r * 0.94, 0.035), (0.0, 0.012)], seg=20)


def mooncakes(x, y, z, n=5, m='青花'):
    plate(x, y, z, 0.15, m)
    for i in range(n):
        a = 2 * math.pi * i / max(1, n - 1)
        cx, cy = (x, y) if i == 0 else (x + 0.075 * math.cos(a), y + 0.075 * math.sin(a))
        K.cyl('土定', cx, cy, z + 0.02 + (0.035 if i == 0 else 0), z + 0.055 + (0.035 if i == 0 else 0), 0.045, seg=14)


def fruit_plate(x, y, z, m='粉彩', col='花红', n=7):
    plate(x, y, z, 0.14, m)
    r = K.rng
    for i in range(n):
        a = r.uniform(0, 6.283)
        d = 0.06 * math.sqrt(r.random()) if i else 0
        K.sph(col, x + d * math.cos(a), y + d * math.sin(a), z + 0.06 + (0.04 if i == 0 else 0), 0.035, seg=8)


def wine_cup(x, y, z):
    K.lathe('瓷白', x, y, z, [(0.012, 0), (0.02, 0.006), (0.028, 0.04)], seg=10, cap=False)


def candle_holder(x, y, z, h=0.55):
    """铜烛台（高足盘）+ 红烛。"""
    K.lathe('铜', x, y, z, [(0.09, 0), (0.09, 0.02), (0.03, 0.05), (0.018, 0.08), (0.018, h - 0.06), (0.07, h - 0.04), (0.08, h - 0.02), (0.02, h)], seg=12)
    K.cyl('朱漆', x, y, z + h, z + h + 0.2, 0.025, seg=10)
    K.cyl('烛', x, y, z + h + 0.2, z + h + 0.24, 0.008, seg=6)


# ================= 明间四扇门敞开：向室内折贴两侧门柱 =================
for x_h, sgn in ((-1.66, 1), (1.66, -1)):
    for k in range(2):
        with K.at(x_h + sgn * 0.06 * k, YS + 0.03, 1.01, 90):
            K.door_leaf('朱漆', 0.84, 2.64, t=0.05)

# ================= 地上：圆毡 =================
TX, TY = 0.0, 1.0                     # 圆桌中心
K.cyl('红毡', TX, TY, Z0, Z0 + 0.008, 1.72, seg=48)
K.cyl('描金', TX, TY, Z0, Z0 + 0.006, 1.8, seg=48)

# ================= 大圆桌 + 一圈九座 =================
round_table(TX, TY)
RS = 1.28
for k in range(-4, 5):
    a = math.radians(90 + 36 * k)
    sx, sy = TX + RS * math.cos(a), TY + RS * math.sin(a)
    if k == 0:
        # 贾母：圈椅（椅背在 +Y，面朝圆桌）
        with K.at(sx, sy + 0.05, Z0):
            K.chair(TAN, 'quan', cushion='锦缎黄')
    else:
        with K.at(sx, sy, Z0):
            K.stool(TAN, top='描金', h=0.46, r=0.19)
            K.cyl('锦缎', 0, 0, 0.46, 0.49, 0.17, seg=16)

# 桌上：中间大果盘（西瓜、各色果品）、月饼、酒杯、攒盒
ZT = Z0 + 0.82
K.lathe('青花', TX, TY, ZT, [(0.14, 0), (0.17, 0.01), (0.3, 0.05), (0.28, 0.055), (0.0, 0.02)], seg=24)   # 大盘
K.sph('叶绿', TX - 0.06, TY + 0.02, ZT + 0.12, 0.13, 0.12, 0.1, seg=12)                                   # 西瓜
K.sph('花红', TX + 0.12, TY - 0.06, ZT + 0.07, 0.07, 0.045, 0.05, seg=10)                                 # 切开的瓜瓤
for i in range(6):
    a = i * 1.05
    K.sph('菊黄' if i % 2 else '花红', TX + 0.2 * math.cos(a), TY + 0.2 * math.sin(a), ZT + 0.07, 0.04, seg=8)
for k in range(9):
    a = math.radians(90 + 36 * (k - 4))
    wine_cup(TX + 0.66 * math.cos(a), TY + 0.66 * math.sin(a), ZT)
    if k % 2 == 0:
        mooncakes(TX + 0.45 * math.cos(a + 0.33), TY + 0.45 * math.sin(a + 0.33), ZT, n=4)
    else:
        fruit_plate(TX + 0.45 * math.cos(a + 0.33), TY + 0.45 * math.sin(a + 0.33), ZT, col='菊黄' if k % 4 == 1 else '花白')
# 酒壶两把
for dx in (-0.28, 0.28):
    K.lathe('青花', TX + dx, TY + 0.3, ZT, [(0.04, 0), (0.07, 0.04), (0.075, 0.1), (0.035, 0.17), (0.02, 0.22), (0.03, 0.24)], seg=14)
    K.rod('青花', (TX + dx + 0.06, TY + 0.3, ZT + 0.08), (TX + dx + 0.13, TY + 0.3, ZT + 0.18), 0.008, seg=5)

# ================= 圆桌后：八扇大围屏 =================
with K.at(0, 2.88, Z0):
    K.screen(TAN, 4.4, 2.55, panels=8, silk='山水图', fold=6)
# 围屏两侧羊角灯
for sx in (-1, 1):
    K.candle_stand(sx * 2.55, 2.55, Z0, h=1.45)
    K.col(sx * 2.55 - 0.18, 2.37, Z0, sx * 2.55 + 0.18, 2.73, Z0 + 1.5)

# ================= 匾额（后墙，围屏上方） =================
K.box('匾额_深木边框', -1.15, YN - 0.1, 3.62, 1.15, YN, 4.32)
K.box('匾心', -1.03, YN - 0.115, 3.71, 1.03, YN - 0.1, 4.23)

# ================= 东山墙：香案供月 =================
XA = XE - 0.33                          # 香案中线
with K.at(XA, TY, Z0, 90):              # 长边顺 y
    K.table(TAN, 2.0, 0.6, 0.9, top=0.05, leg=0.07, apron=0.1)
    K.box('锦缎', -1.02, -0.31, 0.9, 1.02, 0.31, 0.905)                     # 案面锦袱
K.box('锦缎', XA - 0.31, TY - 0.95, Z0 + 0.45, XA - 0.30,  # 锦袱前垂
      TY + 0.95, Z0 + 0.905)
ZA = Z0 + 0.905
tripo('月供', XA + 0.08, TY, ZA, 0.36, 1.1, 0.32, '-X',
      'Mid-autumn moon offering arranged in a row on a altar table: a stack of round mooncakes on a blue-and-white plate, a halved watermelon cut in lotus-petal shape, and a plate of pomegranates and pears, Qing dynasty style, realistic')
tripo('香炉', XA - 0.17, TY, ZA, 0.26, 0.26, 0.3, '-X',
      'Chinese bronze tripod incense burner (ding) with two upright handles and a few incense sticks, Qing dynasty, dark patinated bronze')
for dy in (-0.78, 0.78):
    candle_holder(XA - 0.12, TY + dy, ZA)
# 香案上方挂月宫图
with K.at(XE - 0.01, TY, 0, -90):
    K.scroll(0, 0, 3.75, 1.1, 1.75, face=-1, paint='画心')

# ================= 西山墙：翘头案，供桂花 =================
XQ = XW + 0.3
with K.at(XQ, TY, Z0, -90):
    K.qiaotou(WOOD, 2.2, 0.46, 0.88)
    K.vase('青瓷', 0.0, 0.0, 0.88, 0.5, 'meiping', flowers=18, fcol='菊黄')      # 桂花
    K.vase('瓷白', -0.75, 0.0, 0.88, 0.32, 'guan')
    K.vase('瓷白', 0.75, 0.0, 0.88, 0.32, 'guan')
with K.at(XW + 0.01, TY, 0, 90):
    K.scroll(0, 0, 3.75, 1.1, 1.75, face=-1, paint='山水图')

# ================= 宫灯 =================
LAMPS = [(TX, TY, 4.68, 0.85), (-3.3, 0.9, 4.68, 0.75), (3.3, 0.9, 4.68, 0.75)]
for x, y, zt, d in LAMPS:
    K.lantern(x, y, zt, drop=d)


save_and_export(K)
print('TRIPO 占位：名称, 中心x, 中心y, 底z, 长x, 宽y, 高z, 正面')
for t in TRIPO:
    print('TRIPO', t[0], *[round(v, 3) for v in t[1:7]], t[7], '|', t[8])
print('LIGHTS(web)', [[round(x, 2), round(zt - d - 0.25, 2), round(-y, 2)] for x, y, zt, d in LAMPS])
