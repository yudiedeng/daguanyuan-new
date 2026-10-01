import bpy
s=bpy.context.scene
assert s.name=='窗棂样板_参考图右下'
c=bpy.data.collections['样板V2_清晰图描形']
changed=[];bodies=[]
for o in c.objects:
    if o.type!='MESH' or o.hide_render or o.hide_get() or o.name=='V2_可隐藏绢底':continue
    # All carving and mullion bodies occupy the SAME depth interval.
    # The narrow colored edge lines are only a shallow surface treatment.
    if '磨损边' in o.name:
        front,back=-.0474,-.0472
    elif o.name.startswith('V4_') and ('轮廓线脚' in o.name or '卷头刻线' in o.name):
        front,back=-.0472,-.0470
    else:
        front,back=-.047,-.023
        bodies.append(o)
    coords=[o.matrix_world@v.co for v in o.data.vertices]
    lo=min(v.y for v in coords);hi=max(v.y for v in coords)
    assert hi-lo>1e-7
    inv=o.matrix_world.inverted()
    for vertex,p in zip(o.data.vertices,coords):
        p.y=front+(p.y-lo)/(hi-lo)*(back-front)
        vertex.co=inv@p
    o.data.update();changed.append(o.name)
bpy.context.view_layer.update()
for o in bodies:
    ys=[(o.matrix_world@v.co).y for v in o.data.vertices]
    assert abs(min(ys)+.047)<1e-6 and abs(max(ys)+.023)<1e-6
s['lattice_depth_check']='雕花、卷花、横竖棂实体统一前后平面：-0.047 / -0.023；表面描边不超过0.4毫米。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Aligned',len(changed),'parts; verified',len(bodies),'bodies coplanar, thickness 24mm.')
