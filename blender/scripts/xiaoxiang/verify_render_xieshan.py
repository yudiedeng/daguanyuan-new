import bpy, os, json, math
from mathutils import Vector
scene=bpy.context.scene
out=os.path.dirname(bpy.data.filepath)
def cols(name):return bpy.data.collections[name]
def names(prefix):return [o for o in scene.objects if o.name.startswith(prefix)]
report={
 'master':bpy.data.filepath,
 'design':'明清风格单檐灰瓦歇山园林房屋，非实测复原与施工结构',
 'roof_planes':len(names('XS_前后坡望板_'))+len(names('XS_山面下坡望板_')),
 'gables':len(names('XS_山花_')),
 'main_ridges':len(names('XS2_正脊')),
 'verge_ridges':len(names('XS2_垂脊_')),
 'hip_ridges':len(names('XS2_戗脊_')),
 'tile_strips':len(cols('23_灰瓦_分垄搭接').objects),
 'frame_parts':len(cols('20_歇山_正身与山面梁架').objects),
 'rafter_corner_parts':len(cols('25_椽子与角梁').objects),
 'joinery_parts':len(cols('26_格扇门窗与廊栏').objects),
 'five_purlin_beams':len(names('XS_五架梁_')),
 'three_purlin_beams':len(names('XS_三架梁_')),
 'ridge_short_posts':len(names('XS_脊瓜柱_')),
 'horizontal_veranda_beams':len(names('XS_抱头梁_')),
 'packed_images':[im.name for im in bpy.data.images if im.packed_file],
 'missing_images':[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file and not os.path.exists(bpy.path.abspath(im.filepath))],
 'old_sloping_frame_hidden':cols('12C_内外圈梁枋').hide_render,
 'platform':scene.get('platform_dimensions_m'),
}
assert report['roof_planes']==4 and report['gables']==2
assert (report['main_ridges'],report['verge_ridges'],report['hip_ridges'])==(1,4,4)
assert report['tile_strips']>=150 and report['joinery_parts']>1000
assert report['five_purlin_beams']==4 and report['ridge_short_posts']==4
assert report['horizontal_veranda_beams']==8
assert not report['missing_images']
assert report['old_sloping_frame_hidden']
for o in names('XS_抱头梁_'):
    zs=[v.co.z for v in o.data.vertices]
    a=o.matrix_world@Vector((0,0,min(zs)));b=o.matrix_world@Vector((0,0,max(zs)))
    assert abs(a.z-b.z)<.001
report['horizontal_veranda_beams_verified']=True
with open(os.path.join(out,'xieshan_verification.json'),'w') as f:json.dump(report,f,ensure_ascii=False,indent=2)
scene.render.resolution_x=1500;scene.render.resolution_y=1100
scene.render.resolution_percentage=100
def render(name,loc,target,lens):
    scene.camera.location=loc
    scene.camera.rotation_euler=(Vector(target)-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.lens=lens
    scene.render.filepath=os.path.join(out,name+'.png')
    bpy.ops.render.render(write_still=True)
render('xiaoxiang_xieshan_front',(15,-19,12),(0,.3,3.6),43)
render('xiaoxiang_xieshan_rear',(-15,20,11),(0,.5,3.6),43)
# Cutaway is a diagnostic render only; do not save a master with missing roof or walls.
for name in ['22_歇山_望板与山花','23_灰瓦_分垄搭接','24_九脊与檐口','25_椽子与角梁','28_砖砌脊与卷草收头','21_围护_灰砖素墙','26_格扇门窗与廊栏','29_室内木板顶棚']:
    cols(name).hide_render=True
render('xiaoxiang_xieshan_frame_check',(13,-17,15),(0,.3,3.1),45)
print('VERIFIED',json.dumps(report,ensure_ascii=False))
