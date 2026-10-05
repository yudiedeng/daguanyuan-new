"""潇湘馆泉沟两岸的卵石、沟中露头的石头、墙根入水处的叠石（Blender 建模），导出 models/t/xx_rill_rocks.wasm。
用法：python3 blender/scripts/flora/build_rill_rocks.py --out /tmp/zhu
坐标：潇湘馆院落局部（与 index.html 的 RILL_PTS 同一套；网页 x→X，网页 z→−Y，高 →Z），水面在 0。
  两岸：沿中线每 0.2–0.3 m 一块圆卵石，离中线 0.29–0.4 m，大小 8–24 cm，压扁、半埋；
  沟中：RILL_PTS 第 MID 号点上各一块露出水面几公分的石头（网页里浅滩白花就在这些点）；
  入水处：墙根出水口（约 0.42 m）出水，沟头两级石阶跌下，两侧夹石。
材质只有一个 xx_rill_rock（网页里用三向投影的石头贴图），顶面偏青苔色靠网页着色。
"""
import bpy, bmesh, math, random, os, sys
from mathutils import Vector, noise
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else '/tmp/zhu'
os.makedirs(OUT, exist_ok=True)
R = [3,-11.8,3.11,-11.4,3.34,-10.81,3.44,-10.49,3.5,-10.15,3.51,-9.83,3.45,-9.52,3.28,-9.24,3,-9,2.57,-8.81,1.99,-8.65,1.29,-8.52,0.52,-8.4,-0.3,-8.29,-1.14,-8.18,-1.96,-8.06,-2.73,-7.93,-3.42,-7.78,-4,-7.6,-4.49,-7.41,-4.93,-7.23,-5.33,-7.05,-5.7,-6.86,-6.02,-6.65,-6.32,-6.42,-6.58,-6.14,-6.81,-5.82,-7.02,-5.44,-7.2,-5,-7.35,-4.46,-7.45,-3.82,-7.51,-3.1,-7.54,-2.32,-7.55,-1.53,-7.54,-0.72,-7.51,0.06,-7.47,0.79,-7.43,1.44,-7.4,2,-7.37,2.47,-7.34,2.88,-7.31,3.25,-7.27,3.57,-7.14,4.11,-6.93,4.57,-6.6,5,-6.37,5.2,-6.09,5.39,-5.78,5.55,-5.44,5.69,-5.08,5.82,-4.71,5.93,-4.35,6.04,-4,6.13,-3.68,6.22,-3.14,6.36,-2.61,6.42,-2.12,6.42,-1.73,6.43,-1.4,6.6,-1.47,7.07,-1.69,7.49,-2.01,7.92,-2.4,8.27,-2.82,8.49,-3.34,8.55,-3.94,8.54,-4.25,8.54,-4.57,8.56,-4.89,8.59,-5.2,8.67,-5.5,8.8,-5.8,8.98,-6.1,9.21,-6.41,9.47,-6.72,9.76,-7.02,10.07,-7.33,10.38,-7.63,10.69,-7.93,10.99,-8.22,11.26,-8.5,11.5,-8.77,11.71,-9.04,11.89,-9.31,12.05,-9.57,12.21,-10.07,12.5,-10.55,12.82,-11,13.2,-11.22,13.44,-11.43,13.7,-11.65,14,-11.86,14.3,-12.06,14.61,-12.24,14.9,-12.41,15.18,-12.7,15.64,-12.8,15.8]
P = [Vector((R[i], -R[i + 1], 0)) for i in range(0, len(R), 2)]
MID = [8, 18, 27, 37, 47, 58, 69, 80, 90]          # 网页 rif 用同一组
rnd = random.Random(31)
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()


def stone(c, r, flat=0.55, bury=0.35, rot=None):
    g = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    sd = Vector((rnd.uniform(0, 100), rnd.uniform(0, 100), rnd.uniform(0, 100)))
    sx, sy = rnd.uniform(0.8, 1.25), rnd.uniform(0.75, 1.1)
    a = rot if rot is not None else rnd.uniform(0, 6.28)
    for v in g['verts']:
        d = v.co.copy()
        k = 1 + 0.18 * noise.noise(d * 1.6 + sd) + 0.06 * noise.noise(d * 4 + sd)
        p = Vector((d.x * sx, d.y * sy, d.z * flat)) * r * k
        p = Vector((p.x * math.cos(a) - p.y * math.sin(a), p.x * math.sin(a) + p.y * math.cos(a), p.z))
        v.co = c + p + Vector((0, 0, r * flat * (1 - 2 * bury)))


# 两岸
s = 0.0
for i in range(1, len(P)):
    a, b = P[i - 1], P[i]
    seg = (b - a).length
    d = (b - a).normalized()
    n = Vector((-d.y, d.x, 0))
    t = 0.0
    while t < seg:
        p = a + d * t
        for side in (-1, 1):
            if rnd.random() < 0.12:
                continue
            r = rnd.uniform(0.04, 0.12)
            stone(p + n * side * (0.29 + r * 0.6 + rnd.uniform(-0.02, 0.05)), r, flat=rnd.uniform(0.45, 0.7), bury=rnd.uniform(0.25, 0.45))
        t += rnd.uniform(0.18, 0.3)
# 沟中露头石
for k in MID:
    p = P[k] + Vector((rnd.uniform(-0.06, 0.06), rnd.uniform(-0.06, 0.06), 0))
    stone(p, rnd.uniform(0.08, 0.12), flat=0.6, bury=0.35)
    if rnd.random() < 0.6:
        stone(p + Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0)), rnd.uniform(0.05, 0.07), flat=0.6, bury=0.4)
# 入水处：墙根出水口两侧高石，沟头两级石阶（扁平的承水石，顶面略低于水面），各级两侧夹石，潭边两块
#   d 为离墙根出水口（P[0] 往墙里 0.32 m）的距离，与 index.html buildRill 的 stepY 同一套
up = (P[0] - P[1]).normalized()
W0 = P[0] + up * 0.32
path = [W0] + P
def along(d):
    acc = 0.0
    for i in range(1, len(path)):
        l = (path[i] - path[i - 1]).length
        if acc + l >= d:
            t = (d - acc) / l
            dd = (path[i] - path[i - 1]).normalized()
            return path[i - 1] + (path[i] - path[i - 1]) * t, dd
        acc += l
    return path[-1], (path[-1] - path[-2]).normalized()
for (d, side, r, top, flat) in ((0.05, -0.42, 0.22, 0.6, 0.75), (0.05, 0.42, 0.2, 0.56, 0.75),
                                (0.12, 0, 0.2, 0.39, 0.4), (0.3, -0.36, 0.19, 0.5, 0.7), (0.3, 0.36, 0.18, 0.47, 0.7),
                                (0.55, 0, 0.22, 0.19, 0.4), (0.75, -0.36, 0.17, 0.32, 0.7), (0.75, 0.36, 0.16, 0.3, 0.7),
                                (1.05, -0.45, 0.15, 0.15, 0.7), (1.1, 0.46, 0.14, 0.13, 0.7)):
    c, dd = along(d)
    n = Vector((-dd.y, dd.x, 0))
    p = c + n * side
    stone(Vector((p.x, p.y, top - r * flat * 1.4)), r, flat=flat, bury=0.3, rot=math.atan2(dd.y, dd.x))
# 出水口几块
end = P[-1]; ed = (P[-1] - P[-2]).normalized(); en = Vector((-ed.y, ed.x, 0))
for (f, side, r) in ((0.1, -0.45, 0.2), (0.1, 0.45, 0.17), (0.35, -0.3, 0.15), (0.35, 0.35, 0.14)):
    stone(end + ed * f + en * side, r, flat=0.65, bury=0.3)

me = bpy.data.meshes.new('xx_rill_rock'); bm.to_mesh(me); bm.free()
for poly in me.polygons:
    poly.use_smooth = True
m = bpy.data.materials.new('xx_rill_rock'); me.materials.append(m)
o = bpy.data.objects.new('xx_rill_rock', me); bpy.context.collection.objects.link(o)
print('rill rocks tris', len(me.polygons))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'xx_rill_rocks.glb'), export_format='GLB', export_yup=True, export_materials='EXPORT')
# node blender/scripts/web/pack_prop.mjs /tmp/zhu/xx_rill_rocks.glb models/t/xx_rill_rocks.wasm 99999 16 keep
