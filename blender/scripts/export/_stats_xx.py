
import bpy,json
dg=bpy.context.evaluated_depsgraph_get()
st={}
for c in bpy.data.collections:
    n=0;t=0;inst=0
    for o in c.objects:
        if o.type!='MESH': continue
        n+=1
        me=o.evaluated_get(dg).to_mesh() if False else None
        try:
            ev=o.evaluated_get(dg);m=ev.to_mesh();t+=sum(len(p.vertices)-2 for p in m.polygons);ev.to_mesh_clear()
        except Exception as e: pass
    st[c.name]={"objs":n,"tris":t,"hidden":c.hide_render or c.hide_viewport}
json.dump(st,open(r"/Users/dengyudie/Downloads/dgy_models/xiaoxiang_stats.json","w"),ensure_ascii=False)
