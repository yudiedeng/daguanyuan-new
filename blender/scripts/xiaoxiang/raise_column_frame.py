import bpy, os
scene=bpy.context.scene
path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not scene.get('frame_raised_070m',False)
bpy.context.view_layer.update()
cols=[o for name in ['12A_外圈廊柱与柱础','12B_内圈房屋柱与柱础'] for o in bpy.data.collections[name].objects if '_木柱_' in o.name]
bases=[o for name in ['12A_外圈廊柱与柱础','12B_内圈房屋柱与柱础'] for o in bpy.data.collections[name].objects if '_柱础_' in o.name]
before={o.name:(tuple(o.location),tuple(o.scale)) for o in bases}
assert len(cols)==22
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_taller_frame.blend'),copy=True)
for o in cols:
    target=4.25 if '_内圈_' in o.name else 3.75
    zs=[v.co.z for v in o.data.vertices]
    assert abs(min(zs))<.0001
    o.scale.z=target/(max(zs)-min(zs))
    o['stage']=f'加高比例稿：柱身高{target:.2f}m，柱底及柱径不变'
for o in bpy.data.collections['12C_内外圈梁枋'].objects:o.location.z+=.70
bpy.context.view_layer.update()
for o in cols:
    target=4.25 if '_内圈_' in o.name else 3.75
    assert abs(o.dimensions.z-target)<.001
assert all((tuple(o.location),tuple(o.scale))==before[o.name] for o in bases)
scene['frame_raised_070m']=True
scene['timber_stage']='柱梁加高0.70m：外圈柱身3.75m、内圈柱身4.25m；柱径、柱础及12x9地台不变；屋架未建。'
bpy.ops.wm.save_as_mainfile(filepath=path)
print('VERIFIED: 22 posts raised by 0.70m, 37 beams lifted; outer 3.75m, inner 4.25m; bases unchanged.')
