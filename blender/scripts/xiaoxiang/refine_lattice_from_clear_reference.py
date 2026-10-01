import bpy,os,sys,math
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box,beam,mesh,material
s=bpy.context.scene;path=bpy.data.filepath
assert s.name=='窗棂样板_参考图右下'
assert not bpy.data.collections.get('样板V2_清晰图描形')
old=bpy.data.collections['样板_折线竖棂卷花'];old.hide_render=True;old.hide_viewport=True
c=bpy.data.collections.new('样板V2_清晰图描形');s.collection.children.link(c)
green=material('SAMPLE2_深绿漆',(.016,.045,.025),.80)
gold=material('SAMPLE2_旧金褐线',(.24,.18,.065),.88)
paper=material('SAMPLE2_旧绢色底',(.40,.34,.23),.95)
for mat,lo,hi in [(green,(.007,.019,.010,1),(.027,.062,.032,1)),(gold,(.06,.050,.020,1),(.32,.24,.085,1))]:
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED');noise=next(n for n in nodes if n.type=='TEX_NOISE')
    noise.inputs['Scale'].default_value=32
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=lo;ramp.color_ramp.elements[1].color=hi
    links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs[0],bs.inputs['Base Color'])
K=.00105
def P(p,y=-.034):return Vector(((p[0]-677.5)*K,y,(1060-p[1])*K+.12))

def ribbon(name,pts,width=12,depth=.024,y=-.035,trim=True):
    # Continuous profiled strip; mitered 90 degree turns, thin worn edges.
    def strip(suffix,w,d,yy,mat,offset=0):
        vs=[];N=len(pts)
        for i,p in enumerate(pts):
            prev=Vector(pts[max(0,i-1)]);nxt=Vector(pts[min(N-1,i+1)]);p=Vector(p)
            a=(p-prev).normalized() if i else (nxt-p).normalized()
            b=(nxt-p).normalized() if i<N-1 else a
            na=Vector((-a.y,a.x));nb=Vector((-b.y,b.x));n=(na+nb).normalized()
            n/=max(.40,n.dot(na))
            for dz in [-d/2,d/2]:
                for side in [-1,1]:vs.append(tuple(P(p+n*(offset+side*w/2),yy+dz)))
        fs=[]
        for i in range(N-1):
            a=i*4;b=a+4
            fs += [(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)]
        fs += [(0,1,3,2),((N-1)*4,(N-1)*4+2,(N-1)*4+3,(N-1)*4+1)]
        return mesh(name+suffix,vs,fs,mat,c,.0007)
    strip('_绿漆木条',width,depth,y,green)
    if trim:
        for sign in [-1,1]:strip('_磨损边'+str(sign),1.25,.0025,y-depth/2-.0014,gold,sign*width*.33)
def rect(name,x0,y0,x1,y1,w=12):ribbon(name,[(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)],w)
box('V2_可隐藏绢底',P((677.5,580),.01),(1045*K,.010,960*K),paper,c,.001)
rect('V2_外框',106,52,1249,1108,48)
rect('V2_框线脚',135,82,1220,1078,22)
rect('V2_内口',155,100,1200,1060,14)
# Source pixels: 4 broad folding bays crossed by 3 narrower rectangular frames.
ribbon('V2_左半大折框',[(155,185),(315,185),(315,977),(155,977)])
rect('V2_中左大折框',390,185,635,977)
rect('V2_中右大折框',710,185,955,977)
ribbon('V2_右半大折框',[(1200,185),(1030,185),(1030,977),(1200,977)])
for i,(a,b) in enumerate([(235,475),(555,795),(875,1120)]):rect('V2_交错小折框'+str(i),a,273,b,897,11)
for y in [350,815]:ribbon('V2_贯通横棂'+str(y),[(155,y),(1200,y)],12,y=-.047)
for x in [195,515,835,1160]:
    ribbon('V2_上短棂'+str(x),[(x,100),(x,185)],9)
    ribbon('V2_下短棂'+str(x),[(x,977),(x,1060)],9)

def bezier(p0,p1,p2,p3,N=12):
    return [tuple((1-t)**3*Vector(p0)+3*(1-t)**2*t*Vector(p1)+3*(1-t)*t*t*Vector(p2)+t**3*Vector(p3)) for t in [i/N for i in range(N+1)]]
def cloud(name,cx,cy,flip):
    # An open paired C-scroll, connected to the neighbouring mullions at its shoulders.
    right=[]
    for curve in [((0,-15),(12,-15),(31,-11),(31,1)),((31,1),(31,16),(12,18),(12,5)),((12,5),(12,-1),(22,-2),(22,4))]:
        right+=bezier(*curve)
    left=[(-x,y) for x,y in right]
    pts=list(reversed(left))+right[1:]
    pts=[(cx+x,cy+flip*y) for x,y in pts]
    ribbon(name,pts,7,.015,-.059)
for j,x in enumerate([195,275,435,515,595,755,835,915,1075,1160]):
    # Pairing is inverted between the upper and lower bands, like the reference.
    orientation=1 if j%2==0 else -1
    cloud('V2_上双卷'+str(x),x,507,orientation)
    cloud('V2_下双卷'+str(x),x,666,-orientation)
    # Short terminal stems meet the scroll shoulders instead of floating in the opening.
    ribbon('V2_卷花上竖接'+str(x),[(x,350),(x,507-orientation*15)],7,.017,-.052)
    ribbon('V2_卷花下竖接'+str(x),[(x,666+orientation*15),(x,815)],7,.017,-.052)

def flower(name,cx,cy,flip):
    # Three larger paired floral heads have a lobed outline and long hanging legs.
    def tr(pts):return [(cx+x,cy+flip*y) for x,y in pts]
    outline=[]
    curves=[((-25,0),(-25,-14),(-6,-16),(0,-5)),((0,-5),(6,-16),(25,-14),(25,0)),((25,0),(26,12),(26,30),(24,43)),((24,43),(10,39),(6,34),(7,27)),((7,27),(3,36),(-3,36),(-7,27)),((-7,27),(-6,34),(-10,39),(-24,43)),((-24,43),(-26,25),(-26,9),(-25,0))]
    for curve in curves:outline+=bezier(*curve)
    ribbon(name+'_外花头',tr(outline),6.8,.018,-.062)
    # Inner paired seed-shaped curls.
    heart=[]
    for curve in [((-14,9),(-18,-3),(-2,-3),(0,8)),((0,8),(2,-3),(18,-3),(14,9)),((14,9),(10,19),(3,16),(0,11)),((0,11),(-3,16),(-10,19),(-14,9))]:heart+=bezier(*curve)
    ribbon(name+'_双心',tr(heart),4.4,.015,-.067)
    for dx in [-27,27]:ribbon(name+'_垂脚'+str(dx),tr([(dx,-16),(dx,93)]),5,.016,-.058)
for x in [355,675,995]:
    flower('V2_上花头'+str(x),x,378,1)
    flower('V2_下花头'+str(x),x,787,-1)

s['reference']='最新清晰正面图，按可见坐标手工重建4组大折框、3组小折框、上下对称卷花；非贴照片。'
s.camera.data.ortho_scale=1.47;s.camera.location=(0,-4,.624)
s.camera.rotation_euler=(Vector((0,0,.624))-s.camera.location).to_track_quat('-Z','Y').to_euler()
s.render.resolution_x=1200;s.render.resolution_y=1150
s.render.filepath=os.path.join(os.path.dirname(path),'lattice_clear_reference.png')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=Vector((0,0,.624));r.view_distance=1.95;r.view_rotation=s.camera.rotation_euler.to_quaternion()
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=path)
print('V2 saved',len(c.objects),'parts; old approximation hidden; building untouched')
