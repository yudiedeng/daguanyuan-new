import bpy,os,sys
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box,material
s=bpy.context.scene
assert not bpy.data.collections.get('34_正门木匾')
c=bpy.data.collections.new('34_正门木匾');s.collection.children.link(c)
wood=material('匾额_温润深栗木',(.105,.039,.019),.55)
edge=material('匾额_深木边框',(.047,.019,.009),.58)
n,l=wood.node_tree.nodes,wood.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
noise=next(x for x in n if x.type=='TEX_NOISE');noise.inputs['Scale'].default_value=3
coord=n.new('ShaderNodeTexCoord');vec=n.new('ShaderNodeVectorMath');vec.operation='MULTIPLY';vec.inputs[1].default_value=(3,80,110)
l.new(coord.outputs['Generated'],vec.inputs[0]);l.new(vec.outputs[0],noise.inputs['Vector'])
r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.045,.012,.006,1);r.color_ramp.elements[1].color=(.15,.065,.03,1)
l.new(noise.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],bs.inputs['Base Color'])
bump=next(x for x in n if x.type=='BUMP');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.0002
box('木匾_整木匾板',(0,-3.813,4.12),(1.30,.080,.30),wood,c,.008)
for z in [3.98,4.26]:box('木匾_上下边框_'+str(z),(0,-3.86,z),(1.32,.035,.035),edge,c,.005)
for x in [-.643,.643]:box('木匾_左右边框_'+str(x),(x,-3.86,4.12),(.034,.035,.25),edge,c,.005)
for x in [-.44,.44]:box('木匾_背部固定木_'+str(x),(x,-3.768,4.12),(.07,.025,.20),edge,c,.003)
for o in c.objects:
    for mod in o.modifiers:
        if mod.type=='BEVEL':mod.segments=4
c['description']='正门中轴木匾，宽1.32米高约0.315米，深栗木板和凸起木边框；空白待题字。'
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=Vector((0,-3.7,3.8));r.view_distance=4.2;r.view_rotation=Vector((0,1,0)).to_track_quat('-Z','Y')
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Installed blank wooden plaque centered on entrance beam; 7 components.')
