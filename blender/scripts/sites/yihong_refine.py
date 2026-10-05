"""怡红院外檐精修（参考图：朱红廊柱、彩画梁枋、一色精雕槅扇、檐下金漆彩绘）。在 blender/yihong.blend 上就地修改：
  1. （槅扇、屋面保持 .blend 原材质 M_朱漆、M_灰瓦；早先换过的会换回）
  3. 梁上“包袱”贴苏式彩画（M_彩画_baofu，tex/caihua_baofu.jpg；按每块包袱的外接框铺满）；
  4. 抱厦、厢房、游廊、连廊外檐：柱头两侧贴金透雕雀替（M_雕花_huaya/huayar），柱间倒挂楣子（M_雕花_meizi，步步锦，tex/diao_meizi.png）。
可重复执行：先删掉上次加的 YHR_* 对象、把材质恢复成脚本处理前的样子再做。
用法：python3 blender/scripts/sites/yihong_refine.py
之后：export_glb.py → pack_glb.mjs（第三参用现有 models/b/yihong.wasm 继承节点名）→ glb_cut 重开门洞、剪窗心（见 blender/README.md）。
"""
import bpy, bmesh, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
BLEND = os.path.join(ROOT, 'blender', 'yihong.blend')
bpy.ops.wm.open_mainfile(filepath=BLEND)


def mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    if b:
        b.inputs['Base Color'].default_value = (*rgb, 1)
    return m


# ---- 复位（可重复执行） ----
for o in [o for o in bpy.data.objects if o.name.startswith('YHR_')]:
    bpy.data.objects.remove(o, do_unlink=True)
M_RED = bpy.data.materials['M_朱漆']
M_TILE = bpy.data.materials['M_灰瓦']
M_BAOFU = bpy.data.materials['M_包袱']

M_CH = mat('M_彩画_baofu', (0.85, 0.82, 0.7))
M_HY = mat('M_雕花_huaya', (0.7, 0.5, 0.15))
M_HYR = mat('M_雕花_huayar', (0.7, 0.5, 0.15))
M_MZ = mat('M_雕花_meizi', (0.1, 0.3, 0.2))


def set_mat(o, new, old=None):
    for s in o.material_slots:
        if old is None or s.material in (old, ) or (s.material and s.material.name == (old.name if old else '')):
            s.material = new


# 槅扇、屋面沿用 .blend 原来的 M_朱漆、M_灰瓦（带照片贴图和做旧；网页烘焙后照搬）。早先版本换过，这里换回
for o in bpy.data.objects:
    if o.type != 'MESH':
        continue
    for s_ in o.material_slots:
        if s_.material and s_.material.name == 'M_槅扇':
            s_.material = M_RED
        elif s_.material and s_.material.name == 'M_YH_灰瓦':
            s_.material = M_TILE


# ---- 包袱：每块外接框 UV ----
def loose_parts(bm):
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        st, grp = [f], []
        seen.add(f.index)
        while st:
            g = st.pop(); grp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index); st.append(h)
        out.append(grp)
    return out


for o in bpy.data.objects:
    if o.type != 'MESH' or not o.name.endswith('_baofu'):
        continue
    for s in o.material_slots:
        s.material = M_CH
    me = o.data
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.get('UVMap') or bm.loops.layers.uv.new('UVMap')
    W = o.matrix_world
    for grp in loose_parts(bm):
        pts = [W @ v.co for f in grp for v in f.verts]
        xs, ys, zs = [p.x for p in pts], [p.y for p in pts], [p.z for p in pts]
        horiz_x = (max(xs) - min(xs)) >= (max(ys) - min(ys))
        a0, a1 = (min(xs), max(xs)) if horiz_x else (min(ys), max(ys))
        z0, z1 = min(zs), max(zs)
        for f in grp:
            for l in f.loops:
                p = W @ l.vert.co
                a = p.x if horiz_x else p.y
                l[uvl].uv = ((a - a0) / max(a1 - a0, 1e-6), (p.z - z0) / max(z1 - z0, 1e-6))
    bm.to_mesh(me); bm.free()


# ---- 雀替、倒挂楣子 ----
def quad(name, m, p0, p1, z0, z1, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    """竖直四边形：底边 p0→p1（xy），z0..z1，双面；uv 依次为 左下、右下、右上、左上。"""
    me = bpy.data.meshes.new(name)
    v = [(p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1)]
    me.from_pydata(v, [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name='UVMap')
    for i, l in enumerate(me.loops):
        uvl.data[l.index].uv = uv[l.vertex_index]
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def colonnade(cols, axis, face_off, top, mz=0.34, qt=(0.62, 0.42), cr=0.15, skip=()):
    """cols：一排柱的位置（沿 axis 方向排列，xy），face_off：雀替、楣子相对柱心朝外挪的距离（避免和额枋共面），
    top：额枋下皮高。每柱两侧雀替，相邻柱之间倒挂楣子（skip 里的间不挂）。"""
    cols = sorted(cols, key=lambda c: c[0] if axis == 'x' else c[1])
    for i, c in enumerate(cols):
        for sd in (-1, 1):
            if (sd < 0 and i == 0) or (sd > 0 and i == len(cols) - 1):
                continue
            a = (c[0] if axis == 'x' else c[1])
            p0 = a + sd * cr
            p1 = a + sd * (cr + qt[0])
            P = (lambda t: (t, c[1] + face_off)) if axis == 'x' else (lambda t: (c[0] + face_off, t))
            # 雀替：直角贴柱、贴枋；贴图 huaya 的直角在左上，柱右侧用 huaya，左侧用 huayar
            m = M_HY if sd > 0 else M_HYR
            uv = ((0, 0), (1, 0), (1, 1), (0, 1)) if sd > 0 else ((1, 0), (0, 0), (0, 1), (1, 1))
            quad('YHR_雀替', m, P(p0), P(p1), top - qt[1], top, uv)
        if i < len(cols) - 1 and i not in skip:
            a = (c[0] if axis == 'x' else c[1]) + cr
            b = (cols[i + 1][0] if axis == 'x' else cols[i + 1][1]) - cr
            P = (lambda t: (t, c[1] + face_off * 1.02)) if axis == 'x' else (lambda t: (c[0] + face_off * 1.02, t))
            L = (b - a) / 1.4
            quad('YHR_楣子', M_MZ, P(a), P(b), top - mz, top, ((0, 0), (L, 0), (L, 1), (0, 1)))


# 抱厦前檐：柱 x=±8、±5、±1.8，y=4.0，额枋下皮 3.74；明间（中间那间）有帐幔，楣子照挂（在帐幔以上）
for off in (-0.13, 0.13):
    colonnade([(x, 4.0) for x in (-8, -5, -1.8, 1.8, 5, 8)], 'x', off, 3.74)
# 东西厢房前廊：柱 x=±10.5，y=2.1、-1.2、-4.6、-7.9，柱顶 4.0 → 额枋下皮约 3.64
for sx in (-1, 1):
    for off in (-0.13, 0.13):
        colonnade([(sx * 10.5, y) for y in (2.1, -1.2, -4.6, -7.9)], 'y', off, 3.64, cr=0.16)
# 东西游廊内侧一排：x=±17.4，柱顶 3.05 → 额枋下皮约 2.8；连廊 y=4.9
for sx in (-1, 1):
    ys = (-17.1, -14.7, -12.3, -9.8, -7.4, -5.0, -2.6, -0.2, 2.3, 4.9, 7.1)
    for off in (-0.1, 0.1):
        colonnade([(sx * 17.4, y) for y in ys], 'y', off, 2.8, mz=0.3, qt=(0.45, 0.32), cr=0.12)
        colonnade([(sx * x, 4.9) for x in (9.2, 11.1, 13.2, 15.3, 17.4)], 'x', off, 2.8, mz=0.3, qt=(0.45, 0.32), cr=0.12)

bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
print('REFINE done', len([o for o in bpy.data.objects if o.name.startswith('YHR_')]), 'pieces')
