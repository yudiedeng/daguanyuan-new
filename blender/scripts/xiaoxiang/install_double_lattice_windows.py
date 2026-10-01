import bpy,math
from mathutils import Matrix,Vector
path=bpy.data.filepath
assert not bpy.data.collections.get('30_银红纱双层花窗')
src=bpy.data.collections['样板V2_清晰图描形']
parts=[o for o in src.objects if o.type=='MESH' and not o.hide_render and not o.hide_get()]
assert len(parts)>100 and any(o.name=='V7_银红霞影纱' for o in parts)
house=bpy.data.scenes['Scene']
# Source collection is not linked directly to either scene; only its instances appear.
unit=bpy.data.collections.new('ASSET_完整一扇窗_上下两格')
H=1.1592;W=1.25055;BOTTOM=.0444
for row in range(2):
    for source in parts:
        o=source.copy();o.name='窗扇模块_'+str(row)+'_'+source.name
        unit.objects.link(o)
        o.matrix_world=Matrix.Translation((0,0,row*H-BOTTOM))@source.matrix_world
        o.hide_render=False;o.hide_viewport=False
out=bpy.data.collections.new('30_银红纱双层花窗');house.collection.children.link(out)
bpy.context.window.scene=house
green=bpy.data.materials['SAMPLE2_深绿漆']
prefixes=['XS_前槛窗_-2.625','XS_前槛窗_2.625','XS_侧窗_-1','XS_侧窗_1']
hidden=0
for o in house.objects:
    if any(o.name.startswith(p) for p in prefixes):
        # Retain the structural surround; replace only the old individual sashes.
        if '_框横' in o.name or '_框竖' in o.name:
            if o.type=='MESH':
                o.data=o.data.copy();o.data.materials.clear();o.data.materials.append(green)
        else:
            o.hide_render=True;o.hide_set(True);hidden+=1
def install(name,origin,width,height,angle,number):
    opening=width-.105
    sashw=opening/number
    sashh=height-.105
    R=Matrix.Rotation(angle,4,'Z');T=Matrix.Translation(Vector(origin))
    for i in range(number):
        x=-opening/2+sashw*(i+.5)
        o=bpy.data.objects.new(name+'_完整窗扇'+str(i+1),None)
        out.objects.link(o)
        o.instance_type='COLLECTION';o.instance_collection=unit
        o.matrix_world=T@R@Matrix.Translation((x,-.025,.0525))@Matrix.Diagonal((sashw/W,1,sashh/(2*H),1))
        o['layout']='上下两块花纹组成一扇完整窗'
        o['reference_asset']='窗棂样板_参考图右下'
        o['size_m']=[sashw,sashh]
for x in [-2.625,2.625]:install('银红花窗_正面'+str(x),(x,-1.94,1.33),2.06,2.87,0,2)
for side in [-1,1]:install('银红花窗_侧面'+str(side),(side*3.95,.425,1.61),2.72,2.14,side*math.pi/2,3)
house['window_installation']='4个窗洞，10扇完整窗，每扇上下2格，共20块银红纱花纹；保留原窗洞和门，旧窗隐藏可回退。'
# Open the house on a front oblique view with the new windows visible.
target=Vector((0,-.3,3.3));eye=Vector((11,-18,10))
q=(target-eye).to_track_quat('-Z','Y')
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            r=area.spaces.active.region_3d;r.view_location=target;r.view_distance=19;r.view_rotation=q
bpy.context.view_layer.update()
assert len(out.objects)==10
assert len(unit.objects)==2*len(parts)
bpy.ops.wm.save_as_mainfile(filepath=path)
print({'installed_sashes':len(out.objects),'pattern_panels':20,'module_parts':len(unit.objects),'old_window_parts_hidden':hidden,'active_scene':house.name})
