import bpy, os, shutil
from mathutils import Vector
out=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
path=os.path.join(out,'xiaoxiang_master.blend')
bpy.ops.wm.open_mainfile(filepath=path)
backup=os.path.join(out,'xiaoxiang_master_before_darker_soil.blend')
if not os.path.exists(backup):shutil.copy2(path,backup)
mat=bpy.data.materials['MAT_用户泥土贴图_颗粒碎石']
n,l=mat.node_tree.nodes,mat.node_tree.links
bs=n.get('Principled BSDF')
node=n.get('泥土深色调整')
if not node:
    source=bs.inputs['Base Color'].links[0].from_socket
    node=n.new('ShaderNodeMixRGB');node.name='泥土深色调整';node.label='深灰褐泥土'
    node.blend_type='MULTIPLY';node.inputs[0].default_value=1
    l.new(source,node.inputs[1]);l.new(node.outputs[0],bs.inputs['Base Color'])
node.inputs[2].default_value=(.53,.55,.57,1)
scene=bpy.context.scene
bpy.ops.wm.save_as_mainfile(filepath=path)
scene.camera.location=(-4.8,-7.5,2.25)
scene.camera.rotation_euler=(Vector((-1.5,-4.2,.05))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.lens=48
scene.render.filepath=os.path.join(out,'xiaoxiang_master_darker_soil.png')
bpy.ops.render.render(write_still=True)
print('SAVED',path)
