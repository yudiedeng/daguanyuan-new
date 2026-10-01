import bpy, os, random
from mathutils import Vector
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'xiaoxiang_platform_v07_aged.blend'))
scene=bpy.context.scene
ground=bpy.data.objects['CONTEXT_地面']
mat=bpy.data.materials.new('MAT_压实泥土_灰褐')
mat.diffuse_color=(.15,.105,.062,1);mat.use_nodes=True
n,l=mat.node_tree.nodes,mat.node_tree.links
bs=n.get('Principled BSDF');bs.inputs['Roughness'].default_value=.95
tc=n.new('ShaderNodeTexCoord')
macro=n.new('ShaderNodeTexNoise');macro.inputs['Scale'].default_value=1.5;macro.inputs['Detail'].default_value=4
l.new(tc.outputs['Object'],macro.inputs['Vector'])
ramp=n.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(.045,.032,.022,1)
ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.23,.17,.105,1)
l.new(macro.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
prev=None
for scale,dist,strength in [(13,.018,.48),(150,.002,.58)]:
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=scale;noise.inputs['Detail'].default_value=3
    l.new(tc.outputs['Object'],noise.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=dist;bump.inputs['Strength'].default_value=strength
    l.new(noise.outputs['Fac'],bump.inputs['Height'])
    if prev:l.new(prev,bump.inputs['Normal'])
    prev=bump.outputs[0]
l.new(prev,bs.inputs['Normal'])
ground.data.materials.clear();ground.data.materials.append(mat)
# Retain broad terrain dimensions, replace the perfectly flat top with a shallow grid.
bpy.data.objects.remove(ground,do_unlink=True)
verts=[];faces=[];nx=170;ny=140
random.seed(808)
for j in range(ny+1):
    y=-6.8+j*.1
    for i in range(nx+1):
        x=-8.5+i*.1
        # Soil stays at or below the footing contact height.
        z=-.003+random.uniform(-.004,.002)
        verts.append((x,y,z))
for j in range(ny):
    for i in range(nx):
        k=j*(nx+1)+i;faces.append((k,k+1,k+nx+2,k+nx+1))
mesh=bpy.data.meshes.new('EARTH_微起伏');mesh.from_pydata(verts,[],faces);mesh.update()
obj=bpy.data.objects.new('CONTEXT_地面',mesh);bpy.data.collections['90_环境参照'].objects.link(obj);mesh.materials.append(mat)
for p in mesh.polygons:p.use_smooth=True
solid=obj.modifiers.new('土层厚度','SOLIDIFY');solid.thickness=.08
pebmat=bpy.data.materials.new('MAT_泥土碎石');pebmat.diffuse_color=(.19,.16,.115,1);pebmat.use_nodes=True
pbs=pebmat.node_tree.nodes.get('Principled BSDF');pbs.inputs['Base Color'].default_value=pebmat.diffuse_color;pbs.inputs['Roughness'].default_value=.96
for i in range(180):
    x=random.uniform(-8.2,8.2);y=random.uniform(-6.5,6.8)
    if abs(x)<5.5 and -4.7<y<3.7:continue
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=(x,y,0))
    ob=bpy.context.object;ob.name=f'EARTH_细碎石_{i}'
    s=random.uniform(.008,.025);ob.scale=(s,s*random.uniform(.6,1.3),s*.35)
    ob.data.materials.append(pebmat)
    for c in list(ob.users_collection):c.objects.unlink(ob)
    bpy.data.collections['90_环境参照'].objects.link(ob)
scene['ground_note']='Grey-brown compacted earth with procedural grain, millimetric relief and sparse small pebbles'
target=os.path.join(OUT,'xiaoxiang_platform_v08_earth.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v08_overview.png');bpy.ops.render.render(write_still=True)
scene.camera.location=(-4.8,-7.5,2.25);scene.camera.rotation_euler=(Vector((-1.5,-4.2,.05))-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.lens=48
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v08_earth_detail.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=target)
assert bpy.data.objects['CONTEXT_地面'].data.materials[0].name=='MAT_压实泥土_灰褐'
assert scene is not None
print('VERIFIED_EARTH',target)
