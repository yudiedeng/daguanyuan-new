"""大观楼玉石牌坊（冲天式四柱三间）：Blender 里搭白石骨架，再挂 Tripo 精雕件，导出 models/p/paifang.glb。
用法：python3 blender/scripts/sites/paifang_build.py <tripo 原始 glb 目录> /tmp/paifang.glb
      node blender/scripts/web/pack_prop.mjs /tmp/paifang.glb models/p/paifang.glb 90000 1024
第十七回：“只见正面现出一座玉石牌坊来，上面龙蟠螭护，玲珑凿就。”按参考图：四根冲天柱高出额枋，柱身盘龙（Tripo pf_zhu），
柱顶云冠、金火珠；明间两道额枋夹一条镂空螭纹花板（pf_hua），正中空白匾；明间额枋上一块双龙戏珠镂空大花板（pf_ding）；
次间同样两道额枋夹花板，上置小一号双龙板。Tripo 整件生成的牌坊雕刻浅、多是贴图，分件生成每件才有足够面数。
单位米，底面中心在原点，正面朝 −Y（网页里 PROPS.daguan 按总高缩放）。
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector, Matrix

RAW, OUT = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def pmat(name, color, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m


STONE = pmat('白玉', (0.50, 0.48, 0.44), 0.7)      # 线性色；与 Tripo 雕件贴图的亮度相当，网页泛光下不发白
TEX = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tex'))
# 骨架石料贴网页 汉白玉 同一套纹理（marble_r 底色、marble_n 法线），否则大面积素面在网页强光下一片白
_nt = STONE.node_tree; _b = _nt.nodes['Principled BSDF']
_ti = _nt.nodes.new('ShaderNodeTexImage'); _ti.image = bpy.data.images.load(os.path.join(TEX, 'marble_r.jpg'))
_mix = _nt.nodes.new('ShaderNodeMix'); _mix.data_type = 'RGBA'; _mix.blend_type = 'MULTIPLY'; _mix.inputs['Factor'].default_value = 1.0
_mix.inputs['A'].default_value = (0.62, 0.60, 0.56, 1)
_nt.links.new(_ti.outputs['Color'], _mix.inputs['B']); _nt.links.new(_mix.outputs['Result'], _b.inputs['Base Color'])
_tn = _nt.nodes.new('ShaderNodeTexImage'); _tn.image = bpy.data.images.load(os.path.join(TEX, 'marble_n.jpg')); _tn.image.colorspace_settings.name = 'Non-Color'
_nm = _nt.nodes.new('ShaderNodeNormalMap'); _nt.links.new(_tn.outputs['Color'], _nm.inputs['Color']); _nt.links.new(_nm.outputs['Normal'], _b.inputs['Normal'])
GOLD = pmat('金', (0.83, 0.62, 0.25), 0.32, 1.0)

BMS = {}


def bm_of(m):
    if m.name not in BMS: BMS[m.name] = (bmesh.new(), m)
    return BMS[m.name][0]


def box(m, x0, y0, z0, x1, y1, z1, bevel=0.0):
    bm = bm_of(m); r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=r['verts'] + list({e for v in r['verts'] for e in v.link_edges}), offset=bevel, segments=1, affect='EDGES')


def lathe(m, prof, cx, cy, z0, n=20):
    bm = bm_of(m); rings = []
    for r, z in prof:
        rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0 + z)) for i in range(n)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for i in range(n): bm.faces.new((ra[i], ra[(i + 1) % n], rb[(i + 1) % n], rb[i]))


def tripo(name):
    """导入 Tripo 件：合成一个对象，材质改成白玉（去金属、压亮度），返回对象与包围盒。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(RAW, name + '.glb'))
    objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    for o in [o for o in bpy.data.objects if o not in before and o.type != 'MESH']:
        for c in o.children: c.parent = None if False else c.parent
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for m in o.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == 'BSDF_PRINCIPLED':
                    n.inputs['Metallic'].default_value = 0.0
                    n.inputs['Roughness'].default_value = 0.62
                    for l in list(m.node_tree.links):            # 金属度贴图断开
                        if l.to_socket == n.inputs['Metallic']: m.node_tree.links.remove(l)
    o.name = name
    return o


def bbox(o):
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    return Vector([min(v[i] for v in vs) for i in range(3)]), Vector([max(v[i] for v in vs) for i in range(3)])


def fit(o, x0, x1, z0, z1, yc, thin=None, keep_aspect=True):
    """把一块板（薄的那一轴转到 Y）放进 [x0,x1]×[z0,z1]，中心 y=yc；keep_aspect 时按较紧的一边等比缩放、居中。"""
    mn, mx = bbox(o); d = mx - mn
    if d.x < d.y:                         # 薄轴在 X：绕 Z 转 90°
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Z')); mn, mx = bbox(o); d = mx - mn
    if d.z < d.y and d.z < d.x:           # 薄轴在 Z（平躺）：绕 X 立起来
        o.data.transform(Matrix.Rotation(math.pi / 2, 4, 'X')); mn, mx = bbox(o); d = mx - mn
    # 浮雕板背面是平的：贴着某一面的顶点多，那一面是背面，转到 +Y（正面朝 −Y）
    tol = 0.04 * d.y
    nmin = sum(1 for v in o.data.vertices if v.co.y < mn.y + tol); nmax = sum(1 for v in o.data.vertices if v.co.y > mx.y - tol)
    if nmin > nmax:
        o.data.transform(Matrix.Rotation(math.pi, 4, 'Z')); mn, mx = bbox(o); d = mx - mn
    sx, sz = (x1 - x0) / d.x, (z1 - z0) / d.z
    if keep_aspect: sx = sz = min(sx, sz)
    sy = min(sx, sz) if thin is None else thin / d.y
    c = (mn + mx) / 2
    o.data.transform(Matrix.Translation(((x0 + x1) / 2, yc, (z0 + z1) / 2)) @ Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation(-c))
    return o


def dupo(o, name):
    c = o.copy(); c.data = o.data.copy(); c.name = name; sc.collection.objects.link(c); return c


# ------------------------------------------------------------ 尺寸
XI, XO = 2.8, 7.0          # 明间柱、次间柱中心
PW = 0.78                  # 柱截面
D = 0.62                   # 额枋厚

# 柱：Tripo 盘龙华表式柱（莲座、盘龙柱身、云板、宝珠）从地面立起；云板转成前后向，免得碰额枋和双龙板。
# 没有 Tripo 件时退回：须弥座柱础 + 素柱 + 云冠 + 金火珠。
zhu = os.path.exists(os.path.join(RAW, 'pf_zhu.glb'))
HT = {XI: 13.2, XO: 11.4}  # 柱全高（含宝珠）
if zhu:
    z0 = tripo('pf_zhu')
    mn, mx = bbox(z0); d = mx - mn
    if d.x > d.y: z0.data.transform(Matrix.Rotation(math.pi / 2, 4, 'Z')); mn, mx = bbox(z0); d = mx - mn   # 云板（最宽的方向）转到 Y
    vs = [v.co for v in z0.data.vertices]
    mid = [v for v in vs if mn.z + 0.4 * d.z < v.z < mn.z + 0.6 * d.z]
    wmid = max(max(v.x for v in mid) - min(v.x for v in mid), 0.01)      # 柱身中段的宽
    z0.data.transform(Matrix.Diagonal((1 / d.z, 1 / d.z, 1 / d.z, 1)) @ Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))))
    wmid /= d.z
for x in (-XO, -XI, XI, XO):
    h = HT[abs(x)]
    if zhu:
        c = dupo(z0, f'柱{x}')
        kh = 0.95 / (wmid * h)                               # 柱身中段收到 0.95 m 粗
        c.data.transform(Matrix.Translation((x, 0, 0)) @ Matrix.Diagonal((h * kh, h * kh, h, 1)))
        box(STONE, x - 0.3, -0.3, 1.0, x + 0.3, 0.3, h * 0.7, 0.0)        # 芯柱，挡住镂空处的透光
        continue
    hc = h - 1.85
    box(STONE, x - 0.85, -0.85, 0.0, x + 0.85, 0.85, 0.3, 0.03)
    box(STONE, x - 0.72, -0.72, 0.3, x + 0.72, 0.72, 0.55, 0.02)
    box(STONE, x - 0.6, -0.6, 0.55, x + 0.6, 0.6, 1.05, 0.02)
    box(STONE, x - 0.72, -0.72, 1.05, x + 0.72, 0.72, 1.3, 0.02)
    box(STONE, x - PW / 2, -PW / 2, 1.3, x + PW / 2, PW / 2, hc, 0.03)
    box(STONE, x - 0.55, -0.55, hc, x + 0.55, 0.55, hc + 0.22, 0.04)
    lathe(STONE, [(0.42, 0), (0.5, 0.12), (0.36, 0.3), (0.3, 0.42), (0.46, 0.6), (0.4, 0.78), (0.0, 0.84)], x, 0, hc + 0.22)
    lathe(GOLD, [(0.0, 0), (0.18, 0.04), (0.26, 0.18), (0.24, 0.36), (0.16, 0.5), (0.1, 0.62), (0.13, 0.72), (0.05, 0.92), (0.0, 1.0)], x, 0, hc + 1.0)


def bay(xa, xb, zl, zu, crest_h):
    """一间：下额枋 zl、上额枋 zu，中间花板；上额枋上放双龙板（高 crest_h）。"""
    xa += PW / 2; xb -= PW / 2
    box(STONE, xa, -D / 2, zl, xb, D / 2, zl + 0.55, 0.04)                      # 小额枋
    box(STONE, xa, -D / 2 - 0.04, zl + 0.55, xb, D / 2 + 0.04, zl + 0.62, 0.0)  # 枋线
    box(STONE, xa, -D / 2, zu, xb, D / 2, zu + 0.7, 0.04)                       # 大额枋
    box(STONE, xa - 0.05, -D / 2 - 0.05, zu + 0.7, xb + 0.05, D / 2 + 0.05, zu + 0.82, 0.02)
    # 额枋前后面：枋心（中间略凸的长方框）与两头箍头，免得一整条素面
    for z0_, h_ in ((zl, 0.55), (zu, 0.7)):
        L_ = xb - xa
        for y_ in (-D / 2 - 0.035, D / 2):
            box(STONE, xa + 0.2 * L_, y_, z0_ + 0.1, xb - 0.2 * L_, y_ + 0.035, z0_ + h_ - 0.1, 0.01)
            for xe in (xa + 0.06, xb - 0.06 - 0.12):
                box(STONE, xe, y_, z0_ + 0.06, xe + 0.12, y_ + 0.035, z0_ + h_ - 0.06)
    # 雀替：额枋下两头的托木
    for x, sgn in ((xa, 1), (xb, -1)):
        L = min(1.1, (xb - xa) * 0.22)
        bm = bm_of(STONE)
        pts = [(x, zl), (x + sgn * L, zl), (x + sgn * L * 0.55, zl - 0.18), (x, zl - 0.55)]
        vs = [bm.verts.new((px, y, pz)) for y in (-D / 2 + 0.08, D / 2 - 0.08) for px, pz in pts]
        bm.faces.new(vs[:4][::-1]); bm.faces.new(vs[4:])
        for i in range(4): bm.faces.new((vs[i], vs[(i + 1) % 4], vs[4 + (i + 1) % 4], vs[4 + i]))
    return xa, xb


panels = []
# 明间：下额枋 6.9，上额枋 8.7；中间花板带空白匾；额枋上大双龙板
xa, xb = bay(-XI, XI, 6.9, 8.75, 0)
panels.append(('pf_hua', xa, xb, 7.52, 8.75))
pw_ = 2.3
box(STONE, -pw_ / 2 - 0.14, -0.36, 7.47, pw_ / 2 + 0.14, 0.36, 8.8, 0.03)            # 匾框
box(STONE, -pw_ / 2, -0.4, 7.6, pw_ / 2, 0.4, 8.67, 0.02)                                   # 空白匾（第十七回宝玉未题）
panels.append(('pf_ding', xa + 0.1, xb - 0.1, 9.57, 9.57 + 3.3))
# 次间
for sgn in (-1, 1):
    a, b = sorted((sgn * XI, sgn * XO))
    xa2, xb2 = bay(a, b, 5.55, 7.05, 0)
    panels.append(('pf_hua', xa2, xb2, 6.17, 7.05))
    panels.append(('pf_ding', xa2 + 0.2, xb2 - 0.2, 7.87, 7.87 + 2.1))

have = {n: os.path.exists(os.path.join(RAW, n + '.glb')) for n in ('pf_hua', 'pf_ding')}
src = {n: tripo(n) for n, ok in have.items() if ok}
for i, (n, x0, x1, za, zb) in enumerate(panels):
    if n not in src:
        box(STONE, x0, -0.18, za, x1, 0.18, zb, 0.02); continue
    c = dupo(src[n], f'{n}_{i}')
    if n == 'pf_hua':           # 花板：铺满（略拉伸），躲开中间的匾
        fit(c, x0, x1, za, zb, 0.0, thin=0.3, keep_aspect=False)
    else:                       # 双龙板：等比放进去，底边贴额枋
        fit(c, x0, x1, za, zb, 0.0, thin=0.42, keep_aspect=True)
        mn, mx = bbox(c); c.data.transform(Matrix.Translation((0, 0, za - mn.z)))
        box(STONE, x0 + 0.1, -0.24, za - 0.12, x1 - 0.1, 0.24, za + 0.05, 0.02)    # 板座
for o in src.values(): bpy.data.objects.remove(o, do_unlink=True)
if zhu: bpy.data.objects.remove(z0, do_unlink=True)

for name, (bm, m) in BMS.items():
    bm.normal_update()
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:                    # 盒式投影 UV：每 2.4 m 一张纹理
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co; u, v = [(c.y, c.z), (c.x, c.z), (c.x, c.y)][ax]
            l[uv].uv = (u / 2.4, v / 2.4)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    sc.collection.objects.link(bpy.data.objects.new(name, me))
mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
for o in sc.objects:
    if o.type != 'MESH': continue
    a, b = bbox(o); mn = Vector(map(min, mn, a)); mx = Vector(map(max, mx, b))
print('PAIFANG size', [round(v, 2) for v in (mx - mn)], 'height', round(mx.z, 2))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_apply=True, export_yup=True)
