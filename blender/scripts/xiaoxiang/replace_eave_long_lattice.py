import bpy,os,sys
from mathutils import Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box
s=bpy.context.scene;path=bpy.data.filepath
assert not bpy.data.collections.get('33_檐下横长折线挂落')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_before_eave_lattice.blend'),copy=True)
c=bpy.data.collections.new('33_檐下横长折线挂落');s.collection.children.link(c)
green=bpy.data.materials['SAMPLE2_深绿漆'];gold=bpy.data.materials['SAMPLE2_旧金褐线']
hidden=0
for o in s.objects:
    if o.name.startswith('XS_廊上挂落_') and not any(t in o.name for t in ['边挺','抹头']):
        o.hide_render=True;o.hide_set(True);hidden+=1
index=0
def line(name,a,b):
    global index
    x0,z0=a;x1,z1=b
    assert abs(x0-x1)<1e-7 or abs(z0-z1)<1e-7
    w=.015
    dims=(max(w,abs(x1-x0)+w),.038,max(w,abs(z1-z0)+w))
    o=box(name+'_'+str(index),((x0+x1)/2,-3.686,(z0+z1)/2),dims,green,c,.002)
    for mod in o.modifiers:
        if mod.type=='BEVEL':mod.segments=4
    index+=1
def chain(name,pts):
    for a,b in zip(pts,pts[1:]):line(name,a,b)
for bay,(a,b) in enumerate([(-5.6,-3.8),(-3.8,-1.45),(-1.45,1.45),(1.45,3.8),(3.8,5.6)]):
    lo=a+.16;hi=b-.16;W=hi-lo;z0=3.63;H=.36
    centers=[lo+W*.27,lo+W*.73];gw=min(.37,W*.22)
    def Z(v):return z0+H*v
    # Four widely spaced horizontal rails; each turns into the paired vertical motifs.
    for level in [.18,.38,.62,.82]:
        start=lo
        for cx in centers:
            line('长横棂'+str(bay),(start,Z(level)),(cx-gw/2,Z(level)))
            start=cx+gw/2
        line('长横棂'+str(bay),(start,Z(level)),(hi,Z(level)))
    for j,cx in enumerate(centers):
        name='折线组_'+str(bay)+'_'+str(j)
        for sign in [-1,1]:
            def X(v):return cx+sign*gw*v
            line(name+'_外竖',(X(.5),Z(0)),(X(.5),Z(1)))
            line(name+'_中竖',(X(.085),Z(0)),(X(.085),Z(1)))
            # Stepped returns echo the source's upper/lower opposed rectangular bends.
            chain(name+'_上折',[(X(.5),Z(.82)),(X(.32),Z(.82)),(X(.32),Z(.62)),(X(.5),Z(.62))])
            chain(name+'_下折',[(X(.5),Z(.18)),(X(.32),Z(.18)),(X(.32),Z(.38)),(X(.5),Z(.38))])
            chain(name+'_长折',[(X(.25),Z(1)),(X(.25),Z(.5)),(X(.085),Z(.5))])
            chain(name+'_下长折',[(X(.25),Z(0)),(X(.25),Z(.18)),(X(.085),Z(.18))])
        line(name+'_中央短接',(cx-gw*.085,Z(.5)),(cx+gw*.085,Z(.5)))
bpy.context.view_layer.update()
s['eave_pattern']='参考用户横向长棂图：每跨四道长横条与两组对称折线竖格；旧小方框隐藏，现有外边框及雀替保留。'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=Vector((0,-3.68,3.81));r.view_distance=4.6
            r.view_rotation=Vector((0,1,0)).to_track_quat('-Z','Y')
bpy.ops.wm.save_as_mainfile(filepath=path)
print('New rounded lattice members',len(c.objects),'old inner members hidden',hidden)
