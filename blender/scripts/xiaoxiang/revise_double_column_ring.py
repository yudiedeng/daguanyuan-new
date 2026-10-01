import bpy, os
from mathutils import Vector
scene=bpy.context.scene
path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not bpy.data.collections.get('12_图02参考_内外柱圈')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_double_ring.blend'),copy=True)
root=bpy.data.collections.new('12_图02参考_内外柱圈');scene.collection.children.link(root)
def collection(name):
    c=bpy.data.collections.new(name);root.children.link(c);return c
outer=collection('12A_外圈廊柱与柱础')
inner=collection('12B_内圈房屋柱与柱础')
beams=collection('12C_内外圈梁枋')
base=bpy.data.objects['COLBASE_柱础_Y1_X1']
post=bpy.data.objects['POST_木柱_Y1_X1']
beam_source=bpy.data.objects['TIE_纵向柱头枋_Y1_跨1']
def clone(source,name,loc,scale,group):
    o=source.copy();o.data=source.data.copy();o.name=name;group.objects.link(o)
    o.location=loc;o.scale=scale;o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
    return o
def column(x,y,index,inside):
    label='内圈' if inside else '外圈'
    group=inner if inside else outer
    h=3.55 if inside else 3.05
    radius_scale=1 if inside else .88
    clone(base,f'RING_{label}_柱础_{index:02}',(x,y,.54),(1,1,1),group)
    o=clone(post,f'RING_{label}_木柱_{index:02}',(x,y,.6),(radius_scale,radius_scale,h/3.2),group)
    o['layout_reference']='图02-1潇湘馆室内空间格局；位置按原台基适配，无测绘尺寸'
    o['zone']='室内墙线' if inside else '前廊及左右侧廊外缘'
def beam(name,a,b,w=1,d=1):
    a,b=Vector(a),Vector(b)
    o=clone(beam_source,'RING_'+name,a,(w,d,(b-a).length/3),beams)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o

# Reference shows an outer U-shaped veranda and an inner three-bay enclosure.
# Front is -Y. Rear wall is near the rear terrace edge; no invented rear corridor.
front_x=[-4.8,-3.8,-1.45,1.45,3.8,4.8]
side_y=[-2.95,-1.5,0,1.5,2.95]
outer_pts=[(x,-2.95) for x in front_x]
outer_pts += [(x,y) for x in [-4.8,4.8] for y in side_y[1:]]
inner_x=[-3.8,-1.45,1.45,3.8]
inner_pts=[(x,y) for y in [-1.8,2.65] for x in inner_x]
for i,(x,y) in enumerate(outer_pts,1):column(x,y,i,False)
for i,(x,y) in enumerate(inner_pts,1):column(x,y,i,True)
for i in range(len(front_x)-1):
    beam(f'前廊柱头枋_{i}',(front_x[i],-2.95,3.49),(front_x[i+1],-2.95,3.49),.9,.85)
for x in [-4.8,4.8]:
    for i in range(len(side_y)-1):
        beam(f'侧廊柱头枋_{x}_{i}',(x,side_y[i],3.49),(x,side_y[i+1],3.49),.9,.85)
for y in [-1.8,2.65]:
    for i in range(3):beam(f'内圈前后枋_{y}_{i}',(inner_x[i],y,3.99),(inner_x[i+1],y,3.99))
for x in inner_x:
    beam(f'内圈进深梁_{x}',(x,-1.8,4.02),(x,2.65,4.02),1.15,1.2)
    beam(f'前廊联系梁_{x}',(x,-2.95,3.59),(x,-1.8,3.97),.85,.85)
for sign in [-1,1]:
    for y in side_y:
        # Side links terminate at inner wall line; intermediate bearing details remain schematic.
        iy=max(-1.8,min(2.65,y))
        beam(f'侧廊联系梁_{sign}_{y}',(sign*4.8,y,3.59),(sign*3.8,iy,3.97),.85,.85)

# Keep earlier trial geometry recoverable, but out of both viewport and render.
for name in ['05_柱础_装配接口','10_木构架_比例初稿','11_左右亭廊_地台与柱网']:
    c=bpy.data.collections[name];c.hide_render=True;c.hide_viewport=True
    c['archive_reason']='图02平面关系修订：旧均布柱网及独立侧亭试案，保留但不显示'
scene['column_layout']='外圈14廊柱，内圈8墙线柱；前廊1.15m，侧廊1.0m轴线间距；中心开间2.9m；参考图比例适配。'
scene['side_terraces_note']='原左右独立亭廊试案已隐藏归档；现为原台基上的连续前廊和两侧廊。'
scene['timber_stage']='内外圈柱梁比例初稿；围墙、隔扇、屋架及榫卯细节未建。'
cam=scene.camera;cam.location=(11,-16,14)
cam.rotation_euler=(Vector((0,0,1.6))-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d
            r.view_location=Vector((0,0,1.6));r.view_distance=16
            r.view_rotation=cam.rotation_euler.to_quaternion()
bpy.context.view_layer.update()
assert len(outer_pts)==14 and len(inner_pts)==8
assert all(abs(x)>=1.45 for x,y in inner_pts+outer_pts)
bpy.ops.wm.save_as_mainfile(filepath=path)
print('Saved revised layout: 14 outer columns + 8 inner columns; old layout archived, no original geometry deleted.')
