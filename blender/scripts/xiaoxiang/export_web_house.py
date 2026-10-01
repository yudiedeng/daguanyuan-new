import bpy,bmesh,math,json
from pathlib import Path
out=Path('/Users/dengyudie/Documents/Codex/2026-09-18/yue/outputs/xiaoxiang-3d/public/models')
s=bpy.data.scenes['Scene'];bpy.context.window.scene=s
for ob in bpy.data.objects:
    for mod in ob.modifiers:
        if mod.type=='BEVEL':mod.segments=1
dg=bpy.context.evaluated_depsgraph_get();groups={};count=0
roof_prefix=('22_','23_','24_','25_','28_','29_')
for ins in dg.object_instances:
    ob=ins.object;orig=ob.original
    if ob.type!='MESH':continue
    if ins.is_instance:
        if not ins.parent or not ins.parent.original.visible_get():continue
    elif not orig.visible_get():continue
    if orig.hide_render:continue
    if any(c.name.startswith(('90_','99_','Lighting')) for c in orig.users_collection):continue
    roof=any(c.name.startswith(roof_prefix) for c in orig.users_collection)
    me=ob.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
    mat=ob.material_slots[0].material if len(ob.material_slots) else None
    if mat is None:ob.to_mesh_clear();continue
    key=(roof,mat.name)
    bm=groups.setdefault(key,bmesh.new())
    tmp=bmesh.new();tmp.from_mesh(me);tmp.transform(ins.matrix_world)
    # Metric planar UVs for materials lacking an explicit UV layer.
    if not tmp.loops.layers.uv:
        uv=tmp.loops.layers.uv.new('UVMap')
        for f in tmp.faces:
            axis=max(range(3),key=lambda k:abs(f.normal[k]));axes=[k for k in range(3) if k!=axis]
            for l in f.loops:l[uv].uv=(l.vert.co[axes[0]],l.vert.co[axes[1]])
    scratch=bpy.data.meshes.new('_export_part');tmp.to_mesh(scratch);tmp.free()
    bm.from_mesh(scratch);bpy.data.meshes.remove(scratch);ob.to_mesh_clear();count+=1
print('REALIZED',count,'GROUPS',len(groups),flush=True)
export_scene=bpy.data.scenes.new('WEB_EXPORT');bpy.context.window.scene=export_scene
for (roof,name),bm in groups.items():
    bmesh.ops.dissolve_limit(bm,angle_limit=.01,verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False)
    me=bpy.data.meshes.new(name);bm.to_mesh(me);bm.free();me.update()
    o=bpy.data.objects.new(('WEB_ROOF_' if roof else 'WEB_HOUSE_')+name,me);export_scene.collection.objects.link(o)
    source=bpy.data.materials[name];m=bpy.data.materials.new('WEB_'+name);m.use_nodes=True
    bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    old=next((n for n in source.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    for prop in ['Base Color','Metallic','Roughness']:
        if old:bs.inputs[prop].default_value=old.inputs[prop].default_value
    tex=next((n for n in source.node_tree.nodes if n.type=='TEX_IMAGE' and n.image),None)
    if tex:
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=tex.image;m.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color'])
    me.materials.append(m)
    for p in me.polygons:p.material_index=0
out.mkdir(parents=True,exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(out/'xiaoxiang-master-20260924.glb'),use_active_scene=True,export_materials='EXPORT',export_animations=False,export_draco_mesh_compression_enable=True,export_draco_mesh_compression_level=6)
print('EXPORTED',flush=True)
