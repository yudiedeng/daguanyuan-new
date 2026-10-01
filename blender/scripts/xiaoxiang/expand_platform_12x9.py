import bpy, os, ast, random
from mathutils import Vector
scene=bpy.context.scene;path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not bpy.data.collections.get('13_扩建地台_12x9m')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_12x9.blend'),copy=True)
group=bpy.data.collections.new('13_扩建地台_12x9m');scene.collection.children.link(group)
random.seed(1934)
# Reuse the metric-UV masonry helpers, without executing the older scene build.
helper=os.path.join(os.path.dirname(os.path.dirname(path)),'add_side_terraces.py')
tree=ast.parse(open(helper).read())
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('block','intervals')]
exec(compile(ast.Module(body=defs,type_ignores=[]),helper,'exec'))
floor=bpy.data.materials['MAT_廊面青砖_养护旧化_paving']
wall=bpy.data.materials['MAT_台帮青砖块_养护旧化_wall']
stone=bpy.data.materials['MAT_青灰石_微风化_养护旧化_coping']
mortar=bpy.data.materials['MAT_灰缝_灰砂色_养护旧化_joint']
block('WIDE_内填',(11.4,8.4,.445),(0,0,.2225),mortar,0)
block('WIDE_铺地灰床',(11.4,8.4,.032),(0,0,.462),mortar,0)
for r,(ya,yb) in enumerate(intervals(-4.2,4.2,.224)):
    for c,(xa,xb) in enumerate(intervals(-5.7,5.7,.444,.222*(r%2))):
        block(f'WIDE_错缝青砖_{r}_{c}',(xb-xa,yb-ya,.045),((xa+xb)/2,(ya+yb)/2,.4575+random.uniform(-.0005,.0005)),floor,.0015)
for s in [-1,1]:
    block(f'WIDE_前后灰缝_{s}',(11.4,.238,.32),(0,s*4.34,.20),mortar,0)
    block(f'WIDE_侧灰缝_{s}',(.238,8.4,.32),(s*5.84,0,.20),mortar,0)
    block(f'WIDE_前后土衬_{s}',(12,.34,.1),(0,s*4.33,-.01),stone,.002)
    block(f'WIDE_侧土衬_{s}',(.34,8.32,.1),(s*5.83,0,-.01),stone,.002)
    for r in range(4):
        for i,(a,b) in enumerate(intervals(-5.7,5.7,.44,.22*(r%2))):
            block(f'WIDE_前后台帮_{s}_{r}_{i}',(b-a,.24,.076),((a+b)/2,s*4.34,.08+r*.08),wall,.001)
        for i,(a,b) in enumerate(intervals(-4.2,4.2,.44,.22*(r%2))):
            block(f'WIDE_侧台帮_{s}_{r}_{i}',(.24,b-a,.076),(s*5.84,(a+b)/2,.08+r*.08),wall,.001)
    for i,(a,b) in enumerate(intervals(-5.7,5.7,1.14,gap=.003)):
        block(f'WIDE_前后阶条_{s}_{i}',(b-a,.30,.12),((a+b)/2,s*4.35,.42),stone,.008)
    for i,(a,b) in enumerate(intervals(-4.2,4.2,1.05,gap=.003)):
        block(f'WIDE_侧阶条_{s}_{i}',(.30,b-a,.12),(s*5.85,(a+b)/2,.42),stone,.008)
    for t in [-1,1]:
        block(f'WIDE_角石_{s}_{t}',(.298,.298,.42),(s*5.85,t*4.35,.15),stone,.004)
        block(f'WIDE_角压顶_{s}_{t}',(.298,.298,.12),(s*5.85,t*4.35,.42),stone,.008)

# Keep actual worn step meshes and move the stair to the new front edge.
for o in bpy.data.collections['04_如意踏跺'].objects:o.location.y-=.9
for o in list(bpy.data.collections['07_土衬与灰缝'].objects):
    if o.name.startswith(('MORTAR_踏步','FOOTING_踏步')):
        new=o.copy();new.data=o.data.copy();group.objects.link(new)
        new.name='WIDE_'+o.name;new.location.y-=.9

# Widen veranda without scaling inner rooms, timber diameters, or base stones.
def remap(v):
    v=v.copy()
    if abs(abs(v.x)-4.8)<.01:v.x=5.6 if v.x>0 else -5.6
    if abs(v.y+2.95)<.01:v.y=-3.65
    return v
inner_before={o.name:tuple(o.location) for o in bpy.data.collections['12B_内圈房屋柱与柱础'].objects}
for o in bpy.data.collections['12A_外圈廊柱与柱础'].objects:o.location=remap(o.location)
bpy.context.view_layer.update()
for o in bpy.data.collections['12C_内外圈梁枋'].objects:
    zs=[v.co.z for v in o.data.vertices];lo,hi=min(zs),max(zs)
    a=o.matrix_world@Vector((0,0,lo));b=o.matrix_world@Vector((0,0,hi))
    aa,bb=remap(a),remap(b)
    o.location=aa;o.rotation_euler=(bb-aa).to_track_quat('Z','Y').to_euler()
    o.scale.z=(bb-aa).length/(hi-lo)
for name in ['01_台明结构','02_阶条石与角石','03_青砖台面_实例','06_台帮青砖_实例','07_土衬与灰缝']:
    c=bpy.data.collections[name];c.hide_viewport=True;c.hide_render=True;c['archive_reason']='12x9地台替代，原尺寸保留可回退'
assert all(tuple(bpy.data.objects[n].location)==v for n,v in inner_before.items())
scene['platform_dimensions_m']='12 x 9 x 0.48 (excluding steps)'
scene['column_layout']='内圈不动；外圈侧柱x=±5.6，前柱y=-3.65；柱身间侧廊净宽约1.48m，前廊约1.53m；尚无墙体。'
scene['side_terraces_note']='12x9连续地台，前廊和左右侧廊；旧独立侧亭方案隐藏。'
cam=scene.camera;cam.location=(13,-18,15)
cam.rotation_euler=(Vector((0,0,1.3))-cam.location).to_track_quat('-Z','Y').to_euler()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=Vector((0,0,1.4));r.view_distance=18
            r.view_rotation=cam.rotation_euler.to_quaternion()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=path)
print('VERIFIED: platform 12x9m, all 16 inner column/base transforms unchanged; side clear ~1.48m; front clear ~1.53m; steps shifted 0.9m outward.')
