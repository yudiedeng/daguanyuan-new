import bpy, os, math, random, json
from mathutils import Vector

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, 'xiaoxiang_platform_v03_textured.blend'))
random.seed(19)
scene = bpy.context.scene
brick = bpy.data.materials['MAT_台帮青砖块']
floor = bpy.data.materials['MAT_廊面青砖']
stone = bpy.data.materials['MAT_青灰石_微风化']
mortar = bpy.data.materials.new('MAT_灰缝_灰砂色')
mortar.diffuse_color = (.17,.18,.165,1)
mortar.use_nodes = True
bs = mortar.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value = mortar.diffuse_color
bs.inputs['Roughness'].default_value = .96

# Rebuild only the platform components in this new, isolated file.
for obj in list(bpy.data.objects):
    if obj.name.startswith(('PLATFORM_', 'EDGE_', 'CORNER_', 'PAVING_', 'BRICK_', 'STEP_', 'CONTEXT_苔痕')):
        bpy.data.objects.remove(obj, do_unlink=True)

def col(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
    return c

records = []
def block(name, dims, loc, mat, group, bevel=.002):
    x,y,z = (v/2 for v in dims)
    vertices = [(-x,-y,-z), (x,-y,-z), (x,y,-z), (-x,y,-z),
                (-x,-y,z), (x,-y,z), (x,y,z), (-x,y,z)]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col(group).objects.link(obj)
    obj.location = loc
    mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='UV_Metric_1m')
    ox,oy = random.uniform(0,2),random.uniform(0,2)
    for p in mesh.polygons:
        axis = max(range(3), key=lambda i: abs(p.normal[i]))
        a,b = [(1,2),(0,2),(0,1)][axis]
        for i in p.loop_indices:
            v = mesh.vertices[mesh.loops[i].vertex_index].co
            uv.data[i].uv = (v[a]+ox,v[b]+oy)
    if bevel:
        mod=obj.modifiers.new('细倒棱', 'BEVEL'); mod.width=bevel; mod.segments=2
    records.append({'name':name,'size':dims,'center':loc})
    return obj

def intervals(start,end,pitch,offset=0,gap=.004):
    cursor=start-offset
    while cursor < end-1e-8:
        lo,hi=max(start,cursor),min(end,cursor+pitch)
        if hi-lo > gap:
            yield lo+gap/2,hi-gap/2
        cursor += pitch

# Internal fill reaches the flooring bed. Brick wall is 240 mm thick.
block('PLATFORM_内填与铺地垫层',(10.23,6.63,.445),(0,0,.2225),mortar,'01_台明结构',0)
# Footing embeds beneath finished outdoor grade, 40 mm exposed.
for sy in (-1,1):
    block('FOOTING_前后土衬_'+str(sy),(10.8,.34,.10),(0,sy*3.43,-.01),stone,'07_土衬与灰缝',.002)
    block('MORTAR_前后台帮_'+str(sy),(10.14,.238,.32),(0,sy*3.438,.20),mortar,'07_土衬与灰缝',0)
for sx in (-1,1):
    block('FOOTING_两侧土衬_'+str(sx),(.34,6.52,.10),(sx*5.23,0,-.01),stone,'07_土衬与灰缝',.002)
    block('MORTAR_两侧台帮_'+str(sx),(.238,6.54,.32),(sx*5.238,0,.20),mortar,'07_土衬与灰缝',0)

# Four courses of staggered stretchers, with cut end units and filled 4 mm joints.
for row in range(4):
    z=.04+row*.08+.04
    for side in (-1,1):
        for i,(a,b) in enumerate(intervals(-5.06,5.06,.44, .22*(row%2))):
            block(f'BRICK_前后_{side}_R{row}_B{i}',(b-a,.24,.076),((a+b)/2,side*3.44,z),brick,'06_台帮青砖_实例',.001)
        for i,(a,b) in enumerate(intervals(-3.26,3.26,.44,.22*(row%2))):
            block(f'BRICK_两侧_{side}_R{row}_B{i}',(.24,b-a,.076),(side*5.24,(a+b)/2,z),brick,'06_台帮青砖_实例',.001)
for sx in (-1,1):
    for sy in (-1,1):
        block(f'CORNER_埋头角石_{sx}_{sy}',(.338,.338,.42),(sx*5.23,sy*3.43,.15),stone,'02_阶条石与角石',.003)

# Individually jointed coping blocks, including four square corner pieces.
for sx in (-1,1):
    for sy in (-1,1):
        block(f'EDGE_转角压顶_{sx}_{sy}',(.298,.298,.12),(sx*5.25,sy*3.45,.42),stone,'02_阶条石与角石',.003)
for side in (-1,1):
    for i,(a,b) in enumerate(intervals(-5.1,5.1,1.275,gap=.003)):
        block(f'EDGE_前后阶条_{side}_{i}',(b-a,.30,.12),((a+b)/2,side*3.45,.42),stone,'02_阶条石与角石',.003)
    for i,(a,b) in enumerate(intervals(-3.3,3.3,1.1,gap=.003)):
        block(f'EDGE_两侧阶条_{side}_{i}',(.30,b-a,.12),(side*5.25,(a+b)/2,.42),stone,'02_阶条石与角石',.003)

# Paving bed sits 2 mm below the brick surface; cut border bricks close the perimeter.
block('MORTAR_铺地灰床',(10.2,6.6,.032),(0,0,.462),mortar,'07_土衬与灰缝',0)
for row,(ya,yb) in enumerate(intervals(-3.3,3.3,.224,gap=.004)):
    for i,(xa,xb) in enumerate(intervals(-5.1,5.1,.444,.222*(row%2),gap=.004)):
        block(f'PAVING_错缝_R{row}_C{i}',(xb-xa,yb-ya,.045),((xa+xb)/2,(ya+yb)/2,.4575),floor,'03_青砖台面_实例',.001)

# Each step is a supported solid course assembled from several stone pieces.
for level,(width,depth) in enumerate(((3.6,.99),(3.0,.66),(2.4,.33))):
    z=level*.16+.08
    count=3 if level==0 else 2
    for i,(a,b) in enumerate(intervals(-width/2,width/2,width/count,gap=.003)):
        block(f'STEP_第{level+1}级_石件{i+1}',(b-a,depth,.16),((a+b)/2,-3.6-depth/2,z),stone,'04_如意踏跺',.003)
    block(f'MORTAR_踏步接缝填实{level}',(width-.004,depth-.004,.156),(0,-3.6-depth/2,z),mortar,'07_土衬与灰缝',0)
block('FOOTING_踏步埋地基础',(3.64,1.03,.06),(0,-4.095,-.03),mortar,'07_土衬与灰缝',.001)
ground=bpy.data.objects.get('CONTEXT_地面')
ground.location.z=-.04

scene['construction_note']='v04: 240mm brick wall, four staggered courses, filled 4mm joints, embedded footing, segmented coping and steps. Interpretive model, not surveyed restoration.'
scene['platform_dimensions_m']='10.8 x 7.2 x 0.48'
scene.render.resolution_x=1400;scene.render.resolution_y=1000
scene.render.resolution_percentage=100
def camera(loc,target,lens):
    scene.camera.location=loc
    scene.camera.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.lens=lens

camera((12,-14,10),(0,-.3,.24),48)
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            s=area.spaces.active;s.shading.type='MATERIAL';s.overlay.show_overlays=False
            s.region_3d.view_rotation=scene.camera.rotation_euler.to_quaternion()
            s.region_3d.view_location=Vector((0,0,.2));s.region_3d.view_distance=17
blend=os.path.join(OUT,'xiaoxiang_platform_v04_masonry.blend')
bpy.ops.wm.save_as_mainfile(filepath=blend)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v04_overview.png')
bpy.ops.render.render(write_still=True)
camera((-4.8,-7.5,1.65),(-1.6,-3.65,.27),55)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v04_detail.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=blend)
assert len([o for o in bpy.data.objects if o.name.startswith('STEP_')])==7
assert len([o for o in bpy.data.objects if o.name.startswith('EDGE_')])==32
assert all(o.data.uv_layers.get('UV_Metric_1m') for o in bpy.data.objects if o.name.startswith(('BRICK_','PAVING_','EDGE_','STEP_')))
assert len([im for im in bpy.data.images if im.packed_file])>=2
with open(os.path.join(OUT,'v04_verification.json'),'w') as f:
    json.dump({'blend_reopened':True,'packed_textures':True,'joint_m':.004,'wall_thickness_m':.24,'generated_components':len(records),'stone_step_pieces':7},f,indent=2)
print('VERIFIED',blend)
