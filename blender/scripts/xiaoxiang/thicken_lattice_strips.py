import bpy
from mathutils import Vector
c=bpy.data.collections['样板V2_清晰图描形']
factor=1.25
groups=[]
for body in list(c.objects):
    if not body.name.startswith('V2_') or not body.name.endswith('_绿漆木条') or body.hide_render or body.hide_get():continue
    assert not body.get('width_adjustment_125')
    n=len(body.data.vertices)
    assert n%4==0
    # Each four-vertex section is widened around its original centreline.
    # Length, pattern placement and front/back depth remain unchanged.
    centers=[]
    for j in range(0,n,4):
        centers.append(sum((body.matrix_world@body.data.vertices[j+k].co for k in range(4)),Vector())/4)
    prefix=body.name[:-len('_绿漆木条')]
    group=[body]+[o for o in c.objects if o.name.startswith(prefix+'_磨损边') and not o.hide_render]
    for obj in group:
        assert len(obj.data.vertices)==n
        inv=obj.matrix_world.inverted()
        for i,v in enumerate(obj.data.vertices):
            p=obj.matrix_world@v.co;center=centers[i//4]
            p.x=center.x+(p.x-center.x)*factor
            p.z=center.z+(p.z-center.z)*factor
            v.co=inv@p
        obj.data.update()
    body['width_adjustment_125']=True
    groups.append(prefix)
bpy.context.view_layer.update()
bpy.context.scene['lattice_strip_width']='内部格棂及双卷木条横截面加宽25%，深度与中心线不变；外围厚框及雕花头不变。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Widened 25 percent:',len(groups),'strip groups; outer frame untouched.')
