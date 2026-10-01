import bpy, math, random
from mathutils import Vector

def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c

def mesh(name,verts,faces,mat,col,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);col.objects.link(o)
    if mat:me.materials.append(mat)
    if bevel:
        m=o.modifiers.new('细倒棱','BEVEL');m.width=bevel;m.segments=2
    return o

def box(name,loc,dims,mat,col,bevel=.006):
    x,y,z=[v/2 for v in dims]
    vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,col,bevel);o.location=loc
    uv=o.data.uv_layers.new(name='UV_Metric_1m')
    for p in o.data.polygons:
        a,b=[(1,2),(0,2),(0,1)][max(range(3),key=lambda i:abs(p.normal[i]))]
        for i in p.loop_indices:
            v=o.data.vertices[o.data.loops[i].vertex_index].co;uv.data[i].uv=(v[a]+loc[a],v[b]+loc[b])
    return o

def beam(name,a,b,width,depth,mat,col):
    a,b=Vector(a),Vector(b)
    o=box(name,(a+b)/2,(width,depth,(b-a).length),mat,col)
    o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    return o

def cylinder(name,a,b,r,mat,col,N=16):
    a,b=Vector(a),Vector(b);h=(b-a).length
    vs=[(r*math.cos(j*math.tau/N),r*math.sin(j*math.tau/N),z) for z in [0,h] for j in range(N)]
    fs=[tuple(reversed(range(N))),tuple(range(N,N*2))]+[(j,(j+1)%N,(j+1)%N+N,j+N) for j in range(N)]
    o=mesh(name,vs,fs,mat,col);o.location=a;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
    for p in o.data.polygons:p.use_smooth=len(p.vertices)==4
    return o

def material(name,color,rough=.8):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.use_nodes=True
    n,l=m.node_tree.nodes,m.node_tree.links
    bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
    m.diffuse_color=(*color,1)
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=65;tex.inputs['Detail'].default_value=3
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.004
    l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
    return m

# One continuous nine-ridge roof, upper gables on the +/- X ends.
YC=.425; G=4.10; E=6.35; D=2.225; DE=4.775
def height(d):
    if d<=D:
        t=d/D
        return 7.65-2.12*t+.19*t*t
    u=d-D
    return 5.72-.72*u+.085*u*u
def kick(x,d):
    return .40*max(0,(abs(x)-G)/(E-G))**3*max(0,(d-D)/(DE-D))**3
def bound(d):return G if d<=D else G+(E-G)*(d-D)/(DE-D)
def frontpoint(x,d,sign):return Vector((x,YC+sign*d,height(d)+kick(x,d)))
def sidepoint(y,u,sign):
    x=G+(E-G)*u;d=D+(DE-D)*u
    return Vector((sign*x,YC+y,height(d)+kick(x,abs(y))))

def polyline_beam(name,points,r,mat,col):
    for i in range(len(points)-1):cylinder(name+'_'+str(i),points[i],points[i+1],r,mat,col,12)
