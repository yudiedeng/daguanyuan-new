import bpy
import os
import runpy
import json

folder = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(folder, 'prepare_texture_interfaces.py'), run_name='__main__')
out = os.path.join(folder, 'output')
brick = bpy.data.images.load('/Users/dengyudie/Downloads/Codex 图像 2026年9月19日 10_57_45.png', check_existing=True)
stone = bpy.data.images.load('/Users/dengyudie/Downloads/Codex 图像 2026年9月19日 10_58_48.png', check_existing=True)
for im in (brick, stone):
    im.colorspace_settings.name = 'sRGB'
    im.pack()

for name in ('MAT_廊面青砖', 'MAT_台帮青砖块', 'MAT_青灰石_微风化', 'MAT_柱础青石'):
    mat = bpy.data.materials[name]
    n, l = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(x for x in n if x.type == 'BSDF_PRINCIPLED')
    is_brick = '青砖' in name
    tex = n['INPUT_BaseColor']
    tex.image = brick if is_brick else stone
    tex.label = '用户提供：青砖' if is_brick else '用户提供：青石'
    n['TEXTURE_SCALE'].inputs['Scale'].default_value = (1.4, 2.8, 1) if is_brick else (0.8, 1.6, 1)
    # Mild per-object tonal variation keeps repeated units from looking identical.
    info = n.new('ShaderNodeObjectInfo')
    value = n.new('ShaderNodeMapRange')
    value.inputs['To Min'].default_value = .78 if is_brick else .90
    value.inputs['To Max'].default_value = 1.04
    l.new(info.outputs['Random'], value.inputs['Value'])
    mix = n.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = 1
    l.new(tex.outputs['Color'], mix.inputs[1])
    l.new(value.outputs['Result'], mix.inputs[2])
    l.new(mix.outputs['Color'], bsdf.inputs['Base Color'])
    # Appearance approximation from colour; these are not measured PBR height maps.
    gray = n.new('ShaderNodeRGBToBW')
    l.new(tex.outputs['Color'], gray.inputs[0])
    bump = n.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .18
    bump.inputs['Distance'].default_value = .003 if is_brick else .0015
    l.new(gray.outputs[0], bump.inputs['Height'])
    l.new(bump.outputs[0], bsdf.inputs['Normal'])
    rough = n.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .74 if is_brick else .60
    rough.inputs['To Max'].default_value = .94 if is_brick else .83
    l.new(gray.outputs[0], rough.inputs['Value'])
    l.new(rough.outputs[0], bsdf.inputs['Roughness'])
    mat['texture_status'] = 'User base colour connected; roughness and fine bump approximated from luminance'

scene = bpy.context.scene
scene['texture_status'] = 'User brick and stone images packed and connected'
scene.camera.location = (10.7, -12.5, 8.7)
from mathutils import Vector
scene.camera.rotation_euler = (Vector((0,-.25,.3))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.lens = 48
scene.render.resolution_x = 1400
scene.render.resolution_y = 1000
scene.render.filepath = os.path.join(out, 'xiaoxiang_platform_v03_textured.png')
target = os.path.join(out, 'xiaoxiang_platform_v03_textured.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=target)
assert all(i.packed_file for i in bpy.data.images if i.name in (os.path.basename('/Users/dengyudie/Downloads/Codex 图像 2026年9月19日 10_57_45.png'), os.path.basename('/Users/dengyudie/Downloads/Codex 图像 2026年9月19日 10_58_48.png')))
print('TEXTURED_FILE_VERIFIED', target)
