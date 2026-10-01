import bpy
import os
import math
import json
from mathutils import Vector

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
source = os.path.join(out, 'xiaoxiang_platform_v01.blend')
target = os.path.join(out, 'xiaoxiang_platform_v02_uv_ready.blend')
bpy.ops.wm.open_mainfile(filepath=source)

# UV units represent metres: one repeat covers 1 m, without object-size stretching.
seen = set()
count = 0
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH' or not obj.name.startswith(('PLATFORM_', 'EDGE_', 'CORNER_', 'PAVING_', 'BRICK_', 'STEP_', 'COLBASE_')):
        continue
    mesh = obj.data
    count += 1
    if mesh.as_pointer() in seen:
        continue
    seen.add(mesh.as_pointer())
    uv = mesh.uv_layers.get('UV_Metric_1m') or mesh.uv_layers.new(name='UV_Metric_1m')
    mesh.uv_layers.active = uv
    uv.active_render = True
    for poly in mesh.polygons:
        normal = poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        # Cylindrical sides unwrap continuously around the circumference.
        if obj.name.startswith('COLBASE_') and abs(normal.z) < 0.5:
            angles = [math.atan2(mesh.vertices[mesh.loops[i].vertex_index].co.y,
                                 mesh.vertices[mesh.loops[i].vertex_index].co.x) for i in poly.loop_indices]
            if max(angles) - min(angles) > math.pi:
                angles = [a + 2 * math.pi if a < 0 else a for a in angles]
            for i, a in zip(poly.loop_indices, angles):
                v = mesh.vertices[mesh.loops[i].vertex_index].co
                uv.data[i].uv = (a * math.hypot(v.x, v.y), v.z)
        else:
            axes = [(1, 2), (0, 2), (0, 1)][axis]
            for i in poly.loop_indices:
                v = mesh.vertices[mesh.loops[i].vertex_index].co
                uv.data[i].uv = (v[axes[0]], v[axes[1]])

base_stone = bpy.data.materials['MAT_青灰石_微风化']
column_stone = base_stone.copy()
column_stone.name = 'MAT_柱础青石'
for obj in bpy.data.objects:
    if obj.name.startswith('COLBASE_'):
        obj.data.materials.clear()
        obj.data.materials.append(column_stone)

materials = [bpy.data.materials[n] for n in ('MAT_廊面青砖', 'MAT_台帮青砖块', 'MAT_青灰石_微风化', 'MAT_柱础青石')]
for mat in materials:
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    frame = nodes.new('NodeFrame')
    frame.label = '待用户贴图 / UV: 1 repeat = 1 metre'
    frame.name = 'USER_TEXTURE_INPUTS'
    uv = nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UV_Metric_1m'
    uv.parent = frame
    uv.location = (-800, 0)
    mapping = nodes.new('ShaderNodeMapping')
    mapping.name = 'TEXTURE_SCALE'
    mapping.label = '纹理尺度：默认 1 米'
    mapping.parent = frame
    mapping.location = (-600, 0)
    links.new(uv.outputs['UV'], mapping.inputs['Vector'])
    for index, kind in enumerate(('BaseColor', 'Roughness', 'Normal')):
        tex = nodes.new('ShaderNodeTexImage')
        tex.name = 'INPUT_' + kind
        tex.label = '待贴图：' + kind
        tex.extension = 'REPEAT'
        tex.parent = frame
        tex.location = (-350, -index * 290)
        links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
    # Empty image sockets remain disconnected so the existing preview stays visible.
    normal = nodes.new('ShaderNodeNormalMap')
    normal.name = 'NORMAL_MAP_READY'
    normal.uv_map = 'UV_Metric_1m'
    normal.parent = frame
    normal.location = (0, -580)
    links.new(nodes['INPUT_Normal'].outputs['Color'], normal.inputs['Color'])
    mat['texture_status'] = 'Awaiting user images; connect BaseColor to Principled Base Color after loading.'

for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.shading.type = 'MATERIAL'
            space.overlay.show_overlays = False
            space.region_3d.view_rotation = bpy.context.scene.camera.rotation_euler.to_quaternion()
            space.region_3d.view_location = Vector((0, 0, 0.25))
            space.region_3d.view_distance = 17
bpy.data.collections['99_尺寸说明'].hide_viewport = True
bpy.context.scene['texture_status'] = 'UV ready; user base-color images pending'
bpy.ops.wm.save_as_mainfile(filepath=target)
material_names = [m.name for m in materials]
bpy.ops.wm.open_mainfile(filepath=target)
assert all(bpy.data.materials[name].node_tree.nodes.get('INPUT_BaseColor') for name in material_names)
result = {'file': target, 'mesh_objects_with_metric_uv': count, 'unique_meshes': len(seen), 'texture_images_loaded': 0, 'reopen_verified': True}
print(json.dumps(result, ensure_ascii=False))
