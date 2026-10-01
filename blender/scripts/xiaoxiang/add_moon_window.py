import bpy, math, bmesh
from mathutils import Vector
from pathlib import Path
s=bpy.context.scene
assert s.name=='Scene'
assert not bpy.data.collections.get('35_居室月洞窗')
path=bpy.data.filepath
backup=str(Path(path).with_name('xiaoxiang_before_moon_window.blend'))
bpy.ops.wm.save_as_mainfile(filepath=backup,copy=True)
c=bpy.data.collections.new('35_居室月洞窗');s.collection.children.link(c)
wood=bpy.data.materials['SAMPLE2_深绿漆']
plaster=bpy.data.materials['XS_旧白灰墙']
gauze=bpy.data.materials['SAMPLE7_银红软烟罗_经纬透纱']
for o in s.objects:
    if o.name.startswith('XS_侧窗_-1_'):
        o.hide_render=True;o.hide_set(True)
        o['replacement']='35_居室月洞窗；原件保留，可恢复'
def mesh(name,vs,fs,mat,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    o=bpy.data.objects.new(name,me);c.objects.link(o);me.materials.append(mat)
    if bevel:
        m=o.modifiers.new('柔和木边','BEVEL');m.width=bevel;m.segments=4
        m.limit_method='ANGLE'
        o.modifiers.new('面法线','WEIGHTED_NORMAL')
    return o
N=192;cy=.425;cz=2.7
def ring(name,rout,rin,front,back,mat,rect=False,bev=0):
    vs=[]
    for x in [front,back]:
        for outer in [True,False]:
            for i in range(N):
                a=math.tau*i/N;co=math.cos(a);si=math.sin(a)
                r=(min(1.375/max(abs(co),1e-9),1.1/max(abs(si),1e-9)) if rect else rout) if outer else rin
                vs.append((x,cy+r*co,cz+r*si))
    fs=[]
    for i in range(N):
        j=(i+1)%N
        fs.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
    return mesh(name,vs,fs,mat,bev)
ring('月洞窗_圆洞周围补灰墙',1,1.005,-3.92,-3.68,plaster,True)
ring('月洞窗_贯墙木框',1.025,.94,-3.955,-3.66,wood,bev=.006)
ring('月洞窗_外侧圆润压边',1.065,.975,-3.985,-3.935,wood,bev=.008)
ring('月洞窗_内侧压边',1.045,.955,-3.69,-3.64,wood,bev=.006)
def bar(name,y,z,dy,dz):
    vs=[(x,yy,zz) for x in [-3.947,-3.901] for yy in [y-dy/2,y+dy/2] for zz in [z-dz/2,z+dz/2]]
    return mesh(name,vs,[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)],wood,.003)
for k in [-2,-1,0,1,2]:
    v=k*.30;h=math.sqrt(.947**2-(abs(v)+.015)**2)
    bar('月洞窗_竖棂_'+str(k),cy+v,cz,.030,2*h)
    bar('月洞窗_横棂_'+str(k),cy,cz+v,2*h,.030)
# Local X/Z fabric coordinates preserve both procedural weave directions.
vs=[(0,0,0)];fs=[]
for j in range(1,49):
    r=.955*j/48
    for i in range(N):
        a=math.tau*i/N
        vs.append((r*math.cos(a),.0006*math.sin(a*5)*(1-r/.955),r*math.sin(a)))
for i in range(N):fs.append((0,1+i,1+(i+1)%N))
for j in range(47):
    a=1+j*N;b=a+N
    for i in range(N):
        q=(i+1)%N;fs.append((a+i,b+i,b+q,a+q))
o=mesh('月洞窗_银红霞影纱',vs,fs,gauze)
o.rotation_euler.z=math.pi/2;o.location=(-3.89,cy,cz)
for p in o.data.polygons:p.use_smooth=True
c['设计说明']='依月洞窗文本作视觉诠释；左侧居室位置及尺寸为本模型设计，非原文指定。'
bpy.context.view_layer.update()
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        r=a.spaces.active.region_3d
        r.view_location=(-3.8,cy,cz)
        r.view_rotation=Vector((-1,-.12,.06)).to_track_quat('Z','Y')
        r.view_distance=4.0
bpy.ops.wm.save_as_mainfile(filepath=path)
print('Installed',len(c.objects),'moon-window parts. Saved',path)
