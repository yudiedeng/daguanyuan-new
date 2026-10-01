import bpy,bmesh,os,sys
from mathutils import Matrix,Vector
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box
s=bpy.context.scene;path=bpy.data.filepath
assert not bpy.data.collections.get('32_固定门上横窗')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_before_fixed_transom.blend'),copy=True)
c=bpy.data.collections.new('32_固定门上横窗');s.collection.children.link(c)
green=bpy.data.materials['SAMPLE2_深绿漆'];cut=3.3225
for i,x in [(1,-.33),(2,.33)]:
    paper=bpy.data.objects['XS_隔扇格心_'+str(i)+'_窗纸']
    original=paper.matrix_world.copy()
    closed=Matrix.Translation((x,-1.862,3.05))
    correction=closed@original.inverted()
    pattern=bpy.data.objects['新门格心_'+str(i)+'_上格'];pattern.matrix_world=correction@pattern.matrix_world
    divider=bpy.data.objects['门格心_中横档_'+str(i)];divider.matrix_world=correction@divider.matrix_world
    candidates=[o for o in list(s.objects) if o.type=='MESH' and not o.hide_render and o.name.startswith(('XS_隔扇边挺_'+str(i)+'_','XS_隔扇抹头_'+str(i)+'_','XS_隔扇格心_'+str(i)+'_'))]
    for o in candidates:
        zs=[(o.matrix_world@v.co).z for v in o.data.vertices]
        if max(zs)<=cut:continue
        if min(zs)>=cut:
            o.matrix_world=correction@o.matrix_world;continue
        # Split the long stile and backing at the fixed transom, preserving both halves.
        for upper in [False,True]:
            new=o.copy();new.data=o.data.copy();new.name=('固定横窗_' if upper else '下门扇_')+o.name;c.objects.link(new)
            bm=bmesh.new();bm.from_mesh(new.data)
            bmesh.ops.transform(bm,matrix=o.matrix_world,verts=list(bm.verts))
            bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper)
            edges=[e for e in bm.edges if e.is_boundary]
            if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(new.data);bm.free()
            new.matrix_world=correction if upper else Matrix.Identity(4)
        o.hide_render=True;o.hide_set(True)
    cap=box('下门扇新上抹头_'+str(i),(0,0,0),(.65,.11,.055),green,c,.003)
    cap.matrix_world=original@Matrix.Translation((0,-.018,cut-3.05-.030))
# One fixed horizontal rail physically ties the two upper lights to the jambs.
box('固定横窗_贯通下横档',(0,-1.90,3.35),(1.38,.13,.055),green,c,.003)
box('固定横窗_中央接合条',(0,-1.88,3.755),(.045,.11,.81),green,c,.003)
bpy.context.view_layer.update()
for i in [1,2]:
    o=bpy.data.objects['新门格心_'+str(i)+'_上格']
    assert abs(o.matrix_world.to_euler().z)<1e-5
s['door_transom']='中间两扇上部为固定共面横窗，贯通横档连接；下门扇保留38度开启，边挺和背衬已分段。'
bpy.ops.wm.save_as_mainfile(filepath=path)
print('Fixed two upper lights; split full-height stiles/backing; lower doors keep opening angles.')
