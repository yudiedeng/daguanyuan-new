import bpy, os, sys, math
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import *
scene=bpy.context.scene;path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not bpy.data.collections.get('20_歇山_正身与山面梁架')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_xieshan.blend'),copy=True)
frame=collection('20_歇山_正身与山面梁架');walls=collection('21_围护_灰砖素墙');roof=collection('22_歇山_望板与山花')
wood=bpy.data.materials['MAT_暗褐旧木_顺纹']
brick=bpy.data.materials['MAT_台帮青砖块_养护旧化_wall']
stone=bpy.data.materials['MAT_青灰石_微风化_养护旧化_coping']
plaster=material('XS_旧白灰墙',(.57,.54,.46),.94)
gable=material('XS_山花深褐木',(.055,.033,.019),.84)
under=material('XS_望板暗木',(.055,.038,.024),.86)
old=bpy.data.collections['12C_内外圈梁枋'];old.hide_viewport=True;old.hide_render=True

# Rear veranda support completes the roof bearing ring; original inner room stays fixed.
outer=bpy.data.collections['12A_外圈廊柱与柱础']
for o in outer.objects:
    if abs(o.location.y-2.95)<.01:o.location.y=3.95
postsrc=bpy.data.objects['RING_外圈_木柱_01'];basesrc=bpy.data.objects['RING_外圈_柱础_01']
for i,x in enumerate([-3.8,-1.45,1.45,3.8]):
    for source,kind,z in [(postsrc,'木柱',.6),(basesrc,'柱础',.54)]:
        o=source.copy();o.data=source.data.copy();o.name=f'XS_后廊_{kind}_{i}';outer.objects.link(o);o.location=(x,3.95,z)

# Horizontal lower framing. Mortise endpoints enter the receiving post/beam.
fx=[-5.6,-3.8,-1.45,1.45,3.8,5.6]
sy=[-3.65,-1.5,0,1.5,3.95]
for y in [-3.65,3.95]:
    for i in range(5):beam(f'XS_檐枋_{y}_{i}',(fx[i],y,4.12),(fx[i+1],y,4.12),.22,.32,wood,frame)
    cylinder('XS_檐檩_'+str(y),(-5.72,y,4.39),(5.72,y,4.39),.145,wood,frame)
for x in [-5.6,5.6]:
    for i in range(4):beam(f'XS_侧檐枋_{x}_{i}',(x,sy[i],4.12),(x,sy[i+1],4.12),.22,.32,wood,frame)
    cylinder('XS_侧檐檩_'+str(x),(x,-3.77,4.39),(x,4.07,4.39),.145,wood,frame)
ix=[-3.8,-1.45,1.45,3.8]
for y in [-1.8,2.65]:
    for i in range(3):beam(f'XS_金枋_{y}_{i}',(ix[i],y,5.15),(ix[i+1],y,5.15),.24,.36,wood,frame)
for x in ix:
    beam('XS_五架梁_'+str(x),(x,-2.04,5.32),(x,2.89,5.32),.32,.46,wood,frame)
    for y0,y1 in [(-3.65,-1.8),(3.95,2.65)]:
        beam(f'XS_抱头梁_{x}_{y0}',(x,y0,4.25),(x,y1,4.25),.25,.34,wood,frame)
        beam(f'XS_穿插枋_{x}_{y0}',(x,y0,3.82),(x,y1,3.82),.14,.20,wood,frame)
    # Two upper posts bear a three-purlin beam; a central short post bears ridge.
    for y in [YC-1.08,YC+1.08]:box(f'XS_金瓜柱_{x}_{y}',(x,y,5.91),(.24,.24,.72),wood,frame)
    beam('XS_三架梁_'+str(x),(x,YC-1.25,6.27),(x,YC+1.25,6.27),.27,.36,wood,frame)
    box('XS_脊瓜柱_'+str(x),(x,YC,6.87),(.25,.25,.84),wood,frame)
for d in [-D,-1.08,0,1.08,D]:
    z=height(abs(d))-.20
    cylinder('XS_檩_'+str(d),(-4.22,YC+d,z),(4.22,YC+d,z),.14 if d else .17,wood,frame)
for s in [-1,1]:
    # Gable-end receiving member, carried by end frame and short packing blocks.
    beam('XS_踩步金_'+str(s),(s*4.0,YC-D,5.35),(s*4.0,YC+D,5.35),.32,.42,wood,frame)
    for y in [-1.5,0,1.5]:
        beam(f'XS_山面顺梁_{s}_{y}',(s*5.6,y,4.25),(s*3.8,y,4.25),.27,.36,wood,frame)
        box(f'XS_交金墩_{s}_{y}',(s*4.0,y,4.77),(.27,.30,.70),wood,frame)

# Walls enclose actual rooms while leaving an open front veranda.
for x in [-3.8,3.8]:
    box('XS_侧墙砖裙_'+str(x),(x,.425,.86),(.24,4.45,.76),brick,walls)
    # Windows left clear between y=-.95 and 1.80, sill at 1.6 and head 3.8.
    box('XS_侧墙窗下_'+str(x),(x,.425,1.42),(.24,4.45,.36),plaster,walls)
    box('XS_侧墙窗上_'+str(x),(x,.425,4.47),(.24,4.45,1.34),plaster,walls)
    for yc,length in [(-1.375,.85),(2.225,.85)]:box(f'XS_侧墙窗旁_{x}_{yc}',(x,yc,2.7),(.24,length,2.2),plaster,walls)
box('XS_后墙砖裙',(0,2.65,.86),(7.6,.24,.76),brick,walls)
box('XS_后墙白灰',(0,2.65,3.18),(7.6,.24,3.88),plaster,walls)
for x in [-2.625,2.625]:
    box('XS_前檐窗下砖裙_'+str(x),(x,-1.8,.86),(2.05,.24,.76),brick,walls)
    box('XS_前檐窗台_'+str(x),(x,-1.83,1.27),(2.15,.32,.09),stone,walls)
box('XS_正面门窗上槛墙',(0,-1.8,4.67),(7.6,.23,.85),plaster,walls)
# Room partitions match the supplied three-bay diagram; clear central hall.
for x in [-1.45,1.45]:
    box('XS_内隔墙后段_'+str(x),(x,1.55,2.45),(.13,2.2,3.94),plaster,walls)
    box('XS_内隔墙门上_'+str(x),(x,-.675,3.98),(.13,2.25,.9),wood,walls)

# Curved boarding surfaces; real tiles are added in next stage.
for sign in [-1,1]:
    vs=[];fs=[];N=32;M=64
    for j in range(N+1):
        d=DE*j/N;w=bound(d)
        for i in range(M+1):vs.append(tuple(frontpoint(-w+2*w*i/M,d,sign)))
    for j in range(N):
        for i in range(M):
            a=j*(M+1)+i;fs.append((a,a+1,a+M+2,a+M+1))
    o=mesh('XS_前后坡望板_'+str(sign),vs,fs,under,roof)
    for p in o.data.polygons:p.use_smooth=True
    vs=[];fs=[];N=20;M=40
    for j in range(N+1):
        u=j/N;half=D+(DE-D)*u
        for i in range(M+1):vs.append(tuple(sidepoint(-half+2*half*i/M,u,sign)))
    for j in range(N):
        for i in range(M):
            a=j*(M+1)+i;fs.append((a,a+1,a+M+2,a+M+1))
    mesh('XS_山面下坡望板_'+str(sign),vs,fs,under,roof)
    # Gable is a real triangular infill, not a full hip ending at the ridge.
    vs=[(sign*G,YC-D,5.72),(sign*G,YC+D,5.72),(sign*G,YC,7.65)]
    mesh('XS_山花_'+str(sign),vs,[(0,1,2)],gable,roof)
    for j in range(21):
        y=YC-D+(2*D)*j/20;top=height(abs(y-YC))-.05
        if top>5.76:box(f'XS_山花板缝_{sign}_{j}',(sign*(G+.013),y,(5.72+top)/2),(.018,.025,top-5.72),wood,roof,.002)

scene['xieshan_design']='明清风格园林单檐歇山；三间房屋带廊，灰瓦素墙，无宫殿式斗拱。非潇湘馆实测复原。'
scene['timber_stage']='斜接试架已隐藏，正身抬梁与山面构架已建；屋面细部继续施工。'
bpy.ops.wm.save_as_mainfile(filepath=path)
print('STAGE 1: corrected frame, enclosure and four roof surfaces with two gables saved.')
