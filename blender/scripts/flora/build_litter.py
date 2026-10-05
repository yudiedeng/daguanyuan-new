"""竹下地面贴图：深褐泥土上铺满竹子落叶、细枝、小石子，Blender 建模后 Cycles 正交俯拍，输出可平铺的 tex/zhu_litter.jpg。
用法：python3 blender/scripts/flora/build_litter.py --out /tmp/zhu      （需要 bpy）

一块 2 m × 2 m（1024 px，约 2 mm/px），越过边界的东西在对边复制一份，四方连续；
天光均匀（只有叶子之间、叶下的柔和阴影，不带方向光），网页里当竹下地面的颜色贴图。
落叶：竹叶细长披针形，长 8–18 cm，叶片纵向微卷、整片略弯；颜色以干黄、浅褐、深褐为主，夹几片尚青的。
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector

OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/zhu'
os.makedirs(OUT, exist_ok=True)
T = 2.0
rnd = random.Random(2024)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene


def mat(name, col, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    return m


def wrap_offsets(x, y, r):
    """跨边界时，在对边多放一份（四方连续）。"""
    xs = [0] + ([T] if x < r else []) + ([-T] if x > T - r else [])
    ys = [0] + ([T] if y < r else []) + ([-T] if y > T - r else [])
    return [(dx, dy) for dx in xs for dy in ys]


def link(name, bm, mats):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    sc.collection.objects.link(o)
    return me


# 泥土底
soil = bmesh.new()
bmesh.ops.create_grid(soil, x_segments=1, y_segments=1, size=T)
bmesh.ops.translate(soil, verts=soil.verts, vec=(T / 2, T / 2, 0))
link('soil', soil, [mat('soil', (0.075, 0.055, 0.038), 0.95)])

# 碎土粒、小石子
pm = [mat('p%d' % i, c, 0.9) for i, c in enumerate(((0.11, 0.08, 0.055), (0.16, 0.13, 0.1), (0.23, 0.21, 0.18), (0.06, 0.045, 0.03)))]
peb = bmesh.new()
pidx = []
for k in range(2600):
    x, y = rnd.uniform(0, T), rnd.uniform(0, T)
    r = rnd.uniform(0.002, 0.009) if rnd.random() < 0.9 else rnd.uniform(0.01, 0.02)
    ci = rnd.randrange(len(pm))
    for dx, dy in wrap_offsets(x, y, 0.03):
        g = bmesh.ops.create_icosphere(peb, subdivisions=1, radius=r)
        bmesh.ops.scale(peb, vec=(1, rnd.uniform(0.6, 1.0), 0.45), verts=g['verts'])
        bmesh.ops.translate(peb, verts=g['verts'], vec=(x + dx, y + dy, r * 0.2))
        pidx += [ci] * len({f for v in g['verts'] for f in v.link_faces})
me = link('pebbles', peb, pm)
for f, ci in zip(me.polygons, pidx):
    f.material_index = ci

# 落叶
cols = [((0.55, 0.45, 0.24), 5), ((0.47, 0.36, 0.19), 5), ((0.36, 0.26, 0.14), 4), ((0.24, 0.16, 0.09), 3), ((0.6, 0.53, 0.3), 2),
        ((0.46, 0.46, 0.2), 1.5), ((0.3, 0.4, 0.15), 0.8), ((0.2, 0.3, 0.1), 0.5)]
lm = [mat('l%d' % i, c, 0.75) for i, (c, w) in enumerate(cols)]
wsum = sum(w for c, w in cols)
def pick():
    r = rnd.uniform(0, wsum)
    for i, (c, w) in enumerate(cols):
        r -= w
        if r <= 0:
            return i
    return 0

prof = [0.0, 0.5, 0.9, 1.0, 0.85, 0.6, 0.3, 0.0]
lv = bmesh.new()
lidx = []
for k in range(1500):
    x, y = rnd.uniform(0, T), rnd.uniform(0, T)
    L, W = rnd.uniform(0.08, 0.18), rnd.uniform(0.015, 0.03)
    a = rnd.uniform(0, 2 * math.pi)
    curl, bend = rnd.uniform(0.2, 0.9), rnd.uniform(-0.12, 0.25)
    z0 = 0.002 + k * 0.000012                       # 后铺的叶压在先铺的上面
    ci = pick()
    d = Vector((math.cos(a), math.sin(a), 0)); s = Vector((-math.sin(a), math.cos(a), 0))
    for dx, dy in wrap_offsets(x, y, L):
        base = Vector((x + dx, y + dy, z0)) - d * (L / 2)
        grid = []
        for i, w in enumerate(prof):
            u = i / (len(prof) - 1)
            row = []
            for v in (-1, 0, 1):
                p = base + d * (L * u) + s * (v * W * 0.5 * max(w, 0.04)) + Vector((0, 0, curl * W * 0.5 * v * v + bend * L * math.sin(math.pi * u) * 0.25))
                row.append(lv.verts.new(p))
            grid.append(row)
        for i in range(len(grid) - 1):
            for j in range(2):
                lv.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
                lidx.append(ci)
me = link('leaves', lv, lm)
for f, ci in zip(me.polygons, lidx):
    f.material_index = ci

# 细枝
tw = bmesh.new()
for k in range(40):
    x, y = rnd.uniform(0, T), rnd.uniform(0, T)
    a = rnd.uniform(0, 2 * math.pi); L = rnd.uniform(0.1, 0.35)
    for dx, dy in wrap_offsets(x, y, L):
        g = bmesh.ops.create_cone(tw, segments=5, radius1=0.003, radius2=0.0015, depth=L, cap_ends=False)
        bmesh.ops.rotate(tw, verts=g['verts'], cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(math.pi / 2, 3, 'Y'))
        bmesh.ops.rotate(tw, verts=g['verts'], cent=(0, 0, 0), matrix=__import__('mathutils').Matrix.Rotation(a, 3, 'Z'))
        bmesh.ops.translate(tw, verts=g['verts'], vec=(x + dx, y + dy, 0.02 + k * 0.0001))
link('twigs', tw, [mat('twig', (0.33, 0.27, 0.16), 0.7)])

# 均匀天光 + 正交俯拍
world = bpy.data.worlds.new('w'); sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'; cam.ortho_scale = T
co = bpy.data.objects.new('cam', cam); co.location = (T / 2, T / 2, 3); sc.collection.objects.link(co); sc.camera = co
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
sc.render.resolution_x = sc.render.resolution_y = 1024
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 90
sc.render.filepath = os.path.join(OUT, 'zhu_litter.jpg')
bpy.ops.render.render(write_still=True)
print('litter', sc.render.filepath)
# cp /tmp/zhu/zhu_litter.jpg tex/zhu_litter.jpg
