"""怡红院门前花园用的花叶贴图集（1024²，RGBA）：用 PIL 画出带脉纹、渐变、噪点的月季花瓣（红/粉/白/黄）、
锯齿月季小叶、石竹、小白花、萱草花瓣、细叶草。yihong_garden.py 按 CELLS 给花瓣和叶片贴 UV。
单独运行：python3 yihong_atlas.py out.png
"""
import math, random, sys
import numpy as np
from PIL import Image, ImageFilter

S = 1024          # 宽
SH = 1280         # 高：最下一行是海棠
# 名称: (x0, y0, w, h)，PIL 坐标（y 向下）；格子底边是花瓣/叶的基部
CELLS = {
    'petal_red': (0, 0, 256, 512), 'petal_pink': (256, 0, 256, 512), 'petal_white': (512, 0, 256, 512), 'petal_yellow': (768, 0, 256, 512),
    'leaf': (0, 512, 512, 512), 'dianthus': (512, 512, 256, 256), 'smallwhite': (768, 512, 256, 256),
    'lily': (512, 768, 256, 256), 'blade': (768, 768, 256, 256),
    'haitang': (0, 1024, 256, 256), 'ht_bud': (256, 1024, 128, 256), 'leaf_young': (384, 1024, 256, 256), 'bitao': (640, 1024, 256, 256),
}


def noise(h, w, scale, seed):
    r = np.random.RandomState(seed)
    small = r.rand(max(2, h // scale), max(2, w // scale))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255.0


def fbm(h, w, seed):
    return 0.5 * noise(h, w, 64, seed) + 0.3 * noise(h, w, 16, seed + 1) + 0.2 * noise(h, w, 4, seed + 2)


def petal_cell(w, h, base, mid, edge, seed, notch=0.06, veins=0.08):
    """花瓣：底部窄、顶端圆而略带波，底部偏暗偏黄，边缘透亮，放射细脉。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = 1 - yy / (h - 1)                         # 0 底 → 1 顶
    u = (xx - w / 2) / (w / 2)
    prof = np.clip(np.sin(np.pi * np.clip(0.06 + 0.94 * t, 0, 1)), 0, 1) ** 0.6 * (0.42 + 0.58 * np.clip(t * 1.4, 0, 1))
    top = 1 - notch * np.cos(u * np.pi * 2.0) * (t > 0.85)
    inside = (np.abs(u) < prof * 0.96) & (t < 0.985 * top) & (t > 0.004)
    a = inside.astype(np.float32)
    # 颜色：底 → 中 → 边
    c = np.zeros((h, w, 3), np.float32)
    k1 = np.clip(t / 0.35, 0, 1)[..., None]
    c[:] = np.array(base) * (1 - k1) + np.array(mid) * k1
    rim = np.clip((np.abs(u) / np.maximum(prof, 1e-3) - 0.7) / 0.3, 0, 1) * 0.6 + np.clip((t - 0.8) / 0.2, 0, 1) * 0.5
    c = c * (1 - rim[..., None]) + np.array(edge) * rim[..., None]
    # 放射脉纹
    ang = np.arctan2(xx - w / 2, (h - yy) + h * 0.15)
    v = 0.5 + 0.5 * np.sin(ang * 70 + fbm(h, w, seed) * 6)
    c *= (1 - veins * (v ** 3)[..., None])
    # 低频斑驳 + 基部压暗（花心里的阴影）
    n = fbm(h, w, seed + 7)
    c *= (0.9 + 0.2 * n)[..., None]
    c *= (0.7 + 0.3 * np.clip(t / 0.25, 0, 1))[..., None]
    return c, a


def leaf_cell(w, h, seed):
    """月季小叶：卵形、尖头、锯齿边；中脉 + 斜出侧脉；深绿而有光泽。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = 1 - yy / (h - 1)
    u = (xx - w / 2) / (w / 2)
    prof = np.clip(np.sin(np.pi * np.clip(t, 0, 1)), 0, 1) ** 0.75 * (1 - 0.35 * t) * 0.78
    teeth = 1 - 0.07 * np.abs(((t * 22) % 1) - 0.5) * 2
    inside = (np.abs(u) < prof * teeth) & (t > 0.03) & (t < 0.98)
    a = inside.astype(np.float32)
    n = fbm(h, w, seed)
    c = np.zeros((h, w, 3), np.float32)
    dark, light = np.array((0.11, 0.2, 0.06)), np.array((0.27, 0.4, 0.13))
    k = (0.35 + 0.4 * n + 0.25 * np.abs(u))[..., None]
    c[:] = dark * (1 - k) + light * k
    mid = np.exp(-(u / 0.018) ** 2)
    side = np.exp(-((((np.abs(u) * 0.9 - (t - 0.1) * 0.8) * 9) % 1 - 0.5) / 0.05) ** 2) * (np.abs(u) > 0.03)
    vein = np.clip(mid * 0.9 + side * 0.35, 0, 1)
    c = c * (1 - vein[..., None] * 0.5) + np.array((0.45, 0.55, 0.25)) * vein[..., None] * 0.5
    c *= (0.85 + 0.15 * np.clip(1 - np.abs(u) / np.maximum(prof, 1e-3), 0, 1))[..., None]
    return c, a


def flower_cell(w, h, k, col, ring, edge, center, seed, fringe=0.0, rr=0.95):
    """正面小花：k 瓣，圆瓣或流苏边，花心一圈深色环。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    x, y = (xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)
    r, th = np.hypot(x, y), np.arctan2(y, x)
    lobe = np.abs(np.cos(th * k / 2))
    R = rr * (0.45 + 0.55 * lobe ** 0.6)
    if fringe:
        R *= 1 - fringe * (0.5 + 0.5 * np.sin(th * k * 9))
    a = (r < R).astype(np.float32)
    c = np.zeros((h, w, 3), np.float32)
    kk = np.clip(r / 0.35, 0, 1)[..., None]
    c[:] = np.array(ring) * (1 - kk) + np.array(col) * kk
    e = np.clip((r / np.maximum(R, 1e-3) - 0.75) / 0.25, 0, 1)[..., None]
    c = c * (1 - e) + np.array(edge) * e
    c *= (0.88 + 0.24 * fbm(h, w, seed))[..., None]
    c *= (1 - 0.12 * (0.5 + 0.5 * np.sin(th * 60)))[..., None] * 1.0
    cm = r < 0.13
    c[cm] = np.array(center) * (0.8 + 0.4 * fbm(h, w, seed + 3)[cm])[..., None]
    a[cm] = 1
    return c, a


def blade_cell(w, h, seed):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / (w - 1)
    t = 1 - yy / (h - 1)
    c = np.zeros((h, w, 3), np.float32)
    k = (0.3 + 0.5 * t + 0.2 * noise(h, w, 8, seed))[..., None]
    c[:] = np.array((0.12, 0.22, 0.07)) * (1 - k) + np.array((0.36, 0.48, 0.17)) * k
    c *= (0.85 + 0.15 * np.sin(u * np.pi * 14) ** 2)[..., None]
    c *= (0.8 + 0.2 * np.exp(-((u - 0.5) / 0.08) ** 2))[..., None]
    return c, np.ones((h, w), np.float32)


def build(path):
    img = np.zeros((SH, S, 4), np.float32)
    parts = {
        'petal_red': petal_cell(256, 512, (0.35, 0.03, 0.06), (0.62, 0.05, 0.11), (0.78, 0.16, 0.22), 11),
        'petal_pink': petal_cell(256, 512, (0.95, 0.85, 0.65), (0.93, 0.5, 0.6), (0.99, 0.8, 0.84), 12),
        'petal_white': petal_cell(256, 512, (0.92, 0.88, 0.62), (0.96, 0.93, 0.86), (1.0, 0.99, 0.96), 13, veins=0.05),
        'petal_yellow': petal_cell(256, 512, (0.95, 0.7, 0.2), (0.98, 0.85, 0.45), (1.0, 0.95, 0.75), 14),
        'leaf': leaf_cell(512, 512, 21),
        'dianthus': flower_cell(256, 256, 5, (0.88, 0.2, 0.45), (0.45, 0.04, 0.16), (0.98, 0.75, 0.85), (0.95, 0.92, 0.85), 31, fringe=0.08),
        'smallwhite': flower_cell(256, 256, 5, (0.97, 0.96, 0.92), (0.9, 0.88, 0.75), (1, 1, 1), (0.95, 0.75, 0.15), 32, rr=0.9),
        'lily': petal_cell(256, 256, (0.85, 0.55, 0.05), (0.96, 0.45, 0.07), (0.98, 0.6, 0.2), 33, notch=0.0),
        'blade': blade_cell(256, 256, 41),
        # 西府海棠：花瓣外面胭脂红、里面渐淡粉，花心淡黄蕊；花苞朱砂；嫩叶黄绿
        'haitang': flower_cell(256, 256, 5, (0.86, 0.26, 0.38), (0.97, 0.72, 0.74), (0.72, 0.08, 0.2), (0.93, 0.85, 0.45), 51, rr=0.96),
        'bitao': flower_cell(256, 256, 5, (0.95, 0.52, 0.62), (0.98, 0.8, 0.84), (0.9, 0.38, 0.5), (0.95, 0.8, 0.4), 54, rr=0.96),
        'ht_bud': petal_cell(128, 256, (0.45, 0.04, 0.06), (0.72, 0.08, 0.12), (0.8, 0.2, 0.22), 52, notch=0.0, veins=0.03),
        'leaf_young': leaf_cell(256, 256, 53),
    }
    c, a = parts['leaf_young']
    parts['leaf_young'] = (np.clip(c * np.array((1.25, 1.35, 1.0)) + np.array((0.05, 0.06, 0.0)), 0, 1), a)
    for k, (c, a) in parts.items():
        x0, y0, w, h = CELLS[k]
        img[y0:y0 + h, x0:x0 + w, :3] = np.clip(c, 0, 1)
        img[y0:y0 + h, x0:x0 + w, 3] = a
    # 透明处填邻近颜色（防止 mip 时边缘发黑）
    rgb = Image.fromarray((img[..., :3] * 255).astype(np.uint8))
    al = Image.fromarray((img[..., 3] * 255).astype(np.uint8))
    bl = rgb.filter(ImageFilter.GaussianBlur(6))
    m = np.asarray(al)[..., None] > 127
    out = np.where(m, np.asarray(rgb), np.asarray(bl))
    Image.fromarray(np.dstack([out, np.asarray(al)]).astype(np.uint8), 'RGBA').save(path)
    return path


def uv(cell, u, v):
    """格内坐标 u∈[0,1] 左→右，v∈[0,1] 基部→顶端 → Blender UV（v 向上）。"""
    x0, y0, w, h = CELLS[cell]
    return ((x0 + u * w) / S, 1 - (y0 + (1 - v) * h) / SH)


if __name__ == '__main__':
    print(build(sys.argv[-1]))
