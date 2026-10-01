import bpy, random, os
from mathutils import Vector
random.seed(1931)
scene=bpy.context.scene
path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not bpy.data.collections.get('11_左右亭廊_地台与柱网')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_side_terraces.blend'),copy=True)
group=bpy.data.collections.new('11_左右亭廊_地台与柱网');scene.collection.children.link(group)
floor=bpy.data.materials['MAT_廊面青砖_养护旧化_paving']
wall=bpy.data.materials['MAT_台帮青砖块_养护旧化_wall']
stone=bpy.data.materials['MAT_青灰石_微风化_养护旧化_coping']
mortar=bpy.data.materials['MAT_灰缝_灰砂色_养护旧化_joint']

def block(name,dims,loc,mat,bevel=.002):
    x,y,z=[v/2 for v in dims]
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);group.objects.link(ob);ob.location=loc;me.materials.append(mat)
    uv=me.uv_layers.new(name='UV_Metric_1m');ox,oy=random.uniform(0,2),random.uniform(0,2)
    for p in me.polygons:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));a,b=[(1,2),(0,2),(0,1)][axis]
        for i in p.loop_indices:
            v=me.vertices[me.loops[i].vertex_index].co;uv.data[i].uv=(v[a]+ox,v[b]+oy)
    if bevel:
        m=ob.modifiers.new('细磨边','BEVEL');m.width=bevel;m.segments=3
    return ob

def intervals(start,end,pitch,offset=0,gap=.004):
    c=start-offset
    while c<end-1e-7:
        a,b=max(start,c),min(end,c+pitch)
        if b-a>gap:yield a+gap/2,b-gap/2
        c+=pitch

def clone(source,name,loc,scale=(1,1,1)):
    ob=source.copy();ob.data=source.data.copy();ob.name=name;group.objects.link(ob)
    ob.location=loc;ob.scale=scale;return ob

base=bpy.data.objects['COLBASE_柱础_Y1_X1'];post=bpy.data.objects['POST_木柱_Y1_X1']
beam_template=bpy.data.objects['TIE_纵向柱头枋_Y1_跨1']
def beam(name,a,b):
    a,b=Vector(a),Vector(b)
    ob=clone(beam_template,name,a,(.9,.85,(b-a).length/3))
    ob.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()

for sign,label in [(-1,'左'),(1,'右')]:
    def B(name,dims,loc,mat,bevel=.002):
        return block('SIDE_'+label+'_'+name,dims,(sign*loc[0],loc[1],loc[2]),mat,bevel)
    # Flush junction at x=5.4; original side coping remains as a threshold strip.
    B('内填',(2.4,3.8,.446),(6.6,-1.4,.223),mortar,0)
    B('铺地灰床',(2.4,3.8,.032),(6.6,-1.4,.462),mortar,0)
    for r,(ya,yb) in enumerate(intervals(-3.3,.5,.224)):
        for c,(xa,xb) in enumerate(intervals(5.4,7.8,.444,.222*(r%2))):
            o=B(f'青砖铺地_{r}_{c}',(xb-xa,yb-ya,.045),((xa+xb)/2,(ya+yb)/2,.4575+random.uniform(-.0006,.0006)),floor,.0015)
    # Three exposed edges, each with mortar backing and staggered brick face.
    B('外沿灰缝',(.238,4.1,.32),(7.95,-1.4,.20),mortar,0)
    B('外沿土衬',(.34,4.4,.10),(7.94,-1.4,-.01),stone)
    for y in [-3.45,.65]:
        B('横沿灰缝'+str(y),(2.4,.238,.32),(6.6,y,.20),mortar,0)
        B('横沿土衬'+str(y),(2.7,.34,.10),(6.75,y,-.01),stone)
    for r in range(4):
        z=.08+r*.08
        for i,(a,b) in enumerate(intervals(-3.3,.5,.44,.22*(r%2))):
            B(f'外台帮_{r}_{i}',(.24,b-a,.076),(7.95,(a+b)/2,z),wall,.001)
        for y in [-3.45,.65]:
            for i,(a,b) in enumerate(intervals(5.4,7.8,.44,.22*(r%2))):
                B(f'横台帮_{y}_{r}_{i}',(b-a,.24,.076),((a+b)/2,y,z),wall,.001)
    for y in [-3.45,.65]:
        B('角石'+str(y),(.298,.298,.42),(7.95,y,.15),stone,.004)
        B('角压顶'+str(y),(.298,.298,.12),(7.95,y,.42),stone,.007)
        for i,(a,b) in enumerate(intervals(5.4,7.8,1.2,gap=.003)):
            B(f'横阶条_{y}_{i}',(b-a,.3,.12),((a+b)/2,y,.42),stone,.007)
    for i,(a,b) in enumerate(intervals(-3.3,.5,.95,gap=.003)):
        B(f'外阶条_{i}',(.3,b-a,.12),(7.95,(a+b)/2,.42),stone,.007)
    # Low pavilion frame, independent from the taller main house.
    for x in [5.75,7.65]:
        for y in [-2.95,.15]:
            clone(base,f'SIDE_{label}_柱础_{x}_{y}',(sign*x,y,.54))
            clone(post,f'SIDE_{label}_木柱_{x}_{y}',(sign*x,y,.60),(.86,.86,2.65/3.2))
    for y in [-2.95,.15]:beam(f'SIDE_{label}_横枋_{y}',(sign*5.75,y,3.11),(sign*7.65,y,3.11))
    for x in [5.75,7.65]:beam(f'SIDE_{label}_纵枋_{x}',(sign*x,-2.95,3.25),(sign*x,.15,3.25))

ground=bpy.data.objects['CONTEXT_地面']
ground.data=ground.data.copy()
for v in ground.data.vertices:v.co.x*=1.28
for uv in ground.data.uv_layers:
    for item in uv.data:item.uv.x*=1.28
ground.data.update()
scene['side_terraces_note']='左右对称建模假设：每侧外扩2.7m，进深4.4m，台面高0.48m；亭廊柱高2.65m。屋顶与栏杆待建，非测绘复原。'
cam=scene.camera;cam.location=(17,-23,14)
cam.rotation_euler=(Vector((0,-.5,1.3))-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=Vector((0,-.5,1.5));r.view_distance=22
            r.view_rotation=cam.rotation_euler.to_quaternion()
bpy.context.view_layer.update()
assert len([o for o in group.objects if '_柱础_' in o.name])==8
assert len([o for o in group.objects if '_木柱_' in o.name])==8
bpy.ops.wm.save_as_mainfile(filepath=path)
print('ADDED',len(group.objects),'components; side platforms flush at z=0.48; saved',path)
