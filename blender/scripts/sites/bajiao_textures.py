"""芭蕉（Musa basjoo）贴图：叶片（鲜叶 / 老叶 / 枯叶）、假茎。用 numpy + PIL 程序化画，带透明。
叶片 512×1024：u 横向（0 左缘、0.5 中脉、1 右缘），v 自叶基（底）到叶尖（顶）。
  - 粗而浅色的中脉，两侧细密平行侧脉，斜向叶尖；
  - 沿侧脉从叶缘向中脉撕开的裂口（芭蕉叶被风撕成一条条，正是“雨打芭蕉”的样子），裂口边焦黄；
  - 叶色黄绿、带斑驳，叶缘一线焦枯。
假茎 512×1024（可上下平铺）：一层层叶鞘纵纹，青绿夹紫褐斑，叶鞘边缘干膜。
用法：python3 blender/scripts/sites/bajiao_textures.py <out_dir>
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageFilter


def noise(h, w, cell, seed):
    r = np.random.RandomState(seed)
    sm = r.rand(max(2, h // cell + 2), max(2, w // cell + 2))
    return np.asarray(Image.fromarray((sm * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255


def fbm(h, w, seed):
    return 0.5 * noise(h, w, 96, seed) + 0.3 * noise(h, w, 24, seed + 1) + 0.2 * noise(h, w, 6, seed + 2)


def leaf(kind='fresh', seed=1, W=512, H=1024):
    r = np.random.RandomState(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - yy / (H - 1)                     # 0 叶基 → 1 叶尖
    u = (xx / (W - 1)) * 2 - 1               # -1 左缘 → 1 右缘
    side = np.sign(u + 1e-6)
    au = np.abs(u)
    # 叶形：长椭圆，叶基圆钝、叶尖钝圆；边缘微波
    prof = np.clip(np.sin(np.pi * np.clip(v * 0.97 + 0.015, 0, 1)), 0, 1) ** 0.42
    prof *= 0.975 + 0.025 * (noise(H, W, 40, seed + 50) - 0.5)
    inside = au < prof
    # 侧脉坐标：从中脉斜向叶尖伸出，脉线 = 等值线 (v - k*|u|)
    slope = 0.16
    vv = v - slope * au                      # 沿侧脉不变
    vein_f = 260.0
    vein = 0.5 + 0.5 * np.cos(vv * vein_f * 2 * math.pi)
    vein = vein ** 6
    # 撕裂：沿某几条侧脉从叶缘撕向中脉
    tears = np.zeros((H, W), bool)
    edge_burn = np.zeros((H, W), np.float32)
    n_tear = {'fresh': 12, 'old': 20, 'dry': 26}[kind]
    for i in range(n_tear):
        s = 1 if r.rand() < 0.5 else -1
        v0 = r.uniform(0.08, 0.95)
        depth = r.uniform(0.25, 0.92 if kind != 'fresh' else 0.7)    # 撕到离中脉多近
        width = r.uniform(0.004, 0.009) * (1 if kind == 'fresh' else 1.6)
        line = np.abs(vv - (v0 - slope)) < width + 0.004 * np.clip(au - (1 - depth), 0, 1)
        m = line & (side == s) & (au > (1 - depth) * prof * 0.98)
        tears |= m
        near = np.abs(vv - (v0 - slope)) < width + 0.006
        edge_burn = np.maximum(edge_burn, (near & (side == s) & (au > (1 - depth) * prof * 0.95)).astype(np.float32))
    a = (inside & ~tears).astype(np.float32)
    # 颜色
    n = fbm(H, W, seed + 10)
    if kind == 'fresh':
        base, light, rib = np.array((0.13, 0.28, 0.06)), np.array((0.26, 0.42, 0.1)), np.array((0.55, 0.62, 0.32))
    elif kind == 'old':
        base, light, rib = np.array((0.18, 0.28, 0.07)), np.array((0.38, 0.42, 0.12)), np.array((0.55, 0.56, 0.3))
    else:
        base, light, rib = np.array((0.35, 0.25, 0.12)), np.array((0.55, 0.42, 0.22)), np.array((0.6, 0.5, 0.3))
    k = np.clip(0.3 + 0.55 * n + 0.15 * au, 0, 1)[..., None]
    col = base * (1 - k) + light * k
    col *= (1 - 0.28 * vein)[..., None]                                        # 侧脉稍暗的细线
    mid = np.exp(-(u / 0.022) ** 2) * (0.6 + 0.4 * (1 - v))                    # 中脉，叶基粗
    col = col * (1 - mid[..., None]) + rib * mid[..., None]
    # 叶缘一线焦枯 + 撕口焦边 + 老叶的黄斑
    rim = np.clip((au / np.maximum(prof, 1e-3) - 0.975) / 0.025, 0, 1)
    burn = np.clip(np.maximum(rim, edge_burn * 0.8), 0, 1)
    if kind == 'old':
        yel = np.clip((noise(H, W, 140, seed + 20) - 0.55) * 3, 0, 1) * np.clip(au * 1.4, 0, 1)
        col = col * (1 - yel[..., None] * 0.7) + np.array((0.62, 0.55, 0.18)) * yel[..., None] * 0.7
        burn = np.clip(burn + np.clip((v - 0.85) * 5, 0, 1) * 0.6, 0, 1)
    brown = np.array((0.42, 0.3, 0.13))
    col = col * (1 - burn[..., None] * 0.6) + brown * burn[..., None] * 0.6
    if kind == 'dry':
        col *= (0.75 + 0.35 * noise(H, W, 10, seed + 30))[..., None]
    col *= (0.88 + 0.16 * noise(H, W, 3, seed + 40))[..., None]                # 细颗粒
    rgb = np.clip(col, 0, 1)
    # 透明处填邻色（无损存，网页 alphaTest 裁边，远处 mip 不发黑）
    im = Image.fromarray((rgb * 255).astype(np.uint8))
    bl = np.asarray(im.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
    rgb = np.where(a[..., None] > 0.5, rgb, bl * 0 + np.array(base))
    return Image.fromarray(np.dstack([(rgb * 255).astype(np.uint8), (a * 255).astype(np.uint8)]), 'RGBA')


def stem(seed=5, W=512, H=1024):
    """假茎：叶鞘纵向层层相叠（u 方向一片片，边缘一线干膜），青绿底带紫褐斑和白粉，竖向细纹；上下平铺。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    r = np.random.RandomState(seed)
    col = np.zeros((H, W, 3), np.float32)
    green, pale = np.array((0.36, 0.48, 0.2)), np.array((0.58, 0.64, 0.38))
    n = (noise(H, W, 64, seed) + noise(H, W, 16, seed + 1)) / 2
    k = np.clip(0.3 + 0.6 * n, 0, 1)[..., None]
    col[:] = green * (1 - k) + pale * k
    # 叶鞘边：几条斜向的分界（每片鞘从一侧包到另一侧），边缘干膜浅褐
    for i in range(5):
        x0 = (i + r.rand() * 0.4) / 5
        edge = (u - x0 - 0.04 * np.sin(v * 2 * math.pi + i)) % 1.0
        film = np.exp(-(edge / 0.012) ** 2)
        shade = np.clip(edge / 0.06, 0, 1)
        col *= (0.82 + 0.18 * shade)[..., None]
        col = col * (1 - film[..., None] * 0.7) + np.array((0.62, 0.52, 0.34)) * film[..., None] * 0.7
    # 纵纹
    col *= (0.9 + 0.1 * np.sin(u * 2 * math.pi * 90 + noise(H, W, 32, seed + 2) * 4))[..., None]
    # 紫褐斑块
    spot = np.clip((noise(H, W, 40, seed + 3) - 0.68) * 5, 0, 1) * np.clip((noise(H, W, 8, seed + 4) - 0.3) * 2, 0, 1)
    col = col * (1 - spot[..., None] * 0.75) + np.array((0.32, 0.2, 0.18)) * spot[..., None] * 0.75
    return Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8))


if __name__ == '__main__':
    out = sys.argv[-1] if len(sys.argv) > 1 else 'tex'
    os.makedirs(out, exist_ok=True)
    for kind, sd in (('fresh', 1), ('old', 2), ('dry', 3)):
        p = os.path.join(out, f'bajiao_{kind}.png')
        leaf(kind, sd).save(p)
        print(p)
    p = os.path.join(out, 'bajiao_stem.jpg')
    stem().save(p, quality=90)
    print(p)
