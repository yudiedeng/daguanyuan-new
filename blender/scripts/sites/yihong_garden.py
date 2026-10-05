"""怡红院院门外的花园（第十七回：“一径引入，绕着碧桃花，穿过一层竹篱花障编就的月洞门”）。
程序化建模几种花园模块，各存一个 .blend 并导出 GLB，网页里当道具（PROPS.yihong）按地形摆放：
  yh_rosebed   椭圆花坛：卵石镶边、培土，月季数丛（粉、胭脂红、浅黄），地被小花
  yh_huajing   花径：沿小路的一长条花带（石竹、月季、萱草叶丛、小白花），两侧压卵石
  yh_rosebush  单丛月季（院内花池脚下、月洞门两侧）
用法：python3 blender/scripts/sites/yihong_garden.py <out_dir>
  然后 node blender/scripts/web/pack_prop.mjs <out_dir>/<名>.glb models/p/<名>.glb 60000 512
坐标：Blender Z 向上，模块正面朝 -Y；底面中心在原点（pack_prop 会再归一高度，网页用 h 还原真实尺寸）。
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector, Matrix, Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yihong_atlas as AT

OUT = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith('.py') else '/tmp/yh_garden'
os.makedirs(OUT, exist_ok=True)
ATLAS = AT.build(os.path.join(OUT, 'yh_atlas.png'))
HERE = os.path.dirname(os.path.abspath(__file__))
BLEND_DIR = os.path.normpath(os.path.join(HERE, '..', '..'))

PAL = {
    '芭蕉叶': (0.3, 0.5, 0.2), '芭蕉茎': (0.4, 0.5, 0.25),
    '树皮': (0.3, 0.22, 0.17),
    '叶深': (0.13, 0.26, 0.08), '叶': (0.2, 0.36, 0.11), '叶浅': (0.32, 0.47, 0.16), '茎': (0.2, 0.25, 0.1),
    '月季粉': (0.93, 0.45, 0.55), '月季红': (0.68, 0.06, 0.13), '月季黄': (0.98, 0.84, 0.5), '月季白': (0.96, 0.93, 0.88),
    '石竹': (0.86, 0.22, 0.45), '小白花': (0.95, 0.95, 0.9), '萱草': (0.95, 0.5, 0.1), '花心': (0.95, 0.75, 0.2),
    '土': (0.2, 0.14, 0.09), '青花瓷': (0.82, 0.84, 0.86), '青花蓝': (0.1, 0.2, 0.5), '湖石': (0.5, 0.5, 0.47), '卵石': (0.26, 0.25, 0.23), '卵石深': (0.18, 0.175, 0.165), '苔': (0.12, 0.2, 0.07),
}


def mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    if name in ('芭蕉叶', '芭蕉茎'):
        nt = m.node_tree
        tx = nt.nodes.new('ShaderNodeTexImage')
        if name == '芭蕉叶':                  # 颜色图 + 单独的透明图合成一张 RGBA（glTF 只认一张）
            from PIL import Image
            c = Image.open(os.path.join(BLEND_DIR, '..', 'tex', 'leaf_banana_c.png')).convert('RGB')
            a = Image.open(os.path.join(BLEND_DIR, '..', 'tex', 'leaf_banana_a.png')).convert('L').resize(c.size)
            c.putalpha(a)
            pth = os.path.join(OUT, 'banana_leaf_rgba.png')
            c.save(pth)
            tx.image = bpy.data.images.load(pth)
            nt.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
            m.use_backface_culling = False
        else:
            tx.image = bpy.data.images.load(os.path.join(BLEND_DIR, '..', 'tex', 'banana_stem_c.png'))
        tx.image.pack()
        nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.5 if name == '芭蕉叶' else 0.8
        return m
    if name == '树皮':
        nt = m.node_tree
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = bpy.data.images.load(os.path.join(BLEND_DIR, '..', 'tex', 'bark_c.jpg'))
        tx.image.pack()
        nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Roughness'].default_value = 0.95
        return m
    if name == '花叶':                      # 贴图集：颜色 + 透明（网页里按 alphaTest 裁边）
        nt = m.node_tree
        tx = nt.nodes.new('ShaderNodeTexImage')
        tx.image = bpy.data.images.load(ATLAS)
        tx.image.pack()                     # 贴图打进 .blend，不依赖外部文件
        nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
        nt.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
        b.inputs['Roughness'].default_value = 0.55
        m.use_backface_culling = False
        m.blend_method = 'CLIP' if hasattr(m, 'blend_method') else None
        return m
    c = PAL[name]
    b.inputs['Base Color'].default_value = (*c, 1)
    b.inputs['Roughness'].default_value = 0.9 if name in ('土', '卵石', '卵石深', '苔') else 0.6
    if '叶' in name or name in ('茎',) or '月季' in name or name in ('石竹', '小白花', '萱草'):
        m.use_backface_culling = False
    return m


class Geo:
    """按材质累积顶点/面，最后一次性建网格（几千朵花也快）。"""
    def __init__(self):
        self.d = {}

    def add(self, mname, verts, faces, uvs=None):
        V, F, U = self.d.setdefault(mname, ([], [], []))
        o = len(V)
        V.extend(verts)
        U.extend(uvs or [(0.0, 0.0)] * len(verts))
        F.extend([tuple(i + o for i in f) for f in faces])

    def build(self, name):
        objs = []
        for mname, (V, F, U) in self.d.items():
            me = bpy.data.meshes.new(f'{name}_{mname}')
            me.from_pydata([tuple(v) for v in V], [], F)
            uvl = me.uv_layers.new(name='UVMap')
            for lp in me.loops:
                uvl.data[lp.index].uv = U[lp.vertex_index]
            me.validate()
            me.materials.append(mat(mname))
            for p in me.polygons:
                p.use_smooth = True
            o = bpy.data.objects.new(f'{name}_{mname}', me)
            bpy.context.scene.collection.objects.link(o)
            objs.append(o)
        return objs


def frame(n):
    """以 n 为 +Z 的旋转矩阵。"""
    n = Vector(n).normalized()
    return Vector((0, 0, 1)).rotation_difference(n).to_matrix()


def petal(G, cell, base, R, L, W, cup, tilt, twist):
    """一片花瓣：4×3 网格，沿长度微卷、横向内兜，贴图集 cell 格。base 处为花心，R 为花的朝向矩阵，tilt 为外翻角（0=直立）。"""
    rot = R @ Matrix.Rotation(twist, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'X')
    vs, us = [], []
    for i in range(3):
        t = i / 2
        for j in range(3):
            u = (j - 1)
            x = u * W / 2
            y = -abs(u) * cup * W * 0.5 + (t * t) * cup * L * 0.3
            z = t * L
            vs.append(base + rot @ Vector((x, -y, z)))
            us.append(AT.uv(cell, j / 2, t))
    fs = [(i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j) for i in range(2) for j in range(2)]
    G.add('花叶', vs, fs, us)


def leaf(G, cell, base, d, L, W, rnd, fold=0.25):
    """一片叶：3×4 网格贴 cell 格（叶形由透明裁出），沿中脉对折一点，叶尖下垂。d 为叶伸出的方向。"""
    if cell in ('叶深', '叶', '叶浅'):
        cell = 'leaf'
    d = Vector(d).normalized()
    side = d.cross(Vector((0, 0, 1)))
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(d).normalized()
    if up.z < 0:
        up = -up
    vs, us = [], []
    for i in range(3):
        t = i / 2
        c = base + d * (t * L) - up * (t * t * L * 0.3)
        for j in range(3):
            u = j - 1
            vs.append(c + side * (u * W / 2) + up * (abs(u) * fold * W * 0.5))
            us.append(AT.uv(cell, j / 2, t))
    fs = [(i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j) for i in range(2) for j in range(2)]
    G.add('花叶', vs, fs, us)


def stem(G, m, a, b, r, n=4):
    a, b = Vector(a), Vector(b)
    R = frame(b - a)
    vs = []
    for p in (a, b):
        for k in range(n):
            ang = 2 * math.pi * k / n
            vs.append(p + R @ Vector((math.cos(ang) * r, math.sin(ang) * r, 0)))
    fs = [(k, (k + 1) % n, n + (k + 1) % n, n + k) for k in range(n)]
    G.add(m, vs, fs)


CELL = {'月季红': 'petal_red', '月季粉': 'petal_pink', '月季白': 'petal_white', '月季黄': 'petal_yellow', '萱草': 'lily'}


def rose(G, rnd, c, n, size, col):
    """一朵重瓣月季：四圈花瓣，内圈紧抱成杯、外圈外翻。"""
    R = frame(n)
    col = CELL[col]
    for ring, (k, tilt, Ls) in enumerate(((3, 0.12, 0.5), (4, 0.45, 0.72), (5, 0.85, 0.9), (5, 1.25, 1.0))):
        for i in range(k):
            tw = 2 * math.pi * i / k + ring * 0.7 + rnd.uniform(-0.2, 0.2)
            petal(G, col, c, R, size * Ls, size * Ls * 1.05, 0.55, tilt + rnd.uniform(-0.12, 0.12), tw)
    # 花萼下几片小叶
    for i in range(3):
        a = rnd.uniform(0, 6.28)
        leaf(G, '叶深', c - R @ Vector((0, 0, size * 0.1)), R @ Vector((math.cos(a), math.sin(a), -0.4)), size * 0.9, size * 0.5, rnd)


def bud(G, rnd, c, n, size, col):
    R = frame(n)
    col = CELL[col]
    for i in range(4):
        petal(G, col, c, R, size, size * 0.8, 0.8, 0.12, 2 * math.pi * i / 4)


def small_flower(G, rnd, c, n, size, col, k=5):
    """正面小花：一张微微内兜的花片（石竹、小白花）；萱草用花瓣拼。"""
    R = frame(n)
    if col == '萱草':
        for i in range(6):
            petal(G, 'lily', c, R, size, size * 0.55, 0.3, 1.0, 2 * math.pi * i / 6 + rnd.uniform(-0.15, 0.15))
        return
    cell = {'石竹': 'dianthus', '小白花': 'smallwhite', '月季黄': 'smallwhite'}[col]
    rot = R @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, 'Z')
    vs, us = [], []
    for i in range(3):
        for j in range(3):
            x, y = (j - 1) * size, (i - 1) * size
            z = (abs(j - 1) + abs(i - 1)) * size * 0.25
            vs.append(c + rot @ Vector((x, y, z)))
            us.append(AT.uv(cell, j / 2, i / 2))
    G.add('花叶', vs, [(i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j) for i in range(2) for j in range(2)], us)


def rosebush(G, rnd, cx, cy, z0, r, h, colors):
    """一丛月季：基部数根茎，冠为半椭球；叶子铺满冠体，花开在顶面和外沿。"""
    nstem = rnd.randint(5, 8)
    tips = []
    for i in range(nstem):
        a = rnd.uniform(0, 6.28)
        rr = rnd.uniform(0.3, 0.85) * r
        top = Vector((cx + math.cos(a) * rr, cy + math.sin(a) * rr, z0 + h * rnd.uniform(0.55, 0.85)))
        stem(G, '茎', (cx + rnd.uniform(-0.04, 0.04), cy + rnd.uniform(-0.04, 0.04), z0), top, 0.0065)
        tips.append(top)
    nleaf = int(680 * r * h / 0.25)
    for i in range(nleaf):
        u, v = rnd.uniform(0, 6.28), rnd.uniform(0.05, 1.0)
        ph = math.acos(1 - v)          # 偏向上半
        p = Vector((cx + r * math.sin(ph) * math.cos(u) * rnd.uniform(0.55, 1.0),
                    cy + r * math.sin(ph) * math.sin(u) * rnd.uniform(0.55, 1.0),
                    z0 + h * 0.15 + (h * 0.85) * math.cos(ph) * rnd.uniform(0.75, 1.0)))
        out = Vector((p.x - cx, p.y - cy, (p.z - z0) * 0.6)).normalized()
        d = (out + Vector((rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), rnd.uniform(-.2, .5)))).normalized()
        leaf(G, 'leaf', p, d, rnd.uniform(0.06, 0.095), rnd.uniform(0.045, 0.065), rnd)
    nflower = int(38 * r * r / 0.16) + 4
    for i in range(nflower):
        u, v = rnd.uniform(0, 6.28), rnd.uniform(0.0, 0.75)
        ph = math.acos(1 - v)
        p = Vector((cx + r * math.sin(ph) * math.cos(u), cy + r * math.sin(ph) * math.sin(u), z0 + h * 0.15 + h * 0.88 * math.cos(ph)))
        n = Vector((math.sin(ph) * math.cos(u) * 0.8, math.sin(ph) * math.sin(u) * 0.8, 1.0)) + Vector((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), 0))
        col = rnd.choice(colors)
        if rnd.random() < 0.22:
            bud(G, rnd, p, n, rnd.uniform(0.022, 0.03), col)
        else:
            rose(G, rnd, p, n, rnd.uniform(0.035, 0.05), col)


def pebble(G, rnd, c, s, m):
    """一块卵石：压扁的八面细分球（直接写顶点，省得 bpy.ops）。"""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1)
    sx, sy, sz = s * rnd.uniform(0.8, 1.2), s * rnd.uniform(0.7, 1.0), s * rnd.uniform(0.45, 0.65)
    a = rnd.uniform(0, 6.28)
    R = Matrix.Rotation(a, 3, 'Z')
    vs = [c + R @ Vector((v.co.x * sx * (1 + rnd.uniform(-.12, .12)), v.co.y * sy, v.co.z * sz)) for v in bm.verts]
    fs = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    G.add(m, vs, fs)


def mound(G, m, cx, cy, rx, ry, h, z0=0.0, n=20, rings=4):
    """椭圆土丘（培土、苔垫）。"""
    vs = [Vector((cx, cy, z0 + h))]
    for i in range(1, rings + 1):
        t = i / rings
        for k in range(n):
            a = 2 * math.pi * k / n
            vs.append(Vector((cx + rx * t * math.cos(a), cy + ry * t * math.sin(a), z0 + h * math.cos(t * math.pi / 2) - 0.02 * t)))
    fs = [(0, 1 + k, 1 + (k + 1) % n) for k in range(n)]
    for i in range(rings - 1):
        for k in range(n):
            a, b = 1 + i * n + k, 1 + i * n + (k + 1) % n
            fs.append((a, a + n, b + n, b))
    G.add(m, vs, fs)


def groundcover(G, rnd, pts, colors, dens=1.0):
    """地被：低矮叶丛 + 小花。pts 为 (x,y,z) 列表。"""
    for (x, y, z) in pts:
        for i in range(int(6 * dens)):
            a = rnd.uniform(0, 6.28)
            leaf(G, 'leaf', Vector((x, y, z)), Vector((math.cos(a), math.sin(a), rnd.uniform(0.2, 0.9))), rnd.uniform(0.07, 0.11), 0.05, rnd, 0.35)
        if rnd.random() < 0.7:
            for i in range(rnd.randint(1, 3)):
                p = Vector((x + rnd.uniform(-.05, .05), y + rnd.uniform(-.05, .05), z + rnd.uniform(0.05, 0.12)))
                small_flower(G, rnd, p, (rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), 1), rnd.uniform(0.022, 0.032), rnd.choice(colors))


def grass_tuft(G, rnd, x, y, z, h, m='叶'):
    """萱草 / 沿阶草一类的细长叶丛。"""
    for i in range(rnd.randint(9, 14)):
        a = rnd.uniform(0, 6.28)
        d = Vector((math.cos(a) * rnd.uniform(0.25, 0.6), math.sin(a) * rnd.uniform(0.25, 0.6), 1)).normalized()
        L = h * rnd.uniform(0.7, 1.1)
        side = d.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        base = Vector((x, y, z))
        vs, us = [], []
        for t in (0, 0.35, 0.7, 1.0):
            c = base + d * (t * L) + Vector((math.cos(a), math.sin(a), 0)) * (t * t * L * 0.45) - Vector((0, 0, t * t * L * 0.3))
            w = 0.014 * (1 - t * 0.9)
            vs += [c - side * w, c + side * w]
            us += [AT.uv('blade', 0.1, t), AT.uv('blade', 0.9, t)]
        G.add('花叶', vs, [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)], us)


def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def save_export(name):
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND_DIR, name + '.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True,
                              export_apply=True, export_materials='EXPORT', export_yup=True)
    zs = [(o.matrix_world @ Vector(c)).z for o in bpy.data.objects if o.type == 'MESH' for c in o.bound_box]
    xs = [(o.matrix_world @ Vector(c)).x for o in bpy.data.objects if o.type == 'MESH' for c in o.bound_box]
    ys = [(o.matrix_world @ Vector(c)).y for o in bpy.data.objects if o.type == 'MESH' for c in o.bound_box]
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    print(f'EXPORT {name} h={max(zs) - min(zs):.2f} w={max(xs) - min(xs):.2f} d={max(ys) - min(ys):.2f} tris={tris}')


# ---------------- 椭圆花坛 ----------------
def build_rosebed():
    new_scene()
    rnd = random.Random(1701)
    G = Geo()
    RX, RY = 1.7, 0.95
    # 卵石镶边：两圈
    n = 58
    for k in range(n):
        a = 2 * math.pi * (k + rnd.uniform(-.2, .2)) / n
        pebble(G, rnd, Vector((RX * math.cos(a), RY * math.sin(a), 0.02)), rnd.uniform(0.07, 0.095), rnd.choice(('卵石', '卵石', '卵石深')))
    for k in range(int(n * 0.85)):
        a = 2 * math.pi * (k + 0.5) / int(n * 0.85)
        pebble(G, rnd, Vector(((RX - 0.13) * math.cos(a), (RY - 0.11) * math.sin(a), 0.07)), rnd.uniform(0.06, 0.08), '卵石深')
    mound(G, '土', 0, 0, RX - 0.12, RY - 0.1, 0.16, 0.0)
    # 月季：中间一丛高的，四周几丛矮的
    rosebush(G, rnd, 0.0, 0.05, 0.12, 0.42, 0.75, ('月季红', '月季红', '月季粉'))
    for (x, y, r, h, cols) in ((-0.95, 0.2, 0.33, 0.55, ('月季粉', '月季粉', '月季白')), (0.95, 0.15, 0.33, 0.55, ('月季粉', '月季红')),
                               (-0.45, -0.45, 0.28, 0.45, ('月季黄', '月季白')), (0.5, -0.48, 0.28, 0.45, ('月季粉', '月季黄')),
                               (-0.35, 0.55, 0.26, 0.5, ('月季红', '月季粉')), (0.45, 0.55, 0.26, 0.5, ('月季白', '月季粉'))):
        rosebush(G, rnd, x, y, 0.1, r, h, cols)
    # 边沿地被
    pts = []
    for k in range(70):
        a = 2 * math.pi * k / 70
        f = rnd.uniform(0.72, 0.92)
        pts.append((math.cos(a) * (RX - 0.12) * f, math.sin(a) * (RY - 0.1) * f, 0.06))
    for k in range(40):
        a, f = rnd.uniform(0, 6.28), math.sqrt(rnd.uniform(0.1, 0.6))
        pts.append((math.cos(a) * RX * f, math.sin(a) * RY * f, 0.13))
    groundcover(G, rnd, pts, ('石竹', '小白花', '小白花', '石竹'), 1.2)
    G.build('yh_rosebed')
    save_export('yh_rosebed')


# ---------------- 花径 ----------------
def build_huajing():
    new_scene()
    rnd = random.Random(1702)
    G = Geo()
    L, W = 4.0, 0.8
    for side in (-1, 1):                         # 两长边压卵石
        x = -L / 2
        while x < L / 2:
            s = rnd.uniform(0.07, 0.1)
            pebble(G, rnd, Vector((x, side * W / 2, 0.02)), s, rnd.choice(('卵石', '卵石深')))
            x += s * 1.7
    mound(G, '土', 0, 0, L / 2 - 0.05, W / 2 - 0.05, 0.08, -0.01, n=28, rings=3)
    # 后排萱草叶丛 + 橙花，前排石竹、小白花，中间穿插矮月季
    x = -L / 2 + 0.25
    while x < L / 2 - 0.2:
        grass_tuft(G, rnd, x, 0.18 + rnd.uniform(-.05, .05), 0.05, rnd.uniform(0.4, 0.55))
        if rnd.random() < 0.85:
            for i in range(rnd.randint(2, 4)):
                p = Vector((x + rnd.uniform(-.06, .06), 0.18, 0.05 + rnd.uniform(0.45, 0.6)))
                stem(G, '茎', (x, 0.18, 0.05), p, 0.006)
                small_flower(G, rnd, p, (rnd.uniform(-.3, .3), -0.4, 1), 0.04, '萱草', 6)
        x += rnd.uniform(0.32, 0.45)
    for x in (-1.6, -0.8, 0.0, 0.8, 1.6):
        rosebush(G, rnd, x + rnd.uniform(-.1, .1), -0.02, 0.05, 0.26, 0.45, rnd.choice((('月季粉', '月季红'), ('月季白', '月季粉'), ('月季红', '月季黄'))))
    pts = [(rnd.uniform(-L / 2 + 0.12, L / 2 - 0.12), rnd.uniform(-W / 2 + 0.1, 0.0), 0.05) for i in range(80)]
    groundcover(G, rnd, pts, ('石竹', '石竹', '小白花', '月季黄'), 1.0)
    G.build('yh_huajing')
    save_export('yh_huajing')


# ---------------- 单丛月季 ----------------
def build_rosebush():
    new_scene()
    rnd = random.Random(1703)
    G = Geo()
    rosebush(G, rnd, 0, 0, 0.0, 0.42, 0.85, ('月季红', '月季粉', '月季粉'))
    groundcover(G, rnd, [(math.cos(a) * 0.4, math.sin(a) * 0.4, 0.0) for a in [i * 0.9 for i in range(7)]], ('小白花', '石竹'), 0.8)
    G.build('yh_rosebush')
    save_export('yh_rosebush')


# ---------------- 西府海棠 ----------------
def tube(G, a, b, r0, r1, n=6, v0=0.0):
    """树皮圆台，贴 bark_c.jpg（u 绕一圈、v 沿长度）。"""
    a, b = Vector(a), Vector(b)
    R = frame(b - a)
    L = (b - a).length
    vs, us = [], []
    for p, r, v in ((a, r0, v0), (b, r1, v0 + L / 0.6)):
        for k in range(n + 1):
            ang = 2 * math.pi * k / n
            vs.append(p + R @ Vector((math.cos(ang) * r, math.sin(ang) * r, 0)))
            us.append((k / n, v))
    fs = [(k, k + 1, n + 2 + k, n + 1 + k) for k in range(n)]
    G.add('树皮', vs, fs, us)
    return v0 + L / 0.6


def card(G, cell, c, R, size, cup=0.25, u0=0.0, u1=1.0, flat=False):
    """3×3 微兜的方片（小花、花苞正面）；flat=True 时只用一块四边形（远看一样，省面）。"""
    if flat:
        vs = [c + R @ Vector((x * size, y * size, 0)) for (x, y) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        us = [AT.uv(cell, u, v) for (u, v) in ((u0, 0), (u1, 0), (u1, 1), (u0, 1))]
        G.add('花叶', vs, [(0, 1, 2, 3)], us)
        return
    vs, us = [], []
    for i in range(3):
        for j in range(3):
            vs.append(c + R @ Vector(((j - 1) * size, (i - 1) * size, (abs(j - 1) + abs(i - 1)) * size * cup)))
            us.append(AT.uv(cell, u0 + (u1 - u0) * j / 2, i / 2))
    G.add('花叶', vs, [(i * 3 + j, i * 3 + j + 1, (i + 1) * 3 + j + 1, (i + 1) * 3 + j) for i in range(2) for j in range(2)], us)


def ht_cluster(G, rnd, p, out):
    """一簇海棠花：4–7 根细长花梗从短枝头垂下（“丝垂翠缕”），梗端开花或含着朱砂花苞（“葩吐丹砂”）。"""
    out = Vector(out).normalized()
    for i in range(rnd.randint(4, 7)):
        d = (out * 0.6 + Vector((rnd.uniform(-.7, .7), rnd.uniform(-.7, .7), rnd.uniform(-1.0, -0.2)))).normalized()
        L = rnd.uniform(0.05, 0.09)
        q = p + d * L
        side = d.cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
        G.add('茎', [p - side * 0.002, p + side * 0.002, q + side * 0.002, q - side * 0.002], [(0, 1, 2, 3)])
        if rnd.random() < 0.45:                                  # 花苞：合抱的朱红瓣
            R = frame(d)
            for k in range(2):
                petal(G, 'ht_bud', q, R, 0.022, 0.018, 0.9, 0.08, math.pi * k)
        else:                                                    # 半开、全开的花朝外略垂
            n = (out * 0.8 + d * 0.5 + Vector((rnd.uniform(-.3, .3), rnd.uniform(-.3, .3), 0.2))).normalized()
            card(G, 'haitang', q, frame(n) @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, 'Z'), rnd.uniform(0.026, 0.034), flat=True)


def ht_branch(G, rnd, p, d, L, r, depth, tips, v=0.0):
    d = d.normalized()
    mid = p + d * L * 0.5 + Vector((rnd.uniform(-.06, .06), rnd.uniform(-.06, .06), 0)) * L
    end = p + d * L
    v = tube(G, p, mid, r, r * 0.86, 6 if depth > 1 else 4, v)
    tube(G, mid, end, r * 0.86, r * 0.72, 6 if depth > 1 else 4, v)
    if depth == 0:
        tips.append((end, d))
        return
    k = rnd.randint(2, 3)
    for i in range(k):
        a = 2 * math.pi * i / k + rnd.uniform(-0.5, 0.5)
        side = Vector((math.cos(a), math.sin(a), 0))
        # 越往外越平展，树冠成伞
        nd = (d + side * rnd.uniform(0.45, 0.8) + Vector((0, 0, 0.15 if depth > 1 else -0.08))).normalized()
        ht_branch(G, rnd, end, nd, L * rnd.uniform(0.6, 0.75), r * 0.6, depth - 1, tips, v)
    if depth <= 2:
        tips.append((end, d))


def build_haitang():
    new_scene()
    rnd = random.Random(1717)
    G = Geo()
    tips = []
    v = tube(G, (0, 0, 0), (0.03, 0.02, 0.8), 0.16, 0.13, 8)
    v = tube(G, (0.03, 0.02, 0.8), (0.0, 0.05, 1.5), 0.13, 0.11, 8, v)
    n = 5
    for i in range(n):                                          # 五根主枝斜上，瓶形起伞
        a = 2 * math.pi * i / n + rnd.uniform(-0.25, 0.25)
        d = Vector((math.cos(a) * 0.55, math.sin(a) * 0.55, 1.0))
        ht_branch(G, rnd, Vector((0, 0.05, 1.45)), d, 1.15 + rnd.uniform(-0.15, 0.2), 0.075, 4, tips)
    cx = sum((t[0] for t in tips), Vector()) / len(tips)
    for (p, d) in tips:
        out = Vector((p.x, p.y, (p.z - 2.6) * 0.5)).normalized()
        for k in range(rnd.randint(8, 12)):                     # 新叶
            dd = (out + d * 0.4 + Vector((rnd.uniform(-.8, .8), rnd.uniform(-.8, .8), rnd.uniform(-.3, .6)))).normalized()
            q = p + Vector((rnd.uniform(-.22, .22), rnd.uniform(-.22, .22), rnd.uniform(-.18, .1)))
            leaf(G, rnd.choice(('leaf_young', 'leaf_young', 'leaf')), q, dd, rnd.uniform(0.06, 0.09), rnd.uniform(0.045, 0.06), rnd)
        for k in range(rnd.randint(4, 6)):                      # 花簇
            q = p + Vector((rnd.uniform(-.28, .28), rnd.uniform(-.28, .28), rnd.uniform(-.16, .12)))
            ht_cluster(G, rnd, q, out)
    G.build('yh_haitang')
    save_export('yh_haitang')


def build_shrub():
    """院中常绿灌木丛（黄杨、冬青一类），给铺地添些绿意。"""
    new_scene()
    rnd = random.Random(1704)
    G = Geo()
    for (cx, cy, r, h) in ((0, 0, 0.55, 0.85), (0.45, 0.25, 0.4, 0.6), (-0.4, 0.2, 0.38, 0.55)):
        shrub_mass(G, rnd, cx, cy, 0.0, r, h, 3600)
        for i in range(5):
            a = rnd.uniform(0, 6.28)
            stem(G, '茎', (cx, cy, 0), (cx + math.cos(a) * r * 0.5, cy + math.sin(a) * r * 0.5, h * 0.6), 0.012)
    G.build('yh_shrub')
    save_export('yh_shrub')


# ---------------- 芭蕉 ----------------
def banana_leaf(G, rnd, base, azim, L, W, rise, droop):
    """一片芭蕉叶：叶柄斜出，叶片先扬后垂，横向成 V 形对折、边缘略卷，沿长 9 段、横 5 列。"""
    dirh = Vector((math.cos(azim), math.sin(azim), 0))
    side = Vector((-math.sin(azim), math.cos(azim), 0))
    pet = rnd.uniform(0.25, 0.4)                       # 叶柄
    p0 = base
    p1 = base + dirh * pet * 0.6 + Vector((0, 0, pet * rise))
    side_ = side * 0.03
    G.add('茎', [p0 - side_, p0 + side_, p1 + side_ * 0.6, p1 - side_ * 0.6], [(0, 1, 2, 3)])
    twist = rnd.uniform(-0.25, 0.25)
    vs, us = [], []
    NL, NW = 9, 5
    for i in range(NL + 1):
        t = i / NL
        # 中脉曲线：仰角从 rise 逐渐转为下垂
        ang = math.atan(rise) * (1 - t) - droop * t * t
        x = 0.0
        pos = p1
        # 数值积分中脉
        cur = Vector(p1)
        steps = 6
        for k in range(steps):
            tt = t * k / steps
            a = math.atan(rise) * (1 - tt) - droop * tt * tt
            cur = cur + (dirh * math.cos(a) + Vector((0, 0, math.sin(a)))) * (L * t / steps)
        a = math.atan(rise) * (1 - t) - droop * t * t
        tang = dirh * math.cos(a) + Vector((0, 0, math.sin(a)))
        nrm = tang.cross(side).normalized()
        if nrm.z < 0:
            nrm = -nrm
        tw = twist * t
        sd = side * math.cos(tw) + nrm * math.sin(tw)
        for j in range(NW):
            u = (j / (NW - 1)) * 2 - 1
            fold = abs(u) * W * 0.1 * (1 - 0.5 * t)     # V 形对折
            curl = (u * u) * W * 0.06 * t                # 边缘下卷
            vs.append(cur + sd * (u * W / 2) + nrm * (fold - curl))
            us.append((j / (NW - 1), t))
    fs = [(i * NW + j, i * NW + j + 1, (i + 1) * NW + j + 1, (i + 1) * NW + j) for i in range(NL) for j in range(NW - 1)]
    G.add('芭蕉叶', vs, fs, us)


def build_bajiao():
    """“一边种几本芭蕉”：五本成丛，高低错落；每本假茎顶端七八片大叶，外层叶下垂，中心一卷新叶。"""
    new_scene()
    rnd = random.Random(1705)
    G = Geo()
    for (cx, cy, h) in ((0, 0, 2.0), (0.65, 0.4, 1.65), (-0.6, 0.35, 1.4), (0.3, -0.65, 1.1), (-0.45, -0.55, 0.75)):
        r0 = 0.055 + h * 0.018
        top = Vector((cx + rnd.uniform(-.08, .08), cy + rnd.uniform(-.08, .08), h))
        v = tube(G, (cx, cy, 0), top, r0, r0 * 0.7, 10) if False else None
        # 假茎：贴芭蕉茎纹理
        a, b = Vector((cx, cy, 0)), top
        R = frame(b - a)
        n = 10
        vs, us = [], []
        for z, rr in ((0, r0 * 1.15), (0.5, r0 * 0.92), (1.0, r0 * 0.72)):
            p = a + (b - a) * z
            for k in range(n + 1):
                ang = 2 * math.pi * k / n
                vs.append(p + R @ Vector((math.cos(ang) * rr, math.sin(ang) * rr, 0)))
                us.append((k / n, z * h / 0.9))
        fs = [(r * (n + 1) + k, r * (n + 1) + k + 1, (r + 1) * (n + 1) + k + 1, (r + 1) * (n + 1) + k) for r in range(2) for k in range(n)]
        G.add('芭蕉茎', vs, fs, us)
        nl = rnd.randint(8, 10)
        for i in range(nl):
            az = 2 * math.pi * i / nl + rnd.uniform(-0.3, 0.3)
            outer = i < nl - 2
            L = (1.2 + h * 0.45) * rnd.uniform(0.85, 1.05) * (1.0 if outer else 0.75)
            banana_leaf(G, rnd, top - Vector((0, 0, rnd.uniform(0.0, 0.45) if outer else 0.0)), az, L, L * rnd.uniform(0.36, 0.42),
                        rnd.uniform(0.9, 1.6) if outer else rnd.uniform(2.2, 3.5), rnd.uniform(0.9, 1.6) if outer else 0.4)
        # 心叶：卷成筒直立
        R = frame(Vector((rnd.uniform(-.1, .1), rnd.uniform(-.1, .1), 1)))
        vs, us = [], []
        for z in (0, 1):
            for k in range(7):
                ang = 2 * math.pi * k / 6 * 0.85
                vs.append(top + R @ Vector((math.cos(ang) * 0.035, math.sin(ang) * 0.035, z * h * 0.22)))
                us.append((k / 6, 0.3 + z * 0.4))
        G.add('芭蕉叶', vs, [(k, k + 1, 8 + k, 7 + k) for k in range(6)], us)
    G.build('yh_bajiao')
    save_export('yh_bajiao')


def build_bitao():
    """碧桃（重瓣观赏桃）：干矮、枝开展，花无梗、密密地贴在一年生枝上，叶才冒头。"""
    new_scene()
    rnd = random.Random(1706)
    G = Geo()
    tips = []
    v = tube(G, (0, 0, 0), (0.05, -0.03, 0.9), 0.12, 0.1, 8)
    for i in range(4):
        a = 2 * math.pi * i / 4 + rnd.uniform(-0.3, 0.3)
        d = Vector((math.cos(a) * 0.75, math.sin(a) * 0.75, 1.0))
        ht_branch(G, rnd, Vector((0.05, -0.03, 0.85)), d, 1.0 + rnd.uniform(-0.1, 0.2), 0.065, 4, tips)
    for (p, d) in tips * 2:
        # 一年生枝：每个枝头抽两根细长枝，花沿枝密生
        e = p + (d + Vector((rnd.uniform(-.4, .4), rnd.uniform(-.4, .4), 0.35))).normalized() * rnd.uniform(0.35, 0.55)
        side = (e - p).cross(Vector((0, 0, 1)))
        side = side.normalized() if side.length > 1e-3 else Vector((1, 0, 0))
        G.add('树皮', [p - side * 0.005, p + side * 0.005, e + side * 0.003, e - side * 0.003], [(0, 1, 2, 3)], [(0, 0), (0.1, 0), (0.1, 1), (0, 1)])
        for k in range(rnd.randint(9, 14)):
            t = rnd.uniform(0.05, 1.0)
            q = p + (e - p) * t + Vector((rnd.uniform(-.02, .02), rnd.uniform(-.02, .02), rnd.uniform(-.02, .02)))
            n = (Vector((q.x, q.y, 0)).normalized() * 0.6 + Vector((rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), rnd.uniform(0.2, 0.9)))).normalized()
            R = frame(n) @ Matrix.Rotation(rnd.uniform(0, 6.28), 3, 'Z')
            s = rnd.uniform(0.019, 0.025)
            card(G, 'bitao', q, R, s, flat=True)                                  # 重瓣：两层错开
            card(G, 'bitao', q + n * 0.006, R @ Matrix.Rotation(0.6, 3, 'Z'), s * 0.72, flat=True)
        for k in range(rnd.randint(2, 4)):
            q = e + Vector((rnd.uniform(-.05, .05), rnd.uniform(-.05, .05), 0))
            leaf(G, 'leaf_young', q, (e - p).normalized() + Vector((rnd.uniform(-.6, .6), rnd.uniform(-.6, .6), 0.3)), rnd.uniform(0.05, 0.08), 0.03, rnd)
    G.build('yh_bitao')
    save_export('yh_bitao')


def shrub_mass(G, rnd, cx, cy, z0, r, h, n_per=1500):
    """常绿灌木团（黄杨、冬青一类）。"""
    for i in range(int(n_per * r * h)):
        u, w = rnd.uniform(0, 6.28), rnd.uniform(0.0, 1.0)
        ph = math.acos(1 - w)
        p = Vector((cx + r * math.sin(ph) * math.cos(u) * rnd.uniform(0.75, 1.0), cy + r * math.sin(ph) * math.sin(u) * rnd.uniform(0.75, 1.0), z0 + h * 0.12 + h * 0.88 * math.cos(ph) * rnd.uniform(0.85, 1.0)))
        out = Vector((p.x - cx, p.y - cy, (p.z - z0 - h * 0.3) * 0.8)).normalized()
        d = (out + Vector((rnd.uniform(-.7, .7), rnd.uniform(-.7, .7), rnd.uniform(-.2, .6)))).normalized()
        leaf(G, 'leaf', p, d, rnd.uniform(0.07, 0.1), rnd.uniform(0.05, 0.07), rnd)


def build_bigbed():
    """院中大花床（参考图：院里满是花木，不露铺地）：不规则卵石镶边、培土，满铺细草与地被小花，
    后排灌木、中间月季、点一块湖石。约 5.6 × 3.4 m，正面朝 -Y。"""
    new_scene()
    rnd = random.Random(1707)
    G = Geo()
    RX, RY = 2.8, 1.7
    def rad(a):
        return 1 + 0.08 * math.sin(3 * a + 0.7) + 0.05 * math.sin(5 * a + 2.1)
    n = 150
    for k in range(n):
        a = 2 * math.pi * (k + rnd.uniform(-.2, .2)) / n
        f = rad(a)
        pebble(G, rnd, Vector((RX * f * math.cos(a), RY * f * math.sin(a), 0.02)), rnd.uniform(0.065, 0.09), rnd.choice(('卵石', '卵石', '卵石深')))
    mound(G, '苔', 0, 0, RX - 0.08, RY - 0.08, 0.22, 0.0, n=32, rings=5)          # 苔面，不露土
    # 满铺细草
    x = -RX
    while x < RX:
        y = -RY
        while y < RY:
            px, py = x + rnd.uniform(-.08, .08), y + rnd.uniform(-.08, .08)
            a = math.atan2(py / RY, px / RX)
            e = math.hypot(px / RX, py / RY)
            if e < rad(a) * 0.93:
                z = 0.22 * math.cos(min(e, 1) * math.pi / 2) - 0.01
                grass_tuft(G, rnd, px, py, z, rnd.uniform(0.18, 0.3))
            y += 0.16
        x += 0.16
    # 后排灌木、中排月季、前缘地被花
    for (x, y, r, h) in ((-0.4, 0.75, 0.6, 1.05), (0.9, 0.85, 0.55, 0.9), (2.0, 0.5, 0.45, 0.75), (-2.3, -0.2, 0.4, 0.7)):
        shrub_mass(G, rnd, x, y, 0.12, r, h, 3600)
    for (x, y, r, h, cols) in ((-0.6, -0.35, 0.34, 0.65, ('月季红', '月季粉')), (0.55, -0.25, 0.32, 0.6, ('月季粉', '月季白')),
                               (1.65, -0.45, 0.3, 0.55, ('月季红', '月季黄')), (-1.55, -0.7, 0.28, 0.5, ('月季粉', '月季红'))):
        rosebush(G, rnd, x, y, 0.12, r, h, cols)
    pts = []
    for k in range(120):
        a = rnd.uniform(0, 6.28)
        f = rnd.uniform(0.55, 0.92) * rad(a)
        pts.append((RX * f * math.cos(a), RY * f * math.sin(a), 0.12))
    groundcover(G, rnd, pts, ('石竹', '小白花', '小白花', '石竹', '月季黄'), 1.0)
    G.build('yh_bigbed')
    save_export('yh_bigbed')


def build_pot():
    """青花盆栽：台基、廊前一溜摆开。盆是青花缠枝，上种一丛月季。"""
    new_scene()
    rnd = random.Random(1708)
    G = Geo()
    prof = [(0.0, 0.0), (0.16, 0.0), (0.2, 0.05), (0.24, 0.3), (0.26, 0.34), (0.22, 0.34)]
    seg = 24
    vs, fs = [], []
    for i, (r, z) in enumerate(prof):
        for k in range(seg):
            a = 2 * math.pi * k / seg
            vs.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    for i in range(len(prof) - 1):
        for k in range(seg):
            a, b = i * seg + k, i * seg + (k + 1) % seg
            fs.append((a, b, b + seg, a + seg))
    G.add('青花瓷', vs, fs)
    # 青花带：腰上一圈蓝
    vs2 = []
    for (r, z) in ((0.225, 0.12), (0.238, 0.22)):
        for k in range(seg):
            a = 2 * math.pi * k / seg
            vs2.append(Vector((r * 1.004 * math.cos(a), r * 1.004 * math.sin(a), z)))
    G.add('青花蓝', vs2, [(k, (k + 1) % seg, seg + (k + 1) % seg, seg + k) for k in range(seg)])
    mound(G, '土', 0, 0, 0.22, 0.22, 0.03, 0.31, n=16, rings=2)
    rosebush(G, rnd, 0, 0, 0.32, 0.26, 0.5, ('月季红', '月季粉', '月季粉'))
    G.build('yh_pot')
    save_export('yh_pot')


WHICH = os.environ.get('YH_ONLY', 'rosebed,huajing,rosebush,haitang,shrub,bajiao,bitao,bigbed,pot').split(',')
for nm in WHICH:
    globals()['build_' + nm]()
