import bpy
import math
import os
from mathutils import Vector


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "blender", "output")
BLEND_PATH = os.path.join(OUT_DIR, "xiaoxiang_platform_v01.blend")
GLB_PATH = os.path.join(OUT_DIR, "xiaoxiang_platform_v01.glb")
RENDER_PATH = os.path.join(OUT_DIR, "xiaoxiang_platform_v01.png")


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        pass


def collection(name):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def move_to_collection(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)


def material_principled(name, base, roughness=0.7, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*base, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def stone_material():
    mat = bpy.data.materials.new("MAT_青灰石_微风化")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    noise = nodes.new("ShaderNodeTexNoise")
    ramp = nodes.new("ShaderNodeValToRGB")
    bump = nodes.new("ShaderNodeBump")
    tex = nodes.new("ShaderNodeTexCoord")
    noise.inputs["Scale"].default_value = 5.5
    noise.inputs["Detail"].default_value = 4.0
    noise.inputs["Roughness"].default_value = 0.75
    ramp.color_ramp.elements[0].color = (0.12, 0.15, 0.15, 1)
    ramp.color_ramp.elements[1].color = (0.34, 0.39, 0.38, 1)
    bsdf.inputs["Roughness"].default_value = 0.82
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.08
    links.new(tex.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def brick_material():
    mat = bpy.data.materials.new("MAT_深灰青砖_台帮")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for node in list(nodes):
        nodes.remove(node)
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    brick = nodes.new("ShaderNodeTexBrick")
    bump = nodes.new("ShaderNodeBump")
    brick.offset = 0.5
    brick.offset_frequency = 2
    brick.squash = 1.0
    brick.inputs["Color1"].default_value = (0.075, 0.09, 0.09, 1)
    brick.inputs["Color2"].default_value = (0.13, 0.15, 0.15, 1)
    brick.inputs["Mortar"].default_value = (0.025, 0.028, 0.027, 1)
    brick.inputs["Scale"].default_value = 6.0
    brick.inputs["Mortar Size"].default_value = 0.028
    brick.inputs["Mortar Smooth"].default_value = 0.01
    bsdf.inputs["Roughness"].default_value = 0.88
    bump.inputs["Strength"].default_value = 0.35
    bump.inputs["Distance"].default_value = 0.035
    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], brick.inputs["Vector"])
    links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(brick.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def tile_material():
    mat = bpy.data.materials.new("MAT_廊面青砖")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.115, 0.14, 0.135, 1)
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat


def moss_material():
    mat = bpy.data.materials.new("MAT_苔痕")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.055, 0.12, 0.07, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    return mat


def cube(name, size, location, mat, col, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("石材倒角", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    move_to_collection(obj, col)
    return obj


def cylinder(name, radius, depth, location, mat, col, vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("石础柔边", "BEVEL")
    mod.width = 0.018
    mod.segments = 2
    move_to_collection(obj, col)
    return obj


def add_text(name, body, location, size, col, color_mat, rotation=(math.radians(67), 0, 0)):
    curve = bpy.data.curves.new(name + "_curve", "FONT")
    curve.body = body
    curve.align_x = "CENTER"
    curve.size = size
    curve.extrude = 0.004
    obj = bpy.data.objects.new(name, curve)
    obj.location = location
    obj.rotation_euler = rotation
    curve.materials.append(color_mat)
    col.objects.link(obj)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    clear_scene()

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 760
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = RENDER_PATH
    scene.render.film_transparent = False
    scene.world.color = (0.025, 0.035, 0.03)

    parts = collection("01_台明结构")
    edge = collection("02_阶条石与角石")
    paving = collection("03_青砖台面_实例")
    steps = collection("04_如意踏跺")
    bases = collection("05_柱础_装配接口")
    veneer = collection("06_台帮青砖_实例")
    context = collection("90_环境参照")
    guides = collection("99_尺寸说明")
    lights = collection("Lighting_Camera")

    core_mat = material_principled("MAT_台芯", (0.12, 0.105, 0.085), 1.0)
    brick_mat = brick_material()
    stone_mat = stone_material()
    tile_mat = tile_material()
    moss_mat = moss_material()
    ground_mat = material_principled("MAT_湿润园土地", (0.045, 0.065, 0.045), 1.0)
    label_mat = material_principled("MAT_尺寸字", (0.7, 0.55, 0.22), 0.55, 0.08)

    # Overall three-bay garden residence platform: 10.8 m x 7.2 m x 0.48 m.
    cube("PLATFORM_台芯", (10.52, 6.92, 0.34), (0, 0, 0.17), core_mat, parts)
    cube("PLATFORM_前台帮_青砖", (10.2, 0.22, 0.36), (0, -3.46, 0.18), brick_mat, parts, 0.008)
    cube("PLATFORM_后台帮_青砖", (10.2, 0.22, 0.36), (0, 3.46, 0.18), brick_mat, parts, 0.008)
    cube("PLATFORM_左台帮_青砖", (0.22, 6.72, 0.36), (-5.26, 0, 0.18), brick_mat, parts, 0.008)
    cube("PLATFORM_右台帮_青砖", (0.22, 6.72, 0.36), (5.26, 0, 0.18), brick_mat, parts, 0.008)

    # Four understated corner stones.
    for sx in (-1, 1):
        for sy in (-1, 1):
            cube(
                f"CORNER_角柱石_{'东' if sx > 0 else '西'}{'北' if sy > 0 else '南'}",
                (0.34, 0.34, 0.36),
                (sx * 5.23, sy * 3.43, 0.18), stone_mat, edge, 0.012
            )

    # Top perimeter edge stones, separate for future editing.
    cube("EDGE_前阶条石", (10.8, 0.30, 0.12), (0, -3.45, 0.42), stone_mat, edge, 0.014)
    cube("EDGE_后阶条石", (10.8, 0.30, 0.12), (0, 3.45, 0.42), stone_mat, edge, 0.014)
    cube("EDGE_左阶条石", (0.30, 6.60, 0.12), (-5.25, 0, 0.42), stone_mat, edge, 0.014)
    cube("EDGE_右阶条石", (0.30, 6.60, 0.12), (5.25, 0, 0.42), stone_mat, edge, 0.014)

    # Linked brick paving instances. 0.44 x 0.22 m with 10 mm joints.
    tile_w, tile_d, gap = 0.44, 0.22, 0.012
    usable_w, usable_d = 10.18, 6.58
    cols = int(usable_w // (tile_w + gap))
    rows = int(usable_d // (tile_d + gap))
    start_x = -((cols - 1) * (tile_w + gap)) / 2
    start_y = -((rows - 1) * (tile_d + gap)) / 2
    master = cube("PAVING_青砖_母件", (tile_w, tile_d, 0.055), (start_x, start_y, 0.4475), tile_mat, paving, 0.004)
    for row in range(rows):
        row_offset = 0.0
        for col_i in range(cols):
            if row == 0 and col_i == 0:
                obj = master
            else:
                obj = master.copy()
                obj.data = master.data
                paving.objects.link(obj)
            obj.name = f"PAVING_青砖_R{row+1:02d}_C{col_i+1:02d}"
            obj.location = (start_x + col_i * (tile_w + gap) + row_offset,
                            start_y + row * (tile_d + gap), 0.4475)

    # Actual three-course brick veneer avoids texture stretching on thin vertical faces.
    side_brick_mat = material_principled("MAT_台帮青砖块", (0.085, 0.105, 0.102), 0.92)
    joint = 0.014
    course_h = 0.105
    long_count = 24
    long_len = (10.18 - (long_count - 1) * joint) / long_count
    short_count = 16
    short_len = (6.70 - (short_count - 1) * joint) / short_count
    for course in range(3):
        z = 0.055 + course * (course_h + joint)
        for i in range(long_count):
            x = -5.09 + long_len / 2 + i * (long_len + joint)
            for y, side_name in ((-3.585, "南"), (3.585, "北")):
                cube(f"BRICK_台帮_{side_name}_R{course+1}_C{i+1:02d}",
                     (long_len, 0.045, course_h), (x, y, z), side_brick_mat, veneer, 0.003)
        for i in range(short_count):
            y = -3.35 + short_len / 2 + i * (short_len + joint)
            for x, side_name in ((-5.385, "西"), (5.385, "东")):
                cube(f"BRICK_台帮_{side_name}_R{course+1}_C{i+1:02d}",
                     (0.045, short_len, course_h), (x, y, z), side_brick_mat, veneer, 0.003)

    # Three-step ruyi stair: lower courses are wider, with no flanking bands.
    cube("STEP_如意踏跺_一级", (3.60, 0.99, 0.16), (0, -4.095, 0.08), stone_mat, steps, 0.018)
    cube("STEP_如意踏跺_二级", (3.00, 0.66, 0.16), (0, -3.93, 0.24), stone_mat, steps, 0.018)
    cube("STEP_如意踏跺_三级", (2.40, 0.33, 0.16), (0, -3.765, 0.40), stone_mat, steps, 0.018)

    # 4 x 3 column-grid interfaces for later assembly, each kept independent.
    xs = (-4.5, -1.5, 1.5, 4.5)
    ys = (-2.45, 0.0, 2.45)
    for yi, y in enumerate(ys, 1):
        for xi, x in enumerate(xs, 1):
            cylinder(f"COLBASE_柱础_Y{yi}_X{xi}", 0.235, 0.12, (x, y, 0.54), stone_mat, bases)

    # Ground and a restrained moss fringe are context only, not part of the platform asset.
    cube("CONTEXT_地面", (17.0, 14.0, 0.08), (0, 0.2, -0.06), ground_mat, context, 0.02)
    for x, y, sx, sy in [(-5.35, -2.0, .14, 2.4), (5.35, 1.1, .13, 1.7),
                         (-3.5, 3.56, 1.5, .11), (3.7, -3.57, 1.2, .10)]:
        cube("CONTEXT_苔痕", (sx, sy, 0.018), (x, y, 0.015), moss_mat, context, 0.01)

    add_text("LABEL_尺寸", "潇湘馆地台  10.8 m × 7.2 m × 0.48 m", (0, 4.15, 0.03), 0.34, guides, label_mat)
    add_text("LABEL_踏跺", "三级如意踏跺  3 × 0.16 m", (0, -5.0, 0.03), 0.28, guides, label_mat)

    # Camera and calm overcast studio lighting.
    bpy.ops.object.light_add(type="AREA", location=(-4.5, -6.5, 10.5))
    key = bpy.context.object
    key.name = "LIGHT_主光"
    key.data.energy = 1700
    key.data.shape = "DISK"
    key.data.size = 7.0
    move_to_collection(key, lights)
    look_at(key, (0, 0, 0))

    bpy.ops.object.light_add(type="AREA", location=(6.0, 3.5, 6.0))
    fill = bpy.context.object
    fill.name = "LIGHT_补光"
    fill.data.energy = 900
    fill.data.size = 6.0
    fill.data.color = (0.65, 0.78, 0.72)
    move_to_collection(fill, lights)
    look_at(fill, (0, 0, 0.5))

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 8))
    sun = bpy.context.object
    sun.name = "LIGHT_天光"
    sun.data.energy = 1.3
    sun.rotation_euler = (math.radians(28), math.radians(-22), math.radians(-28))
    move_to_collection(sun, lights)

    bpy.ops.object.camera_add(location=(13.7, -15.2, 11.3))
    camera = bpy.context.object
    camera.name = "CAMERA_地台总览"
    camera.data.lens = 52
    camera.data.sensor_width = 36
    look_at(camera, (0, -0.25, 0.35))
    move_to_collection(camera, lights)
    scene.camera = camera

    # Neutral color management for material judgement.
    scene.view_settings.look = "AgX - Medium High Contrast"

    # Metadata stays with the scene.
    scene["asset_name"] = "潇湘馆地台 v01"
    scene["period_basis"] = "清代中期小式园林建筑"
    scene["platform_dimensions_m"] = "10.8 x 7.2 x 0.48"
    scene["stair_type"] = "三级素面青石如意踏跺"
    scene["construction_note"] = "青砖台帮、青石阶条、青砖铺地、独立柱础；非须弥座"

    # Keep hidden paving overflow out of exports.
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    guides.hide_render = True
    context.hide_render = False
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    bpy.ops.object.select_all(action="DESELECT")
    for col in (parts, edge, paving, steps, bases, veneer):
        for obj in col.objects:
            if not obj.hide_render and not obj.hide_viewport:
                obj.select_set(True)
    bpy.context.view_layer.objects.active = next(obj for obj in parts.objects if obj.type == "MESH")
    bpy.ops.export_scene.gltf(filepath=GLB_PATH, export_format="GLB", use_selection=True,
                              export_apply=True, export_materials="EXPORT")
    bpy.ops.object.select_all(action="DESELECT")

    scene.render.filepath = RENDER_PATH
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    print(f"BLEND={BLEND_PATH}")
    print(f"GLB={GLB_PATH}")
    print(f"RENDER={RENDER_PATH}")
    print(f"OBJECTS={len(bpy.data.objects)}")


if __name__ == "__main__":
    build()
