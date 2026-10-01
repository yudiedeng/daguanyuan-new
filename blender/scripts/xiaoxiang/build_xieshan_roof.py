import bpy, os, sys, math, random
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import *
random.seed(1938)
assert not bpy.data.collections.get('23_灰瓦_分垄搭接')
tiles=collection('23_灰瓦_分垄搭接');ridges=collection('24_九脊与檐口');rafters=collection('25_椽子与角梁')
wood=bpy.data.materials['MAT_暗褐旧木_顺纹']
tilem=[material('XS_灰瓦色差_'+str(i),(.064+i*.005,.075+i*.005,.080+i*.005),.86) for i in range(7)]
ridge_mat=material('XS_屋脊青灰',(.075,.083,.080),.83)
wooddark=material('XS_檐口深木',(.036,.025,.017),.78)

def tile_strip(name,mapping,start,end,width=.215,step=.265):
    vs=[];fs=[];mids=[]
    # Tile pans and raised cover tiles are separate curved shells with overlapping courses.
    for row in range(math.ceil((end-start)/step)):
        a=start+row*step;b=min(end+.02,a+step+.045)
        if b<=a:continue
        for cover in [False,True]:
            off=len(vs);N=8
            for d in [a,b]:
                for j in range(N+1):
                    t=j/N
                    if cover:
                        du=width/2+.069*math.cos(math.pi*t)
                        dz=.068*math.sin(math.pi*t)+.047
                    else:
                        du=(t-.5)*width
                        dz=.022+.037*(2*t-1)**2
                    p=Vector(mapping(du,d));p.z+=dz+.004*(row%2)
                    vs.append(tuple(p))
            for j in range(N):fs.append((off+j,off+j+1,off+N+2+j,off+N+1+j));mids.append(random.randrange(7))
            # Thin visible front edge, important for tiled rather than corrugated appearance.
            off2=len(vs)
            for j in range(N+1):
                p=Vector(vs[off+N+1+j]);p.z-=.014;vs.append(tuple(p))
            for j in range(N):fs.append((off+N+1+j,off+N+2+j,off2+j+1,off2+j));mids.append(random.randrange(7))
    o=mesh(name,vs,fs,tilem[0],tiles)
    for m in tilem[1:]:o.data.materials.append(m)
    for p,idx in zip(o.data.polygons,mids):p.material_index=idx;p.use_smooth=True
    o['tile_course_pitch_m']=step
    return o

pitch=.215
for sign in [-1,1]:
    for i in range(-29,30):
        x=i*pitch
        # Avoid cover tiles crossing the diagonal roof junction; ridge covers the last 0.12m.
        start=0 if abs(x)+pitch*.8<=G else D+(abs(x)+pitch*.8-G)/(E-G)*(DE-D)
        if start>=DE:continue
        tile_strip(f'XS_前后瓦垄_{sign}_{i}',lambda du,d,x=x,s=sign:frontpoint(x+du,d,s),start,DE)
    for i in range(-21,22):
        y=i*pitch
        u0=max(0,(abs(y)+pitch*.8-D)/(DE-D))
        if u0>=1:continue
        tile_strip(f'XS_山面瓦垄_{sign}_{i}',lambda du,d,y=y,s=sign:sidepoint(y+du,(d-G)/(E-G),s),G+(E-G)*u0,E,step=.245)

# Explicit nine ridges: one main ridge, four gable/verge ridges, four hips.
def ridge(name,pts,r=.115):
    pts=[Vector(p)+Vector((0,0,.13)) for p in pts]
    # Each short cap is individually editable and follows the curved roof.
    polyline_beam(name,pts,r,ridge_mat,ridges)
    for o in list(ridges.objects):
        if o.name.startswith(name+'_'):o['ridge_family']=name
ridge('XS_正脊',[(x,YC,7.70+.13*(abs(x)/4.14)**8) for x in [-4.14+i*8.28/36 for i in range(37)]],.135)
# Masonry ridge base beneath rounded cap.
box('XS_正脊脊座',(0,YC,7.73),(8.35,.23,.22),ridge_mat,ridges,.025)
for sx in [-1,1]:
    for sy in [-1,1]:
        ridge(f'XS_垂脊_{sx}_{sy}',[frontpoint(sx*G,D*j/18,sy) for j in range(19)],.11)
        ridge(f'XS_戗脊_{sx}_{sy}',[frontpoint(sx*(G+(E-G)*j/24),D+(DE-D)*j/24,sy) for j in range(25)],.105)
    # Restrained curved ridge terminals, not palace beast arrays.
    points=[(sx*(4.13+.28*t),YC,7.91+.48*t*t) for t in [i/8 for i in range(9)]]
    polyline_beam('XS_正脊卷头_'+str(sx),points,.105,ridge_mat,ridges)
for sy in [-1,1]:
    points=[frontpoint(-E+2*E*j/80,DE,sy)-Vector((0,0,.055)) for j in range(81)]
    polyline_beam('XS_前后封檐_'+str(sy),points,.075,wooddark,ridges)
for sx in [-1,1]:
    points=[sidepoint(-DE+2*DE*j/60,1,sx)-Vector((0,0,.055)) for j in range(61)]
    polyline_beam('XS_山面封檐_'+str(sx),points,.075,wooddark,ridges)

# Sloping members now are rafters above purlins, not replacements for horizontal beams.
for sy in [-1,1]:
    for i in range(-27,28):
        x=i*.225
        start=0 if abs(x)<G else D+(abs(x)-G)/(E-G)*(DE-D)
        ds=sorted(set([start]+[d for d in [1.08,D,3.3,4.1,DE] if d>start]))
        for j in range(len(ds)-1):
            a=frontpoint(x,ds[j],sy)-Vector((0,0,.085));b=frontpoint(x,ds[j+1],sy)-Vector((0,0,.085))
            cylinder(f'XS_前后椽_{sy}_{i}_{j}',a,b,.038,wood,rafters,10)
for sx in [-1,1]:
    for i in range(-19,20):
        y=i*.24;u0=max(0,(abs(y)-D)/(DE-D))
        if u0>=1:continue
        for j in range(4):
            a=sidepoint(y,u0+(1-u0)*j/4,sx)-Vector((0,0,.085))
            b=sidepoint(y,u0+(1-u0)*(j+1)/4,sx)-Vector((0,0,.085))
            cylinder(f'XS_山面椽_{sx}_{i}_{j}',a,b,.038,wood,rafters,10)
    for sy in [-1,1]:
        pts=[frontpoint(sx*(G+(E-G)*j/12),D+(DE-D)*j/12,sy)-Vector((0,0,.19)) for j in range(13)]
        polyline_beam(f'XS_角梁_{sx}_{sy}',pts,.12,wood,rafters)

# Bearing blocks at rear eave account for its shorter horizontal run.
frame=collection('20_歇山_正身与山面梁架')
rear=bpy.data.objects['XS_檐檩_3.95'];rear.location.z+=.34
for x in [-5.6,-3.8,-1.45,1.45,3.8,5.6]:box('XS_后檐承托_'+str(x),(x,3.95,4.48),(.22,.25,.30),wood,frame)
bpy.context.scene['roof_structure']='单檐歇山：2山花、4坡面、1正脊+4垂脊+4戗脊，实体瓦垄、椽、檩、梁、瓜柱分层。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('STAGE 2: tile strips',len(tiles.objects),'nine ridge families and rafters saved')
