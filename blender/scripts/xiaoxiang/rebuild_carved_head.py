import bpy, ast, os, sys
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import mesh
s=bpy.context.scene
assert s.name=='窗棂样板_参考图右下'
c=bpy.data.collections['样板V2_清晰图描形']
green=bpy.data.materials['SAMPLE2_深绿漆'];gold=bpy.data.materials['SAMPLE2_旧金褐线'];K=.00105
source=ast.parse(open(os.path.join(os.path.dirname(__file__),'refine_lattice_from_clear_reference.py')).read())
for node in source.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('P','ribbon','bezier'):
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<helpers>','exec'))
for o in list(c.objects):
    if o.name.startswith(('V2_上花头','V2_下花头','V3_实心雕花底')):
        o.hide_render=True;o.hide_set(True)
# Trace one half of the new close-up: solid shoulders, an open arched recess,
# an inward curled pendant, a bottom returning hook, and a long stepped leg.
right=[(577,220),(750,220),(780,250),(780,915),(803,915),(803,947),(731,947),(731,633),(700,633)]
def curve(a,b,end):
    right.extend(bezier(right[-1],a,b,end,18)[1:])
curve((683,611),(644,613),(624,589))
curve((589,554),(606,502),(640,500))
curve((620,532),(653,568),(700,550))
curve((730,544),(730,523),(730,489))
right.append((730,341))
curve((730,259),(606,257),(601,335))
curve((597,353),(601,365),(610,369))
curve((646,337),(684,389),(657,420))
curve((642,447),(596,456),(577,431))
outline=right+[(1154-x,y) for x,y in reversed(right[1:-1])]
for cx in [355,675,995]:
    for cy,flip,label in [(350,1,'上'),(815,-1,'下')]:
        def tr(points):return [(cx+(x-577)*.125,cy+flip*(y-220)*.16) for x,y in points]
        pts=tr(outline);plane=[P(p,0) for p in pts];n=len(pts)
        verts=[(v.x,y,v.z) for y in [-.064,-.040] for v in plane]
        faces=[]
        for tri in tessellate_polygon([plane]):
            ids=[v if isinstance(v,int) else min(range(n),key=lambda i:(plane[i]-v).length_squared) for v in tri]
            faces.extend([tuple(ids),tuple(i+n for i in reversed(ids))])
        faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
        name='V4_镂空木雕_'+label+str(cx)
        mesh(name,verts,faces,green,c)
        ribbon(name+'_轮廓线脚',pts+[pts[0]],2.4,.003,-.065,True)
        # Small curved relief incisions emphasize a carved curl rather than wire loops.
        for side in [-1,1]:
            curl=[]
            for segment in [((604,419),(638,445),(669,399),(644,379)),((644,379),(624,363),(607,389),(626,394))]:
                curl.extend(bezier(*segment,16)[1:])
            curl=[(577+side*(x-577),y) for x,y in curl]
            ribbon(name+'_卷头刻线'+str(side),tr(curl),1.6,.002,-.066,True)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Six pierced carved heads replaced; old heads hidden for recovery.')
