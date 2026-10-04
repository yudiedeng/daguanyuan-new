"""Blender 离线预览：用 Workbench 引擎（CPU 可跑）从指定机位渲染 .blend / .glb，检查门、陈设、座位等。
用法：python3 tools/bl_render.py <in.blend|in.glb>[,<另一个.blend>] <outdir> '<json 机位列表>' [hide_roof=1]
机位：[{"name":"a","loc":[x,y,z],"look":[x,y,z],"lens":24}]（Blender 坐标：网页 x→X，网页 z→−Y，网页 y→Z）
"""
import bpy, sys, json, os, re, math
from mathutils import Vector
src, outdir, cams = sys.argv[-4], sys.argv[-3], json.loads(sys.argv[-2]); hide_roof = sys.argv[-1] != '0'
os.makedirs(outdir, exist_ok=True)
srcs = src.split(',')      # 可以同时给外壳和室内两个 .blend：逗号隔开，后面的并入第一个
src = srcs[0]
if src.endswith('.glb'):
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=src)
else:
    bpy.ops.wm.open_mainfile(filepath=src)
for extra in srcs[1:]:
    with bpy.data.libraries.load(extra, link=False) as (a, b):
        b.objects = [n for n in a.objects]
    for o in b.objects:
        if o is not None and o.type == 'MESH': bpy.context.scene.collection.objects.link(o)
sc = bpy.context.scene
for m in bpy.data.materials:
    c = None
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'BSDF_PRINCIPLED': c = tuple(n.inputs['Base Color'].default_value); break
    if c: m.diffuse_color = c
roof = re.compile(r'屋面|卷棚|椽|正脊|垂脊|罗锅|博缝|望板|天花|吊顶|ceiling', re.I)
if hide_roof:
    for o in bpy.data.objects:
        if o.type == 'MESH' and roof.search(o.name): o.hide_render = True; o.hide_viewport = True
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = False; sc.render.resolution_x, sc.render.resolution_y = 900, 560
sc.cycles.max_bounces = 3
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 4.0; sun.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(sun)
sc.world = sc.world or bpy.data.worlds.new('w'); sc.world.use_nodes = True; bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.7, 0.75, 0.82, 1); bg.inputs['Strength'].default_value = 1.2
sc.view_settings.view_transform = 'Standard'
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
for c in cams:
    cam.location = Vector(c['loc']); cam.data.lens = c.get('lens', 24); cam.data.clip_start = 0.05; cam.data.clip_end = 400
    d = Vector(c['look']) - cam.location; cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(outdir, c['name'] + '.png'); bpy.ops.render.render(write_still=True); print('RENDER', c['name'])
