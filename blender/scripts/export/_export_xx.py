
import bpy,json
info={"collections":[c.name for c in bpy.data.collections],"objects":len(bpy.data.objects),"materials":sorted({m.name for m in bpy.data.materials}),"dims":{}}
import mathutils
mn=mathutils.Vector((1e9,)*3);mx=mathutils.Vector((-1e9,)*3)
for o in bpy.data.objects:
    if o.type!='MESH' or not o.visible_get(): continue
    for c in o.bound_box:
        v=o.matrix_world@mathutils.Vector(c);mn=mathutils.Vector(map(min,mn,v));mx=mathutils.Vector(map(max,mx,v))
info["dims"]={"min":list(mn),"max":list(mx)}
json.dump(info,open(r"/Users/dengyudie/Downloads/dgy_models/xiaoxiang_info.json","w"),ensure_ascii=False)
bpy.ops.export_scene.gltf(filepath=r"/Users/dengyudie/Downloads/dgy_models/xiaoxiang.glb",export_format='GLB',export_apply=True,use_visible=True,export_image_format='NONE',export_materials='EXPORT',export_yup=True)
