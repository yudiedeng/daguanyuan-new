"""潇湘馆前院小瀑布的叠石（Blender 建模），导出 models/t/xx_falls.wasm。
用法：python3 blender/scripts/flora/build_falls.py --out /tmp/zhu
位置：泉沟在正房台阶前回环的那一弯里（院落局部 C=(-3.9, 7.3)），水从后面两块高石的石缝里出来，
向东（朝弯头）跌三级：唇口高 0.95 / 0.6 / 0.28 m（离地面），最后落进泉沟。
坐标：院落局部，网页 x→X、网页 z→−Y、离地高→Z。与 index.html 的 FALLS 同一组数。
按黄石叠山：棱角分明的块石层层出挑，三级唇口左右错开、宽窄不一，两侧夹石左高右低，后面两块竖石夹缝出水。材质只有一个 xx_falls_rock（网页里贴三向投影石纹、顶上长苔、近水湿暗）。
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, noise
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/zhu'
os.makedirs(OUT, exist_ok=True)
C = Vector((-3.9, -7.3, 0))                  # 院落局部 (x,z)=(-3.9,7.3)
D = Vector((1.0, 0.1, 0)).normalized()       # 朝弯头（网页 z 往小处偏一点 → Blender Y 往正）
S = Vector((-D.y, D.x, 0))
LIPS = [(0.4, 0.95, 0.0, 0.07), (0.85, 0.62, 0.12, 0.12), (1.28, 0.3, -0.06, 0.17)]   # (沿 D 的距离, 唇口高, 左右偏, 水帘半宽)——与 index.html FLIPS 同
rnd = random.Random(9)
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()


def block(c, sx, sy, sz, yaw=0.0, top=None, rough=0.025):
    """黄石块：方块细分后加噪声，棱角分明但不齐整；top 给定时顶面削平（承水）。c 为底面中心。"""
    g = bmesh.ops.create_cube(bm, size=1.0)
    vs = g['verts']
    bmesh.ops.subdivide_edges(bm, edges=list({e for v in vs for e in v.link_edges}), cuts=3, use_grid_fill=True)
    vs = list({v for f in bm.faces for v in f.verts if v.tag is False})
    sd = Vector((rnd.uniform(0, 99), rnd.uniform(0, 99), rnd.uniform(0, 99)))
    for v in vs:
        if v.select:
            continue
        v.select = True
        p = v.co.copy()
        n = Vector((noise.noise(p * 2.3 + sd), noise.noise(p * 2.3 + sd + Vector((5, 0, 0))), noise.noise(p * 2.3 + sd + Vector((0, 7, 0)))))
        q = Vector((p.x * sx, p.y * sy, (p.z + 0.5) * sz)) + n * rough * 2 + Vector((0, 0, noise.noise(p * 6 + sd) * rough * 0.5))
        q = Vector((q.x * math.cos(yaw) - q.y * math.sin(yaw), q.x * math.sin(yaw) + q.y * math.cos(yaw), q.z))
        v.co = c + q
        if top is not None and v.co.z > top:
            v.co.z = top - 0.004 * (1 + noise.noise(v.co * 11))


def stack(c, sx, sy, sz, yaw=0.0, rough=0.03):
    """高石改成两三层错开、大小不一的横向石板叠起来（黄石的层理），不做成竖柱。"""
    n = 1 if sz < 0.4 else (2 if sz < 0.8 else 3)
    z = 0.0
    hs = [rnd.uniform(0.8, 1.2) for _ in range(n)]
    for k in range(n):
        h = sz * hs[k] / sum(hs)
        f = 1.0 - 0.12 * k
        off = Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.06, 0.06), z))
        block(c + off, sx * f * rnd.uniform(0.9, 1.15), sy * f * rnd.uniform(0.9, 1.15), h + 0.01, yaw + rnd.uniform(-0.25, 0.25), rough=rough)
        z += h


def at(dist, side=0.0):
    return C + D * dist + S * side


ang = math.atan2(D.y, D.x)
# 后面：两块竖石夹一道缝（出水），一块斜倚的
stack(at(-0.05, -0.3), 0.5, 0.42, 1.25, ang + 0.25, rough=0.035)
stack(at(-0.02, 0.28), 0.44, 0.38, 1.05, ang - 0.35, rough=0.035)
stack(at(-0.32, 0.05), 0.6, 0.66, 0.8, ang + 0.1, rough=0.03)
block(at(-0.2, 0.55), 0.38, 0.32, 0.55, ang + 0.8, rough=0.03)
# 三级承水石：层层出挑、左右错开、宽窄不一；底下垫石
prev = 0.05
for i, (dl, h, sd, hw) in enumerate(LIPS):
    mid = (prev + dl) / 2 + 0.015
    L = dl - prev + 0.05
    th = 0.16 + 0.05 * i
    block(at(mid, sd) - Vector((0, 0, 0)) + Vector((0, 0, h - th)), L, hw * 2 + 0.26 + 0.05 * rnd.random(), th + 0.01, ang + rnd.uniform(-0.12, 0.12), top=h - 0.015, rough=0.018)
    if h - th > 0.08:
        block(at(mid - 0.05, sd + rnd.uniform(-0.05, 0.05)), L * 0.9, hw * 2 + 0.2, h - th, ang + rnd.uniform(-0.2, 0.2), rough=0.03)
    prev = dl - 0.02
# 两侧夹石：左边高、右边低，不对称
for (dl, sd, sx, sy, sz, yaw) in ((0.35, -0.34, 0.3, 0.22, 1.12, 0.3), (0.75, -0.36, 0.26, 0.2, 0.72, -0.2), (1.2, -0.38, 0.22, 0.2, 0.42, 0.5),
                                  (0.42, 0.3, 0.24, 0.2, 0.98, -0.4), (0.95, 0.38, 0.3, 0.24, 0.66, 0.1), (1.45, 0.34, 0.18, 0.16, 0.2, 0.7)):
    stack(at(dl, sd), sx * 1.15, sy * 1.2, sz, ang + yaw, rough=0.03)
# 落水处与四周散石
for (dl, sd, sx, sy, sz, yaw) in ((1.62, -0.33, 0.16, 0.12, 0.1, 0.4), (1.66, 0.3, 0.12, 0.1, 0.08, -0.6), (0.65, -0.62, 0.2, 0.16, 0.12, 1.0),
                                  (0.15, 0.68, 0.18, 0.14, 0.1, 0.2), (-0.55, -0.42, 0.22, 0.18, 0.14, 0.7), (-0.5, 0.48, 0.16, 0.14, 0.1, -0.3)):
    block(at(dl, sd), sx, sy, sz, ang + yaw, rough=0.02)
for v in bm.verts:
    v.select = False
me = bpy.data.meshes.new('xx_falls_rock'); bm.to_mesh(me); bm.free()
for p in me.polygons:
    p.use_smooth = False
me.materials.append(bpy.data.materials.new('xx_falls_rock'))
bpy.context.collection.objects.link(bpy.data.objects.new('xx_falls_rock', me))
print('falls tris', len(me.polygons))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'xx_falls.glb'), export_format='GLB', export_yup=True, export_materials='EXPORT')
# node blender/scripts/web/pack_prop.mjs /tmp/zhu/xx_falls.glb models/t/xx_falls.wasm 99999 16 keep
