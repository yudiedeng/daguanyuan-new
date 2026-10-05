"""栊翠庵外观细部（在 blender/longcui.blend 上就地修改，可重复执行）。
用法：python3 blender/scripts/sites/longcui_detail.py        （改 longcui.blend，只导出新加的细部 → /tmp/longcui_xi.glb）
      node blender/scripts/web/pack_glb.mjs /tmp/longcui_xi.glb models/b/longcui_xi.wasm
外壳 wasm（不是 pack_glb 流水线出的，见 longcui_doors.py）直接改，两步都只能从原始模型跑一次：
      node tools/glb_lift.mjs models/b/longcui.wasm models/b/longcui.wasm "$(python3 blender/scripts/sites/longcui_detail.py --liftspec)"
      node tools/glb_cut.mjs  models/b/longcui.wasm models/b/longcui.wasm "$(python3 blender/scripts/sites/longcui_detail.py --cutspec)"

原模型的毛病：佛殿檐檩直接压在额枋、平板枋上，檐下一片平板，没有斗栱；各屋正脊是两块方条，
吻兽、戗脊翘头、走兽都是几块小方块垒的“像素”弯钩；柱头与额枋交接处光秃。改为：

1. 佛殿屋面整体抬高 LIFT（0.66 m，按连通块判定：在佛殿平面范围内、最低点高于 5.4、最高点高于 5.68 的构件），
   让出一圈五踩单翘单昂斗栱（斗口 D = LIFT/11）：柱头科、平身科（明间四攒、次间三攒、山面廊步一攒、后五攒）、
   四角角科（斜翘斜昂、由昂）；正心枋、拽枋、挑檐枋、井口枋，挑檐桁；正心线上垫栱板；山面补平板枋。
   斗栱青绿相间（彩画青 / 枋绿），斗升青色，拱眼壁朱红。前金柱一线（槅扇门上方）加垫板、隔架科，免得从廊下望进殿顶。
2. 正脊全部重做（佛殿、山门、东西禅堂、东西耳房）：当沟、压当条、混砖线脚、脊身、盖脊筒瓦；两端正吻
   （吞脊的龙头、卷尾、剑把、背兽、鳍）。佛殿歇山：垂脊、戗脊（随屋面起伏，末端起翘），垂兽、戗兽，
   戗脊上仙人 + 三只走兽，仔角梁头套兽，脊中宝顶（莲座宝瓶托火焰珠）；山花绶带金钱、博缝板梅花钉、悬鱼。
   原来的脊（材质 M_屋脊灰，围墙压顶除外）从外壳里剪掉。
3. 雀替：佛殿前檐、东禅堂/西厢前檐、东西耳房檐柱与额枋交角处，卷草轮廓，青绿地描金边。
4. 风铎：佛殿四角仔角梁下各挂一只铜铎。
坐标是 Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z）。新件与 longcui 同一原点，网页里 {id:'longcui_xi'} 同位同转角。
"""
import sys, json, math
LIFT = 0.66
LIFT_BOX = (-6.72, 1.95, 6.72, 11.3)          # 佛殿屋面平面范围（耳房、禅堂的屋面都伸出盒外，不会被带上去）
LIFT_ZMIN, LIFT_ZMAX = 5.4, 5.68              # 平板枋顶 5.66 不动，檐檩（5.66–5.88）以上整块抬
LIFT_RING, LIFT_ZLOW = (-5.75, 2.75, 5.75, 10.05), 5.0   # 柱网外（出檐部分）z>5.0 的顶点也抬：滴水、连檐压得比平板枋低
if '--liftspec' in sys.argv:
    print(json.dumps(dict(box=LIFT_BOX, zmin=LIFT_ZMIN, zmax=LIFT_ZMAX, dz=LIFT, ring=LIFT_RING, zlow=LIFT_ZLOW))); sys.exit(0)
if '--cutspec' in sys.argv:                   # 旧屋脊：围墙压顶 z≤4.17 留着
    print(json.dumps([[-20, -20, 4.3, 20, 20, 20, '^M_屋脊灰$']])); sys.exit(0)

import bpy, bmesh, os
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, '..', '..', 'longcui.blend'))
OUT = '/tmp/longcui_xi.glb'
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
COLL = '栊翠庵_细部'


# ---------------------------------------------------------------- 1a. 抬佛殿屋面（.blend 里只做一次）
def lift_vert(p):
    rx0, ry0, rx1, ry1 = LIFT_RING
    return (LIFT_BOX[0] <= p.x <= LIFT_BOX[2] and LIFT_BOX[1] <= p.y <= LIFT_BOX[3] and p.z > LIFT_ZLOW
            and not (rx0 < p.x < rx1 and ry0 < p.y < ry1))


def lift_blend():
    sc = bpy.context.scene
    if sc.get('lc_lift'):
        return
    n = 0
    for o in list(bpy.data.collections['栊翠庵_佛殿'].objects):
        if o.type != 'MESH':
            continue
        bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
        mw = o.matrix_world; seen = set()
        for v in bm.verts:
            if v.index in seen:
                continue
            st = [v]; seen.add(v.index); grp = []
            while st:
                a = st.pop(); grp.append(a)
                for e in a.link_edges:
                    b = e.other_vert(a)
                    if b.index not in seen:
                        seen.add(b.index); st.append(b)
            W = [mw @ g.co for g in grp]
            x0, x1 = min(p.x for p in W), max(p.x for p in W)
            y0, y1 = min(p.y for p in W), max(p.y for p in W)
            z0, z1 = min(p.z for p in W), max(p.z for p in W)
            d = mw.inverted().to_3x3() @ Vector((0, 0, LIFT))
            if x0 >= LIFT_BOX[0] and x1 <= LIFT_BOX[2] and y0 >= LIFT_BOX[1] and y1 <= LIFT_BOX[3] and z0 > LIFT_ZMIN and z1 > LIFT_ZMAX:
                for g in grp:
                    g.co += d
                n += 1
                continue
            for g, p in zip(grp, W):
                if lift_vert(p):
                    g.co += d
        bm.to_mesh(o.data); bm.free()
    sc['lc_lift'] = LIFT
    print('lifted blocks', n)


def drop_old_ridges():
    """旧屋脊（M_屋脊灰，围墙压顶除外）从 .blend 里删掉：与网页外壳剪掉的一致。"""
    for o in list(O):
        if o.type == 'MESH' and o.data.materials and o.data.materials[0] and o.data.materials[0].name == 'M_屋脊灰' \
                and not o.name.startswith('围墙'):
            bpy.data.objects.remove(o, do_unlink=True)


lift_blend()
# 屋面射线（在删旧脊之前建：戗脊、垂脊沿屋面走）
def build_bvh(pred):
    dg = bpy.context.evaluated_depsgraph_get(); bm = bmesh.new()
    for o in O:
        if o.type != 'MESH' or not pred(o):
            continue
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world)
        tm = bpy.data.meshes.new('tmp'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
    b = BVHTree.FromBMesh(bm); bm.free(); return b

ROOF = build_bvh(lambda o: o.users_collection[0].name == '栊翠庵_佛殿' and ('屋面' in o.name or '撒头' in o.name) and '望板' not in o.name)
UNDER = build_bvh(lambda o: o.users_collection[0].name == '栊翠庵_佛殿' and ('望板' in o.name or 'wood_dark' in o.name))
DECK = build_bvh(lambda o: o.users_collection[0].name == '栊翠庵_佛殿' and '屋面' in o.name and '望板' in o.name)   # 只要上身屋面（不要撒头）
drop_old_ridges()
if COLL in bpy.data.collections:
    for o in list(bpy.data.collections[COLL].objects):
        bpy.data.objects.remove(o, do_unlink=True)
    C = bpy.data.collections[COLL]
else:
    C = bpy.data.collections.new(COLL); bpy.context.scene.collection.children.link(C)


def roof_z(x, y, top=12.0):
    h = ROOF.ray_cast(Vector((x, y, top)), Vector((0, 0, -1)), 20)
    return h[0].z if h[0] is not None else None


def under_z(x, y, z, bvh=None):
    h = (bvh or UNDER).ray_cast(Vector((x, y, z)), Vector((0, 0, 1)), 4)
    return h[0].z if h[0] is not None else None


# ---------------------------------------------------------------- 几何工具（按材质累积到 bmesh）
G = {}

def B(m):
    if m not in G:
        G[m] = bmesh.new()
    return G[m]


def faces(m, vs, fs):
    bm = B(m); V = [bm.verts.new(v) for v in vs]
    for f in fs:
        try:
            bm.faces.new([V[i] for i in f])
        except ValueError:
            pass


class F:
    """局部坐标系：原点 o，u（沿墙）、v（向外）、w（向上）"""
    def __init__(self, o, u, v, w=(0, 0, 1)):
        self.o, self.u, self.v, self.w = Vector(o), Vector(u).normalized(), Vector(v).normalized(), Vector(w).normalized()

    def __call__(self, a, b, c):
        return self.o + self.u * a + self.v * b + self.w * c


def box(m, f, u0, u1, v0, v1, w0, w1):
    vs = [f(u, v, w) for w in (w0, w1) for v in (v0, v1) for u in (u0, u1)]
    faces(m, vs, [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)])


def frustum(m, f, cu, cv, hu0, hv0, hu1, hv1, w0, w1):
    """下口 hu0×hv0、上口 hu1×hv1 的方台（斗底）"""
    vs = [f(cu + su * hu, cv + sv * hv, w) for (hu, hv, w) in ((hu0, hv0, w0), (hu1, hv1, w1))
          for (su, sv) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    faces(m, vs, [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])


def prism(m, f, poly, axis, a0, a1):
    """二维轮廓沿一轴拉伸：axis='u' 时 poly 为 (v,w)，axis='v' 时 poly 为 (u,w)"""
    n = len(poly)
    if axis == 'u':
        P = lambda a, p: f(a, p[0], p[1])
    else:
        P = lambda a, p: f(p[0], a, p[1])
    vs = [P(a0, p) for p in poly] + [P(a1, p) for p in poly]
    fs = [tuple(range(n))[::-1], tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    faces(m, vs, fs)


def sweep(m, path, prof, cap=True, scales=None):
    """沿折线扫掠截面。prof 为 (h, w)：h 横向（水平、垂直于路径），w 向上；路径点即截面原点。scales：逐点缩放截面"""
    vs = []; n = len(prof)
    for i, p in enumerate(path):
        k = scales[i] if scales else 1.0
        p = Vector(p)
        t = (Vector(path[min(i + 1, len(path) - 1)]) - Vector(path[max(i - 1, 0)])).normalized()
        s = t.cross(Vector((0, 0, 1)))
        s = s.normalized() if s.length > 1e-6 else Vector((1, 0, 0))
        up = s.cross(t).normalized()
        if up.z < 0:
            up = -up
        vs += [p + s * h * k + up * w * k for (h, w) in prof]
    fs = []
    for i in range(len(path) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            fs.append((a, b, b + n, a + n))
    if cap:
        fs.append(tuple(range(n))[::-1]); k = (len(path) - 1) * n; fs.append(tuple(range(k, k + n)))
    faces(m, vs, fs)


def lathe(m, c, prof, seg=16):
    c = Vector(c); vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        vs += [c + Vector((r * math.cos(a), r * math.sin(a), z)) for (r, z) in prof]
    n = len(prof); fs = []
    for i in range(seg):
        for j in range(n - 1):
            a, b = i * n + j, ((i + 1) % seg) * n + j
            fs.append((a, b, b + 1, a + 1))
    faces(m, vs, fs)


def sph(m, c, r, seg=8, sz=1.0):
    prof = [(r * math.sin(math.pi * k / seg), -r * sz * math.cos(math.pi * k / seg)) for k in range(seg + 1)]
    lathe(m, c, prof, seg=seg + 2)


def tube(m, pts, r0, r1, seg=8):
    prof = []
    n = len(pts)
    vs = []
    for i, p in enumerate(pts):
        p = Vector(p)
        t = (Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = t.orthogonal().normalized(); b = t.cross(a)
        r = r0 + (r1 - r0) * i / (n - 1)
        vs += [p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * r for k in range(seg)]
    fs = [(i * seg + k, i * seg + (k + 1) % seg, (i + 1) * seg + (k + 1) % seg, (i + 1) * seg + k) for i in range(n - 1) for k in range(seg)]
    fs.append(tuple(range(seg))[::-1]); fs.append(tuple(range((n - 1) * seg, n * seg)))
    faces(m, vs, fs)


# ================================================================ 2. 佛殿斗栱
QING, LV, ZHU, JIN, MU = 'M_彩画青', 'M_枋绿', 'M_朱漆', 'M_描金', 'M_旧木'
Z0 = 5.66                                  # 平板枋顶
D = LIFT / 11.0                            # 斗口
CX, CY, HX, HY = 0.0, 6.4, 5.1, 3.0        # 檐柱网：x ±5.1，y 3.4 / 9.4
COLS_X = (-5.1, -1.9, 1.9, 5.1)
COLS_Y = (3.4, 4.8, 9.4)

# 四条檐面：(名, 局部系, 沿 u 的柱位, u 的半长)
def line_frame(side):
    if side == 'S':  return F((CX, CY - HY, Z0), (1, 0, 0), (0, -1, 0)), [x - CX for x in COLS_X], HX
    if side == 'N':  return F((CX, CY + HY, Z0), (-1, 0, 0), (0, 1, 0)), [CX - x for x in COLS_X], HX
    if side == 'W':  return F((CX - HX, CY, Z0), (0, -1, 0), (-1, 0, 0)), [CY - y for y in COLS_Y], HY
    return F((CX + HX, CY, Z0), (0, 1, 0), (1, 0, 0)), [y - CY for y in COLS_Y], HY


def gong(m, f, u, v, L, w0, t=1.24):
    """拱：沿 u，长 L（斗口数），高 2，两端下部卷杀；中心在 (u, v)，底 w0（斗口数）"""
    h = 2 * D; l = L * D / 2; ins = 0.9 * D
    pts = [(-l, h), (-l, h * 0.55)]
    for k in range(1, 5):
        a = k / 4 * math.pi / 2
        pts.append((-l + ins * (1 - math.cos(a)), h * 0.55 * (1 - math.sin(a))))
    pts += [(-p[0], p[1]) for p in reversed(pts)]
    pts = [(u + a, w0 * D + b) for a, b in pts]
    prism(m, f, pts, 'v', v - t * D / 2, v + t * D / 2)


def qiao(m, f, u, v0, v1, w0, t=1.0):
    """翘：沿 v（v0、v1 为斗口数），两端卷杀，同拱"""
    h = 2 * D; ins = 0.9 * D; v0 *= D; v1 *= D
    pts = [(v0, w0 * D + h), (v0, w0 * D + h * 0.55)]
    for k in range(1, 5):
        a = k / 4 * math.pi / 2
        pts.append((v0 + ins * (1 - math.cos(a)), w0 * D + h * 0.55 * (1 - math.sin(a))))
    tail = [(v1 - (p[0] - v0), p[1]) for p in reversed(pts)]
    prism(m, f, pts + tail, 'u', u - t * D / 2, u + t * D / 2)


def dou(m, f, u, v, w0, su=1.4, sv=1.4, big=False):
    """斗/升：底（收分）0.4、腰 0.2、耳 0.4（斗口数）；大斗高 2"""
    k = 2.0 if big else 1.0
    a, b = su * D / 2, sv * D / 2
    frustum(m, f, u, v, a * 0.75, b * 0.75, a, b, w0 * D, (w0 + 0.4 * k) * D)
    box(m, f, u - a, u + a, v - b, v + b, (w0 + 0.4 * k) * D, (w0 + 1.0 * k) * D)


def ang(m, f, u, w0, t=1.0, back=-6.0):
    """昂：后尾平，前出昂嘴下斜（斗口数，v 向外）"""
    pts = [(back, 0), (4.6, 0), (8.9, -1.55), (9.6, -1.35), (9.4, -0.85), (6.3, 2.0), (back, 2.0)]
    prism(m, f, [(a * D, (w0 + b) * D) for a, b in pts], 'u', u - t * D / 2, u + t * D / 2)


def shuatou(m, f, u, w0, t=1.0, back=-9.0):
    """耍头：外端蚂蚱头，里端麻叶头（简化）"""
    pts = [(back, 0.3), (back + 0.6, 0), (7.6, 0), (9.6, 0.7), (9.6, 1.1), (8.8, 1.3), (8.8, 2.0), (back, 2.0)]
    prism(m, f, [(a * D, (w0 + b) * D) for a, b in pts], 'u', u - t * D / 2, u + t * D / 2)


def dougong_set(f, u, kind='ping'):
    """一攒五踩单翘单昂。kind: ping 平身科 / zhu 柱头科"""
    zt = kind == 'zhu'
    # 坐斗
    dou(QING, f, u, 0, 0, su=4 if zt else 3, sv=3, big=True)
    # 第一层（w 1.2–3.2）：正心瓜拱 + 头翘
    gong(LV, f, u, 0, 6.2, 1.2)
    qiao(QING, f, u, -3.55, 3.55, 1.2, t=2 if zt else 1)
    for s in (-1, 1):
        dou(QING, f, u + s * 2.6 * D, 0, 3.2, 1.3, 1.7)          # 槽升子
        dou(QING, f, u, s * 3 * D, 3.2, 1.8, 1.5)                 # 十八斗
    # 第二层（w 3.8–5.8）：正心万拱、里外单才瓜拱、昂
    gong(QING, f, u, 0, 9.2, 3.8)
    for s in (-1, 1):
        gong(LV, f, u, s * 3 * D, 6.2, 3.8, t=1.0)
    ang(LV, f, u, 3.8, t=3 if zt else 1, back=-6.5)
    for s in (-1, 1):
        dou(QING, f, u + s * 4.1 * D, 0, 5.8, 1.3, 1.7)
        for sv in (-1, 1):
            dou(QING, f, u + s * 2.6 * D, sv * 3 * D, 5.8, 1.3, 1.4)  # 三才升
    dou(QING, f, u, 6 * D, 5.8, 1.8, 1.5)
    dou(QING, f, u, -6 * D, 5.8, 1.8, 1.5)
    # 第三层（w 6.4–8.4）：里外单才万拱、厢拱、耍头（柱头科为桃尖梁头）
    for s in (-1, 1):
        gong(QING, f, u, s * 3 * D, 9.2, 6.4)
        gong(LV, f, u, s * 6 * D, 7.2, 6.4)
    if zt:
        pts = [(-9, 0), (8.0, 0), (10.2, 1.0), (10.2, 2.6), (8.5, 4.6), (-9, 4.6)]   # 桃尖梁头
        prism(ZHU, f, [(a * D, (6.4 + b) * D) for a, b in pts], 'u', u - 2 * D, u + 2 * D)
    else:
        shuatou(LV, f, u, 6.4)
    for s in (-1, 1):
        for sv in (-1, 1):
            dou(QING, f, u + s * 4.1 * D, sv * 3 * D, 8.4, 1.3, 1.4)
            dou(QING, f, u + s * 3.1 * D, sv * 6 * D, 8.4, 1.3, 1.4)
    # 撑头木
    if not zt:
        pts = [(-6, 0), (8.2, 0), (8.2, 2.0), (-6, 2.0)]
        prism(QING, f, [(a * D, (9.0 + b) * D) for a, b in pts], 'u', u - 0.5 * D, u + 0.5 * D)


def corner_set(fa, fb, ua, ub):
    """角科：两面各出一攒（柱头科做法，只到自身一侧），加 45° 斜翘、斜昂、由昂"""
    dougong_set(fa, ua, 'zhu')
    dougong_set(fb, ub, 'zhu')
    o = fa(ua, 0, 0); d = (fa.v + fb.v).normalized(); s = d.cross(Vector((0, 0, 1)))
    fd = F(o, s, d)
    r2 = math.sqrt(2)
    qiao(QING, fd, 0, -3.55 * r2, 3.55 * r2, 1.2, t=1.5)
    pts = [(-6 * r2, 0), (4.6 * r2, 0), (8.9 * r2, -1.8), (9.6 * r2, -1.6), (9.4 * r2, -1.0), (6.3 * r2, 2.0), (-6 * r2, 2.0)]
    prism(LV, fd, [(a * D, (3.8 + b) * D) for a, b in pts], 'u', -0.75 * D, 0.75 * D)
    pts = [(-6 * r2, 0), (7.0 * r2, 0), (10.0 * r2, -1.6), (10.6 * r2, -1.4), (10.4 * r2, -0.9), (7.4 * r2, 2.0), (-6 * r2, 2.0)]  # 由昂
    prism(LV, fd, [(a * D, (6.4 + b) * D) for a, b in pts], 'u', -0.75 * D, 0.75 * D)
    dou(QING, fd, 0, 3 * r2 * D, 3.2, 1.8, 1.8)
    dou(QING, fd, 0, 6 * r2 * D, 5.8, 1.8, 1.8)
    pts = [(-6 * r2, 0), (8.6 * r2, 0), (8.6 * r2, 2.0), (-6 * r2, 2.0)]
    prism(QING, fd, [(a * D, (9.0 + b) * D) for a, b in pts], 'u', -0.6 * D, 0.6 * D)


def bracket_ring():
    sets = 0
    for side in 'SNWE':
        f, cols, H = line_frame(side)
        cols = sorted(cols)
        # 柱头科（角柱另做角科）
        for c in cols:
            if abs(abs(c) - H) > 1e-3:
                dougong_set(f, c, 'zhu'); sets += 1
        # 平身科
        for a, b in zip(cols, cols[1:]):
            n = max(1, round((b - a) / 0.78) - 1)
            for k in range(1, n + 1):
                dougong_set(f, a + (b - a) * k / (n + 1), 'ping'); sets += 1
        # 通长构件：伸到与相邻檐面的同名枋相交
        def run(m, v, w0, w1, t):
            L = H + v
            box(m, f, -L, L, v - t / 2, v + t / 2, w0 * D, w1 * D)
        run(ZHU, 0, 1.6, 6.4, 0.3 * D)                 # 正心线垫栱板（拱眼壁）
        run(QING, 0, 6.4, 8.4, 1.24 * D)               # 正心枋
        run(LV, 0, 9.0, 11.0, 1.24 * D)
        for v in (3 * D, -3 * D):
            run(LV, v, 9.0, 11.0, 1.0 * D)             # 拽枋
        run(QING, 6 * D, 9.0, 11.0, 1.0 * D)           # 挑檐枋
        run(QING, -6 * D, 9.0, 11.0, 1.0 * D)          # 井口枋
        # 挑檐桁
        L = H + 6 * D
        a = f(-L, 6 * D, 12.0 * D); b = f(L, 6 * D, 12.0 * D)
        tube(MU, [a, b], 1.15 * D, 1.15 * D, seg=10)
        # 山面没有平板枋：补上（前后檐原有）
        if side in 'WE':
            box(ZHU, f, -H - 0.12, H + 0.12, -0.07, 0.07, -0.14, 0)
        # 正心线上方到屋面底：垫板封住（抬高屋面后露出的缝）
        top_fill(f, H, 0.0, 11.0 * D)
    # 四角
    fS, _, _ = line_frame('S'); fN, _, _ = line_frame('N'); fW, _, _ = line_frame('W'); fE, _, _ = line_frame('E')
    corner_set(fS, fW, -HX, HY)
    corner_set(fS, fE, HX, -HY)
    corner_set(fN, fE, -HX, HY)
    corner_set(fN, fW, HX, -HY)
    return sets


def top_fill(f, H, v, w0, cap=1.6, bvh=None):
    """沿檐面一线从 w0 向上封到屋面底（射线测得），朱红垫板"""
    n = int(2 * H / 0.2) + 1; vs = []; fs = []
    for i in range(n + 1):
        u = -H + 2 * H * i / n
        p = f(u, v, w0)
        z = under_z(p.x, p.y, p.z + 0.01, bvh)
        z = min(z, p.z + cap) if z is not None else p.z + 0.25
        z = max(z, p.z + 0.02)
        vs += [p, Vector((p.x, p.y, z - 0.01))]
        if i:
            k = 2 * i
            fs.append((k - 2, k, k + 1, k - 1))
    faces(ZHU, vs, fs)


def jinzhu_line():
    """前金柱一线（槅扇门上方）：平板枋上垫板 + 隔架科（一斗三升），封到屋面底"""
    f = F((0, 4.8, Z0), (1, 0, 0), (0, -1, 0))
    box(ZHU, f, -5.1, 5.1, -0.03, 0.03, 0, 11.0 * D)
    box(QING, f, -5.1, 5.1, -0.62 * D, 0.62 * D, 6.4 * D, 8.4 * D)
    for x in [-3.5, -0.38 - 0.76, -0.38, 0.38, 0.38 + 0.76, 3.5, -4.3, -2.7, 2.7, 4.3]:
        dou(QING, f, x, 0, 0, 3, 3, big=True)
        gong(LV, f, x, 0, 6.2, 1.2, t=1.0)
        for s in (-1, 0, 1):
            dou(QING, f, x + s * 2.6 * D, 0, 3.2, 1.3, 1.4)
    top_fill(f, 5.1, 0, 11.0 * D)


def gable_fill():
    """歇山山花里皮（x ±3.80）：从墙顶封到屋面底。原模型山花板上沿与屋面之间有一道缝，殿里抬头能看见天。"""
    for sx in (-1, 1):
        f = F((sx * 3.80, CY, Z0), (0, 1, 0), (sx, 0, 0))
        top_fill(f, HY, 0.0, 0.0, cap=4.0, bvh=DECK)


# ================================================================ 3. 屋脊、吻兽
JI = 'M_屋脊灰'

def ridge_prof(W, H, depth=0.14):
    """正脊截面（左右对称）：底部埋入屋面 depth；当沟、压当条、混砖、脊身、盖脊筒瓦"""
    h = W / 2
    half = [(h + 0.015, -depth), (h + 0.015, 0.05), (h + 0.035, 0.065), (h + 0.035, 0.095),
            (h - 0.005, 0.10), (h - 0.005, 0.17), (h + 0.012, 0.18), (h + 0.022, 0.20), (h + 0.012, 0.22),
            (h - 0.01, 0.23), (h - 0.01, H - 0.075), (h + 0.012, H - 0.065), (h + 0.02, H - 0.04),
            (h * 0.75, H - 0.01), (h * 0.35, H)]
    return [(-a, b) for a, b in reversed(half)] + half


def small_ridge_prof(W, H, depth=0.12):
    h = W / 2
    half = [(h + 0.01, -depth), (h + 0.01, 0.04), (h + 0.025, 0.055), (h + 0.025, 0.08),
            (h - 0.005, 0.085), (h - 0.005, H - 0.06), (h + 0.01, H - 0.05), (h + 0.015, H - 0.03),
            (h * 0.7, H - 0.008), (h * 0.3, H)]
    return [(-a, b) for a, b in reversed(half)] + half


def zhengwen(o, out, Hw, T):
    """正吻：o 脊端底点，out 指向脊外（单位水平向量），Hw 高，T 厚。龙口吞脊朝里，尾向外上卷。"""
    s = out.cross(Vector((0, 0, 1)))
    f = F(o, -out, s)             # u 朝脊里（正值向内），v 横向
    U = Hw
    body = [(-0.14, 0), (0.48, 0), (0.55, 0.05), (0.53, 0.11), (0.40, 0.15), (0.34, 0.19), (0.47, 0.25),
            (0.56, 0.31), (0.53, 0.37), (0.45, 0.41), (0.37, 0.44), (0.35, 0.52), (0.30, 0.60), (0.27, 0.70),
            (0.20, 0.80), (0.10, 0.86), (-0.02, 0.88), (-0.12, 0.84), (-0.16, 0.76), (-0.22, 0.72), (-0.17, 0.66),
            (-0.21, 0.59), (-0.16, 0.53), (-0.20, 0.46), (-0.15, 0.40), (-0.19, 0.33), (-0.14, 0.27),
            (-0.18, 0.20), (-0.13, 0.14), (-0.16, 0.07)]
    pts = [(a * U, b * U) for a, b in body]
    # 两层拉伸：中间厚、边缘薄一圈（假倒角）
    prism(JI, f, pts, 'v', -T / 2, T / 2)
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    inner = [(cx + (a - cx) * 0.86, cy + (b - cy) * 0.9) for a, b in pts]
    prism(JI, f, inner, 'v', -T / 2 - 0.012 * U, T / 2 + 0.012 * U)
    # 卷尾：向外上卷的螺旋
    sp = []
    c = (-0.04, 0.92)
    for k in range(24):
        t = k / 23
        a = math.radians(-23 + 320 * t)          # 从吻背里侧起，过顶向外，再向下卷回
        r = 0.15 * (1 - 0.62 * t)
        sp.append(f((c[0] + r * math.cos(a)) * U, 0, (c[1] + r * math.sin(a)) * U))
    tube(JI, sp, 0.075 * U, 0.03 * U, seg=8)
    # 剑把：插在吻背里侧
    box(JI, f, 0.20 * U, 0.26 * U, -0.02 * U, 0.02 * U, 0.72 * U, 1.0 * U)
    box(JI, f, 0.15 * U, 0.31 * U, -0.035 * U, 0.035 * U, 0.86 * U, 0.9 * U)
    # 背兽：吻外侧中部
    sph(JI, f(-0.18 * U, 0, 0.5 * U), 0.07 * U, seg=6)
    # 眼、鼻
    for sv in (-1, 1):
        sph(JI, f(0.44 * U, sv * (T / 2 + 0.01 * U), 0.42 * U), 0.04 * U, seg=5)
        sph(JI, f(0.52 * U, sv * (T / 2 - 0.02 * U), 0.30 * U), 0.025 * U, seg=4)
    # 吻下口：脊在嘴里（上下颌夹住的一截）
    box(JI, f, 0.30 * U, 0.6 * U, -T * 0.35, T * 0.35, 0.12 * U, 0.26 * U)


def beast(o, out, h, kind='chui'):
    """垂兽 / 戗兽：坐在脊上的兽头，朝 out 方向"""
    s = out.cross(Vector((0, 0, 1)))
    f = F(o, out, s)
    U = h
    prof = [(-0.35, 0), (0.30, 0), (0.42, 0.18), (0.48, 0.38), (0.40, 0.52), (0.30, 0.55), (0.22, 0.72),
            (0.10, 0.80), (0.0, 0.95), (-0.10, 0.82), (-0.25, 0.78), (-0.38, 0.55)]
    prism(JI, f, [(a * U, b * U) for a, b in prof], 'v', -0.22 * U, 0.22 * U)
    for sv in (-1, 1):
        sph(JI, f(0.34 * U, sv * 0.22 * U, 0.45 * U), 0.06 * U, seg=5)          # 眼
        tube(JI, [f(0.05 * U, sv * 0.12 * U, 0.8 * U), f(-0.15 * U, sv * 0.18 * U, 1.0 * U), f(-0.32 * U, sv * 0.2 * U, 1.02 * U)],
             0.05 * U, 0.02 * U, seg=5)                                          # 角


def zoushou(o, out, h, kind):
    """走兽：仙人骑凤、龙、凤、狮（蹲坐的小兽，朝外）"""
    s = out.cross(Vector((0, 0, 1)))
    f = F(o, out, s)
    if kind == 'xian':
        sph(JI, f(-0.02, 0, 0.05), 0.07, seg=6, sz=0.6)                          # 凤身
        tube(JI, [f(0.03, 0, 0.06), f(0.08, 0, 0.1), f(0.1, 0, 0.12)], 0.025, 0.012, seg=6)
        lathe(JI, f(-0.03, 0, 0.08), [(0.0, 0), (0.05, 0.0), (0.035, 0.12), (0.0, 0.13)], seg=8)   # 仙人
        sph(JI, f(-0.03, 0, 0.24), 0.035, seg=6)
        return
    sph(JI, f(-0.02, 0, 0.06), 0.06, seg=6, sz=0.9)                              # 身
    sph(JI, f(0.04, 0, 0.15), 0.045, seg=6)                                       # 头
    box(JI, f, -0.06, 0.06, -0.035, 0.035, -0.05, 0.02)                           # 座
    if kind == 'long':
        for sv in (-1, 1):
            tube(JI, [f(0.03, sv * 0.02, 0.18), f(-0.02, sv * 0.03, 0.24)], 0.012, 0.005, seg=4)
    elif kind == 'feng':
        tube(JI, [f(-0.06, 0, 0.06), f(-0.12, 0, 0.14), f(-0.1, 0, 0.2)], 0.03, 0.01, seg=5)
    else:
        sph(JI, f(0.02, 0, 0.17), 0.05, seg=6, sz=0.7)                           # 鬃


def zhengji(axis, c, half, z0, ztop, W, Hw):
    """直的正脊 + 两端正吻。axis 'x' 或 'y'；c 为另一轴坐标；z0 脊底，ztop 原脊顶"""
    H = ztop - z0 + 0.03
    if axis == 'x':
        a, b = Vector((-half[0], c, z0)), Vector((half[1], c, z0))
    else:
        a, b = Vector((c, -half[0], z0)), Vector((c, half[1], z0))
    n = 6
    sweep(JI, [a.lerp(b, k / n) for k in range(n + 1)], ridge_prof(W, H))
    d = (b - a).normalized()
    for p, out in ((a, -d), (b, d)):
        zhengwen(p + out * 0.04 + Vector((0, 0, 0.04)), out, Hw, W * 0.95)


def roof_path(x0, y0, x1, y1, n, lift=0.0):
    pts = []
    for k in range(n + 1):
        t = k / n; x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
        z = roof_z(x, y)
        if z is None:
            continue
        pts.append(Vector((x, y, z + lift)))
    return pts


def fodian_roof():
    L = LIFT
    # 正脊（原：x ±4.15，y 6.25–6.55，z 8.15–8.54）
    zhengji('x', 6.4, (4.1, 4.1), 8.15 + L, 8.54 + L, 0.30, 1.15)
    # 宝顶：须弥座 + 莲瓣 + 宝瓶 + 火焰珠
    c = Vector((0, 6.4, 8.52 + L))
    lathe(JI, c, [(0.0, 0), (0.24, 0), (0.24, 0.05), (0.19, 0.07), (0.17, 0.12), (0.21, 0.15), (0.21, 0.19), (0.0, 0.19)], seg=16)
    lathe(JIN, c + Vector((0, 0, 0.19)), [(0.0, 0), (0.17, 0.0), (0.2, 0.05), (0.15, 0.1), (0.09, 0.13), (0.0, 0.13)], seg=16)
    lathe(JIN, c + Vector((0, 0, 0.31)), [(0.0, 0), (0.06, 0), (0.12, 0.08), (0.13, 0.17), (0.09, 0.25), (0.045, 0.29), (0.05, 0.33),
                                         (0.08, 0.36), (0.0, 0.37)], seg=14)
    lathe(JIN, c + Vector((0, 0, 0.68)), [(0.0, 0), (0.05, 0.02), (0.075, 0.08), (0.05, 0.15), (0.02, 0.21), (0.0, 0.25)], seg=12)
    # 垂脊（歇山，x ±3.75，从正脊端 y 6.4 前后分落到 y 4.71 / 8.09，原 z 8.35 → 6.81）
    for sx in (-1, 1):
        for y1 in (4.75, 8.05):
            pts = [Vector((sx * 3.75, 6.4 + (y1 - 6.4) * k / 8, 0)) for k in range(9)]
            z_top = [8.35 + (6.81 - 8.35) * k / 8 for k in range(9)]
            # 屋面在山花边上往下走，取原脊顶线（直线）
            path = [Vector((p.x, p.y, z - 0.30 + L)) for p, z in zip(pts, z_top)]
            sweep(JI, path, small_ridge_prof(0.20, 0.32, depth=0.10))
            o = path[-1] + (path[-1] - path[-2]).normalized() * -0.25
            beast(o + Vector((0, 0, 0.30)), Vector((0, (y1 - 6.4) / abs(y1 - 6.4), 0)), 0.32)
            bofeng(sx, path)
        shanhua(sx)
    # 戗脊：从垂脊下端沿 45° 到翼角，随屋面，末端起翘
    for sx in (-1, 1):
        for sy, (ya, yb) in ((-1, (4.75, 2.05)), (1, (8.05, 10.75))):
            xa, xb = sx * 3.78, sx * 6.42
            path = roof_path(xa, ya, xb, yb, 12, lift=0.02)
            if len(path) < 4:
                continue
            last = path[-1]; dirh = Vector((xb - xa, yb - ya, 0)).normalized()
            nb = len(path)
            for k in range(1, 6):                      # 起翘：再向外 0.34 m，抬 0.38 m，截面收小
                t = k / 5
                path.append(last + dirh * 0.34 * t + Vector((0, 0, 0.38 * t * t)))
            sc = [1.0] * nb + [1.0 - 0.32 * (k / 5) for k in range(1, 6)]
            sweep(JI, path, small_ridge_prof(0.20, 0.28, depth=0.10), scales=sc)
            # 戗兽（脊前段三分之一处），其外走兽
            i0 = len(path) // 3
            beast(path[i0] + Vector((0, 0, 0.26)), dirh, 0.30)
            for j, kind in enumerate(('long', 'feng', 'shi')):
                i = i0 + 2 + j * 2
                if i < len(path) - 4:
                    zoushou(path[i] + Vector((0, 0, 0.27)), dirh, 0.16, kind)
            zoushou(path[-6] + Vector((0, 0, 0.27)), dirh, 0.16, 'xian')
            # 套兽 + 风铎：仔角梁头
            tip = Vector((sx * 6.44, 2.05 if sy < 0 else 10.75, 5.80 + L))
            taoshou(tip, dirh)
            fengduo(tip + dirh * 0.02 + Vector((0, 0, -0.14)))


def taoshou(o, d):
    s = d.cross(Vector((0, 0, 1))); f = F(o, d, s)
    prof = [(-0.08, -0.08), (0.10, -0.08), (0.16, -0.03), (0.17, 0.04), (0.10, 0.08), (0.02, 0.12), (-0.08, 0.1)]
    prism(JI, f, [(a, b) for a, b in prof], 'v', -0.075, 0.075)
    for sv in (-1, 1):
        sph(JI, f(0.12, sv * 0.075, 0.04), 0.022, seg=4)


def fengduo(o):
    """风铎：吊环、铎身（钟形）、风摆"""
    tube('M_铜', [o + Vector((0, 0, 0.12)), o + Vector((0, 0, 0.0))], 0.006, 0.006, seg=4)
    lathe('M_铜', o + Vector((0, 0, -0.17)), [(0.0, 0.17), (0.03, 0.17), (0.05, 0.14), (0.058, 0.06), (0.075, 0.0), (0.06, 0.0)], seg=12)
    tube('M_铜', [o + Vector((0, 0, -0.17)), o + Vector((0, 0, -0.27))], 0.004, 0.004, seg=4)
    box('M_铜', F(o + Vector((0, 0, -0.27)), (1, 0, 0), (0, 1, 0)), -0.035, 0.035, -0.004, 0.004, -0.09, 0.0)


def bofeng(sx, path):
    """博缝板：垂脊下贴山花外皮，朱红，梅花钉五枚一组；正中悬鱼"""
    x = sx * 3.91
    vs = []; fs = []
    for i, p in enumerate(path):
        vs += [Vector((x, p.y, p.z + 0.02)), Vector((x, p.y, p.z - 0.30))]
        if i:
            k = 2 * i; fs.append((k - 2, k, k + 1, k - 1) if sx > 0 else (k - 2, k - 1, k + 1, k))
    faces(ZHU, vs, fs)
    for i in range(2, len(path) - 1, 3):
        p = path[i]
        for dy, dz in ((0, 0), (-0.05, -0.05), (0.05, -0.05), (-0.05, 0.05), (0.05, 0.05)):
            sph(JIN, Vector((x + sx * 0.01, p.y + dy * 0.6, p.z - 0.14 + dz * 0.6)), 0.016, seg=4)
    if path[-1].y < path[0].y:      # 每山只挂一次悬鱼（在前坡那条路径时）
        top = path[0]
        f = F(Vector((x + sx * 0.012, top.y, top.z - 0.26)), (0, 1, 0), (sx, 0, 0))
        pts = [(-0.10, 0), (0.10, 0), (0.16, -0.12), (0.10, -0.26), (0.13, -0.40), (0.0, -0.52), (-0.13, -0.40),
               (-0.10, -0.26), (-0.16, -0.12)]
        prism(JIN, f, pts, 'v', -0.012, 0.012)


def shanhua(sx):
    """山花绶带：金钱 + 两条飘带（贴在山花板外皮）"""
    x = sx * 3.895; L = LIFT
    c = Vector((x, 6.4, 7.45 + L))
    f = F(c, (0, 1, 0), (sx, 0, 0))
    ring = [(0.17 * math.cos(2 * math.pi * k / 16), 0.17 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    prism(JIN, f, ring, 'v', 0, 0.02)
    sq = [(-0.05, -0.05), (0.05, -0.05), (0.05, 0.05), (-0.05, 0.05)]
    prism(ZHU, f, sq, 'v', 0.015, 0.03)
    for s in (-1, 1):
        rib = [(s * 0.14, 0.06), (s * 0.55, 0.16), (s * 0.85, 0.02), (s * 0.95, -0.12), (s * 0.80, -0.06),
               (s * 0.55, 0.06), (s * 0.14, -0.06)]
        if s < 0:
            rib = rib[::-1]
        prism(JIN, f, rib, 'v', 0, 0.015)


def side_ridges():
    """其余各屋正脊（硬山、悬山），尺寸取原脊"""
    zhengji('x', -7.7, (2.77, 2.77), 5.85, 6.15, 0.26, 0.62)                   # 山门
    zhengji('y', 9.2, (6.89, 3.29), 6.18, 6.48, 0.26, 0.66)                   # 东禅堂
    zhengji('y', -9.2, (6.89, 3.29), 6.18, 6.48, 0.26, 0.66)                  # 西厢
    zhengji('x', 7.1, (-6.86, 10.64), 5.43, 5.73, 0.26, 0.56)                  # 东耳房
    zhengji('x', 7.1, (10.64, -6.86), 5.43, 5.73, 0.26, 0.56)                  # 西耳房


# ================================================================ 4. 雀替
def queti(o, along, L, H, t=0.09):
    """雀替：o 为柱面与额枋底交点，along 指向开间（水平单位向量）；卷草轮廓"""
    s = Vector((0, 0, 1)).cross(along)
    f = F(o, along, s)
    pts = [(0, 0), (L, 0)]
    N = 28
    for i in range(N + 1):                     # 下缘：从梢头圆滑落到柱边，三道卷草凹口
        q = i / N
        x = L * (1 - q); y = -H * (0.10 + 0.90 * q ** 1.7)
        dip = 0.07 * H * abs(math.sin(3 * math.pi * q)) * (1 - 0.4 * q)
        pts.append((x - dip * 0.5, y + dip))
    pts[2] = (L, -0.10 * H)
    prism(LV, f, pts, 'v', -t / 2, t / 2)
    # 描金卷草边（略小一圈、两面各凸出 6 mm）
    inner = [(L * 0.03 + a * 0.88, b * 0.88 - 0.010) for a, b in pts]
    prism(JIN, f, inner, 'v', -t / 2 - 0.006, t / 2 + 0.006)
    inner2 = [(L * 0.06 + a * 0.80, b * 0.80 - 0.02) for a, b in pts]
    prism(LV, f, inner2, 'v', -t / 2 - 0.009, t / 2 + 0.009)
    # 底下的翘头
    box(QING, f, -0.002, 0.10, -t / 2, t / 2, -H - 0.05, -H)


def all_queti():
    n = 0
    # 佛殿前檐 y=3.4，柱径 0.34，额枋底 5.18
    xs = COLS_X
    for i, x in enumerate(xs):
        for s in (-1, 1):
            if (i == 0 and s < 0) or (i == len(xs) - 1 and s > 0):
                continue
            bay = abs(xs[i + s] - x)
            queti(Vector((x + s * 0.17, 3.4, 5.18)), Vector((s, 0, 0)), bay * 0.2, 0.36); n += 1
    # 东禅堂（前檐朝西，柱列 x=7.1）、西厢（x=-7.1）：额枋底 4.28，柱径 0.26
    ys = (-6.5, -3.5, -0.1, 2.9)
    for sx in (-1, 1):
        for i, y in enumerate(ys):
            for s in (-1, 1):
                if (i == 0 and s < 0) or (i == len(ys) - 1 and s > 0):
                    continue
                bay = abs(ys[i + s] - y)
                queti(Vector((sx * 7.1, y + s * 0.13, 4.28)), Vector((0, s, 0)), bay * 0.2, 0.3, t=0.08); n += 1
    # 耳房（檐柱 x 7.25 / 10.25，y=5.5，额枋底 3.83）
    for sx in (-1, 1):
        for x, s in ((7.25, 1), (10.25, -1)):
            queti(Vector((sx * x + sx * s * 0.12, 5.5, 3.83)), Vector((sx * s, 0, 0)), 0.55, 0.26, t=0.08); n += 1
    return n


# ================================================================ 生成
sets = bracket_ring()
jinzhu_line()
gable_fill()
fodian_roof()
side_ridges()
nq = all_queti()

objs = []
for m, bm in G.items():
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('细部_' + m[2:]); bm.to_mesh(me); bm.free()
    mat = bpy.data.materials.get(m) or bpy.data.materials.new(m)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = False
    o = bpy.data.objects.new('细部_' + m[2:], me); C.objects.link(o); objs.append(o)
# 新材质的底色（网页按材质名配色，这里只为 Blender 里好看）
for m, col in (('M_彩画青', (0.07, 0.15, 0.33, 1)), ('M_枋绿', (0.12, 0.33, 0.24, 1))):
    mt = bpy.data.materials[m]; mt.use_nodes = True
    bs = next(n for n in mt.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'); bs.inputs['Base Color'].default_value = col
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)
print('dougong sets', sets, 'queti', nq, 'objects', len(objs), 'tris', tris)
bpy.ops.wm.save_mainfile(filepath=SRC)

bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='NONE', export_materials='EXPORT', export_yup=True)
print('wrote', OUT)
