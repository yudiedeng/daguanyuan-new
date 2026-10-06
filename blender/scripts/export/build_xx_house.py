"""潇湘馆正房：从 blender/xiaoxiang.blend 导出更完整的网页模型（替代原来按构件折叠减面的 _lite 版），并在 Cycles 里把做旧烘进顶点颜色。
用法（需要 Blender 5 的 bpy，xiaoxiang.blend 是 5.2 存的）：
  python3 blender/scripts/export/build_xx_house.py --out /tmp/xx
  node blender/scripts/web/pack_glb.mjs /tmp/xx/xiaoxiang_full.glb models/b/xiaoxiang.wasm models/b/xiaoxiang.wasm keepcolor 0.0006
  然后照 blender/README.md 重做 glb_cut（明间两扇门）。

取哪些：编号 0x–3x 的正房构件集合（与原 _lite_xx.py 相同），实例全部转成实体；窗扇、门格心的花心原件（ASSET_*、样板*）不导出，
网页里仍用 tex/xx_win.json 的烘焙贴片。不做折叠减面（打包时用 meshopt 按误差上限简化，形状基本不变）。
做旧（顶点颜色 COLOR_0，网页 bmat 的 ao 变体读取）：
  R：Cycles 烘的环境光遮蔽（地面也参与遮挡，距离 1.2 m）；
  G：墙根溅泥（离地面 0.9 m 以内、越低越重，只在竖向面上）；
  B：青苔（朝上的面、背阴处，靠近地面和檐下更多，加一层噪声成片）。
大块平面（墙、台面、顶棚）先把超过 0.4 m 的边细分，免得顶点太稀、做旧糊成一片。
"""
import bpy, bmesh, re, sys, math, os
from mathutils import Vector, noise

SRC = os.path.join(os.path.dirname(__file__), '..', '..', 'xiaoxiang.blend')
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/xx'
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(SRC))
sc = bpy.context.scene


def log(*a):
    print('XX', *a, flush=True)


# 与 _lite_xx.py 一样：所有集合挂进场景、取消隐藏
def intree(c, root):
    return c == root or any(intree(c, ch) for ch in root.children)


for c in bpy.data.collections:
    if not intree(c, sc.collection):
        try:
            sc.collection.children.link(c)
        except Exception:
            pass


def unex(lc):
    lc.exclude = False
    lc.hide_viewport = False
    for c in lc.children:
        unex(c)


unex(bpy.context.view_layer.layer_collection)
for c in bpy.data.collections:
    c.hide_viewport = False
    c.hide_render = False

HOUSE = re.compile(r'^(0\d|1\d|2\d|3\d)')
keep = [c for c in bpy.data.collections if HOUSE.match(c.name)]
keepn = {c.name for c in keep}

# 实例转实体（窗扇、门格心花心原件除外）
empties = [o for c in keep for o in c.all_objects if o.type == 'EMPTY' and o.instance_collection
           and not re.match(r'^(ASSET_|样板)', o.instance_collection.name)]
log('instances', len(empties))
bpy.ops.object.select_all(action='DESELECT')
for e in empties:
    e.hide_set(False)
    e.select_set(True)
if empties:
    bpy.context.view_layer.objects.active = empties[0]
    bpy.ops.object.duplicates_make_real(use_base_parent=False, use_hierarchy=False)

sel = [o for o in bpy.data.objects if o.type == 'MESH' and o.users_collection and o.users_collection[0].name in keepn and not o.hide_get()]
log('objects', len(sel))

# 合成一个物体（应用修改器）
bpy.ops.object.select_all(action='DESELECT')
for o in sel:
    if o.data.users > 1:
        o.data = o.data.copy()
    o.select_set(True)
bpy.context.view_layer.objects.active = sel[0]
bpy.ops.object.convert(target='MESH')
bpy.ops.object.join()
H = bpy.context.view_layer.objects.active
H.name = 'xx_house'
for m in list(H.modifiers):
    H.modifiers.remove(m)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
log('joined tris', sum(len(p.vertices) - 2 for p in H.data.polygons))

# 长边细分
bm = bmesh.new()
bm.from_mesh(H.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
for it in range(4):
    long = [e for e in bm.edges if e.calc_length() > 0.4]
    if not long:
        break
    bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
bmesh.ops.triangulate(bm, faces=bm.faces)
bm.to_mesh(H.data)
bm.free()
zmin = min(v.co.z for v in H.data.vertices)
log('after subdiv tris', len(H.data.polygons), 'zmin', round(zmin, 3))

# 只留正房和一块地面，烘 AO
for o in list(bpy.data.objects):
    if o != H:
        bpy.data.objects.remove(o, do_unlink=True)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, zmin + 0.005))
ground = bpy.context.view_layer.objects.active
ground.data.materials.append(bpy.data.materials.new('ground'))

attr = H.data.color_attributes.new('WX', 'FLOAT_COLOR', 'POINT')
H.data.color_attributes.active_color = attr
H.data.attributes.default_color_name = 'WX'
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 48
if sc.world is None:
    sc.world = bpy.data.worlds.new('w')
sc.world.light_settings.distance = 1.2
bpy.ops.object.select_all(action='DESELECT')
H.select_set(True)
bpy.context.view_layer.objects.active = H
log('baking AO ...')
bpy.ops.object.bake(type='AO', target='VERTEX_COLORS')
log('baked')

# G 墙根溅泥、B 青苔
me = H.data
me.update()
vn = [Vector((0, 0, 0)) for _ in me.vertices]
for p in me.polygons:
    for i in p.vertices:
        vn[i] += p.normal * p.area
for i, v in enumerate(me.vertices):
    n = vn[i].normalized() if vn[i].length > 0 else Vector((0, 0, 1))
    c = attr.data[i].color
    ao = c[0]
    h = v.co.z - zmin
    vert = 1 - min(1, abs(n.z) / 0.7)
    splash = vert * max(0.0, 1 - h / 0.9) ** 1.6
    nz = noise.noise(v.co * 1.7) * 0.5 + 0.5
    moss = max(0.0, n.z - 0.45) / 0.55 * (1 - ao) ** 0.6 * (0.55 + 0.9 * max(0.0, 1 - h / 1.5)) * (0.4 + 1.2 * nz)
    attr.data[i].color = (ao, min(1, splash), min(1, moss), 1)
bpy.data.objects.remove(ground, do_unlink=True)

path = os.path.join(OUT, 'xiaoxiang_full.glb')
bpy.ops.object.select_all(action='DESELECT')
H.select_set(True)
bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_image_format='NONE',
                          export_materials='EXPORT', export_yup=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False)
log('export', path, len(me.polygons))
