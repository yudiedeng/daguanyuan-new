
import bpy,re,json,bmesh
def log(*a):
    print('XX',*a,flush=True)
sc=bpy.context.scene
def unex(lc):
    lc.exclude=False;lc.hide_viewport=False
    for c in lc.children: unex(c)
def intree(c,root):
    if c==root: return True
    return any(intree(c,ch) for ch in root.children)
for c in bpy.data.collections:
    if not intree(c,sc.collection):
        try: sc.collection.children.link(c)
        except Exception as e: log('link fail',c.name,e)
for o in bpy.data.objects:
    if not o.users_collection:
        sc.collection.objects.link(o)
unex(bpy.context.view_layer.layer_collection)
for c in bpy.data.collections: c.hide_viewport=False;c.hide_render=False
for o in bpy.data.objects: o.hide_viewport=False
def tris(o):
    dg=bpy.context.evaluated_depsgraph_get();ev=o.evaluated_get(dg);m=ev.to_mesh();t=sum(len(p.vertices)-2 for p in m.polygons);ev.to_mesh_clear();return t
def join_decimate(coll,name,ratio,planar=True):
    objs=[o for o in coll.all_objects if o.type=='MESH']
    if not objs: return None
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.hide_set(False);o.hide_viewport=False;o.select_set(True)
    for o in objs:
        if o.data.users>1: o.data=o.data.copy()
    bpy.context.view_layer.objects.active=objs[0]
    bpy.ops.object.convert(target='MESH')
    bpy.ops.object.join()
    ob=bpy.context.view_layer.objects.active;ob.name=name
    if ob.data.users>1: ob.data=ob.data.copy()
    before=tris(ob)
    if planar:
        m=ob.modifiers.new('pl','DECIMATE');m.decimate_type='DISSOLVE';m.angle_limit=0.09;bpy.ops.object.modifier_apply(modifier='pl')
    mid=tris(ob)
    if ratio<1:
        m=ob.modifiers.new('co','DECIMATE');m.decimate_type='COLLAPSE';m.ratio=ratio;bpy.ops.object.modifier_apply(modifier='co')
    log(name,before,mid,tris(ob))
    return ob
# 1) shrink the window/door assets that get instanced everywhere
for cn,ratio in [('ASSET_完整一扇窗_上下两格',0.35),('ASSET_门格心_单组折线卷花',0.5)]:
    c=bpy.data.collections.get(cn)
    if c: join_decimate(c,cn+'_lite',ratio)
# 2) make collection instances real inside the building collections
keep=[c for c in bpy.data.collections if re.match(r'^\d\d',c.name) and not c.name.startswith('99') and not c.name.startswith('90')]
empties=[o for c in keep for o in c.all_objects if o.type=='EMPTY' and o.instance_collection]
log('instances',len(empties))
bpy.ops.object.select_all(action='DESELECT')
for e in empties: e.hide_set(False);e.select_set(True)
if empties:
    bpy.context.view_layer.objects.active=empties[0];bpy.ops.object.duplicates_make_real(use_base_parent=True,use_hierarchy=False)
# 3) decimate heavy columns / bricks
for cn,ratio in [('12A_外圈廊柱与柱础',0.3),('12B_内圈房屋柱与柱础',0.3),('13_扩建地台_12x9m',0.5),('04_如意踏跺',0.4),('35_居室月洞窗',0.5)]:
    c=bpy.data.collections.get(cn)
    if c: join_decimate(c,cn+'_lite',ratio,planar=True)
# 4) select export set: all mesh objects whose top collection is a keep collection (incl. realized instances)
def top(o):
    return o.users_collection[0].name if o.users_collection else ''
sel=[]
for o in bpy.data.objects:
    if o.type!='MESH': continue
    cn=top(o)
    if re.match(r'^\d\d',cn) and not cn.startswith('99') and not cn.startswith('90'):
        if not o.hide_get(): sel.append(o)
    elif o.name.startswith('ASSET_') and o.name.endswith('_lite'):
        pass
# realized instances land in the active collection of the empty's collection -> fine
bpy.ops.object.select_all(action='DESELECT')
tot=0
for o in sel:
    o.select_set(True);tot+=tris(o)
log('export objects',len(sel),'tris',tot)
bpy.ops.export_scene.gltf(filepath=r"/Users/dengyudie/Downloads/dgy_models/xiaoxiang_lite.glb",export_format='GLB',use_selection=True,export_apply=True,export_image_format='NONE',export_materials='EXPORT',export_yup=True)
log('done')
