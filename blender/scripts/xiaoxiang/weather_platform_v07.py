import bpy, os, math
from mathutils import Vector
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'xiaoxiang_platform_v06_rounded.blend'))
scene=bpy.context.scene

def weather_material(original, role):
    mat=original.copy();mat.name=original.name+'_养护旧化_'+role
    n,l=mat.node_tree.nodes,mat.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    pos=n.new('ShaderNodeNewGeometry')
    sep=n.new('ShaderNodeSeparateXYZ');l.new(pos.outputs['Position'],sep.inputs[0])
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=9;noise.inputs['Detail'].default_value=4
    l.new(pos.outputs['Position'],noise.inputs['Vector'])
    def mathnode(op,a,b):
        node=n.new('ShaderNodeMath');node.operation=op
        for i,val in enumerate((a,b)):
            if isinstance(val,(int,float)):node.inputs[i].default_value=val
            else:l.new(val,node.inputs[i])
        return node.outputs[0]
    def ramp(val,lo,hi):
        node=n.new('ShaderNodeMapRange');node.clamp=True
        node.inputs['From Min'].default_value=lo;node.inputs['From Max'].default_value=hi
        l.new(val,node.inputs[0]);return node.outputs['Result']
    old=bs.inputs['Base Color'].links[0].from_socket if bs.inputs['Base Color'].is_linked else None
    if old is None:
        rgb=n.new('ShaderNodeRGB');rgb.outputs[0].default_value=bs.inputs['Base Color'].default_value;old=rgb.outputs[0]
    # Irregular damp rise depends on actual height above soil, not individual block coordinates.
    if role in ('wall','footing','steps'):
        height=mathnode('ADD',.085,mathnode('MULTIPLY',noise.outputs['Fac'],.14))
        damp=ramp(mathnode('SUBTRACT',height,sep.outputs['Z']),-.06,.08)
        amount=mathnode('MULTIPLY',damp,.58)
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';l.new(amount,mix.inputs[0]);l.new(old,mix.inputs[1]);mix.inputs[2].default_value=(.40,.43,.35,1);old=mix.outputs[0]
        # Sparse subdued olive moss, broken by fine noise.
        moss=mathnode('MULTIPLY',damp,ramp(noise.outputs['Fac'],.53,.72))
        moss=mathnode('MULTIPLY',moss,.62 if role!='steps' else .3)
        mix=n.new('ShaderNodeMixRGB');l.new(moss,mix.inputs[0]);l.new(old,mix.inputs[1]);mix.inputs[2].default_value=(.065,.09,.027,1);old=mix.outputs[0]
    if role=='column':
        grime=ramp(mathnode('SUBTRACT',.535,sep.outputs['Z']),0,.045)
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';l.new(mathnode('MULTIPLY',grime,.5),mix.inputs[0]);l.new(old,mix.inputs[1]);mix.inputs[2].default_value=(.42,.39,.30,1);old=mix.outputs[0]
    if role in ('coping','wall','joint'):
        mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(22,22,2)
        l.new(pos.outputs['Position'],mapping.inputs[0])
        streak=n.new('ShaderNodeTexNoise');streak.inputs['Scale'].default_value=1;streak.inputs['Detail'].default_value=2
        l.new(mapping.outputs[0],streak.inputs['Vector'])
        fac=mathnode('MULTIPLY',ramp(streak.outputs['Fac'],.42,.72),.22 if role!='joint' else .45)
        mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';l.new(fac,mix.inputs[0]);l.new(old,mix.inputs[1]);mix.inputs[2].default_value=(.40,.35,.27,1);old=mix.outputs[0]
    if role in ('steps','paving'):
        # Foot traffic follows a soft central strip, strongest on horizontal faces.
        nx=n.new('ShaderNodeSeparateXYZ');l.new(pos.outputs['Normal'],nx.inputs[0])
        central=mathnode('SUBTRACT',1,ramp(mathnode('ABSOLUTE',sep.outputs['X'],0),.25,1.2))
        top=ramp(nx.outputs['Z'],.7,1)
        worn=mathnode('MULTIPLY',central,top)
        worn=mathnode('MULTIPLY',worn,mathnode('ADD',.6,mathnode('MULTIPLY',noise.outputs['Fac'],.4)))
        rough=bs.inputs['Roughness'].links[0].from_socket
        mixrough=n.new('ShaderNodeMixRGB');l.new(mathnode('MULTIPLY',worn,.7),mixrough.inputs[0]);l.new(rough,mixrough.inputs[1]);mixrough.inputs[2].default_value=(.43,.43,.43,1)
        l.new(mixrough.outputs[0],bs.inputs['Roughness'])
        mix=n.new('ShaderNodeMixRGB');l.new(mathnode('MULTIPLY',worn,.10),mix.inputs[0]);l.new(old,mix.inputs[1]);mix.inputs[2].default_value=(.23,.235,.21,1);old=mix.outputs[0]
    l.new(old,bs.inputs['Base Color'])
    mat['weathering']='Maintained garden residence: restrained damp, dirt, wear by position'
    return mat

cache={}
for obj in bpy.data.objects:
    if obj.type!='MESH' or not obj.data.materials:continue
    role=next((role for prefix,role in [('BRICK_','wall'),('FOOTING_','footing'),('STEP_','steps'),('EDGE_','coping'),('CORNER_','wall'),('COLBASE_','column'),('PAVING_','paving'),('MORTAR_','joint')] if obj.name.startswith(prefix)),None)
    if not role:continue
    old=obj.data.materials[0];key=(old.name,role)
    if key not in cache:cache[key]=weather_material(old,role)
    obj.data.materials[0]=cache[key]
    if role=='steps':
        # Apply this asset's modifiers locally before shaping a shallow central foot-worn hollow.
        bpy.context.view_layer.objects.active=obj
        for mod in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        top=max(v.co.z for v in obj.data.vertices)
        for v in obj.data.vertices:
            wx=obj.location.x+v.co.x
            topmask=max(0,min(1,(v.co.z-top+.028)/.028))
            v.co.z-=.006*math.exp(-(wx/.62)**2)*topmask
        obj.data.update()

scene['weathering_note']='v07 maintained aged finish; central step wear up to 6mm; subdued irregular damp band, sparse moss, rain streaks and column foot dirt'
def camera(loc,target,lens):
    scene.camera.location=loc;scene.camera.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();scene.camera.data.lens=lens
camera((12,-14,10),(0,-.3,.24),48)
target=os.path.join(OUT,'xiaoxiang_platform_v07_aged.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v07_overview.png');bpy.ops.render.render(write_still=True)
camera((-3.2,-5.8,1.05),(-1.6,-3.35,.38),60)
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v07_detail.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=target)
assert len([im for im in bpy.data.images if im.packed_file])>=2
assert bpy.context.scene.get('weathering_note')
print('VERIFIED_AGED',target)
