import bpy
m=bpy.data.materials['SAMPLE2_深绿漆']
backup=m.copy();backup.name='ARCHIVE_墨绿漆_加深前'
n,l=m.node_tree.nodes,m.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
ramp=next(x for x in n if x.type=='VALTORGB')
ramp.color_ramp.elements[0].color=(.0045,.014,.008,1)
ramp.color_ramp.elements[1].color=(.019,.045,.025,1)
m.diffuse_color=(.011,.031,.017,1)
noise=next(x for x in n if x.type=='TEX_NOISE')
noise.inputs['Scale'].default_value=24
noise.inputs['Detail'].default_value=3.5
oldbump=next(x for x in n if x.type=='BUMP')
oldbump.inputs['Strength'].default_value=.12
oldbump.inputs['Distance'].default_value=.00025
# Subtle fine finish over slower variations in the old paint.
coord=n.new('ShaderNodeTexCoord');coord.label='漆面坐标'
stretch=n.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
stretch.inputs[1].default_value=(95,95,7)
l.new(coord.outputs['Object'],stretch.inputs[0])
grain=n.new('ShaderNodeTexNoise');grain.label='漆下细木纹'
grain.inputs['Scale'].default_value=5;grain.inputs['Detail'].default_value=2
l.new(stretch.outputs['Vector'],grain.inputs['Vector'])
fine=n.new('ShaderNodeBump');fine.label='细微木纹起伏'
fine.inputs['Strength'].default_value=.15;fine.inputs['Distance'].default_value=.00013
l.new(grain.outputs['Fac'],fine.inputs['Height']);l.new(oldbump.outputs['Normal'],fine.inputs['Normal'])
l.new(fine.outputs['Normal'],bs.inputs['Normal'])
rough=n.new('ShaderNodeMapRange');rough.label='旧漆柔光变化'
rough.inputs['From Min'].default_value=.15;rough.inputs['From Max'].default_value=.85
rough.inputs['To Min'].default_value=.48;rough.inputs['To Max'].default_value=.72
l.new(noise.outputs['Fac'],rough.inputs['Value']);l.new(rough.outputs['Result'],bs.inputs['Roughness'])
if 'Coat Weight' in bs.inputs:
    bs.inputs['Coat Weight'].default_value=.13
    bs.inputs['Coat Roughness'].default_value=.38
# Worn edges remain muted gold-brown, not bright metallic outlines.
g=bpy.data.materials['SAMPLE2_旧金褐线']
for node in g.node_tree.nodes:
    if node.type=='VALTORGB':
        node.color_ramp.elements[0].color=(.035,.032,.013,1)
        node.color_ramp.elements[-1].color=(.24,.18,.062,1)
bpy.context.scene['paint_finish']='墨绿压深约25%，微木纹凹凸、局部柔光与粗糙度变化；金褐磨边降亮度。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Dark green paint updated; previous green material preserved as archive; geometry unchanged.')
