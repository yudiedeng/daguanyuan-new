import bpy,math
s=bpy.context.scene;c=bpy.data.collections['样板V2_清晰图描形']
old=c.objects['V2_可隐藏绢底']
assert not bpy.data.objects.get('V7_银红霞影纱')
m=bpy.data.materials.new('SAMPLE7_银红软烟罗_经纬透纱');m.use_nodes=True
m.surface_render_method='DITHERED'
m.diffuse_color=(.55,.23,.29,.65)
n,l=m.node_tree.nodes,m.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
bs.inputs['Roughness'].default_value=.52
bs.inputs['Base Color'].default_value=(.55,.23,.29,1)
if 'Sheen Weight' in bs.inputs:
    bs.inputs['Sheen Weight'].default_value=.48
    bs.inputs['Sheen Roughness'].default_value=.6
    bs.inputs['Sheen Tint'].default_value=(.86,.65,.68,1)
coord=n.new('ShaderNodeTexCoord')
sep=n.new('ShaderNodeSeparateXYZ');l.new(coord.outputs['Object'],sep.inputs[0])
def mathnode(op,a,b=None):
    node=n.new('ShaderNodeMath');node.operation=op
    if hasattr(a,'node'):l.new(a,node.inputs[0])
    else:node.inputs[0].default_value=a
    if b is not None:
        if hasattr(b,'node'):l.new(b,node.inputs[1])
        else:node.inputs[1].default_value=b
    return node.outputs[0]
strands=[]
for axis,pitch in [('X',.0018),('Z',.00165)]:
    phase=mathnode('MULTIPLY',sep.outputs[axis],math.tau/pitch)
    wave=mathnode('SINE',phase)
    mask=n.new('ShaderNodeMapRange');mask.label='细经纬纱线_'+axis
    mask.inputs['From Min'].default_value=.35;mask.inputs['From Max'].default_value=.85
    mask.inputs['To Min'].default_value=0;mask.inputs['To Max'].default_value=1
    l.new(wave,mask.inputs['Value']);strands.append(mask.outputs['Result'])
weave=mathnode('MAXIMUM',*strands)
coverage=mathnode('MULTIPLY_ADD',weave,.95)
coverage.node.inputs[2].default_value=.025
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.00010
l.new(weave,bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=70;noise.inputs['Detail'].default_value=2
l.new(coord.outputs['Object'],noise.inputs['Vector'])
tint=n.new('ShaderNodeValToRGB');tint.label='银红丝线轻微色差'
tint.color_ramp.elements[0].color=(.36,.115,.165,1)
tint.color_ramp.elements[1].color=(.68,.34,.40,1)
l.new(noise.outputs['Fac'],tint.inputs[0]);l.new(tint.outputs[0],bs.inputs['Base Color'])
trans=n.new('ShaderNodeBsdfTransparent')
mix=n.new('ShaderNodeMixShader');l.new(coverage,mix.inputs[0]);l.new(trans.outputs[0],mix.inputs[1]);l.new(bs.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
# Single thin sheet, not an opaque double-sided slab. Tiny tension undulations only.
nx,nz=80,80;vs=[];fs=[]
for j in range(nz+1):
    v=j/nz
    for i in range(nx+1):
        u=i/nx;x=(u-.5)*1.09725;z=.120+v*1.008
        y=.004+.0008*math.sin(math.pi*u)*math.sin(math.pi*v)*math.sin(u*22+v*7)
        vs.append((x,y,z))
for j in range(nz):
    for i in range(nx):
        a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
me=bpy.data.meshes.new('绷纱薄面');me.from_pydata(vs,[],fs);me.update()
o=bpy.data.objects.new('V7_银红霞影纱',me);c.objects.link(o);me.materials.append(m)
for p in me.polygons:p.use_smooth=True
old.hide_render=True;old.hide_set(True)
o['reference']='红楼梦第四十回：银红软烟罗又称霞影纱。配色为视觉诠释，非考据色值。'
o['weave']='1.8 / 1.65毫米细经纬，纱孔透明、丝线柔光，微起伏绷纱。'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Silver-rose gauze installed; opaque backing hidden and recoverable.')
