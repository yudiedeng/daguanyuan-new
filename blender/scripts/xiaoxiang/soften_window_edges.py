import bpy,bmesh,math
c=bpy.data.collections['样板V2_清晰图描形']
counts={'wood':0,'trim':0}
for o in c.objects:
    if o.type!='MESH' or o.hide_render or o.hide_get() or o.name=='V2_可隐藏绢底':continue
    trim=('磨损边' in o.name or '轮廓线脚' in o.name or '卷头刻线' in o.name)
    if trim:
        width=.00008
    elif o.name.startswith('V6_'):
        width=.003
    elif o.name.startswith('V4_'):
        width=.0012
    elif '双卷' in o.name:
        width=.0014
    else:
        width=.002
    # Repair coincident closed-strip seams before rounding real geometry.
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(o.data);bm.free();o.data.update()
    bevel=next((m for m in o.modifiers if m.type=='BEVEL'),None)
    if bevel is None:bevel=o.modifiers.new('木作圆润倒角','BEVEL')
    bevel.width=width;bevel.segments=5;bevel.profile=.5
    bevel.limit_method='ANGLE';bevel.angle_limit=math.radians(25)
    bevel.use_clamp_overlap=True
    counts['trim' if trim else 'wood']+=1
bpy.context.view_layer.update()
bpy.context.scene['edge_finish']='主体木棂2mm圆角、卷花1.4mm、雕花头1.2mm、外框3mm；五段弧面，保持整体轮廓。'
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print('Rounded edges:',counts)
