import bpy, os, sys, math
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box, beam, mesh, material
path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not bpy.data.scenes.get('窗棂样板_参考图右下')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_lattice_sample.blend'),copy=True)
main=bpy.context.scene
sc=bpy.data.scenes.new('窗棂样板_参考图右下')
bpy.context.window.scene=sc
col=bpy.data.collections.new('样板_折线竖棂卷花');sc.collection.children.link(col)
stage=bpy.data.collections.new('样板_展示灯光');sc.collection.children.link(stage)
green=material('SAMPLE_旧绿漆木',(.055,.073,.024),.86)
n,l=green.node_tree.nodes,green.node_tree.links
bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
noise=next(x for x in n if x.type=='TEX_NOISE');noise.inputs['Scale'].default_value=19
r=n.new('ShaderNodeValToRGB');r.color_ramp.elements[0].color=(.019,.031,.011,1);r.color_ramp.elements[0].position=.28
r.color_ramp.elements[-1].color=(.15,.14,.048,1);r.color_ramp.elements[-1].position=.78
l.new(noise.outputs['Fac'],r.inputs[0]);l.new(r.outputs[0],bs.inputs['Base Color'])
lining=material('SAMPLE_暖黄褐衬底',(.30,.245,.12),.95)
edge=material('SAMPLE_线脚磨损',(.115,.132,.039),.87)
W=1.12;H=1.12
def pos(u,v,y=-.03):return ((u-.5)*W,y,v*H+.12)
def line(name,pts,w=.012,depth=.023,y=-.034,mat=green):
    for i in range(len(pts)-1):
        beam(name+'_'+str(i),pos(*pts[i],y),pos(*pts[i+1],y),w,depth,mat,col)
def frame(name,u0,v0,u1,v1,w,depth,y,mat):
    line(name,[(u0,v0),(u1,v0),(u1,v1),(u0,v1),(u0,v0)],w,depth,y,mat)
box('可隐藏衬底',pos(.5,.5,.035),(W,.018,H),lining,col,.004)
frame('外框',-.055,-.055,1.055,1.055,.066,.080,.004,green)
frame('中层线脚',-.016,-.016,1.016,1.016,.027,.047,-.032,edge)
frame('内口细线',.018,.018,.982,.982,.012,.032,-.051,green)

# Manually interpreted paths from the unobscured lower-right panel, not random lattice.
# Three linked stepped frames surround the long central vertical field.
for i,c in enumerate([.19,.50,.81]):
    a,b=c-.125,c+.125
    frame('外围折框'+str(i),a,.155,b,.845,.012,.023,-.043,green)
    line('上沿折返'+str(i),[(c-.19,.925),(c-.19,.86),(a,.86),(a,.775),(b,.775),(b,.86),(c+.19,.86),(c+.19,.925)],.012,.023,-.046)
    line('下沿折返'+str(i),[(c-.19,.075),(c-.19,.14),(a,.14),(a,.225),(b,.225),(b,.14),(c+.19,.14),(c+.19,.075)],.012,.023,-.046)
    line('顶底短接'+str(i),[(c,.925),(c,.975)],.011,.022,-.043)
    line('底短接'+str(i),[(c,.025),(c,.075)],.011,.022,-.043)
line('上贯通横棂',[(.025,.735),(.975,.735)],.012,.027,-.055)
line('下贯通横棂',[(.025,.265),(.975,.265)],.012,.027,-.055)
xs=[.10,.20,.30,.40,.50,.60,.70,.80,.90]
for i,x in enumerate(xs):
    line('细长竖棂'+str(i),[(x,.205),(x,.795)],.010,.024,-.055)

def curl(name,x,z,sx,sz):
    # Small hooked scroll curls back toward its stem, with a short straight neck.
    pts=[(x,z),(x+sx*.018,z),(x+sx*.027,z+sz*.005)]
    for j in range(25):
        t=j/24;ang=-math.pi/2+t*math.pi*1.65
        radius=.016*(1-.6*t)
        pts.append((x+sx*(.026+radius*math.cos(ang)),z+sz*(.019+radius*math.sin(ang))))
    vs=[];fs=[];N=8
    for i,(u,v) in enumerate(pts):
        before=Vector(pts[max(0,i-1)]);after=Vector(pts[min(len(pts)-1,i+1)])
        tangent=(after-before).normalized();perp=Vector((-tangent.y,tangent.x))
        for j in range(N):
            a=j*math.tau/N;q=Vector((u,v))+perp*(.0033*math.cos(a))
            vs.append(pos(q.x,q.y,-.071+.0037*math.sin(a)))
    for i in range(len(pts)-1):
        for j in range(N):fs.append((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j))
    fs += [tuple(reversed(range(N))),tuple(range((len(pts)-1)*N,len(pts)*N))]
    o=mesh(name,vs,fs,edge,col)
    for p in o.data.polygons:p.use_smooth=True
for i,x in enumerate(xs):
    levels=[.39,.61] if i%2==0 else [.285,.715]
    for z in levels:
        for sx in [-1,1]:curl(f'双卷花_{i}_{z}_{sx}',x,z,sx,1 if z<.5 else -1)

sc.world=bpy.data.worlds.new('样板柔光环境');sc.world.use_nodes=True
bg=next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND')
bg.inputs['Color'].default_value=(.18,.18,.15,1);bg.inputs['Strength'].default_value=.4
for name,loc,power,size in [('主光',(-1.4,-2.2,2.7),100,2),('补光',(1.7,-1.2,1.3),45,1.6)]:
    d=bpy.data.lights.new('样板_'+name,'AREA');d.energy=power;d.size=size
    o=bpy.data.objects.new('样板_'+name,d);stage.objects.link(o);o.location=loc
    o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('样板正面');camdata.type='ORTHO';camdata.ortho_scale=1.53
cam=bpy.data.objects.new('样板正面',camdata);stage.objects.link(cam);cam.location=(0,-4,.68)
cam.rotation_euler=(Vector((0,0,.68))-cam.location).to_track_quat('-Z','Y').to_euler();sc.camera=cam
sc.render.engine=main.render.engine;sc.render.resolution_x=1100;sc.render.resolution_y=1150;sc.render.resolution_percentage=100
sc.render.filepath=os.path.join(os.path.dirname(path),'lattice_reference_sample.png')
sc['reference']='用户14.48.43截图右下窗格：手工解释折线、竖棂与卷曲，遮挡处按重复关系简化；不声称逐像素复原。'
sc['sample_only']='独立样板场景，主房屋门窗未替换；衬底可隐藏以查看真实透空木棂。'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            rr=area.spaces.active.region_3d;rr.view_location=Vector((0,0,.68));rr.view_distance=2.1;rr.view_rotation=cam.rotation_euler.to_quaternion()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=path)
print('SAMPLE SAVED',len(col.objects),'parts; main house untouched; separate scene in same master')
