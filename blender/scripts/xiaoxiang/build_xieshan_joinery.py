import bpy, os, sys, math
from mathutils import Vector, Matrix
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import *
assert not bpy.data.collections.get('26_格扇门窗与廊栏')
join=collection('26_格扇门窗与廊栏');detail=collection('27_雀替与细部')
wood=bpy.data.materials['MAT_暗褐旧木_顺纹']
dark=material('XS_门窗深褐木',(.046,.028,.015),.73)
paper=material('XS_窗纸米白',(.48,.43,.32),.93)
bronze=material('XS_门环旧铜',(.12,.075,.028),.55)
stone=bpy.data.materials['MAT_青灰石_微风化_养护旧化_coping']

def lattice(name,cx,z0,w,h,group,back=True):
    # Coordinates are local panel coordinates; all lattice strips are real geometry.
    if back:box(name+'_窗纸',(cx,.018,z0+h/2),(w-.07,.014,h-.07),paper,group,.001)
    for u in [-w/2,w/2]:box(name+'_边挺'+str(u),(cx+u,-.008,z0+h/2),(.052,.085,h+.07),dark,group,.004)
    for z in [z0,z0+h]:box(name+'_抹头'+str(z),(cx,-.008,z),(w,.085,.052),dark,group,.004)
    cols=max(2,round(w/.20));rows=max(3,round(h/.28))
    cw=w/cols;ch=h/rows
    for j in range(1,cols):box(name+'_竖棂'+str(j),(cx-w/2+j*cw,-.047,z0+h/2),(.022,.038,h),dark,group,.002)
    for j in range(1,rows):box(name+'_横棂'+str(j),(cx,-.047,z0+j*ch),(w,.038,.022),dark,group,.002)
    # Alternating nested rectangular motifs create restrained traditional latticework.
    for i in range(cols):
        for j in range(rows):
            if (i+j)%2:continue
            x=cx-w/2+(i+.5)*cw;z=z0+(j+.5)*ch
            for dx in [-cw*.27,cw*.27]:box(name+f'_回纹竖_{i}_{j}_{dx}',(x+dx,-.052,z),(.014,.032,ch*.54),dark,group,.001)
            for dz in [-ch*.27,ch*.27]:box(name+f'_回纹横_{i}_{j}_{dz}',(x,-.052,z+dz),(cw*.54,.032,.014),dark,group,.001)

def transform_new(before,origin,angle=0):
    bpy.context.view_layer.update()
    R=Matrix.Rotation(angle,4,'Z');T=Matrix.Translation(Vector(origin))
    for o in join.objects:
        if o.name not in before:o.matrix_world=T@R@o.matrix_world

def window(name,origin,width,height,angle=0,panels=3):
    before={o.name for o in join.objects}
    for i in range(panels):
        w=width/panels;x=-width/2+w*(i+.5)
        lattice(name+f'_扇{i}',x,.08,w-.045,height-.16,join)
    for z in [0,height]:box(name+'_框横'+str(z),(0,0,z),(width+.12,.15,.10),dark,join)
    for x in [-width/2,width/2]:box(name+'_框竖'+str(x),(x,0,height/2),(.10,.15,height),dark,join)
    transform_new(before,origin,angle)

for x in [-2.625,2.625]:window('XS_前槛窗_'+str(x),(x,-1.94,1.33),2.06,2.87,panels=3)
for s in [-1,1]:window('XS_侧窗_'+str(s),(s*3.95,.425,1.61),2.72,2.14,s*math.pi/2,4)

# Four-leaf front screen door. Middle pair opens inward leaving visible entry.
doorw=.65
for i,x in enumerate([-.99,-.33,.33,.99]):
    before={o.name for o in join.objects}
    for z,h in [(.58,.90),(1.23,.22)]:
        box(f'XS_隔扇裙板_{i}_{z}',(0,0,z),(doorw-.08,.075,h),dark,join)
        box(f'XS_隔扇裙板芯_{i}_{z}',(0,-.043,z),(doorw-.17,.02,h-.10),wood,join,.008)
    for u in [-doorw/2,doorw/2]:box(f'XS_隔扇边挺_{i}_{u}',(u,0,1.82),(.065,.11,3.60),dark,join)
    for z in [.05,1.10,1.36,3.58]:box(f'XS_隔扇抹头_{i}_{z}',(0,0,z),(doorw,.11,.075),dark,join)
    lattice(f'XS_隔扇格心_{i}',0,1.40,doorw-.11,2.10,join)
    cylinder(f'XS_门钮_{i}',(.20,-.06,1.32),(.20,-.10,1.32),.028,bronze,join,16)
    angle=0
    # Hinge rotation about the appropriate outside edge of the central leaves.
    objects=[o for o in join.objects if o.name not in before]
    bpy.context.view_layer.update()
    if i in [1,2]:
        hinge=-doorw/2 if i==1 else doorw/2
        angle=math.radians(38 if i==1 else -38)
        R=Matrix.Translation(Vector((hinge,0,0)))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(Vector((-hinge,0,0)))
        for o in objects:o.matrix_world=R@o.matrix_world
    for o in objects:o.location+=Vector((x,-1.88,.60))
box('XS_门槛',(0,-1.83,.56),(2.8,.26,.16),dark,join)
for x in [-1.36,1.36]:box('XS_门框'+str(x),(x,-1.85,2.48),(.11,.18,3.8),dark,join)
box('XS_门框上槛',(0,-1.85,4.40),(2.82,.18,.18),dark,join)

# Front upper decorative screen beneath the beam, preserving headroom.
for i,(a,b) in enumerate(zip([-5.6,-3.8,-1.45,1.45,3.8],[-3.8,-1.45,1.45,3.8,5.6])):
    before={o.name for o in join.objects}
    lattice('XS_廊上挂落_'+str(i),0,0,b-a-.32,.36,join,False)
    transform_new(before,((a+b)/2,-3.65,3.63))

def rail(name,a,b):
    a,b=Vector(a),Vector(b);v=b-a;L=v.length;v.normalize()
    for z,w,d in [(1.37,.11,.12),(.69,.10,.10)]:
        beam(name+'_横栏'+str(z),(a.x,a.y,z),(b.x,b.y,z),w,d,dark,join)
    count=max(2,round(L/.24))
    for i in range(1,count):
        p=a+v*(L*i/count)
        box(name+'_栏杆'+str(i),(p.x,p.y,1.03),(.045,.045,.63),dark,join,.004)
    for t in [0,1]:
        p=a+v*(L*t);box(name+'_栏端'+str(t),(p.x,p.y,1.03),(.09,.09,.72),wood,join)
for a,b in [(-5.46,-3.96),(-3.64,-1.61),(1.61,3.64),(3.96,5.46)]:rail('XS_前廊栏'+str(a),(a,-3.65,0),(b,-3.65,0))
for s in [-1,1]:
    for a,b in [(-3.48,-1.67),(-1.33,-.17),(.17,1.33),(1.67,3.78)]:rail(f'XS_侧廊栏{s}_{a}',(s*5.6,a,0),(s*5.6,b,0))
    # Stone threshold and lattice entry to the side chambers.
    box('XS_内室门槛'+str(s),(s*1.45,-.65,.54),(.21,2.1,.10),dark,join)
    for y in [-1.64,.34]:box('XS_内室门框'+str(s)+str(y),(s*1.45,y,2.03),(.15,.10,3.0),dark,join)

# Modest curved brackets under the front eave beam; no invented palace dougong.
for x in [-5.6,-3.8,-1.45,1.45,3.8,5.6]:
    for s in [-1,1]:
        if abs(x+s*.45)>5.6:continue
        outline=[(0,0),(.52,0),(.46,-.07),(.36,-.10),(.28,-.14),(.19,-.23),(.13,-.35),(0,-.42)]
        vs=[(x+s*u,y,3.97+z) for y in [-3.71,-3.59] for u,z in outline]
        N=len(outline);fs=[tuple(reversed(range(N))),tuple(range(N,N*2))]+[(j,(j+1)%N,(j+1)%N+N,j+N) for j in range(N)]
        mesh(f'XS_雀替_{x}_{s}',vs,fs,dark,detail,.008)

# More restrained grain: avoid stripes reading like alternating paint bands.
woodnodes=wood.node_tree.nodes
for n in woodnodes:
    if n.type=='VALTORGB':
        n.color_ramp.elements[0].color=(.030,.018,.010,1)
        n.color_ramp.elements[-1].color=(.074,.046,.023,1)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('STAGE 3: lattice windows, four-leaf door, corridor railings and brackets saved',len(join.objects))
