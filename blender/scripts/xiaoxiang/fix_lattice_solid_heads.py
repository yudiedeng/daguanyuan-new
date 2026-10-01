import bpy, os
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

s=bpy.context.scene
assert s.name=='窗棂样板_参考图右下'
c=bpy.data.collections['样板V2_清晰图描形']
# Preserve removed connectors, so this correction remains reversible.
hidden=[]
for o in c.objects:
    if o.name.startswith(('V2_卷花上竖接','V2_卷花下竖接')):
        o.hide_render=True
        o.hide_set(True)
        hidden.append(o.name)

def bez(p0,p1,p2,p3):
    return [tuple((1-t)**3*Vector(p0)+3*(1-t)**2*t*Vector(p1)+3*(1-t)*t*t*Vector(p2)+t**3*Vector(p3)) for t in [i/18 for i in range(19)]]

# The head is a solid carved wooden plaque, connected to the horizontal rail.
# Raised outline and curled relief already exist in front of this new body.
outline=[(-27,-28),(27,-28),(27,43),(24,43)]
for curve in [((24,43),(10,39),(6,34),(7,27)),((7,27),(3,36),(-3,36),(-7,27)),((-7,27),(-6,34),(-10,39),(-24,43))]:
    outline.extend(bez(*curve)[1:])
outline.append((-27,43))
K=.00105
created=[]
for x in [355,675,995]:
    for cy,flip,label in [(378,1,'上'),(787,-1,'下')]:
        name='V3_实心雕花底_'+label+str(x)
        assert name not in bpy.data.objects
        plane=[Vector(((x+px-677.5)*K,0,(1060-cy-flip*py)*K+.12)) for px,py in outline]
        n=len(plane)
        verts=[(v.x,y,v.z) for y in [-.064,-.043] for v in plane]
        faces=[]
        for tri in tessellate_polygon([plane]):
            ids=[v if isinstance(v,int) else min(range(n),key=lambda i:(plane[i]-v).length_squared) for v in tri]
            faces.extend([tuple(ids),tuple(i+n for i in reversed(ids))])
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
        obj=bpy.data.objects.new(name,me);c.objects.link(obj)
        me.materials.append(bpy.data.materials['SAMPLE2_深绿漆'])
        created.append(name)
s['lattice_correction']='隐藏多余卷花中轴竖接；六个花头增加实心绿漆木底并接至横棂，保留表面卷花凸线。'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print({'hidden_connector_parts':len(hidden),'solid_heads':created})
