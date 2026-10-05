"""怡红院室内的透雕贴图（第十七回：“或流云百蝠，或岁寒三友，或山水人物，或翎毛花卉，或集锦，或博古，或万福万寿……
皆是名手雕镂，五彩销金嵌玉的”）。每张 512² RGBA、可平铺：外有边框、内为镂空纹样（透明处即镂空）。
雕面按透明边界做浮雕明暗，边沿贴金；花叶着五彩，云头嵌玉。网页里按材质名 雕花_* 贴 tex/diao_*.png（alphaTest 裁空）。
用法：python3 blender/scripts/interiors/diao_textures.py tex/
"""
import math, os, random, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

N = 512
K = 2            # 超采样
S = N * K
WOOD = np.array((0.30, 0.11, 0.07))
GOLD = np.array((0.86, 0.66, 0.27))
GREEN = np.array((0.16, 0.42, 0.3))
RED = np.array((0.7, 0.13, 0.12))
BLUE = np.array((0.12, 0.25, 0.5))
JADE = np.array((0.55, 0.78, 0.64))


def canvas():
    return Image.new('L', (S, S), 0)


def frame(d, w=34):
    w *= K
    d.rectangle((0, 0, S - 1, w), fill=255)
    d.rectangle((0, S - 1 - w, S - 1, S - 1), fill=255)
    d.rectangle((0, 0, w, S - 1), fill=255)
    d.rectangle((S - 1 - w, 0, S - 1, S - 1), fill=255)
    # 内线（线脚）
    i = w + 10 * K
    d.rectangle((i, i, S - 1 - i, S - 1 - i), outline=255, width=6 * K)


def jindi(d, step=32, w=5, kind='diag'):
    """锦地：主纹样底下满铺的细格（斜方格 / 万字格），雕花才显得满密。"""
    lo, hi = 40, 472
    if kind == 'diag':
        for c in range(-512, 1024, step):
            d.line(((lo + max(0, c - lo) if False else c) * K, lo * K, (c + (hi - lo)) * K, hi * K), fill=255, width=w * K)
            d.line(((c + (hi - lo)) * K, lo * K, c * K, hi * K), fill=255, width=w * K)
    else:
        for c in range(lo, hi + 1, step):
            d.line((c * K, lo * K, c * K, hi * K), fill=255, width=w * K)
            d.line((lo * K, c * K, hi * K, c * K), fill=255, width=w * K)


def clip_field(m):
    """锦地线只留在边框以内。"""
    a = np.asarray(m).copy()
    b = 40 * K
    a[:b, :] = 0; a[-b:, :] = 0; a[:, :b] = 0; a[:, -b:] = 0
    return Image.fromarray(a)


def stroke(d, pts, w):
    pts = [(x * K, y * K) for x, y in pts]
    d.line(pts, fill=255, width=int(w * K), joint='curve')
    r = w * K / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)


def spiral(cx, cy, r0, turns, ang0, sign=1, n=60):
    out = []
    for i in range(n):
        t = i / (n - 1)
        a = ang0 + sign * t * turns * 2 * math.pi
        r = r0 * (1 - 0.8 * t)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def ruyi_cloud(d, cx, cy, s, rot=0.0):
    """如意云头：三个卷涡 + 一条云尾。"""
    for (dx, dy, sg) in ((-0.55, 0.1, 1), (0.55, 0.1, -1), (0, -0.45, 1)):
        x, y = cx + s * (dx * math.cos(rot) - dy * math.sin(rot)), cy + s * (dx * math.sin(rot) + dy * math.cos(rot))
        stroke(d, spiral(x, y, s * 0.42, 1.25, rot + (math.pi if sg < 0 else 0), sg), s * 0.13)
    tail = [(cx + s * 0.4 * math.cos(rot + 1.6) + s * t * 1.6 * math.cos(rot + 0.5), cy + s * 0.4 * math.sin(rot + 1.6) + s * t * 1.6 * math.sin(rot + 0.5) + s * 0.25 * math.sin(t * 6)) for t in np.linspace(0, 1, 20)]
    stroke(d, tail, s * 0.12)


def bat(d, cx, cy, s):
    """蝙蝠（谐“福”）：对称双翼，翼缘作扇贝形。"""
    pts = []
    for side in (1, -1):
        wing = [(0.12, -0.15), (0.45, -0.35), (0.75, -0.3), (1.0, -0.05), (0.88, 0.05), (0.8, 0.22), (0.62, 0.15), (0.52, 0.32), (0.34, 0.2), (0.22, 0.32), (0.1, 0.2)]
        if side < 0:
            wing = [(-x, y) for x, y in reversed(wing)]
        pts += wing
    pts = [(cx + x * s, cy + y * s) for x, y in pts]
    d.polygon([(x * K, y * K) for x, y in pts], fill=255)
    d.ellipse(((cx - 0.13 * s) * K, (cy - 0.3 * s) * K, (cx + 0.13 * s) * K, (cy + 0.25 * s) * K), fill=255)
    for side in (1, -1):                                   # 耳
        d.polygon([((cx + side * 0.05 * s) * K, (cy - 0.28 * s) * K), ((cx + side * 0.13 * s) * K, (cy - 0.42 * s) * K), ((cx + side * 0.13 * s) * K, (cy - 0.24 * s) * K)], fill=255)


def five_petal(d, cx, cy, r, fill=255):
    for k in range(5):
        a = -math.pi / 2 + 2 * math.pi * k / 5
        x, y = cx + r * 0.55 * math.cos(a), cy + r * 0.55 * math.sin(a)
        d.ellipse(((x - r * 0.5) * K, (y - r * 0.5) * K, (x + r * 0.5) * K, (y + r * 0.5) * K), fill=fill)


def leaf_shape(d, cx, cy, L, W, ang, fill=255):
    pts = []
    for t in np.linspace(0, 1, 16):
        pts.append((t * L, W * math.sin(math.pi * t) ** 0.8))
    pts += [(t * L, -W * math.sin(math.pi * t) ** 0.8) for t in np.linspace(1, 0, 16)]
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([((cx + x * ca - y * sa) * K, (cy + x * sa + y * ca) * K) for x, y in pts], fill=fill)


def with_ground(m, kind='diag', step=32, w=5):
    g = canvas()
    jindi(ImageDraw.Draw(g), step, w, kind)
    g = clip_field(g)
    return Image.fromarray(np.maximum(np.asarray(m), np.asarray(g)))


def shade(mask, paints, seed):
    """mask: 雕体 L 图；paints: [(L 图, 颜色)] 局部着色。输出 RGBA 512²。"""
    m = mask.resize((N, N), Image.LANCZOS)
    a = np.asarray(m).astype(np.float32) / 255
    blur = np.asarray(m.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255
    gy, gx = np.gradient(blur)
    light = np.clip(0.5 - (gx * 0.7 + gy * 0.7) * 6, 0, 1)            # 左上受光
    body = np.asarray(m.filter(ImageFilter.MinFilter(5))).astype(np.float32) / 255
    edge = np.clip(a - body, 0, 1)                                   # 雕边一圈
    r = np.random.RandomState(seed)
    noise = np.asarray(Image.fromarray((r.rand(N // 8, N // 8) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255
    col = WOOD[None, None, :] * (0.75 + 0.5 * light[..., None]) * (0.9 + 0.2 * noise[..., None])
    for (pm, c) in paints:
        p = np.asarray(pm.resize((N, N), Image.LANCZOS)).astype(np.float32)[..., None] / 255
        col = col * (1 - p) + c[None, None, :] * (0.7 + 0.6 * light[..., None]) * p
    g = np.clip(edge * 1.6 + np.clip(light - 0.62, 0, 1) * 1.2, 0, 1)[..., None] * 0.9   # 销金：雕边、高处贴金
    col = col * (1 - g) + GOLD[None, None, :] * (0.8 + 0.4 * light[..., None]) * g
    out = np.dstack([np.clip(col, 0, 1) * 255, a * 255]).astype(np.uint8)
    rgb = Image.fromarray(out[..., :3])
    bl = rgb.filter(ImageFilter.GaussianBlur(4))                     # 镂空处填邻色，防 mip 黑边
    keep = a[..., None] > 0.5
    rgb = np.where(keep, out[..., :3], np.asarray(bl))
    return Image.fromarray(np.dstack([rgb, out[..., 3]]).astype(np.uint8), 'RGBA')


def yunfu(seed=1):
    """流云百蝠：中一蝠，四角如意云，云头嵌玉。"""
    m = canvas(); d = ImageDraw.Draw(m)
    frame(d)
    bat(d, 256, 250, 175)
    for (x, y, rot) in ((120, 118, 0.3), (392, 118, 2.8), (120, 392, -0.4), (392, 392, 3.5)):
        ruyi_cloud(d, x, y, 88, rot)
    for (x, y) in ((256, 90), (256, 430), (90, 256), (422, 256)):
        ruyi_cloud(d, x, y, 52, math.atan2(256 - y, 256 - x))
    jade = canvas(); dj = ImageDraw.Draw(jade)
    for (x, y) in ((120, 118), (392, 118), (120, 392), (392, 392)):
        dj.ellipse(((x - 16) * K, (y - 16) * K, (x + 16) * K, (y + 16) * K), fill=255)
        d.ellipse(((x - 18) * K, (y - 18) * K, (x + 18) * K, (y + 18) * K), fill=255)
    dj.ellipse(((256 - 20) * K, (238 - 20) * K, (256 + 20) * K, (238 + 20) * K), fill=255)
    m = with_ground(m, 'diag', 40, 5)
    return shade(m, [(jade, JADE)], seed)


def chanzhi(seed=2):
    """缠枝花卉：两道波状主藤贯通（左右相接可平铺），叶着绿，花着红、蓝，五彩。"""
    m = canvas(); d = ImageDraw.Draw(m)
    frame(d)
    gr = canvas(); dg = ImageDraw.Draw(gr)
    rd = canvas(); dr = ImageDraw.Draw(rd)
    bl = canvas(); db = ImageDraw.Draw(bl)
    for row, ph in ((176, 0.0), (336, math.pi)):
        pts = [(x, row + 46 * math.sin(x / 512 * 4 * math.pi + ph)) for x in np.linspace(40, 472, 60)]
        stroke(d, pts, 22)
        for k, x in enumerate((104, 232, 360, 456)):
            y = row + 46 * math.sin(x / 512 * 4 * math.pi + ph)
            up = -1 if math.cos(x / 512 * 4 * math.pi + ph) > 0 else 1
            # 卷须
            stroke(d, spiral(x + 18, y + up * 34, 22, 1.1, 0, 1, 30), 7)
            for la in (-0.6, 0.7):
                leaf_shape(d, x, y, 58, 20, la + (0 if up < 0 else math.pi))
                leaf_shape(dg, x, y, 53, 15, la + (0 if up < 0 else math.pi))
            if k % 2 == 0:
                fx, fy = x - 30, y - up * 40
                five_petal(d, fx, fy, 50)
                (five_petal(dr, fx, fy, 43) if (k + int(row)) % 4 else five_petal(db, fx, fy, 43))
                d.ellipse(((fx - 8) * K, (fy - 8) * K, (fx + 8) * K, (fy + 8) * K), fill=255)
    m = with_ground(m, 'grid', 42, 4)
    return shade(m, [(gr, GREEN), (rd, RED), (bl, BLUE)], seed)


def songzhumei(seed=3):
    """岁寒三友：一枝老梅斜出，旁有翠竹两竿、松针一簇。"""
    rnd = random.Random(seed)
    m = canvas(); d = ImageDraw.Draw(m)
    frame(d)
    gr = canvas(); dg = ImageDraw.Draw(gr)
    rd = canvas(); dr = ImageDraw.Draw(rd)
    # 梅：主干从左下到右上，折枝
    trunk = [(50, 470), (130, 380), (170, 300), (260, 240), (330, 160), (470, 80)]
    stroke(d, trunk, 22)
    for (a, b) in (((170, 300), (110, 200)), ((260, 240), (350, 290)), ((330, 160), (300, 60)), ((130, 380), (240, 420))):
        stroke(d, [a, ((a[0] + b[0]) / 2 + 10, (a[1] + b[1]) / 2 - 10), b], 12)
        for t in (0.5, 1.0):
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            five_petal(d, x, y, 26)
            five_petal(dr, x, y, 22)
    # 竹：两竿竖贯，竹节，竹叶成个字
    for x in (380, 420):
        stroke(d, [(x, 40), (x, 472)], 14)
        for y in range(80, 472, 70):
            stroke(d, [(x - 10, y), (x + 10, y)], 9)
    for (x, y) in ((360, 300), (430, 360), (395, 420)):
        for la in (2.4, 2.9, 3.4):
            leaf_shape(d, x, y, 60, 9, la)
            leaf_shape(dg, x, y, 56, 6, la)
    # 松：右下一簇松针
    for (cx, cy) in ((250, 420), (300, 380)):
        for k in range(14):
            a = math.pi * (1.05 + k / 13 * 0.9)
            stroke(d, [(cx, cy), (cx + 48 * math.cos(a), cy + 48 * math.sin(a))], 5)
            stroke(dg, [(cx, cy), (cx + 44 * math.cos(a), cy + 44 * math.sin(a))], 3)
    m = with_ground(m, 'diag', 44, 4)
    return shade(m, [(gr, GREEN), (rd, RED)], seed)


def huiwen(seed=4):
    """回纹：方折连续回旋，两行，上下左右相接可平铺。"""
    m = canvas(); d = ImageDraw.Draw(m)
    frame(d, 22)
    w = 18
    for oy in (60, 288):
        for ox in (40, 264):
            s = 200
            pts = [(ox, oy + s), (ox, oy), (ox + s, oy), (ox + s, oy + s * 0.8), (ox + s * 0.25, oy + s * 0.8), (ox + s * 0.25, oy + s * 0.25),
                   (ox + s * 0.75, oy + s * 0.25), (ox + s * 0.75, oy + s * 0.55), (ox + s * 0.5, oy + s * 0.55)]
            stroke(d, pts, w)
    return shade(m, [], seed)


def bingmei(seed=5):
    """冰裂纹嵌梅花（冰梅）：碎冰格子，交点处缀梅花。"""
    rnd = random.Random(seed)
    m = canvas(); d = ImageDraw.Draw(m)
    frame(d)
    rd = canvas(); dr = ImageDraw.Draw(rd)
    pts = [(rnd.uniform(60, 452), rnd.uniform(60, 452)) for _ in range(22)]
    border = [(40, 40), (472, 40), (472, 472), (40, 472)]
    for i, p in enumerate(pts):
        q = sorted(pts[:i] + pts[i + 1:] + border, key=lambda o: (o[0] - p[0]) ** 2 + (o[1] - p[1]) ** 2)
        for o in q[:3]:
            stroke(d, [p, o], 15)
    for p in pts[::2]:
        five_petal(d, p[0], p[1], 30)
        five_petal(dr, p[0], p[1], 25)
    return shade(m, [(rd, np.array((0.88, 0.8, 0.72)))], seed)


# ---------------- 多宝格：柜门、角花 ----------------
def guimen(seed=6):
    """柜门心板：起线框 + 中间夔龙团寿开光，四角云纹，满贴金线。不透空。"""
    m = canvas(); d = ImageDraw.Draw(m)
    d.rectangle((0, 0, S, S), fill=255)
    hl = canvas(); dh = ImageDraw.Draw(hl)                    # 凸起部分（受光、贴金）
    dh.rectangle((30 * K, 30 * K, (N - 30) * K, (N - 30) * K), outline=255, width=10 * K)
    dh.rectangle((56 * K, 56 * K, (N - 56) * K, (N - 56) * K), outline=255, width=5 * K)
    dh.ellipse((176 * K, 176 * K, 336 * K, 336 * K), outline=255, width=14 * K)
    # 团寿：回环方折
    w = 12
    for pts in ([(206, 216), (306, 216)], [(256, 200), (256, 312)], [(216, 256), (296, 256)], [(206, 296), (306, 296)],
                [(216, 236), (216, 276)], [(296, 236), (296, 276)]):
        stroke(dh, pts, w)
    for (x, y, rot) in ((100, 100, 0.8), (412, 100, 2.4), (100, 412, -0.8), (412, 412, -2.4)):
        ruyi_cloud(dh, x, y, 34, rot)
    gl = hl.filter(ImageFilter.MaxFilter(3))
    img = shade(m, [(gl, GOLD * 0.95)], seed)
    return img


def huaya(seed=7, flip=False):
    """角花（花牙子）：贴在格口上角的三角透雕——直角贴框，斜边内凹成弧，里面镂出卷草、如意，整体贴金。左上为直角，镜像得右上。"""
    m = canvas(); d = ImageDraw.Draw(m)
    # 实心三角：直角在左上，斜边是向角内凹的二次曲线
    curve = [((1 - t) ** 2 * 500 + 2 * (1 - t) * t * 150 + t * t * 0, (1 - t) ** 2 * 0 + 2 * (1 - t) * t * 150 + t * t * 500) for t in np.linspace(0, 1, 40)]
    d.polygon([(0, 0)] + [(x * K, y * K) for x, y in curve], fill=255)
    # 镂空：卷草两道、如意一朵、小圆眼
    cut = canvas(); dc = ImageDraw.Draw(cut)
    stroke(dc, spiral(150, 95, 62, 1.15, 0.2, 1), 15)
    stroke(dc, spiral(95, 150, 62, 1.15, -1.7, -1), 15)
    for (x, y, r) in ((60, 60, 22), (250, 40, 14), (40, 250, 14), (190, 190, 10)):
        dc.ellipse(((x - r) * K, (y - r) * K, (x + r) * K, (y + r) * K), fill=255)
    stroke(dc, [(320, 30), (380, 50), (420, 30)], 12)
    stroke(dc, [(30, 320), (50, 380), (30, 420)], 12)
    a = np.asarray(m).astype(np.int16) - np.asarray(cut).astype(np.int16)
    m = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    img = shade(m, [(m.copy(), GOLD)], seed)
    if flip:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


# ---------------- 满墙槽子（第十七回“满墙皆是随依古董玩器之形抠成的槽子”）----------------
# 1 m 见方一格的平铺板，槽口位置（u, v 自左下 0..1）、形状、宽、高；kit.niche_wall 按同一表在槽里摆器物
NICHES = [
    ('vase', 0.17, 0.62, 0.17, 0.36), ('qin', 0.6, 0.87, 0.56, 0.09), ('sword', 0.91, 0.43, 0.07, 0.62),
    ('gourd', 0.5, 0.53, 0.17, 0.31), ('round', 0.19, 0.2, 0.21, 0.21), ('fan', 0.53, 0.17, 0.32, 0.17),
    ('screen', 0.73, 0.55, 0.15, 0.19),
]


def niche_poly(shape, cx, cy, w, h, n=40):
    """槽口轮廓（tile 坐标 0..1，v 向上）。"""
    pts = []
    if shape == 'vase':
        prof = [(0.3, 0), (0.45, 0.05), (0.75, 0.35), (1.0, 0.68), (0.85, 0.84), (0.32, 0.92), (0.28, 0.97), (0.38, 1.0)]
        right = [(cx + r * w / 2, cy - h / 2 + t * h) for r, t in prof]
        pts = right + [(2 * cx - x, y) for x, y in reversed(right)]
    elif shape == 'gourd':
        prof = [(0, 0.15), (0.06, 0.62), (0.18, 0.98), (0.34, 0.98), (0.47, 0.66), (0.53, 0.42), (0.6, 0.52), (0.72, 0.66), (0.86, 0.6), (0.96, 0.32), (1.0, 0.1)]
        right = [(cx + r * w / 2, cy - h / 2 + t * h) for t, r in prof]
        pts = right + [(2 * cx - x, y) for x, y in reversed(right)]
    elif shape in ('round',):
        pts = [(cx + w / 2 * math.cos(2 * math.pi * i / n), cy + h / 2 * math.sin(2 * math.pi * i / n)) for i in range(n)]
    elif shape == 'qin':
        pts = [(cx - w / 2, cy - h * 0.35), (cx + w / 2 - h * 0.3, cy - h / 2), (cx + w / 2, cy - h * 0.2), (cx + w / 2, cy + h * 0.2),
               (cx + w / 2 - h * 0.3, cy + h / 2), (cx - w / 2, cy + h * 0.35)]
    elif shape == 'sword':
        pts = [(cx - w * 0.2, cy - h / 2), (cx + w * 0.2, cy - h / 2), (cx + w * 0.2, cy + h * 0.15), (cx + w / 2, cy + h * 0.15), (cx + w / 2, cy + h * 0.2),
               (cx + w * 0.2, cy + h * 0.2), (cx + w * 0.2, cy + h * 0.44), (cx, cy + h / 2), (cx - w * 0.2, cy + h * 0.44), (cx - w * 0.2, cy + h * 0.2),
               (cx - w / 2, cy + h * 0.2), (cx - w / 2, cy + h * 0.15), (cx - w * 0.2, cy + h * 0.15)]
    elif shape == 'fan':
        R, r0, a0 = h * 1.9, h * 0.85, math.radians(42)
        ox, oy = cx, cy - h / 2 - r0 + h * 0.05
        arc = [(ox + R * math.sin(t), oy + R * math.cos(t)) for t in np.linspace(-a0, a0, 18)]
        inner = [(ox + r0 * math.sin(t), oy + r0 * math.cos(t)) for t in np.linspace(a0, -a0, 12)]
        pts = arc + inner
    elif shape == 'screen':
        pts = [(cx - w / 2, cy - h / 2 + h * 0.12), (cx - w * 0.3, cy - h / 2 + h * 0.12), (cx - w * 0.3, cy - h / 2), (cx + w * 0.3, cy - h / 2),
               (cx + w * 0.3, cy - h / 2 + h * 0.12), (cx + w / 2, cy - h / 2 + h * 0.12), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    return pts


def caozi(seed=8):
    """满墙槽子板：紫檀板面，槽口镂空，口沿一圈贴金线。1024²，网页里 1 m 一格。"""
    n2 = 1024
    m = Image.new('L', (n2 * K, n2 * K), 255)
    d = ImageDraw.Draw(m)
    rim = Image.new('L', (n2 * K, n2 * K), 0)
    dr = ImageDraw.Draw(rim)
    for (sh, cx, cy, w, h) in NICHES:
        poly = [(u * n2 * K, (1 - v) * n2 * K) for u, v in niche_poly(sh, cx, cy, w, h)]
        dr.polygon(poly, outline=255, width=14 * K)
        d.polygon(poly, fill=0)
    m = m.resize((n2, n2), Image.LANCZOS)
    rim = rim.resize((n2, n2), Image.LANCZOS)
    a = np.asarray(m).astype(np.float32) / 255
    rr = np.asarray(rim).astype(np.float32)[..., None] / 255
    r = np.random.RandomState(seed)
    yy = np.mgrid[0:n2, 0:n2][1].astype(np.float32)
    grain = 0.5 + 0.5 * np.sin(yy / 7 + np.asarray(Image.fromarray((r.rand(64, 64) * 255).astype(np.uint8)).resize((n2, n2), Image.BICUBIC)).astype(np.float32) / 255 * 9)
    col = WOOD[None, None, :] * (0.85 + 0.25 * grain[..., None])
    col = col * (1 - rr) + GOLD[None, None, :] * rr
    out = np.dstack([np.clip(col, 0, 1) * 255, a * 255]).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


PATTERNS = {'yunfu': yunfu, 'chanzhi': chanzhi, 'songmei': songzhumei, 'huiwen': huiwen, 'bingmei': bingmei,
            'guimen': guimen, 'huaya': huaya, 'huayar': lambda: huaya(7, True), 'caozi': caozi}

if __name__ == '__main__':
    out = sys.argv[-1] if len(sys.argv) > 1 else 'tex'
    for k, f in PATTERNS.items():
        p = os.path.join(out, f'diao_{k}.png')
        f().save(p, optimize=True)
        print(p, os.path.getsize(p) // 1024, 'KB')
