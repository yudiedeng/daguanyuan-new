import bpy, os
from mathutils import Vector
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'xiaoxiang_platform_v08_earth.blend'))
obj=bpy.data.objects['CONTEXT_地面']
uv=obj.data.uv_layers.new(name='Soil_Metric')
# Image aspect 2:1: one tile spans 2 x 1 metres, retaining small gravel scale.
for p in obj.data.polygons:
    for i in p.loop_indices:
        v=obj.data.vertices[obj.data.loops[i].vertex_index].co
        uv.data[i].uv=(v.x/2,v.y)
mat=bpy.data.materials.new('MAT_用户泥土贴图_颗粒碎石');mat.use_nodes=True
n,l=mat.node_tree.nodes,mat.node_tree.links
bs=n.get('Principled BSDF')
im=bpy.data.images.load('/Users/dengyudie/Downloads/Codex 图像 2026年9月19日 12_52_21.png',check_existing=True);im.pack()
tex=n.new('ShaderNodeTexImage');tex.image=im;tex.extension='REPEAT'
coords=n.new('ShaderNodeUVMap');coords.uv_map='Soil_Metric';l.new(coords.outputs[0],tex.inputs[0])
l.new(tex.outputs['Color'],bs.inputs['Base Color'])
gray=n.new('ShaderNodeRGBToBW');l.new(tex.outputs['Color'],gray.inputs[0])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.45;bump.inputs['Distance'].default_value=.007
l.new(gray.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.78;rough.inputs['To Max'].default_value=.98
l.new(gray.outputs[0],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
obj.data.materials.clear();obj.data.materials.append(mat)
mat['note']='User colour texture packed; bump approximated from luminance, not measured height'
scene=bpy.context.scene
scene['ground_note']='User detailed soil image, tile 2 x 1 m, with fine bump and existing geometric relief'
target=os.path.join(OUT,'xiaoxiang_master.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
scene.camera.location=(-4.8,-7.5,2.25)
scene.camera.rotation_euler=(Vector((-1.5,-4.2,.05))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.lens=48
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v09_soil_detail.png');bpy.ops.render.render(write_still=True)
image_name=im.name
bpy.ops.wm.open_mainfile(filepath=target)
assert bpy.data.images[image_name].packed_file
print('VERIFIED',target)
