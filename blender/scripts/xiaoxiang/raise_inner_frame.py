import bpy, os
from mathutils import Vector
scene=bpy.context.scene;path=bpy.data.filepath
assert path.endswith('xiaoxiang_master.blend')
assert not scene.get('inner_raised_050m',False)
bpy.context.view_layer.update()
posts=[o for o in bpy.data.collections['12B_内圈房屋柱与柱础'].objects if '_木柱_' in o.name]
assert len(posts)==8 and all(abs(o.dimensions.z-4.25)<.001 for o in posts)
outer={o.name:o.matrix_world.copy() for o in bpy.data.collections['12A_外圈廊柱与柱础'].objects}
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(path),'xiaoxiang_master_before_higher_inner.blend'),copy=True)
for o in posts:
    zs=[v.co.z for v in o.data.vertices]
    o.scale.z=4.75/(max(zs)-min(zs))
    o['stage']='内圈柱身4.75m；柱底、柱径不变'
for o in bpy.data.collections['12C_内外圈梁枋'].objects:
    if o.name.startswith('RING_内圈'):
        o.location.z+=.5
    elif '联系梁' in o.name:
        zs=[v.co.z for v in o.data.vertices];lo,hi=min(zs),max(zs)
        a=o.matrix_world@Vector((0,0,lo));b=o.matrix_world@Vector((0,0,hi))
        b.z+=.5
        o.location=a;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler()
        o.scale.z=(b-a).length/(hi-lo)
bpy.context.view_layer.update()
assert all(abs(o.dimensions.z-4.75)<.001 for o in posts)
assert all(bpy.data.objects[n].matrix_world==m for n,m in outer.items())
scene['inner_raised_050m']=True
scene['timber_stage']='外圈柱身3.75m，内圈柱身4.75m，高差1m；连接梁内端同步升高；屋架未建。'
bpy.ops.wm.save_as_mainfile(filepath=path)
print('VERIFIED: inner 8 columns 4.75m, outer unchanged 3.75m; inner beams +0.5m, connecting beam outer ends preserved.')
