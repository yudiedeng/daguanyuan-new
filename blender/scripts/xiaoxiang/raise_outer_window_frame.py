import bpy
from mathutils import Vector
s=bpy.context.scene
assert s.name=='窗棂样板_参考图右下'
c=bpy.data.collections['样板V2_清晰图描形']
assert not c.objects.get('V6_立体厚外框')
# Continuous closed rectangular frame with a deep return and sloped inner reveal.
# Profile goes from the outer back, over the front moulding, to the inner back.
profile=[(.625275,.0444,-.015),(.625275,.0444,-.128),
 (.622275,.0474,-.135),(.618,.051675,-.135),
 (.617,.052675,-.135),(.589,.080675,-.135),
 (.588,.081675,-.135),(.582,.087675,-.129),
 (.570,.099675,-.100),(.5688,.100875,-.100),
 (.553,.116675,-.065),(.549,.120675,-.060),
 (.548,.121675,-.060),(.543,.126675,-.055),
 (.543,.126675,-.015)]
vs=[]
for half,bottom,y in profile:
    vs.extend([(-half,y,bottom),(half,y,bottom),(half,y,1.248-bottom),(-half,y,1.248-bottom)])
faces=[]
for i in range(len(profile)):
    j=(i+1)%len(profile)
    for k in range(4):faces.append((i*4+k,i*4+(k+1)%4,j*4+(k+1)%4,j*4+k))
me=bpy.data.meshes.new('厚外框_连续倒角截面');me.from_pydata(vs,[],faces);me.update()
o=bpy.data.objects.new('V6_立体厚外框',me);c.objects.link(o)
me.materials.append(bpy.data.materials['SAMPLE2_深绿漆'])
me.materials.append(bpy.data.materials['SAMPLE2_旧金褐线'])
for p in me.polygons:p.material_index=1 if p.index//4 in [3,5,8,11] else 0
for old in c.objects:
    if old.name.startswith(('V2_外框','V2_框线脚','V2_内口')):
        old.hide_render=True;old.hide_set(True)
s['outer_frame_depth']='外围厚框总深120mm，正面比内嵌花纹突出91mm；内侧斜口过渡，内部花纹未移动。'
# Show the relief in an oblique view rather than an edge-on view.
q=Vector((-.75,2.6,-.20)).to_track_quat('-Z','Y')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d
            r.view_location=Vector((0,-.035,.624));r.view_distance=1.95;r.view_rotation=q
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Outer frame rebuilt: 120mm deep, projecting 91mm beyond inset carving. Internal lattice unchanged.')
