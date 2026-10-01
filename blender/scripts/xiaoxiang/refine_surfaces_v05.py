import bpy, os, random, math, json
from mathutils import Vector
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'xiaoxiang_platform_v04_masonry.blend'))
random.seed(205)
scene=bpy.context.scene

for name in ('MAT_廊面青砖','MAT_台帮青砖块','MAT_青灰石_微风化','MAT_柱础青石'):
    mat=bpy.data.materials[name]; n=mat.node_tree.nodes;l=mat.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    brick='青砖' in name
    coords=n.new('ShaderNodeTexCoord')
    grain=n.new('ShaderNodeTexNoise');grain.name='细颗粒_真实尺度'
    grain.inputs['Scale'].default_value=210 if brick else 145
    grain.inputs['Detail'].default_value=3
    l.new(coords.outputs['Object'],grain.inputs['Vector'])
    pores=n.new('ShaderNodeTexNoise');pores.name='烧制孔隙' if brick else '石材细孔'
    pores.inputs['Scale'].default_value=65 if brick else 90
    pores.inputs['Detail'].default_value=2
    l.new(coords.outputs['Object'],pores.inputs['Vector'])
    pores_ramp=n.new('ShaderNodeValToRGB')
    pores_ramp.color_ramp.elements[0].position=.34
    pores_ramp.color_ramp.elements[1].position=.49
    l.new(pores.outputs['Fac'],pores_ramp.inputs[0])
    previous=bs.inputs['Normal'].links[0].from_socket
    bump=n.new('ShaderNodeBump');bump.name='颗粒微表面'
    bump.inputs['Strength'].default_value=.48 if brick else .36
    bump.inputs['Distance'].default_value=.0018 if brick else .0012
    l.new(grain.outputs['Fac'],bump.inputs['Height']);l.new(previous,bump.inputs['Normal'])
    pit=n.new('ShaderNodeBump');pit.name='细孔凹陷'
    pit.inputs['Strength'].default_value=.25
    pit.inputs['Distance'].default_value=.001
    l.new(pores_ramp.outputs['Color'],pit.inputs['Height']);l.new(bump.outputs[0],pit.inputs['Normal'])
    l.new(pit.outputs[0],bs.inputs['Normal'])
    cloud=n.new('ShaderNodeTexNoise');cloud.name='表面自然色泽变化'
    cloud.inputs['Scale'].default_value=7 if brick else 3
    cloud.inputs['Detail'].default_value=4
    l.new(coords.outputs['Object'],cloud.inputs['Vector'])
    tint=n.new('ShaderNodeValToRGB')
    tint.color_ramp.elements[0].color=(.48,.53,.55,1) if brick else (.65,.68,.7,1)
    tint.color_ramp.elements[1].color=(1,.93,.82,1) if brick else (1,.98,.92,1)
    l.new(cloud.outputs['Fac'],tint.inputs[0])
    old=bs.inputs['Base Color'].links[0].from_socket
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.65
    l.new(old,mix.inputs[1]);l.new(tint.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],bs.inputs['Base Color'])
    # Broaden the already linked per-block variation, keeping it subtle within each family.
    for node in n:
        if node.type=='MAP_RANGE' and node.inputs['Value'].is_linked and node.inputs['Value'].links[0].from_node.type=='OBJECT_INFO':
            node.inputs['To Min'].default_value=.60 if brick else .78
            node.inputs['To Max'].default_value=1.13 if brick else 1.07
    rough=n.new('ShaderNodeMapRange');rough.name='粗糙度斑驳'
    rough.inputs['To Min'].default_value=.70 if brick else .53
    rough.inputs['To Max'].default_value=.98 if brick else .88
    l.new(cloud.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs['Result'],bs.inputs['Roughness'])

# Mortar has a granular, softly recessed surface rather than a perfect flat stripe.
mat=bpy.data.materials['MAT_灰缝_灰砂色'];n=mat.node_tree.nodes;l=mat.node_tree.links
bs=n.get('Principled BSDF');tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise')
noise.inputs['Scale'].default_value=180
l.new(tc.outputs['Object'],noise.inputs['Vector'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.4;bump.inputs['Distance'].default_value=.0015
l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
bs.inputs['Base Color'].default_value=(.105,.11,.10,1)

# Geometric variation is millimetric so joints and load-bearing contacts stay plausible.
wear=bpy.data.textures.new('石材磨边_微起伏',type='CLOUDS');wear.noise_scale=.045;wear.noise_depth=2
count=0
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    if obj.name.startswith(('BRICK_','PAVING_')):
        if obj.name.startswith('PAVING_'):
            obj.location.z+=random.uniform(-.0005,.0012)
            obj.rotation_euler.x=random.uniform(-.001,.001)
            obj.rotation_euler.y=random.uniform(-.001,.001)
        else:
            obj.location.z+=random.uniform(-.0004,.0004)
        for mod in obj.modifiers:
            if mod.type=='BEVEL':mod.width=random.uniform(.0012,.0028);mod.segments=3
        # Small variations in joints without opening deep gaps.
        obj.scale.x=random.uniform(.997,1.001)
        obj.scale.y=random.uniform(.997,1.001)
        count+=1
    if obj.name.startswith(('EDGE_','STEP_','COLBASE_','CORNER_')):
        for mod in obj.modifiers:
            if mod.type=='BEVEL':mod.width=random.uniform(.004,.007);mod.segments=3
        sub=obj.modifiers.new('磨损表面细分','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2;sub.render_levels=2
        dis=obj.modifiers.new('石面毫米级磨损','DISPLACE');dis.texture=wear;dis.texture_coords='LOCAL';dis.strength=.0018;dis.mid_level=.5

scene['surface_note']='v05: user colour maps retained; procedural grain, pores, roughness variation, per-block tones, small stone edge wear. Not measured material maps.'
def camera(loc,target,lens):
    scene.camera.location=loc;scene.camera.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();scene.camera.data.lens=lens
camera((12,-14,10),(0,-.3,.24),48)
target=os.path.join(OUT,'xiaoxiang_platform_v05_surfaces.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v05_overview.png');bpy.ops.render.render(write_still=True)
camera((-3.2,-5.8,1.05),(-1.6,-3.35,.38),60)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v05_detail.png');bpy.ops.render.render(write_still=True)
camera((-4,-3.4,1.15),(-4.5,-2.45,.49),62)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v05_column_detail.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=target)
assert bpy.data.materials['MAT_廊面青砖'].node_tree.nodes.get('颗粒微表面')
assert len([i for i in bpy.data.images if i.packed_file])>=2
print('VERIFIED',target,'varied brick objects',count)
