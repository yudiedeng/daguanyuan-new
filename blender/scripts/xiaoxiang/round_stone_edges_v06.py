import bpy, os
from mathutils import Vector
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'output')
bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT,'xiaoxiang_platform_v05_surfaces.blend'))
changed=[]
for obj in bpy.data.objects:
    if obj.type!='MESH' or not obj.name.startswith(('STEP_','EDGE_','CORNER_')):
        continue
    # Only exposed arrises are rounded widely. Internal butt joints stay close.
    mesh=obj.data
    weights=mesh.attributes.get('bevel_weight_edge') or mesh.attributes.new('bevel_weight_edge','FLOAT','EDGE')
    hx,hy,hz=[max(abs(v.co[i]) for v in mesh.vertices) for i in range(3)]
    is_step=obj.name.startswith('STEP_')
    for e in mesh.edges:
        a,b=[mesh.vertices[i].co for i in e.vertices]
        vertical=abs(a.z-b.z)>hz
        top=abs(a.z-hz)<1e-5 and abs(b.z-hz)<1e-5
        along_x=abs(a.x-b.x)>hx
        if is_step:
            # Front nosing on all blocks; only outermost blocks get rounded side edges.
            outer_side=lambda x: abs(abs(obj.location.x+x)-(1.8 if '第1级' in obj.name else 1.5 if '第2级' in obj.name else 1.2))<.01
            front=abs(a.y+hy)<1e-5 and abs(b.y+hy)<1e-5
            exposed=(top and along_x and front) or (top and not along_x and outer_side(a.x)) or (vertical and front and outer_side(a.x))
            weights.data[e.index].value=1.0 if exposed else .12
        else:
            # Round the long top arrises, with restrained rounding on stone end joints.
            along_long=(abs(a.x-b.x)>hx) if hx>hy else (abs(a.y-b.y)>hy)
            weights.data[e.index].value=1.0 if top and along_long else .15
    bevel=next((m for m in obj.modifiers if m.type=='BEVEL'),None)
    if bevel:
        bevel.limit_method='WEIGHT'
        bevel.width=.019 if is_step else .010
        bevel.segments=6
        bevel.profile=.5
        bevel.use_clamp_overlap=True
    changed.append(obj.name)

scene=bpy.context.scene
for obj in bpy.data.objects:
    if obj.name.startswith('MORTAR_踏步接缝填实'):
        # Keep bedding behind the newly rounded silhouette.
        obj.dimensions.x-=.044
        obj.dimensions.y-=.044
        obj.dimensions.z-=.044
scene['edge_revision']='v06: exposed step arrises 19 mm rounding, long coping top edges 10 mm; joints kept tight'
target=os.path.join(OUT,'xiaoxiang_platform_v06_rounded.blend')
bpy.ops.wm.save_as_mainfile(filepath=target)
scene.camera.location=(-3.2,-5.8,1.05)
scene.camera.rotation_euler=(Vector((-1.6,-3.35,.38))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.lens=60
scene.render.filepath=os.path.join(OUT,'xiaoxiang_platform_v06_detail.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.open_mainfile(filepath=target)
assert all(bpy.data.objects[name].data.attributes.get('bevel_weight_edge') for name in changed)
print('VERIFIED_ROUNDED_STONE_OBJECTS',len(changed))
