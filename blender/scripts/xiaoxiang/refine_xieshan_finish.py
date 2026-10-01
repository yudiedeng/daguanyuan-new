import bpy, os, sys, math
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import *
assert not bpy.data.collections.get('28_砖砌脊与卷草收头')
col=collection('28_砖砌脊与卷草收头')
old=bpy.data.collections['24_九脊与檐口']
for o in old.objects:
    if o.name.startswith(('XS_正脊','XS_垂脊','XS_戗脊')):o.hide_render=True;o.hide_set(True)
ridge=bpy.data.materials['XS_屋脊青灰']
def sweep(name,pts,width=.23):
    # A masonry rib and rounded cap, not a tube with exposed circular ends.
    profile=[(-.5,0),(.5,0),(.5,.10),(.36,.12),(.30,.17),(.15,.195),(0,.205),(-.15,.195),(-.30,.17),(-.36,.12),(-.5,.10)]
    vs=[];fs=[];N=len(profile)
    for i,p in enumerate(pts):
        p=Vector(p)
        v=Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(0,i-1)])
        perp=Vector((-v.y,v.x,0)).normalized()
        for x,z in profile:vs.append(tuple(p+perp*x*width+Vector((0,0,z+.015))))
    for i in range(len(pts)-1):
        for j in range(N):fs.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
    fs.extend([tuple(reversed(range(N))),tuple(range((len(pts)-1)*N,len(pts)*N))])
    o=mesh(name,vs,fs,ridge,col,.003);o['ridge_family']=name
    return o
sweep('XS2_正脊',[(x,YC,7.69+.12*(abs(x)/4.16)**8) for x in [-4.16+i*8.32/48 for i in range(49)]],.28)
for sx in [-1,1]:
    for sy in [-1,1]:
        sweep(f'XS2_垂脊_{sx}_{sy}',[frontpoint(sx*G,D*i/24,sy) for i in range(25)])
        sweep(f'XS2_戗脊_{sx}_{sy}',[frontpoint(sx*(G+(E-G)*i/28),D+(DE-D)*i/28,sy) for i in range(29)],.24)
    # Modest solid rolled-grass end ornament, deliberately no imperial beast procession.
    outline=[(-.20,0),(.21,0),(.29,.11),(.37,.31),(.38,.49),(.32,.63),(.19,.69),(.08,.64),(.055,.53),(.10,.46),(.19,.48),(.22,.54),(.27,.48),(.25,.36),(.15,.25),(-.03,.18),(-.20,.15)]
    vs=[(sx*(4.05+x),YC+y,7.86+z) for y in [-.12,.12] for x,z in outline]
    N=len(outline);fs=[tuple(reversed(range(N))),tuple(range(N,N*2))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
    mesh('XS2_卷草脊端_'+str(sx),vs,fs,ridge,col,.015)

for i in range(7):
    m=bpy.data.materials['XS_灰瓦色差_'+str(i)];n,l=m.node_tree.nodes,m.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    bs.inputs['Roughness'].default_value=.93
    bs.inputs['Specular IOR Level'].default_value=.20
    tex=next(x for x in n if x.type=='TEX_NOISE')
    ramp=n.new('ShaderNodeValToRGB')
    v=.031+i*.003
    ramp.color_ramp.elements[0].color=(v*.65,v*.75,v*.81,1)
    ramp.color_ramp.elements[1].color=(v*1.45,v*1.55,v*1.61,1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
bs=next(x for x in ridge.node_tree.nodes if x.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.050,.057,.054,1);bs.inputs['Roughness'].default_value=.93
scene=bpy.context.scene
lights=collection('Lighting_Camera')
for name,loc,energy,size in [('LIGHT_前廊柔光',(0,-11,7),1600,8),('LIGHT_山面柔光',(11,3,8),1100,7)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);lights.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((0,0,2.7))-o.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.lens=43
scene['timber_stage']='完整视觉模型：柱梁檩椽、灰瓦歇山顶、砖墙白灰、格扇门窗与廊栏；按参考资料解释建模，非测绘复原或施工模型。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Refined nine masonry ridges, matte clay tiles and facade lighting.')
