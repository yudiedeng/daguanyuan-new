"""潇湘馆室内（第十七回、第二十六回、第四十回）。
用法：python3 blender/scripts/interiors/build_xiaoxiang.py

  第十七回：上面小小两三间房舍，一明两暗，里面都是合着地步打就的床几椅案。
  第二十六回：只见湘帘垂地，悄无人声。
  布局参照 references/…/图02-1 潇湘馆室内空间格局、图02-2 室内陈设（湘妃竹隔断、月洞罩、棋桌）。
  第四十回：刘姥姥因见窗下案上设着笔砚，又见书架上磊着满满的书，……
  “这那像个小姐的绣房，竟比那上等的书房还好。”

房屋（Blender 坐标，与 xiaoxiang.blend 相同）：地面 z=0.48，木顶棚 z=5.02。
室内 x ±3.68、y −1.75…2.53；内圈柱 x=±1.45（前 y=−1.8，后 y=2.65）。
西山墙有月洞窗（y −0.6…1.45）→ 西间作书房；东间作卧室；明间居中。
外壳改动（tools/glb_cut.mjs）：剪去明间两扇半掩的隔扇（另在此处做成全开），
湘帘明间一幅卷起到 z≈2.5；tex/xx_win.json 中两扇门格心贴片同时去掉。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from kit import Kit, new_file, save_and_export

Z0 = 0.48
ZC = 5.02
new_file()
K = Kit('xiaoxiang')
WOOD = '花梨'
BAMBOO = '湘妃竹'
GREEN = 'SAMPLE2_深绿漆'

K.box('方砖地', -3.68, -1.75, Z0, 3.68, 2.53, Z0 + 0.01)

# ---- 入口：明间两扇隔扇全开，贴着门框内侧；湘帘卷起 ----
for sx in (-1, 1):
    with K.at(sx * 0.7, -1.78, Z0 + 0.12, 90):
        K.door_leaf(GREEN, 0.62, 3.32 - 0.6, paper='XS_窗纸米白', t=0.05)
K.rod('YZ_湘竹篾', (-1.2, -3.72, 2.55), (1.2, -3.72, 2.55), 0.075, seg=12)   # 卷起的湘帘
for x in (-0.8, 0.8):
    K.rod('锦缎', (x, -3.72, 3.5), (x, -3.72, 2.47), 0.008, seg=4)

# ---- 西间：书房 ----
# 月洞窗下书案
with K.at(-3.25, 0.42, Z0, 90):
    K.qiaotou(WOOD, 1.7, 0.55, 0.82)
    K.study_set(0.0, 0.0, 0.82)
    K.books('书函', 0.45, 0.8, -0.2, 0.15, 0.82, 1.1, 1.0)
    K.box('画心', -0.75, -0.2, 0.82, -0.45, 0.1, 0.84)          # 诗稿
    K.vase('青瓷', -0.62, 0.15, 0.84, 0.26, 'gu')
    for i in range(5):                                         # 瓶中几枝竹
        a = i * 1.3
        K.rod('竹竿', (-0.62, 0.15, 1.05), (-0.62 + 0.12 * math.cos(a), 0.15 + 0.12 * math.sin(a), 1.55 + 0.08 * (i % 3)), 0.006, seg=4)
        K.sph('叶绿', -0.62 + 0.12 * math.cos(a), 0.15 + 0.12 * math.sin(a), 1.5 + 0.08 * (i % 3), 0.07, 0.03, 0.02, seg=6)
with K.at(-2.55, 0.42, Z0, -90):
    K.chair(BAMBOO, 'quan', cushion='青布')
# 满架书
for x in (-3.13, -2.05):
    with K.at(x, 2.3, Z0):
        K.shelf(BAMBOO, 1.06, 0.42, 2.9, rows=7, fill=0.97)
# 琴桌 + 琴（靠前檐窗下）
with K.at(-2.55, -1.38, Z0):
    K.table('黑漆', 1.25, 0.42, 0.7, top=0.03, leg=0.04, apron=0.05)
    K.box('黑漆', -0.6, -0.1, 0.7, 0.6, 0.1, 0.75)
    K.box('描金', -0.45, -0.1, 0.75, -0.43, 0.1, 0.752)
    for i in range(7):
        K.box('白布', -0.58, -0.07 + i * 0.023, 0.752, 0.58, -0.067 + i * 0.023, 0.755)  # 七弦
    for i in range(13):
        K.cyl('瓷白', -0.5 + i * 0.075, 0.09, 0.75, 0.753, 0.006, seg=6)               # 徽
# 落地罩（书房与明间之间，开敞）
with K.at(-1.45, 0.39, Z0, 90):
    K.luodizhao(BAMBOO, 4.28, ZC - Z0 - 0.02, shape='round', t=0.08)

# ---- 明间 ----
with K.at(0, 2.22, Z0):
    K.qiaotou(WOOD, 2.2, 0.5, 0.88)
    K.vase('青花', -0.75, 0.0, 0.88, 0.38, 'meiping')
    K.ding('铜', 0.0, 0.0, 0.88, 0.18)
    with K.at(0.7, 0, 0.88):
        K.box('紫檀', -0.2, -0.05, 0, 0.2, 0.05, 0.05)
        K.box('画绢', -0.17, -0.015, 0.05, 0.17, 0.015, 0.33)                          # 桌屏
        K.box('紫檀', -0.19, -0.02, 0.33, 0.19, 0.02, 0.36)
K.scroll(0, 2.5, Z0 + 3.9, 1.0, 2.4, face=-1, paint='墨竹图')
for sx in (-1, 1):
    K.scroll(sx * 0.95, 2.5, Z0 + 3.8, 0.36, 2.0, face=-1, paint='对联' + ('上' if sx < 0 else '下'))
    with K.at(sx * 1.2, 2.2, Z0):                              # 高花几 + 兰
        K.table(BAMBOO, 0.32, 0.32, 1.0, top=0.03, leg=0.03, apron=0.04, stretch=True)
        K.vase('青花', 0, 0, 1.0, 0.2, 'guan')
        for k in range(9):
            a = k * 0.7
            K.bar('叶绿', (0, 0, 1.18), (0.25 * math.cos(a), 0.25 * math.sin(a), 1.32 + 0.1 * (k % 3)), 0.02, 0.004)
with K.at(0, 1.05, Z0):                                        # 棋桌
    K.table(WOOD, 0.85, 0.85, 0.8)
    K.box('棋盘', -0.4, -0.4, 0.8, 0.4, 0.4, 0.803)
    for k, c in enumerate(('墨', '瓷白')):
        K.lathe(WOOD, (k * 2 - 1) * 0.3, 0.3, 0.803, [(0.06, 0), (0.07, 0.07), (0.05, 0.08)], seg=12)  # 棋罐
for sx in (-1, 1):
    with K.at(sx * 0.75, 1.05, Z0, 90 if sx < 0 else -90):
        K.chair(BAMBOO, 'guanmao', cushion='青布')
    with K.at(sx * 0.95, -0.6, Z0):
        K.stool('瓷白', top='青花', h=0.44, r=0.17)
K.lantern(0, 0.4, ZC, drop=0.55)

# ---- 东间：卧室（碧纱橱相隔） ----
with K.at(1.45, 0.39, Z0, -90):
    # 碧纱橱 6 扇槅扇，每扇宽 0.7133：第 5、6 扇（局部 x 0.713…2.14 → 世界 y −1.75…−0.32）开作门洞，两扇门敞开向东间折（原先 door 区间没对上槅扇网格，整面碧纱橱是实心的）
    K.lattice_partition(BAMBOO, 4.28, 3.3, paper='碧纱', door=(0.70, 2.15))
    for hx in (0.7133, 2.14):
        with K.at(hx, 0.04, 0, 90):
            K.door_leaf(BAMBOO, 0.70, 3.3, paper='碧纱', t=0.06)
    with K.at(0, 0, 3.3):
        K.lattice_partition(BAMBOO, 4.28, ZC - Z0 - 3.3 - 0.12, paper='碧纱')
with K.at(2.88, 1.25, Z0, -90):
    K.bed(WOOD, w=2.1, d=1.45, H=2.35, curtain='青纱', quilt='素绸', pillow='青布', frieze=WOOD)
with K.at(2.75, -1.3, Z0):                                    # 榻
    K.kang(BAMBOO, 1.6, 0.6, mat_cushion='青布', back=0.3)
with K.at(3.3, -0.35, Z0, -90):
    K.table(WOOD, 0.75, 0.42, 0.78)
    with K.at(0, 0.1, 0.78):
        K.mirror('紫檀', w=0.36, h=0.42, frame=0.03, stand=False, col=False)
    K.lathe('粉彩', -0.25, -0.05, 0.78, [(0.05, 0), (0.06, 0.06), (0.0, 0.07)], seg=12)   # 粉盒
with K.at(2.75, -0.35, Z0):
    K.stool('锦缎', top='描金', h=0.44, r=0.16)
with K.at(2.0, 0.2, Z0):                                     # 药炉：风炉上坐药吊子
    K.lathe('陶', 0, 0, 0, [(0.14, 0), (0.16, 0.2), (0.13, 0.3), (0.1, 0.3)], seg=14)
    K.box('炭', -0.05, -0.17, 0.08, 0.05, -0.15, 0.16)
    K.lathe('紫砂', 0, 0, 0.3, [(0.06, 0), (0.1, 0.05), (0.1, 0.12), (0.06, 0.17), (0.0, 0.18)], seg=14)
    K.rod('紫砂', (0.09, 0, 0.42), (0.16, 0, 0.46), 0.01, seg=5)
    K.col(-0.16, -0.16, 0, 0.16, 0.16, 0.5)
K.lantern(2.55, -0.5, ZC, drop=0.6)
K.lantern(-2.55, 0.0, ZC, drop=0.6)

# ---- 外壳碰撞 ----
W = [
    [-3.92, -2.0, Z0, -0.74, -1.65, ZC, False],
    [0.74, -2.0, Z0, 3.92, -1.65, ZC, False],
    [-3.92, -1.8, Z0, -3.68, 2.77, ZC, False],
    [3.68, -1.8, Z0, 3.92, 2.77, ZC, False],
    [-3.92, 2.53, Z0, 3.92, 2.77, ZC, False],
    [-3.92, -2.0, ZC, 3.92, 2.77, ZC + 0.6, False],     # 顶棚（挡相机）
    [-0.74, -2.0, Z0 + 2.9, 0.74, -1.65, ZC, False],    # 门上横窗
]


def solid_house(b):
    lx, lz, hx, hz, top, bot = b
    return abs(lx) < 0.5 and abs(lz + 0.43) < 0.5 and hx > 3.5 and hz > 2


save_and_export(K, shell_cols_filter=solid_house, extra_cols=W)
