import bpy, math, os, shutil
from mathutils import Vector

path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend'), path
assert not bpy.data.collections.get('10_木构架_比例初稿'), 'Frame already exists'
backup=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_timber.blend')
if not os.path.exists(backup): shutil.copy2(path,backup)
col=bpy.data.collections.new('10_木构架_比例初稿')
bpy.context.scene.collection.children.link(col)
mat=bpy.data.materials.new('MAT_暗褐旧木_顺纹')
mat.use_nodes=True
n,l=mat.node_tree.nodes,mat.node_tree.links
bs=next(n for n in n if n.type=='BSDF_PRINCIPLED')
bs.inputs['Roughness'].default_value=.72
tex=n.new('ShaderNodeTexCoord')
scale=n.new('ShaderNodeVectorMath');scale.operation='MULTIPLY'
scale.inputs[1].default_value=(8,8,.42)
l.new(tex.outputs['Generated'],scale.inputs[0])
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=5
noise.inputs['Detail'].default_value=3
l.new(scale.outputs[0],noise.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.18
ramp.color_ramp.elements[0].color=(.022,.012,.007,1)
ramp.color_ramp.elements[1].position=.82
ramp.color_ramp.elements[1].color=(.13,.072,.032,1)
l.new(noise.outputs['Fac'],ramp.inputs[0])
obj=n.new('ShaderNodeObjectInfo')
variation=n.new('ShaderNodeMapRange')
variation.inputs['To Min'].default_value=.72
variation.inputs['To Max'].default_value=1.12
l.new(obj.outputs['Random'],variation.inputs[0])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
l.new(ramp.outputs[0],mix.inputs[1]);l.new(variation.outputs[0],mix.inputs[2])
l.new(mix.outputs[0],bs.inputs['Base Color'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23
bump.inputs['Distance'].default_value=.002
l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
rough=n.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.62;rough.inputs['To Max'].default_value=.88
l.new(noise.outputs['Fac'],rough.inputs[0]);l.new(rough.outputs[0],bs.inputs['Roughness'])
modifier_types={i.identifier for i in bpy.types.Modifier.bl_rna.properties['type'].enum_items}
assert 'BEVEL' in modifier_types

def mesh_obj(name,verts,faces,loc):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);col.objects.link(ob);ob.location=loc
    ob.data.materials.append(mat)
    bevel=ob.modifiers.new('轻微磨圆','BEVEL');bevel.width=.005;bevel.segments=3
    return ob

for base in sorted((o for o in bpy.data.objects if o.name.startswith('COLBASE')),key=lambda o:o.name):
    x,y,z=base.location
    bottom=.60;top=3.80;h=top-bottom
    N=48;verts=[]
    for zz,r in [(0,.170),(h*.12,.169),(h*.85,.151),(h,.148)]:
        for j in range(N):
            a=2*math.pi*j/N;verts.append((r*math.cos(a),r*math.sin(a),zz))
    faces=[tuple(reversed(range(N)))]
    for k in range(3):
        for j in range(N):faces.append((k*N+j,k*N+(j+1)%N,(k+1)*N+(j+1)%N,(k+1)*N+j))
    faces.append(tuple(range(3*N,4*N)))
    ob=mesh_obj(base.name.replace('COLBASE_柱础','POST_木柱'),verts,faces,(x,y,bottom))
    for p in ob.data.polygons:p.use_smooth=(len(p.vertices)==4)
    ob['stage']='比例初稿：柱高3.20m，柱径下340mm上296mm'
    ob['base_object']=base.name

def beam(name,a,b,width,depth):
    a,b=Vector(a),Vector(b);length=(b-a).length
    # Local Z follows the timber grain; local Y is vertical for these horizontal beams.
    w,d=width/2,depth/2
    verts=[(x,y,z) for z in (0,length) for y in (-d,d) for x in (-w,w)]
    faces=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
    ob=mesh_obj(name,verts,faces,a)
    ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    ob['stage']='梁枋比例初稿；节点细部待深化'
    return ob

xs=[-4.5,-1.5,1.5,4.5];ys=[-2.45,0,2.45]
for j,y in enumerate(ys):
    for i in range(3):
        beam(f'TIE_纵向柱头枋_Y{j+1}_跨{i+1}',(xs[i],y,3.61),(xs[i+1],y,3.61),.20,.28)
for i,x in enumerate(xs):
    for j in range(2):
        beam(f'BEAM_横向承梁_X{i+1}_跨{j+1}',(x,ys[j]-.10,3.94),(x,ys[j+1]+.10,3.94),.26,.34)

scene=bpy.context.scene
scene['timber_stage']='12木柱+9纵枋+8横梁；暂定比例，非历史测绘复原；屋架尚未搭建'
for ob in bpy.context.selected_objects:ob.select_set(False)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_location=Vector((0,0,1.9))
            area.spaces.active.region_3d.view_distance=17
cam=scene.camera
cam.location=(13.7,-16.8,11.6)
cam.rotation_euler=(Vector((0,-.1,1.8))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_timber.png')
bpy.ops.wm.save_as_mainfile(filepath=path)
print('FRAME ADDED',len(col.objects),'objects',path)
