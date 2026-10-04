"""凹晶馆室内（第七十六回；坐标与 blender/aojing.blend 相同，网页 p=[83,1.0,-83]）。
用法：flock /tmp/coljson.lock python3 blender/scripts/interiors/build_aojing.py
外壳开门：先跑 blender/scripts/sites/aojing_doors.py（前檐明间四扇隔扇门删去、后墙凿后门），本脚本放敞开的门扇与陈设。

  第七十六回：（黛玉湘云）二人遂一路下了山坡，只一转弯，就是池沿，沿上一带竹栏相接，直通着那边藕香榭的路径。
  因这几间就在山之凹里，所以凹晶馆。……二人便在两个湘妃竹墩上坐下。只见天上一轮皓月，池中一个月影，上下争辉，
  如置身于晶宫鲛室之内。……（翠缕）……妙玉笑道：「……我那里去吃茶」——联句「寒塘渡鹤影，冷月葬花魂」。

凹晶馆（三开间卷棚，前檐 −Y 面水，后墙 +Y 靠山）：室内 x −4.69…4.69，y −0.71（前檐槛线）…2.60（后墙内皮），地 z=0.51，
  无内柱。前檐明间门洞 x ±1.54（下槛顶 0.65），后墙正中后门 x ±0.65。
布置（素雅、近水）：
  正中对着敞开的明间：两个湘妃竹墩（Tripo 占位）夹一张矮竹几，几上茶具，面水看月。
  西次间：靠山墙一张竹榻（蒲席、竹枕）；明间西侧一张琴桌，桌上一张琴（自建），桌后竹凳。
  东次间：书案一张，笔砚诗笺（联句用），案后竹椅。
  一盏落地羊角灯（竹榻与琴桌之间）。两次间前檐隔扇里侧放下半幅湘帘，明间门楣卷起一卷湘帘。明间四扇门向内折贴门柱。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy, bmesh
from mathutils import Matrix
from kit import Kit, new_file, save_and_export

Z0 = 0.51
XW, XE = -4.69, 4.69
YS, YN = -0.71, 2.60
BAM, BAM2 = '湘妃竹', '竹竿'

new_file()
K = Kit('aojing')
TRIPO = []      # (名称, 中心x, 中心y, 底z, 长x, 宽y, 高z, 正面, 描述)


def tripo(name, cx, cy, z0, sx, sy, sz, face, desc):
    """Tripo 雕塑件占位块：材质一律 'TRIPO占位'（网页隐藏此材质的网格，在原位放 Tripo 模型）；带碰撞。"""
    K.box('TRIPO占位', cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z0 + sz, col=True)
    TRIPO.append((name, cx, cy, z0, sx, sy, sz, face, desc))


def bamboo_frame(w, d, h, r=0.018):
    """竹制方框腿：四腿 + 上下两圈横撑（局部原点在投影中心，面高 h）。"""
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.rod(BAM, (sx * (w / 2 - r), sy * (d / 2 - r), 0), (sx * (w / 2 - r), sy * (d / 2 - r), h), r, seg=8)
    for z in (h - 0.03, 0.12):
        for sy in (-1, 1):
            K.rod(BAM, (-w / 2, sy * (d / 2 - r), z), (w / 2, sy * (d / 2 - r), z), r * 0.8, seg=6)
        for sx in (-1, 1):
            K.rod(BAM, (sx * (w / 2 - r), -d / 2, z), (sx * (w / 2 - r), d / 2, z), r * 0.8, seg=6)


def slat_top(w, d, z, n=None, m=BAM2):
    """竹片面：沿 x 排的细竹片。"""
    n = n or max(4, int(d / 0.045))
    for i in range(n):
        y = -d / 2 + (i + 0.5) * d / n
        K.box(m, -w / 2, y - d / n * 0.42, z, w / 2, y + d / n * 0.42, z + 0.018)


def bamboo_couch(w=1.9, d=0.78, h=0.42):
    """竹榻：面朝 −Y（靠背在 +Y），三面矮围栏，铺蒲席，竹枕。"""
    bamboo_frame(w, d, h, r=0.024)
    slat_top(w, d, h - 0.02, m=BAM2)
    K.box('蒲席', -w / 2 + 0.04, -d / 2 + 0.04, h, w / 2 - 0.04, d / 2 - 0.04, h + 0.015)
    # 后围、两侧扶手：竹竿横档 + 竖棂
    for sx in (-1, 1):
        K.rod(BAM, (sx * (w / 2 - 0.024), d / 2 - 0.024, h), (sx * (w / 2 - 0.024), d / 2 - 0.024, h + 0.38), 0.022, seg=8)
        K.rod(BAM, (sx * (w / 2 - 0.024), -d / 2 + 0.024, h), (sx * (w / 2 - 0.024), -d / 2 + 0.024, h + 0.24), 0.02, seg=8)
        K.rod(BAM, (sx * (w / 2 - 0.024), -d / 2 + 0.024, h + 0.24), (sx * (w / 2 - 0.024), d / 2 - 0.024, h + 0.24), 0.018, seg=6)
        for k in range(1, 5):
            y = -d / 2 + k * d / 5
            K.rod(BAM2, (sx * (w / 2 - 0.024), y, h), (sx * (w / 2 - 0.024), y, h + 0.24), 0.008, seg=5)
    K.rod(BAM, (-w / 2, d / 2 - 0.024, h + 0.38), (w / 2, d / 2 - 0.024, h + 0.38), 0.02, seg=6)
    for k in range(1, 12):
        x = -w / 2 + k * w / 12
        K.rod(BAM2, (x, d / 2 - 0.024, h), (x, d / 2 - 0.024, h + 0.38), 0.008, seg=5)
    # 竹枕（编竹圆枕）
    with K.at(-w / 2 + 0.2, 0.05, h + 0.07, 90):
        K.rod('藤编', (-0.22, 0, 0), (0.22, 0, 0), 0.065, seg=12)
    K.col(-w / 2, -d / 2, 0, w / 2, d / 2, h + 0.38)


def bamboo_stool(w=0.4, d=0.32, h=0.45):
    bamboo_frame(w, d, h, r=0.018)
    slat_top(w, d, h - 0.018)
    K.col(-w / 2, -d / 2, 0, w / 2, d / 2, h)


def bamboo_chair():
    """竹椅：面朝 −Y。"""
    W, D, S = 0.52, 0.44, 0.47
    bamboo_frame(W, D, S, r=0.02)
    slat_top(W, D, S - 0.018)
    for sx in (-1, 1):
        K.rod(BAM, (sx * (W / 2 - 0.02), D / 2 - 0.02, S), (sx * (W / 2 - 0.02), D / 2 + 0.03, S + 0.52), 0.02, seg=8)
        K.rod(BAM, (sx * (W / 2 - 0.02), -D / 2 + 0.02, S), (sx * (W / 2 - 0.02), -D / 2 + 0.02, S + 0.22), 0.018, seg=8)
        K.rod(BAM, (sx * (W / 2 - 0.02), -D / 2 + 0.02, S + 0.22), (sx * (W / 2 - 0.02), D / 2, S + 0.24), 0.016, seg=6)
    K.rod(BAM, (-W / 2 - 0.03, D / 2 + 0.03, S + 0.52), (W / 2 + 0.03, D / 2 + 0.03, S + 0.52), 0.02, seg=6)
    for k in range(1, 7):
        x = -W / 2 + k * W / 7
        K.rod(BAM2, (x, D / 2 - 0.0, S), (x, D / 2 + 0.03, S + 0.5), 0.008, seg=5)
    K.col(-W / 2, -D / 2, 0, W / 2, D / 2, S + 0.5)


def guqin(L=1.2, W0=0.2, W1=0.15, T=0.06):
    """琴：黑漆长板，面板拱起；岳山、龙龈、七弦、十三徽、两雁足。局部 x：琴首在 −x，琴尾在 +x；徽在 +y（抚琴者一侧）。
    局部原点在琴底中心（不计雁足）。"""
    b = bmesh.new()
    NS, NA = 12, 9          # 纵向截面数、拱面分段
    rings = []
    for i in range(NS + 1):
        u = i / NS
        x = -L / 2 + u * L
        w = W0 + (W1 - W0) * u
        if 0.62 < u < 0.7:          # 腰
            w *= 0.93
        pts = [(x, w / 2, 0.0), (x, -w / 2, 0.0)]
        for k in range(NA + 1):
            yy = -w / 2 + k * w / NA
            s = 2 * yy / w
            pts.append((x, yy, T * 0.45 + T * 0.55 * math.sqrt(max(0.0, 1 - s * s))))
        rings.append([b.verts.new(p) for p in pts])
    n = len(rings[0])
    for a, c in zip(rings, rings[1:]):
        for j in range(n):
            k = (j + 1) % n
            b.faces.new((a[j], a[k], c[k], c[j]))
    b.faces.new(rings[0][::-1]); b.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
    K._add('黑漆', b, Matrix.Identity(4))
    xh, xt = -L / 2 + 0.1, L / 2 - 0.05         # 岳山、龙龈
    K.box('紫檀', xh - 0.012, -0.085, T - 0.004, xh + 0.012, 0.085, T + 0.012)
    K.box('紫檀', xt - 0.01, -0.06, T * 0.8, xt + 0.01, 0.06, T * 0.8 + 0.012)
    for s in range(7):                          # 七弦
        y0 = -0.06 + s * 0.02
        y1 = -0.04 + s * 0.0133
        K.rod('素绸', (xh, y0, T + 0.013), (xt, y1, T * 0.8 + 0.013), 0.0015, seg=4)
    Ls = xt - xh
    for f in (1 / 8, 1 / 6, 1 / 5, 1 / 4, 1 / 3, 2 / 5, 1 / 2, 3 / 5, 2 / 3, 3 / 4, 4 / 5, 5 / 6, 7 / 8):   # 十三徽
        x = xt - f * Ls
        w = W0 + (W1 - W0) * ((x + L / 2) / L)
        K.sph('瓷白', x, w / 2 - 0.025, T * 0.45 + T * 0.55 * math.sqrt(max(0.0, 1 - ((w / 2 - 0.025) * 2 / w) ** 2)) + 0.001,
              0.007 if f != 1 / 2 else 0.01, 0.007 if f != 1 / 2 else 0.01, 0.003, seg=8)
    for sy in (-1, 1):                          # 雁足（琴尾一对）+ 琴首下的护轸托
        K.cyl('紫檀', L / 2 - 0.32, sy * 0.04, -0.03, 0.0, 0.016, seg=8)
    K.box('紫檀', -L / 2 + 0.03, -0.07, -0.03, -L / 2 + 0.08, 0.07, 0.0)
    # 琴穗（绒扣垂下）
    K.rod('锦缎黄', (-L / 2 + 0.06, 0.05, 0.0), (-L / 2 + 0.03, 0.12, -0.18), 0.006, seg=4)


def xianglian(x0, x1, y, z0, z1, roll=True):
    """湘帘：细竹帘片 + 上卷的帘卷 + 两根系带。贴在 y 面上。"""
    if z1 - z0 > 0.05:
        K.box('YZ_湘帘', x0, y - 0.006, z0, x1, y + 0.006, z1)
        for k in range(int((z1 - z0) / 0.25)):
            z = z0 + 0.1 + k * 0.25
            K.box('湘妃竹', x0, y - 0.009, z, x1, y + 0.009, z + 0.008)
    if roll:
        K.rod('YZ_湘帘', (x0, y, z0 - 0.04), (x1, y, z0 - 0.04), 0.045, seg=10)
    K.box('湘妃竹', x0 - 0.02, y - 0.015, z1, x1 + 0.02, y + 0.015, z1 + 0.03)       # 帘杆
    for f in (0.2, 0.8):
        x = x0 + (x1 - x0) * f
        K.box('锦缎', x - 0.012, y - 0.05, z0 - 0.1, x + 0.012, y + 0.05, z1)


# ================= 明间四扇门敞开：向室内折贴两侧门柱 =================
for x_h, sgn in ((-1.50, 1), (1.50, -1)):
    for k in range(2):
        with K.at(x_h + sgn * 0.06 * k, -0.80, 0.65, 90):
            K.door_leaf('朱漆', 0.76, 2.38, t=0.05)

# ================= 正中：两个湘妃竹墩夹一张矮竹几，面水 =================
GY = 0.45
with K.at(0, GY, Z0):
    bamboo_frame(0.62, 0.42, 0.36, r=0.016)
    slat_top(0.62, 0.42, 0.34)
    K.col(-0.31, -0.21, 0, 0.31, 0.21, 0.36)
    K.teaset(-0.08, 0.02, 0.358, m='紫砂', cups=2)
    K.lathe('青瓷', 0.2, -0.08, 0.358, [(0.03, 0), (0.05, 0.02), (0.055, 0.05)], seg=12)   # 小盖碗
for sx in (-1, 1):
    tripo(f'湘妃竹墩{"W" if sx < 0 else "E"}', sx * 0.62, GY, Z0, 0.4, 0.4, 0.46, '-Y',
          'A round drum-shaped garden stool made of mottled Xiangfei spotted bamboo (brown-speckled bamboo canes), woven bamboo sides and a flat round seat, Chinese Qing dynasty, about 45 cm tall')

# ================= 西次间：竹榻 + 琴桌 =================
with K.at(XW + 0.42, 1.05, Z0, 90):           # 面朝 +X（靠背贴西山墙）
    bamboo_couch(w=1.9, d=0.78)
with K.at(XW + 0.01, 1.05, 0, 90):
    K.scroll(0, 0, 3.55, 1.0, 1.6, face=-1, paint='山水图')

QX, QY = -2.65, 0.55                          # 琴桌（长边顺 x）
with K.at(QX, QY, Z0):
    K.table('黑漆', 1.35, 0.45, 0.7, top=0.035, leg=0.045, apron=0.06)
    with K.at(0, 0.0, 0.73):                  # 琴：琴首在西（−x），徽在 +y（琴凳一侧）
        guqin()
with K.at(QX, QY + 0.62, Z0):
    bamboo_stool()

# ================= 一盏灯（羊角灯） =================
LAMP = (-1.35, 1.75)
K.candle_stand(LAMP[0], LAMP[1], Z0, h=1.3)
K.col(LAMP[0] - 0.18, LAMP[1] - 0.18, Z0, LAMP[0] + 0.18, LAMP[1] + 0.18, Z0 + 1.3)

# ================= 东次间：书案（笔砚诗笺）+ 竹椅 =================
SX, SY = 2.75, 0.75
with K.at(SX, SY, Z0):
    K.table('花梨', 1.5, 0.66, 0.8, top=0.04, leg=0.055, apron=0.07)
    K.study_set(0.25, 0.0, 0.8, 0)
    # 诗笺：几张散放的笺纸、一叠笺
    for i, (x, y, a) in enumerate(((-0.45, 0.05, 8), (-0.2, -0.12, -12), (-0.55, -0.18, 20))):
        with K.at(x, y, 0.8 + 0.001 * i, a):
            K.box('画心', -0.11, -0.15, 0, 0.11, 0.15, 0.002)
    K.box('书页', 0.52, 0.12, 0.8, 0.68, 0.3, 0.84)
    K.lathe('青瓷', 0.6, -0.2, 0.8, [(0.035, 0), (0.05, 0.03), (0.04, 0.06)], seg=12)   # 水丞
with K.at(SX, SY + 0.62, Z0):
    bamboo_chair()
with K.at(XE - 0.01, 1.0, 0, -90):
    K.scroll(0, 0, 3.55, 0.9, 1.6, face=-1, paint='墨竹图')
# 东山墙下一只竹花几，供一盆菖蒲似的小盆景
with K.at(XE - 0.3, 2.15, Z0):
    bamboo_frame(0.4, 0.4, 0.8, r=0.016)
    slat_top(0.4, 0.4, 0.78)
    K.penjing(0, 0, 0.8, 0.3)
    K.col(-0.2, -0.2, 0, 0.2, 0.2, 0.8)

# ================= 湘帘 =================
for sx in (-1, 1):
    xa, xb = sorted((sx * 1.9, sx * 4.66))
    xianglian(xa, xb, -0.70, 2.15, 3.02)          # 两次间：放下半幅
xianglian(-1.45, 1.45, -0.70, 3.0, 3.02)          # 明间：卷起

save_and_export(K)
print('TRIPO 占位：名称, 中心x, 中心y, 底z, 长x, 宽y, 高z, 正面')
for t in TRIPO:
    print('TRIPO', t[0], *[round(v, 3) for v in t[1:7]], t[7], '|', t[8])
print('LIGHT(web)', [LAMP[0], round(Z0 + 1.15, 2), -LAMP[1]])
