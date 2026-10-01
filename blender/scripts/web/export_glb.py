"""把一个院落 .blend 导出为网页用的原始 GLB（之后再用 pack_glb.mjs 压缩）。
用法：python3 export_glb.py <in.blend> <out.glb>   （需要 pip install bpy）
规则：跳过 __preview / 9x 开头的辅助集合和 FONT 对象（匾额字由网页 plaqueOn 绘制）。
"""
import bpy, sys
src, dst = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=src)
skip = lambda c: c.name.startswith('__') or c.name[:2] in ('90', '99')
bpy.ops.object.select_all(action='DESELECT')
n = 0
for o in bpy.context.scene.objects:
    if o.type != 'MESH' or any(skip(c) for c in o.users_collection):
        continue
    if not o.visible_get() or o.hide_render:
        continue
    o.select_set(True); n += 1
print('EXPORT objects', n)
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='NONE', export_materials='EXPORT', export_yup=True)
