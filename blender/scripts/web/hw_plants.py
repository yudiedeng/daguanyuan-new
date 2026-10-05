"""蘅芜苑的藤萝异草（Blender 建模，替换网页里画布画的草卡、藤带）。

第十七回：“只见许多异草：或有牵藤的，或有引蔓的，或垂山巅，或穿石隙，甚至垂檐绕柱，萦砌盘阶，
或如翠带飘摇，或如金绳蟠屈，或实若丹砂，或花如金桂，味香气馥，非花香之可比。”
第四十回：“那些奇草仙藤愈冷愈苍翠，都结了实，似珊瑚豆子一般，累垂可爱。”

生成三样（叶片是带弧度、有叶脉起伏的三维面片，茎是细管，果、花是小球；颜色写在顶点色里）：
  1. models/b/hw_vines.wasm —— 院里所有藤蔓，按位置烘好（院落模型坐标）：
       垂山巅、穿石隙：hw_vines.json 的 D（贴着石面往下爬的折线，见 hw_vines.mjs）
       绕柱：游廊内侧檐柱、清厦两侧廊前柱、院门门柱，各缠两道螺旋
       垂檐：游廊内侧檐枋、清厦前檐
       萦砌盘阶：清厦台基沿上垂下、落地再沿阶脚爬开；甬路边沿贴地爬（hw_vines.json 的 P）
       南墙内外两面垂挂
  2. models/p/hw_plants.glb —— 网页实例化用的单株：
       herb_0 杜蘅（心形叶贴地）  herb_1 白芷（羽状复叶）  herb_2 兰蕙（长带叶，两枝金桂似的小黄花）  herb_3 珊瑚豆（小叶，结红果）
       herb_4 茝兰（高 1 m 上下）  herb_5 清葛（蔓生成团，三出复叶）  herb_6 杜若（直立宽叶，蓝黑果）  herb_7 紫芸（紫红叶）
       strand_0..3 垂藤一条（2 m，顶端为原点往下垂）：翠带、金绳、珊瑚豆、细叶垂帘 —— 花溆洞口等处用
四种藤：翠带（常春藤似的叶）、金绳（金黄细藤，叶稀，缀小金花）、珊瑚豆（叶密，一串串红果）、细叶（薜荔似的小叶）。

用法：python3 blender/scripts/web/hw_plants.py   （需要 pip install bpy；之后脚本自己调 pack_plants.mjs 压缩）
坐标：脚本里按网页坐标（y 向上）造几何，建 Blender 网格时换成 Blender 坐标（x, -z, y），导出 glTF 时 +Y 向上又换回来。
"""
import bpy, json, math, os, random, subprocess, sys
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TMP = os.environ.get('TMPDIR', '/tmp')
J = json.load(open(os.path.join(ROOT, 'models', 'b', 'hw_vines.json')))
rnd = random.Random(1717)
R = lambda a, b: a + rnd.random() * (b - a)

def srgb(h):  # '#rrggbb' -> 线性 rgb
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
def lerp3(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
def mul3(a, k): return tuple(min(1, x * k) for x in a)

STAT = {}
# 叶片图集 tex/hw_leaf_atlas.webp（2×2 格，Blender UV 左下为原点）：白蜡羽状叶、山杨圆叶（调成深绿）、橡树裂叶、山杨黄叶（紫芸染红用）
# 照片枝叶取自 three.js 植物库 ez-tree（MIT，@dgreenheck/ez-tree）。茎、果、花的 UV 指向图集里一块实心白，颜色靠顶点色。
TILE = {'ash': (0.0, 0.5), 'aspg': (0.5, 0.5), 'oak': (0.0, 0.0), 'aspy': (0.5, 0.0)}
WHITE = (1000 / 2048, 1 - 2024 / 2048)
class Geo:
    def __init__(s): s.V = []; s.F = []; s.C = []; s.U = []
    def add(s, verts, faces, cols, uvs=None):
        k = sys._getframe(1).f_code.co_name; STAT[k] = STAT.get(k, 0) + sum(len(f) - 2 for f in faces)
        b = len(s.V); s.V += verts; s.F += [[b + i for i in f] for f in faces]; s.C += cols; s.U += uvs or [WHITE] * len(verts)
    def tris(s): return sum(len(f) - 2 for f in s.F)

def frame(d, up_hint):
    d = d.normalized(); side = d.cross(up_hint)
    if side.length < 1e-4: side = d.cross(Vector((1, 0, 0)))
    side.normalize(); up = side.cross(d).normalized(); return d, side, up

def leaf(g, base, d, up_hint, L, W, shape, cb, ct, cup=0.35, droop=0.25, rows=4):
    """叶片：沿 d 长 L、宽 W；up_hint 大致是叶面朝向。叶缘略向上卷（cup），叶尖下垂（droop）。"""
    d, side, up = frame(d, up_hint)
    us = [i / rows for i in range(rows + 1)]; vs = (-1, 0, 1)
    def hw(u):
        if shape == 'heart': return (1 - u) ** 0.85 * (0.62 + 1.25 * u) * 0.95
        if shape == 'lance': return math.sin(math.pi * min(u, 0.999)) ** 1.1 * 0.9 + 0.04
        if shape == 'strap': return 1 - 0.8 * u ** 2.2
        if shape == 'ivy': return math.sin(math.pi * min(u * 0.95 + 0.04, 0.999)) ** 0.65
        return math.sin(math.pi * min(u * 0.92 + 0.06, 0.999)) ** 0.8  # ovate
    verts, cols = [], []
    for u in us:
        h = hw(u)
        for v in vs:
            along = u * L
            if shape == 'heart' and u == 0 and v != 0: along -= 0.18 * L   # 心形叶基的两耳
            p = base + d * along + side * (v * W / 2 * h) + up * (cup * abs(v) * W * 0.3 * h - droop * u * u * L)
            verts.append(tuple(p)); c = lerp3(cb, ct, u)
            cols.append(mul3(c, 1.25) if v == 0 else c)
    faces = []
    for i in range(rows):
        for j in range(2):
            a = i * 3 + j; faces.append([a, a + 1, a + 4, a + 3])
    g.add(verts, faces, cols)

def card(g, base, d, n_hint, L, tile, tint, fold=0.3, droop=0.2):
    """照片枝叶卡：叶枝基部在 base，朝 d 方向伸出长 L（宽同长），叶面大致朝 n_hint；沿中线对折一点、梢头下垂。"""
    d, side, up = frame(d, n_hint); u0, v0 = TILE[tile]; verts, cols, uvs = [], [], []
    for u in (0, 0.5, 1):
        for v in (-1, 0, 1):
            p = base + d * (u * L) + side * (v * L / 2) + up * (fold * abs(v) * L * 0.22 - droop * u * u * L)
            verts.append(tuple(p)); cols.append(mul3(tint, 1.0 if v else 1.06)); uvs.append((u0 + 0.25 + v * 0.25, v0 + u * 0.5))
    faces = [[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]]
    g.add(verts, faces, cols, uvs)

def tube(g, pts, r, col, sides=3):
    if len(pts) < 2: return
    verts, cols, faces = [], [], []
    prev = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = prev if prev is not None else t.cross(Vector((0.3, 1, 0.2))).normalized()
        n = (n - t * n.dot(t)).normalized(); prev = n; b = t.cross(n)
        for k in range(sides):
            a = 2 * math.pi * k / sides; verts.append(tuple(p + (n * math.cos(a) + b * math.sin(a)) * r)); cols.append(col)
    for i in range(len(pts) - 1):
        for k in range(sides):
            a, b2 = i * sides + k, i * sides + (k + 1) % sides
            faces.append([a, b2, b2 + sides, a + sides])
    g.add(verts, faces, cols)

def ball(g, c, r, col, sq=1.0):
    P = [(r, 0, 0), (-r, 0, 0), (0, r * sq, 0), (0, -r * sq, 0), (0, 0, r), (0, 0, -r)]
    verts = [tuple(c + Vector(p)) for p in P]
    faces = [[0, 2, 4], [4, 2, 1], [1, 2, 5], [5, 2, 0], [4, 3, 0], [1, 3, 4], [5, 3, 1], [0, 3, 5]]
    g.add(verts, faces, [col] * 6)

def resample(pts, ds):
    out = [pts[0]]; acc = [0.0]; carry = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; L = (b - a).length
        if L < 1e-6: continue
        t = ds - carry
        while t <= L:
            out.append(a.lerp(b, t / L)); acc.append(acc[-1] + ds); t += ds
        carry = L - (t - ds)
    return out, acc

BERRY = [srgb(h) for h in ('#b8321f', '#9e2a1c', '#c9452a', '#ad3a22', '#c23a24')]
GOLD = [srgb(h) for h in ('#d9b048', '#e6c460', '#c89a34')]
LEAF = {  # 叶基色、叶尖色（sRGB）
    'cui': [('#1d3517', '#30532a'), ('#1a3015', '#2b4a24'), ('#223e1b', '#3a5e30')],
    'jin': [('#3a5426', '#5a7a34'), ('#34502a', '#52743a')],
    'shan': [('#1a3015', '#2a4a24'), ('#20381a', '#33572c')],
    'xi': [('#1c3416', '#2f5226'), ('#223e1a', '#3a6030')],
}
STEM = {'cui': srgb('#3e3a24'), 'jin': srgb('#9c7a2c'), 'shan': srgb('#3a3622'), 'xi': srgb('#2f3a20')}

def vine(g, pts, out, kind, spread=1.0, twig=True):
    """一条藤：pts 自上而下的折线（Vector），out 每点外侧方向（Vector 或 i->Vector），kind：cui 翠带 / jin 金绳 / shan 珊瑚豆 / xi 细叶。"""
    if len(pts) < 2: return
    P, A = resample(pts, 0.03); n = len(P); total = A[-1]
    if n < 3: return
    O = [(out(min(int(i / n * len(pts)), len(pts) - 1)) if callable(out) else out) for i in range(n)]
    stemc = STEM[kind]
    tube(g, P[::7] + [P[-1]], 0.0042 if kind != 'xi' else 0.003, stemc)
    if kind == 'jin':  # 金绳：再绕一根更细的
        tw = [P[i] + (O[i].cross(Vector((0, 1, 0))).normalized() * math.sin(A[i] * 18) * 0.012 if O[i].cross(Vector((0, 1, 0))).length > 0.1 else Vector()) for i in range(0, n, 4)]
        tube(g, tw, 0.0025, mul3(stemc, 0.85))
    CARD = {'cui': (0.11, (0.28, 0.42), ('oak', 'aspg')), 'jin': (0.14, (0.22, 0.32), ('ash',)), 'shan': (0.1, (0.28, 0.4), ('ash', 'aspg')), 'xi': (0.09, (0.2, 0.28), ('ash',))}   # 藤别盖满，要看得出“一块巨石当门”
    sp, (l0, l1), tiles = CARD[kind]
    s, alt = R(0, sp), 1
    while s < total:
        i = min(int(s / 0.03), n - 1); f = s / max(total, 1e-6)
        if rnd.random() < f * 0.25: s += sp; continue          # 越往下越稀
        p = P[i]; t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized(); o = O[i]
        side = t.cross(o); side = side.normalized() if side.length > 1e-4 else Vector((1, 0, 0))
        k = (1.0 - 0.35 * f) * R(0.85, 1.15)
        d = (side * alt * R(0.5, 0.9) * spread + o * R(0.2, 0.5) + t * R(0.2, 0.7) + Vector((R(-.15, .15), R(-.1, .15), R(-.15, .15)))).normalized()   # 枝叶顺藤往下、往两边斜出
        b = R(0.62, 0.86); tint = (b * R(0.88, 0.96), b, b * R(0.9, 1.0))   # 深一些、冷一些
        card(g, p, d, o + Vector((0, 0.3, 0)), R(l0, l1) * k, rnd.choice(tiles), tint, 0.3, R(0.05, 0.25))
        if kind == 'jin' and rnd.random() < 0.3:   # 花如金桂
            for _ in range(rnd.randint(4, 7)): ball(g, p + side * alt * 0.025 + Vector((R(-.02, .02), R(-.03, .01), R(-.02, .02))), R(0.004, 0.006), rnd.choice(GOLD), 0.7)
        alt = -alt; s += sp * R(0.8, 1.2)
    # 侧枝：每隔一段斜出一小枝，挂三五片叶，藤显得蓬松
    if twig:
        s = R(0.1, 0.35)
        while s < total * 0.85:
            if rnd.random() < 0.18:
                i = min(int(s / 0.03), n - 1); p = P[i]; o = O[i]; t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)]).normalized()
                sd = t.cross(o); sd = sd.normalized() if sd.length > 1e-4 else Vector((1, 0, 0)); sd *= (1 if rnd.random() < 0.5 else -1)
                tl = R(0.12, 0.28); q = [p, p + (sd * 0.6 + o * 0.3 + t * 0.5).normalized() * tl * 0.5, p + (sd * 0.5 + o * 0.25 + t * 0.9).normalized() * tl]
                vine(g, q, o, kind, spread, twig=False)
            s += R(0.25, 0.45)
    every, prob, nb = {'cui': (0.5, 0.2, (3, 4)), 'jin': (1, 0, (0, 0)), 'shan': (0.32, 0.8, (4, 6)), 'xi': (0.8, 0.1, (2, 3))}[kind]
    s = R(0.1, every)
    while s < total * 0.92:
        if rnd.random() < prob:
            i = min(int(s / 0.03), n - 1); p = P[i] + O[i] * 0.02
            for _ in range(rnd.randint(*nb)): ball(g, p + Vector((R(-.03, .03), R(-.06, 0.0), R(-.03, .03))) + O[i] * R(0, 0.02), R(0.011, 0.016), rnd.choice(BERRY))
        s += every * R(0.7, 1.3)

def pick(w):
    u = rnd.random()
    for k, x in zip(('cui', 'jin', 'shan', 'xi'), w):
        u -= x
        if u <= 0: return k
    return 'xi'

# ------------------------------------------------------------------ 1. 院中藤蔓（烘在原位）
V = Geo(); WR = (0.42, 0.14, 0.24, 0.20)
for d in J['D']:   # 垂山巅、穿石隙（短的去掉一部分，控制面数）
    if len(d) < 3 * 4 + 2 and rnd.random() < 0.3: continue   # 只略去一部分最短的
    dx, dz = d[0], d[1]; pts = [Vector((d[i], d[i + 1], d[i + 2])) for i in range(2, len(d), 3)]; o = Vector((dx, 0.0, dz))
    pts = [p + o * 0.03 for p in pts]; vine(V, pts, o, pick(WR))
    if len(pts) > 6 and rnd.random() < 0.15:
        sh = Vector((dz, 0, -dx)) * 0.16; m = max(3, int(len(pts) * R(0.4, 0.9))); vine(V, [p + sh for p in pts[:m]], o, pick(WR))
COLS = []
for sx in (-1, 1):
    for z in (-6.81, -5.1, -2.9, -0.6, 1.58, 3.9, 6.1, 8.4, 10.6, 12.8): COLS.append((sx * 15.45, z, 0.42, 2.9))
    for x in (10.5, 12.2, 13.81): COLS.append((sx * x, -5.1, 0.42, 2.9))
for x, z in ((-0.85, 12.55), (0.85, 12.55), (-0.85, 13.45), (0.85, 13.45)): COLS.append((x, z, 0.05, 2.7))
for x, z, lo, hi in COLS:   # 绕柱
    if rnd.random() < 0.12: continue
    a0, turns = R(0, 6.283), R(1.6, 2.8)
    for k in range(2 if rnd.random() < 0.5 else 1):
        end = lo + (hi - lo) * (R(0.3, 0.7) if k else 0.0); pts, outs = [], []
        for i in range(41):
            t = i / 40; a = a0 + k * math.pi + t * turns * 6.283 * (-1 if k else 1); r = 0.17 + 0.02 * math.sin(t * 9)
            pts.append(Vector((x + math.cos(a) * r, hi - (hi - end) * t, z + math.sin(a) * r))); outs.append(Vector((math.cos(a), 0.15, math.sin(a))))
        vine(V, pts, lambda i, outs=outs: outs[i], pick((0.45, 0.2, 0.25, 0.1)), 0.7)
for sx in (-1, 1):  # 垂檐：游廊内侧檐枋
    z = -6.5
    while z < 12.8:
        if rnd.random() < 0.75:
            L = R(0.4, 1.7); vine(V, [Vector((sx * 15.25, 2.85, z)), Vector((sx * 15.25 - sx * 0.04, 2.85 - L * 0.5, z + R(-.05, .05))), Vector((sx * 15.25, 2.85 - L, z + R(-.08, .08)))], Vector((-sx, 0, 0)), pick((0.3, 0.15, 0.25, 0.3)))
        z += R(0.55, 1.05)
x = -8.0
while x <= 8.0:     # 垂檐：清厦前檐
    if rnd.random() < 0.8:
        L = R(0.5, 2.1); vine(V, [Vector((x, 4.1, -2.55)), Vector((x + R(-.05, .05), 4.1 - L * 0.5, -2.5)), Vector((x + R(-.1, .1), 4.1 - L, -2.52))], Vector((0, 0, 1)), pick((0.3, 0.15, 0.25, 0.3)))
    x += R(0.5, 1.0)
x = -8.2
while x <= 8.2:     # 萦砌盘阶：台基沿上垂下，落地再沿阶脚爬开
    if abs(x) > 1.7 or rnd.random() < 0.25:
        sd, run = (-1 if rnd.random() < 0.5 else 1), R(0.4, 1.4)
        pts = [Vector(p) for p in ((x, 0.82, -3.2), (x, 0.82, -2.88), (x, 0.55, -2.8), (x, 0.25, -2.76), (x, 0.04, -2.66), (x + sd * run * 0.5, 0.03, -2.45), (x + sd * run, 0.03, -2.3 + R(0, 0.4)))]
        outs = [Vector((0, 1, 0)), Vector((0, 0.6, 0.6)), Vector((0, 0, 1)), Vector((0, 0, 1)), Vector((0, 0.6, 0.6)), Vector((0, 1, 0)), Vector((0, 1, 0))]
        vine(V, pts, lambda i, outs=outs: outs[i], pick((0.4, 0.3, 0.2, 0.1)))
    x += R(0.4, 0.9)
for px, pz, a in J['P']:   # 甬路边沿贴地爬
    L = R(0.8, 1.6); d = Vector((math.sin(a), 0, math.cos(a))); w = Vector((d.z, 0, -d.x))
    pts = [Vector((px, 0.03, pz)) + d * (L * t) + w * (math.sin(t * 5 + px) * 0.08) for t in (0, 0.25, 0.5, 0.75, 1)]
    vine(V, pts, Vector((0, 1, 0)), 'cui' if rnd.random() < 0.5 else 'jin')
x = -14.5
while x <= 14.5:    # 南墙内外两面（院门左右）
    if abs(x) >= 2.3:
        for zf, o, prob, lo_hi in ((13.1, -1, 0.8, (1.2, 3.3)), (14.4, 1, 0.75 if abs(x) < 7 else 0, (1.0, 3.2))):
            if rnd.random() < prob:
                L = R(*lo_hi); pts = [Vector((x + math.sin(t * 4 + x) * 0.05, 3.35 - L * t, zf + o * 0.03)) for t in (0, 0.2, 0.4, 0.6, 0.8, 1)]
                vine(V, pts, Vector((0, 0, o)), pick((0.42, 0.12, 0.26, 0.2)))
    x += R(0.45, 0.95)
print('vines tris', V.tris(), 'verts', len(V.V), STAT)

# ------------------------------------------------------------------ 1b. 花溆港洞的藤萝（路径由 blender/scripts/sites/huaxu_cave.py 沿石面算出；港洞局部坐标）
HX = Geo(); HXP = os.path.join(ROOT, 'models', 'b', 'hx_vines.json')
if os.path.exists(HXP):
    for d in json.load(open(HXP))['D']:
        dx, dz = d[0], d[1]; pts = [Vector((d[i], d[i + 1], d[i + 2])) for i in range(2, len(d), 3)]
        keep, tot, stall = [pts[0]], 0.0, 0     # 截短：总长不过 5 m；连续三步不往下走（在石面上打转）就停
        for a, b in zip(pts, pts[1:]):
            tot += (b - a).length; stall = stall + 1 if a.y - b.y < 0.03 else 0
            if tot > 5 or stall >= 3: break
            keep.append(b)
        if len(keep) >= 3: vine(HX, keep, Vector((dx, 0, dz)), pick((0.4, 0.15, 0.3, 0.15)))
    print('huaxu vines tris', HX.tris())

# ------------------------------------------------------------------ 2. 单株异草、垂藤
def herb_duheng():     # 杜蘅：一丛圆叶贴地斜展
    g = Geo()
    for i in range(9):
        a = i / 9 * 6.283 + R(-.3, .3); d = Vector((math.cos(a), R(0.35, 0.8), math.sin(a)))
        b = R(0.75, 0.95); card(g, Vector((0, 0, 0)), d, Vector((0, 1, 0)), R(0.24, 0.34), 'aspg', (b * 0.95, b, b * 0.95), 0.35, R(0.15, 0.3))
    return g
def herb_baizhi():     # 白芷：羽状复叶几枝斜出
    g = Geo()
    for i in range(8):
        a = i / 8 * 6.283 + R(-.3, .3); d = Vector((math.cos(a) * R(0.4, 0.8), 1, math.sin(a) * R(0.4, 0.8)))
        b = R(0.8, 1.0); card(g, Vector((R(-.03, .03), 0, R(-.03, .03))), d, Vector((math.cos(a), 0.2, math.sin(a))), R(0.38, 0.55), 'ash', (b * 0.95, b, b * 0.92), 0.3, R(0.1, 0.25))
    return g
def herb_lanhui():
    g = Geo()
    for i in range(20):
        a = R(0, 6.283); L = R(0.32, 0.62)
        d = Vector((math.cos(a) * R(0.25, 0.6), 1, math.sin(a) * R(0.25, 0.6)))
        cb, ct = rnd.choice([(srgb('#24421c'), srgb('#3e6a32')), (srgb('#2a4a20'), srgb('#4a7a3a')), (srgb('#1f3a19'), srgb('#365c2a'))])
        leaf(g, Vector((R(-.02, .02), 0, R(-.02, .02))), d, Vector((math.cos(a + 1.57), 0, math.sin(a + 1.57))), L, R(0.016, 0.024), 'strap', cb, ct, 0.6, 1.1, 5)
    for i in range(2):   # 两枝小黄花
        a = R(0, 6.283); top = Vector((math.cos(a) * 0.08, R(0.4, 0.55), math.sin(a) * 0.08))
        tube(g, [Vector((0, 0, 0)), top * 0.5, top], 0.0025, srgb('#5a6a30'))
        for k in range(9):
            p = Vector((0, 0, 0)).lerp(top, R(0.65, 1.0)) + Vector((R(-.02, .02), R(-.01, .01), R(-.02, .02))); ball(g, p, R(0.005, 0.007), rnd.choice(GOLD), 0.8)
    return g
def herb_shanhu():     # 珊瑚豆：小叶枝几枝，结一串串红果
    g = Geo()
    for i in range(7):
        a = i / 7 * 6.283 + R(-.3, .3); d = Vector((math.cos(a) * R(0.3, 0.7), 1, math.sin(a) * R(0.3, 0.7)))
        b = R(0.75, 0.95); L = R(0.32, 0.45); card(g, Vector((0, 0, 0)), d, Vector((math.cos(a), 0.2, math.sin(a))), L, rnd.choice(('ash', 'aspg')), (b * 0.92, b, b * 0.92), 0.3, 0.15)
        if i % 2 == 0:
            q = d.normalized() * L * R(0.5, 0.8)
            for _ in range(rnd.randint(5, 8)): ball(g, q + Vector((R(-.03, .03), R(-.05, 0), R(-.03, .03))), R(0.011, 0.015), rnd.choice(BERRY))
    return g
def herb_chailan():   # 茝兰：一人来高，几枝大羽状复叶
    g = Geo()
    for i in range(5):
        a = i / 5 * 6.283 + R(-.4, .4); H = R(0.45, 0.75); top = Vector((math.cos(a) * 0.08, H, math.sin(a) * 0.08))
        tube(g, [Vector((0, 0, 0)), top], 0.007, srgb('#4e5e30'))
        for k in range(3):
            b2 = a + k * 2.1 + R(-.3, .3); d = Vector((math.cos(b2) * R(0.4, 0.8), R(0.6, 1.0), math.sin(b2) * R(0.4, 0.8)))
            b = R(0.8, 1.0); card(g, top * R(0.6, 1.0), d, Vector((math.cos(b2), 0.3, math.sin(b2))), R(0.5, 0.7), 'ash', (b * 0.92, b, b * 0.9), 0.3, R(0.15, 0.3))
    return g
def herb_qingge():    # 清葛：大叶蔓生成团，贴地铺开一米多宽
    g = Geo()
    for i in range(14):
        a = i / 14 * 6.283 + R(-.25, .25); r0 = R(0.0, 0.25); base = Vector((math.cos(a) * r0, R(0.05, 0.25), math.sin(a) * r0))
        d = Vector((math.cos(a), R(0.05, 0.35), math.sin(a))); b = R(0.75, 0.95)
        card(g, base, d, Vector((0, 1, 0)), R(0.38, 0.55), 'oak', (b * 0.95, b, b * 0.92), 0.35, R(0.2, 0.35))
    return g
def herb_duruo():     # 杜若：直立几枝，顶上几粒蓝黑果
    g = Geo()
    for i in range(5):
        a = i / 5 * 6.283 + R(-.3, .3); d = Vector((math.cos(a) * R(0.15, 0.4), 1, math.sin(a) * R(0.15, 0.4))); L = R(0.5, 0.75)
        b = R(0.75, 0.92); card(g, Vector((0, 0, 0)), d, Vector((math.cos(a), 0, math.sin(a))), L, 'aspg', (b * 0.9, b, b * 0.95), 0.3, 0.08)
        if i < 2:
            top = d.normalized() * L * 0.95
            for _ in range(rnd.randint(3, 6)): ball(g, top + Vector((R(-.03, .03), R(-.02, .03), R(-.03, .03))), R(0.009, 0.012), srgb(rnd.choice(('#2a3a6a', '#3a4a7a', '#283058'))))
    return g
def herb_ziyun():     # 紫芸：“红的自然是紫芸”——山杨黄叶染成紫红
    g = Geo()
    for i in range(8):
        a = i / 8 * 6.283 + R(-.3, .3); d = Vector((math.cos(a) * R(0.4, 0.8), 1, math.sin(a) * R(0.4, 0.8)))
        b = R(0.55, 0.75); card(g, Vector((0, 0, 0)), d, Vector((math.cos(a), 0.2, math.sin(a))), R(0.32, 0.45), 'aspy', (b, b * 0.32, b * 0.4), 0.3, R(0.1, 0.25))
    return g
HERBS = [herb_duheng(), herb_baizhi(), herb_lanhui(), herb_shanhu(), herb_chailan(), herb_qingge(), herb_duruo(), herb_ziyun()]
STRANDS = []
for kind in ('cui', 'jin', 'shan', 'xi'):
    g = Geo(); pts = [Vector((math.sin(t * 3.0) * 0.03, -2.0 * t, 0)) for t in [i / 10 for i in range(11)]]
    vine(g, pts, Vector((0, 0, 1)), kind)
    vine(g, [p + Vector((0.13, 0.04, 0.01)) for p in pts[:7]], Vector((0, 0, 1)), kind)
    STRANDS.append(g)
print('herb tris', [h.tris() for h in HERBS], 'strand tris', [s.tris() for s in STRANDS])

# ------------------------------------------------------------------ 建网格、导出
bpy.ops.wm.read_factory_settings(use_empty=True)
mat = bpy.data.materials.new('HW_藤叶')
def build(name, g):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, -z, y) for x, y, z in g.V], [], g.F); me.update()
    ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(g.C): ca.data[i].color = (c[0], c[1], c[2], 1.0)
    me.color_attributes.active_color = ca
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices: uvl.data[li].uv = g.U[me.loops[li].vertex_index]
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob); return ob
def export(objs, dst):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=False, export_image_format='NONE',
                              export_materials='EXPORT', export_yup=True, export_vertex_color='ACTIVE', export_normals=True, export_texcoords=True)
ov = build('hw_vines', V)
export([ov], os.path.join(TMP, 'hw_vines.glb'))
if HX.F:
    ohx = build('hx_vines', HX); export([ohx], os.path.join(TMP, 'hx_vines.glb'))
objs = [build('herb_%d' % i, h) for i, h in enumerate(HERBS)] + [build('strand_%d' % i, s) for i, s in enumerate(STRANDS)]
export(objs, os.path.join(TMP, 'hw_plants.glb'))
pk = os.path.join(HERE, 'pack_plants.mjs')
subprocess.run(['node', pk, os.path.join(TMP, 'hw_vines.glb'), os.path.join(ROOT, 'models', 'b', 'hw_vines.wasm')], check=True, cwd=HERE)
if HX.F: subprocess.run(['node', pk, os.path.join(TMP, 'hx_vines.glb'), os.path.join(ROOT, 'models', 'b', 'hx_vines.wasm')], check=True, cwd=HERE)
subprocess.run(['node', pk, os.path.join(TMP, 'hw_plants.glb'), os.path.join(ROOT, 'models', 'p', 'hw_plants.glb')], check=True, cwd=HERE)
