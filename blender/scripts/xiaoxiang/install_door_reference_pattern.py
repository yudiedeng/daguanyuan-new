import bpy,bmesh,os
from mathutils import Matrix,Vector
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
assert not bpy.data.collections.get('31_隔扇门_卷花格心')
path=bpy.data.filepath
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_before_door_pattern_20260924.blend'),copy=True)
src=bpy.data.collections['样板V2_清晰图描形']
asset=bpy.data.collections.new('ASSET_门格心_单组折线卷花')
left,right=-.170625,.165375;bottom,top=.120,1.128
for original in list(src.objects):
    if original.type!='MESH' or original.hide_render:continue
    if original.name.startswith(('V6_','V7_')) or original.name=='V2_可隐藏绢底':continue
    coords=[original.matrix_world@v.co for v in original.data.vertices]
    if not coords or max(v.x for v in coords)<left or min(v.x for v in coords)>right:continue
    o=original.copy();o.data=original.data.copy();o.name='门花纹原件_'+original.name
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.transform(bm,matrix=original.matrix_world,verts=list(bm.verts))
    for co,no in [((left,0,0),(-1,0,0)),((right,0,0),(1,0,0)),((0,0,bottom),(0,0,-1)),((0,0,top),(0,0,1))]:
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no,clear_outer=True,clear_inner=False)
    if not bm.faces:
        bm.free();bpy.data.objects.remove(o);continue
    boundary=[e for e in bm.edges if e.is_boundary]
    if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();o.data.update()
    o.matrix_world=Matrix.Identity(4);o.hide_render=False;o.hide_viewport=False
    asset.objects.link(o)
out=bpy.data.collections.new('31_隔扇门_卷花格心');s.collection.children.link(out)
green=bpy.data.materials['SAMPLE2_深绿漆']
import sys
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box
hidden=[]
for i in range(4):
    paper=bpy.data.objects['XS_隔扇格心_'+str(i)+'_窗纸']
    origin=paper.matrix_world.copy()
    # Retain existing backing, edge stiles and top/bottom rails, replace grid only.
    for o in list(s.objects):
        if o.name.startswith('XS_隔扇格心_'+str(i)+'_') and not any(t in o.name for t in ['窗纸','边挺','抹头']):
            o.hide_render=True;o.hide_set(True);hidden.append(o.name)
    for label,z0,height in [('下格',-1.015,1.29),('上格',.325,.690)]:
        o=bpy.data.objects.new('新门格心_'+str(i)+'_'+label,None);out.objects.link(o)
        o.instance_type='COLLECTION';o.instance_collection=asset
        o.matrix_world=origin@Matrix.Translation((0,-.012,z0))@Matrix.Diagonal((.488/(right-left),1,height/(top-bottom),1))@Matrix.Translation((-(left+right)/2,0,-bottom))
        o['pattern']='参考照片的上下分区；抽取已确认窗花中央一组，保留原门开合角。'
    divider=box('门格心_中横档_'+str(i),(0,0,0),(.54,.074,.055),green,out,.003)
    divider.matrix_world=origin@Matrix.Translation((0,-.046,.300))
bpy.context.view_layer.update()
assert len(out.objects)==12
assert len(hidden)==228
# Inspect door front without modifying camera or lighting.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d
            r.view_location=Vector((0,-1.80,2.65));r.view_distance=5.3
            r.view_rotation=Vector((0,1,-.08)).to_track_quat('-Z','Y')
s['door_lattice']='四扇门旧格心替换为上下折线卷花；保留白色背衬、门框、裙板、门钮与开门角度；旧格心隐藏。'
bpy.ops.wm.save_as_mainfile(filepath=path)
print({'asset_parts':len(asset.objects),'door_pattern_instances':8,'old_grid_hidden':len(hidden),'saved':path})
