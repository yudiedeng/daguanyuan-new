"""潇湘馆前院小瀑布的叠石（Blender 建模），导出 models/t/xx_falls.wasm。
用法：python3 blender/scripts/flora/build_falls.py --out /tmp/zhu
位置：泉沟在正房台阶前回环的那一弯里（院落局部 C=(-3.9, 7.3)），水从后面两块高石的石缝里出来，
向东（朝弯头）跌三级：唇口高 0.95 / 0.6 / 0.28 m（离地面），最后落进泉沟。
坐标：院落局部，网页 x→X、网页 z→−Y、离地高→Z。与 index.html 的 FALLS 同一组数。
每级是一块顶面削平的承水石（顶面比水面低 1.5 cm），两侧夹石，后面两块高石（约 1.3 m），
四周散几块小石。材质只有一个 xx_falls_rock（网页里贴三向投影石纹、顶上长苔、近水湿暗）。
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, noise
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/zhu'
os.makedirs(OUT, exist_ok=True)
C = Vector((-3.9, -7.3, 0))                  # 院落局部 (x,z)=(-3.9,7.3)
D = Vector((1.0, 0.1, 0)).normalized()       # 朝弯头（网页 z 往小处偏一点 → Blender Y 往正）
S = Vector((-D.y, D.x, 0))
LIPS = [(0.45, 0.95), (0.9, 0.6), (1.3, 0.28)]   # (沿 D 的距离, 唇口高)
rnd = random.Random(5)
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()


def rock(c, r, sx, sy, sz, top=None, a=None):
    g = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    sd = Vector((rnd.uniform(0, 99), rnd.uniform(0, 99), rnd.uniform(0, 99)))
    a = rnd.uniform(0, 6.28) if a is None else a
    for v in g['verts']:
        d = v.co.copy()
        k = 1 + 0.22 * noise.noise(d * 1.4 + sd) + 0.08 * noise.noise(d * 3.5 + sd)
        p = Vector((d.x * sx, d.y * sy, d.z * sz)) * r * k
        p = Vector((p.x * math.cos(a) - p.y * math.sin(a), p.x * math.sin(a) + p.y * math.cos(a), p.z))
        v.co = c + p
        if top is not None and v.co.z > top:
            v.co.z = top - 0.006 * (1 + noise.noise(v.co * 9))


def at(dist, side=0.0):
    return C + D * dist + S * side


ang = math.atan2(D.y, D.x)
# 后面两块高石，中间留一道缝出水
rock(at(0.05, -0.32) + Vector((0, 0, 0.55)), 0.42, 1.0, 0.8, 1.6, a=ang + 0.3)
rock(at(0.05, 0.34) + Vector((0, 0, 0.5)), 0.4, 0.9, 0.85, 1.5, a=ang - 0.4)
rock(at(-0.25, 0.0) + Vector((0, 0, 0.45)), 0.45, 1.0, 1.0, 1.3)
# 三级承水石：顶面在唇口高 −1.5 cm，前沿就是唇口
prev = 0.15
for i, (dl, h) in enumerate(LIPS):
    mid = (prev + dl) / 2
    length = dl - prev + 0.12
    rock(at(mid - 0.03) + Vector((0, 0, h - 0.015 - 0.2)), 0.5, length * 1.05, 0.34 + 0.04 * i, 0.4, top=h - 0.015, a=ang)
    for side in (-1, 1):                                   # 两侧夹石，比水面高
        rock(at(mid, side * (0.26 + 0.03 * i)) + Vector((0, 0, h - 0.05)), 0.17 + 0.02 * rnd.random(), 1.0, 0.8, 1.1)
    prev = dl + 0.12
# 跌入泉沟处两块、四周散石
for (dl, sd, r, z) in ((1.55, -0.32, 0.13, 0.0), (1.6, 0.3, 0.11, 0.0), (0.6, -0.55, 0.16, 0.05), (0.2, 0.62, 0.14, 0.05), (-0.5, -0.4, 0.18, 0.05), (-0.4, 0.5, 0.15, 0.05)):
    rock(at(dl, sd) + Vector((0, 0, z)), r, 1.0, 0.8, 0.7)
me = bpy.data.meshes.new('xx_falls_rock'); bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = True
me.materials.append(bpy.data.materials.new('xx_falls_rock'))
bpy.context.collection.objects.link(bpy.data.objects.new('xx_falls_rock', me))
print('falls tris', len(me.polygons))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'xx_falls.glb'), export_format='GLB', export_yup=True, export_materials='EXPORT')
# node blender/scripts/web/pack_prop.mjs /tmp/zhu/xx_falls.glb models/t/xx_falls.wasm 99999 16 keep
