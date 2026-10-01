import bpy,sys,os
sys.path.insert(0,os.path.dirname(__file__))
from xieshan_utils import box
c=bpy.data.collections['样板V2_清晰图描形'];K=.00105
green=bpy.data.materials['SAMPLE2_深绿漆']
for cx in [355,675,995]:
    center=(cx-677.5)*K
    for label in ['上','下']:
        prefix='V4_镂空木雕_'+label+str(cx)
        parts=[o for o in c.objects if o.name.startswith(prefix) and not o.hide_render]
        # Thicken only the outside wood, leaving the carved internal openings intact.
        for o in parts:
            inv=o.matrix_world.inverted()
            for v in o.data.vertices:
                p=o.matrix_world@v.co
                dx=(p.x-center)/K;a=abs(dx)
                if a>19.125:
                    limit=35 if dx<0 else 30
                    a=19.125+(min(a,25.375)-19.125)/(25.375-19.125)*(limit-19.125)
                    p.x=center+(-a if dx<0 else a)*K
                    v.co=inv@p
            o.data.update()
        railz=.8592 if label=='上' else .38355
        body=c.objects[prefix]
        zs=[(body.matrix_world@v.co).z for v in body.data.vertices]
        edge=max(zs) if label=='上' else min(zs)
        lo=min(edge,railz)-.0007;hi=max(edge,railz)+.0007
        box('V5_花头贴合横棂_'+label+str(cx),(center-2.5*K,-.035,(lo+hi)/2),(65*K,.024,hi-lo),green,c,0)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Widened six carved side rails to meet mullions; closed six top/bottom gaps; preserved inner cutouts and depth.')
