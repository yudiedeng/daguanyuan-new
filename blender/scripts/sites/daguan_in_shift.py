"""大观楼改样后，顾恩思义殿（正殿）前移 16 m：殿内陈设随之前移（缀锦阁、含芳阁不动）。只能跑一次（看 col.json 里 daguan_in 的标记）。
用法：flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_in_shift.py
  1. blender/daguan_in.blend：|x| < 20 的顶点 y −16，重存、导出 models/b/daguan_in.wasm；
  2. col.json['daguan_in']：|x| < 20 的碰撞框网页 z +16。
网页里 PROPS.daguan_in、INTER_DEF.daguan_in 的正殿坐标、GATES 里的正殿门同样 +16（index.html / game.js 手改）。
"""
import bpy, os, json, subprocess

DH = -16.0
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
cp = os.path.join(ROOT, 'models', 'b', 'col.json')
C = json.load(open(cp, encoding='utf-8'))
if C.get('daguan_in_shift') == DH:
    raise SystemExit('已移过')
blend = os.path.join(ROOT, 'blender', 'daguan_in.blend')
bpy.ops.wm.open_mainfile(filepath=blend)
n = 0
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    mw = o.matrix_world; inv = mw.inverted()
    for v in o.data.vertices:
        w = mw @ v.co
        if abs(w.x) < 20:
            w.y += DH; v.co = inv @ w; n += 1
    o.data.update()
print('moved verts', n)
bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
glb = '/tmp/daguan_in.glb'
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type == 'MESH' and o.visible_get(): o.select_set(True)
bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                          export_image_format='NONE', export_materials='EXPORT', export_yup=True)
out = os.path.join(ROOT, 'models', 'b', 'daguan_in.wasm')
subprocess.run(['node', os.path.join(ROOT, 'blender', 'scripts', 'web', 'pack_glb.mjs'), glb, out, out], check=True)
for b in C['daguan_in']:
    if abs(b[0]) < 20: b[1] = round(b[1] - DH, 3)
C['daguan_in_shift'] = DH
json.dump(C, open(cp, 'w', encoding='utf-8'), ensure_ascii=False)
print('col daguan_in shifted')
