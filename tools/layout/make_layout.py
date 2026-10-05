"""
大观园布局数据：把参考平面图上描下的水面 / 山形换算成园子坐标，写成 tex/layout.png。

  ref_water.png / ref_hill.png  参考平面图（1080×1439 像素）上按颜色描出的水面、山形
  换算：x = (px-575)*K，z = 120 + (py-1020)*K，K = 0.411 米/像素（正门 = (0,120)）
  输出 tex/layout.png：1 米一格，x -170..170（341 列），z -200..210（411 行）
    R = 水深权重（0 = 岸上，255 = 深水），G = 山高（0..255 → 0..24 米），B = 园内标记
用法：python3 tools/layout/make_layout.py
"""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
K = 0.411
X0, Z0, NX, NZ = -170, -200, 341, 411
HILL_MAX = 24.0          # layout.png 里 G 通道的满量程（米）；网页端、check_paths.py 按同一数换算

xs = X0 + np.arange(NX); zs = Z0 + np.arange(NZ)
XX, ZZ = np.meshgrid(xs, zs)          # [row=z, col=x]

def sample(img, px, py):
    a = np.asarray(img, dtype=np.float32)
    return nd.map_coordinates(a, [py, px], order=1, mode='constant', cval=0)

PX = 575 + XX / K; PY = 1020 + (ZZ - 120) / K
water = sample(Image.open(os.path.join(HERE, 'ref_water.png')).convert('L'), PX, PY) > 127
hill = sample(Image.open(os.path.join(HERE, 'ref_hill.png')).convert('L'), PX, PY)

# 园墙：主体 x -150..150, z -180..120；东南怡红院一块 x 20.6..150, z 120..190
garden = ((np.abs(XX) <= 150) & (ZZ >= -180) & (ZZ <= 120)) | ((XX >= 20.6) & (XX <= 150) & (ZZ >= 120) & (ZZ <= 190))
inner = nd.binary_erosion(garden, iterations=4)          # 水离墙至少 4 米
water &= inner; hill = np.where(nd.binary_erosion(garden, iterations=2), hill, 0)
# 被桥截断的溪：按参考图补成连续水道（起点、终点、宽度，米）
CONNECT = [((-100, 52), (30, 52), 7)]
for (ax, az), (bx, bz), w in CONNECT:
    t = np.clip(((XX - ax) * (bx - ax) + (ZZ - az) * (bz - az)) / ((bx - ax) ** 2 + (bz - az) ** 2), 0, 1)
    water |= (np.hypot(XX - (ax + t * (bx - ax)), ZZ - (az + t * (bz - az))) <= w / 2) & inner
# 小碎块去掉
lab, n = nd.label(water); sizes = nd.sum(water, lab, range(1, n + 1))
for i, s in enumerate(sizes):
    if s < 60: water[lab == i + 1] = False

SITES = json.load(open(os.path.join(HERE, 'sites.json')))
def rect(s, m):
    return (np.abs(XX - s['x']) <= s['hw'] + m) & (np.abs(ZZ - s['z']) <= s['hd'] + m)
for s in SITES:
    if s.get('pond'):                      # 建在池中：周围保证一片水
        water |= (np.hypot(XX - s['x'], ZZ - s['z']) <= s['pond']) & inner
        continue
    water &= ~rect(s, s.get('dry', 3))
    if not s.get('onHill'): hill = np.where(rect(s, 6), 0, hill)
    else: hill = np.where(rect(s, 2), 255, hill)

# 水深：到岸距离（米）
din = nd.distance_transform_edt(water); dout = nd.distance_transform_edt(~water)
sd = np.where(water, din, -dout)
W = np.clip((sd + 1.0) / 3.0, 0, 1)
# 山：参考图画的是等高线，先把每座山填实，再按离山脚的距离起坡；山越大越高。
# 园里大树十几米高，山要比树高出一截才像山，不像土坡：山脚陡、山顶圆（指数 < 1）
hb = nd.binary_closing(hill > 40, iterations=3); hb = nd.binary_fill_holes(hb) & ~water
lab, n = nd.label(hb); Hs = np.zeros_like(hill)
for i in range(1, n + 1):
    reg = lab == i; area = reg.sum()
    if area < 120: continue
    d = nd.distance_transform_edt(reg); peak = float(np.clip(np.sqrt(area) / 5, 4.0, 16.0))
    Hs = np.maximum(Hs, peak * np.power(np.clip(d / max(d.max(), 1), 0, 1), 0.6))
# 参考图上贴着园墙、等高线没闭合的山，直接按位置补：中心 x, z，半径 rx, rz，高（米）
EXTRA_HILLS = [(-12, -153, 52, 20, 15.0),
# 以下按原著补的山（院落占地 + 8 米过渡带内会被网页端压平，所以都放在占地之外）
# 第十七回 进门“只见一带翠嶂挡在前面”：翠嶂石山（模型在 x ±20）两翼接土山，连成一带；
#   两翼坐在下面的入口高台上（高度叠加），中轴园路穿翠嶂石洞过去
    (-41, 85, 20, 10, 8.0), (30, 87, 15, 10, 8.0),
# 第十七回 出怡红院往回走“忽见大山阻路，众人都道迷了路了”，“由山脚边忽一转”就是大门前大路
    (38, 157, 16, 21, 19.0),
# 第十七回 往稻香村“倏尔青山斜阻，转过山怀中，隐隐露出一带黄泥筑就矮墙”；
#   第四十九回 芦雪广“就在傍山临水河滩之上”：两处之间这座山，园路从山脚东边绕过去
    (-121, -21, 10, 11, 12.0)]
# 山势起伏：几组正弦叠出的低频扰动，让山脊有峰有坳，不是光滑的馒头
RUG = 0.82 + 0.18 * (0.5 + 0.5 * np.sin(XX * 0.21 + np.cos(ZZ * 0.17) * 2.0) * np.cos(ZZ * 0.23 - XX * 0.07))
for cx, cz, rx, rz, pk in EXTRA_HILLS:
    e = np.hypot((XX - cx) / rx, (ZZ - cz) / rz)
    Hs = np.maximum(Hs, pk * np.clip(1 - e, 0, 1) ** 0.6 * RUG * garden)
# 入口高台：第十七回“只见正门五间……下面白石台矶”，进门“一带翠嶂挡在前面”，“进入石洞来……再进数步，
#   渐向北边，平坦宽豁……俯而视之，则清溪泻雪，石磴穿云，白石为栏，环抱池沿，石桥三港，兽面衔吐。桥上有亭”。
#   正门、翠嶂、出洞后的平地同在一层高台上，沁芳池在低处：出洞即可俯看，再顺石磴下到池边。
#   园墙外接一道土台托住墙根；正门外顺“白石台矶”下到街面。
PLAT = 6.0
def ss(a, b, v): t = np.clip((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
ax = ss(-52, -40, XX) * (1 - ss(26, 44, XX))                         # 东西两头收坡（西至潇湘馆，东至怡红院路）
inner_pl = ax * ss(63, 82, ZZ) * np.where(XX > 20.6, 1 - ss(122, 132, ZZ), 1.0)   # 北面 z 82→63 下到池边
outer_pl = np.maximum(ax * (1 - ss(120, 130, ZZ)),                    # 墙外土台
                      (1 - ss(7, 12, np.abs(XX))) * (1 - ss(126, 150, ZZ)))         # 正门外台阶坡
PL = PLAT * np.where(garden, inner_pl, np.where((ZZ > 119) & (XX < 20.6), outer_pl, 0.0))
H = (nd.gaussian_filter(Hs, 1.5) + PL) * np.clip((-sd - 1) / 4, 0, 1)

img = np.zeros((NZ, NX, 3), np.uint8)
img[..., 0] = np.round(W * 255); img[..., 1] = np.round(H / HILL_MAX * 255); img[..., 2] = garden * 255
Image.fromarray(img, 'RGB').save(os.path.join(ROOT, 'tex', 'layout.png'), optimize=True)

# 每处建筑朝向：给出最近水面方向，供临水建筑面水
out = []
for s in SITES:
    i = int(round(s['z'] - Z0)); j = int(round(s['x'] - X0))
    r = 40; sub = dout[max(0, i - r):i + r, max(0, j - r):j + r] if False else None
    wz, wx = np.nonzero(water[max(0, i - r):i + r, max(0, j - r):j + r])
    near = None
    if len(wz):
        d = np.hypot(wz + max(0, i - r) - i, wx + max(0, j - r) - j); k = d.argmin()
        near = [float(wx[k] + max(0, j - r) - j), float(wz[k] + max(0, i - r) - i), float(d[k])]
    out.append({'id': s['id'], 'x': s['x'], 'z': s['z'], 'hill_m': round(float(H[i, j]), 2), 'water_dir': near})
json.dump(out, open(os.path.join(HERE, 'sites_out.json'), 'w'), ensure_ascii=False, indent=1)
print('water m2', int(water.sum()), 'hill max', round(float(H.max()), 2))
for o in out: print(o)
