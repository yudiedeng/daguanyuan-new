"""把院落 .blend 的材质搬到网页（“Blender 原样”）：
  1. 做旧层烘进顶点色：每种材质临时改成“去掉照片贴图和底色、只留做旧”的版本（缝隙 AO、竖向雨痕、污渍、
     屋面青苔；纯程序材质则整个底色），接到自发光，用 Cycles 烘焙 EMIT 到顶点色 Col；
  2. 照片贴图（PolyHaven 的 diff/nor）转灰度、存 tex/bk_<名>_d.jpg、_n.jpg；
  3. 各材质改名 M_<院>B_<原名>，导出带顶点色的 GLB；写 tex/bk_<院>.json：每种材质的底色（sRGB）、贴图、投影尺度、粗糙度、法线强度。
     网页 bmat 读这份 json：底色 × 灰度照片贴图（世界坐标三向投影，同 .blend 的盒式投影）× 顶点色。
  雕花_*、彩画_* 不动（网页另有贴图）。
用法：python3 blender/scripts/web/bake_court.py blender/yihong.blend yh out.glb [采样数=16]
  再 node blender/scripts/web/pack_glb.mjs out.glb models/b/<id>.wasm models/b/<id>.wasm（pack_glb 对 *B_* 材质保留顶点色）
"""
import bpy, sys, os, json, math
src, tag, dst = sys.argv[1:4]
SAMPLES = int(sys.argv[4]) if len(sys.argv) > 4 else 16
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
TEX = os.path.join(ROOT, 'tex')
bpy.ops.wm.open_mainfile(filepath=os.path.abspath(src))
from PIL import Image
import numpy as np

skip_coll = lambda c: c.name.startswith('__') or c.name[:2] in ('90', '99')
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH' and o.visible_get() and not o.hide_render
        and not any(skip_coll(c) for c in o.users_collection)]
KEEP = lambda name: name.startswith('M_雕花') or name.startswith('M_彩画_')

white = bpy.data.images.new('__white', 4, 4)
white.pixels = [1.0] * 64

lin2srgb = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
recipes, done_img = {}, {}


def save_img(img, kind):
    """照片贴图转灰度（.blend 里先去饱和再乘底色）存 jpg；法线图原样。"""
    base = img.name.rsplit('_', 1)[0].replace('.jpg', '')
    fn = f'bk_{base}_{"g" if kind == "d" else kind}.jpg'   # 灰度照片贴图存 _g（网页约定 _d.jpg 按线性读，这里要按 sRGB）
    if fn in done_img:
        return fn
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    if kind == 'd':
        # pixels 是线性值；灰度后再转 sRGB 存
        g = px @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        g = np.where(g <= 0.0031308, g * 12.92, 1.055 * np.power(np.clip(g, 0, 1), 1 / 2.4) - 0.055)
        Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8), 'L').save(os.path.join(TEX, fn), quality=85)
    else:
        Image.fromarray((np.clip(px, 0, 1) * 255).astype(np.uint8)).save(os.path.join(TEX, fn), quality=88)
    done_img[fn] = 1
    return fn


def is_tint(n):
    """底色那一乘：MULTIPLY 混合，A 来自“照片贴图→去饱和”的 HUE_SAT（不是后面做旧的那一乘）。"""
    if n.type != 'MIX' or n.blend_type != 'MULTIPLY' or not n.inputs[6].is_linked:
        return False
    h = n.inputs[6].links[0].from_node
    return h.type == 'HUE_SAT' and h.inputs['Color'].is_linked and h.inputs['Color'].links[0].from_node.type == 'TEX_IMAGE'


bake_mats = {}
for m in list(bpy.data.materials):
    if not m.users or not m.use_nodes or KEEP(m.name):
        continue
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    if not bsdf:
        continue
    imgs = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image]
    rec = {'rough': round(bsdf.inputs['Roughness'].default_value, 2) if not bsdf.inputs['Roughness'].is_linked else 0.75,
           'metal': round(bsdf.inputs['Metallic'].default_value, 2)}
    tint = (1, 1, 1)
    if imgs:
        diff = next((n for n in imgs if '_diff' in n.image.name), None)
        nor = next((n for n in imgs if '_nor' in n.image.name), None)
        mp = next((n for n in nt.nodes if n.type == 'MAPPING'), None)
        rec['s'] = round(1.0 / mp.inputs['Scale'].default_value[0], 3) if mp else 1.0   # 一格的米数
        if diff:
            rec['a'] = save_img(diff.image, 'd')
        if nor:
            rec['n'] = save_img(nor.image, 'n')
            nm = next((n for n in nt.nodes if n.type == 'NORMAL_MAP'), None)
            rec['nk'] = round(nm.inputs['Strength'].default_value, 2) if nm else 0.5
        mx = [n for n in nt.nodes if is_tint(n)]
        if mx:
            tint = tuple(mx[0].inputs[7].default_value[:3])
        sat2 = [n for n in nt.nodes if n.type == 'HUE_SAT' and n.inputs['Color'].is_linked and n.inputs['Color'].links[0].from_node.type == 'MIX']
        if sat2:                             # 乘完底色后又降了饱和度
            s_ = sat2[0].inputs['Saturation'].default_value
            l_ = sum(tint) / 3
            tint = tuple(l_ + (c - l_) * s_ for c in tint)
    rec['c'] = '#%02x%02x%02x' % tuple(int(round(min(1, lin2srgb(min(c, 1.0))) * 255)) for c in tint)
    if max(tint) > 1:                         # 白灰墙底色 >1：多出的亮度放到 k
        rec['k'] = round(max(tint), 2)
    recipes[f'{tag}B_' + m.name[2:]] = rec
    # 烘焙用的副本：图片换白、底色换白，Base Color 那一路接到自发光
    b = m.copy()
    b.name = '__bake_' + m.name
    bt = b.node_tree
    for n in bt.nodes:
        if n.type == 'TEX_IMAGE':
            n.image = white
        if is_tint(n):
            n.inputs[7].default_value = (1, 1, 1, 1)
    bb = bt.nodes.get('Principled BSDF')
    out = next(n for n in bt.nodes if n.type == 'OUTPUT_MATERIAL')
    em = bt.nodes.new('ShaderNodeEmission')
    if bb.inputs['Base Color'].is_linked:
        bt.links.new(bb.inputs['Base Color'].links[0].from_socket, em.inputs['Color'])
    else:
        em.inputs['Color'].default_value = bb.inputs['Base Color'].default_value
    bt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    bake_mats[m.name] = b

# 换上烘焙材质、建顶点色
orig = {}
for o in objs:
    orig[o.name] = [s.material for s in o.material_slots]
    me = o.data
    if 'Col' in me.color_attributes:
        me.color_attributes.remove(me.color_attributes['Col'])
    ca = me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT')       # 按顶点存，导出后顶点还能焊接
    me.color_attributes.active_color = ca
    for s in o.material_slots:
        if s.material and s.material.name in bake_mats:
            s.material = bake_mats[s.material.name]

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = False
sc.render.bake.target = 'VERTEX_COLORS'
bpy.ops.object.select_all(action='DESELECT')
bake_objs = [o for o in objs if any(s.material and s.material.name.startswith('__bake_') for s in o.material_slots)]
for o in bake_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = bake_objs[0]
print('BAKE', len(bake_objs), 'objects, samples', SAMPLES, flush=True)
bpy.ops.object.bake(type='EMIT')
print('BAKE done', flush=True)

# 换回原材质、改名导出
for o in objs:
    for s, m in zip(o.material_slots, orig[o.name]):
        s.material = m
for m in bpy.data.materials:
    if m.name.startswith('__bake_'):
        continue
    if m.users and not KEEP(m.name) and m.name.startswith('M_') and f'{tag}B_' + m.name[2:] in recipes:
        m.name = f'M_{tag}B_' + m.name[2:]
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(dst)), os.path.basename(src).replace('.blend', '_baked.blend')))
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', use_selection=True, export_apply=True, export_image_format='NONE',
                          export_materials='EXPORT', export_yup=True, export_vertex_color='ACTIVE')
with open(os.path.join(TEX, f'bk_{tag}.json'), 'w') as f:
    json.dump(recipes, f, ensure_ascii=False, indent=1)
print('RECIPES', len(recipes), 'IMGS', len(done_img))
