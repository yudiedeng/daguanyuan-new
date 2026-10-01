"""室内陈设构件库（bpy）。各院落的 build_<id>.py 用它在 Blender 坐标里搭家具，
存成 blender/<id>_in.blend，导出 models/b/<id>_in.wasm，并把碰撞框写进 models/b/col.json。

坐标：与该院落 .blend 相同（网页里与外壳模型同一变换）。Blender X → 网页 x，-Y → 网页 z，Z → 网页 y。
材质：只给名字和近似底色；网页按名字在 index.html 的 BMR 表里重赋（导出时去掉 UV）。
"""
import bpy, bmesh, math, json, os, random, subprocess, sys
from contextlib import contextmanager
from mathutils import Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# 近似底色（仅供 Blender 内预览；网页以 BMR 为准）
COLORS = {
    '紫檀': '#3a1e16', '花梨': '#7a4a2a', '黄花梨': '#9a6a3a', '朱漆': '#7a2a21', '黑漆': '#1d1a18', '描金': '#e0b855',
    '本色木': '#b28f66', '旧木': '#8a7358', '竹竿': '#b9a25f', '黄竹': '#c4ad63', '藤编': '#a88a55',
    '锦缎': '#9a2a2a', '锦缎黄': '#c8a040', '锦帐': '#c98a8a', '碧纱': '#9fbfa6', '青纱': '#7f98a0', '素绸': '#e8e2d2',
    '青布': '#33456a', '白布': '#e9e4d4', '粗布': '#9a8a6c', '红毡': '#7a2a26', '蒲席': '#b49a62',
    '书函': '#2e3f5c', '书函黄': '#9a7a3a', '书页': '#e9dfc6', '画绢': '#d9ccaa', '画心': '#e6dcc0', '绫裱': '#6f8a8a',
    '瓷白': '#efeee8', '青花': '#2f4f8a', '青瓷': '#9fb8a8', '土定': '#d6cbb2', '紫砂': '#7a4030', '粉彩': '#e8b0a8',
    '铜': '#6b6a52', '镜面': '#dfe3e0', '穿衣镜': '#dfe3e0', '玉': '#cfe0c8', '石': '#8f8e86', '太湖石': '#9d9d95', '汉白玉': '#efece4',
    '菊黄': '#e8c04a', '花红': '#d0485a', '花白': '#f6f2ea', '叶绿': '#527f3c', '墨': '#17161a', '烛': '#efe4cc',
    '窗纸': '#e8dcbf', '天花': '#2e5a4c', '天花心': '#2e4c72', '美人画': '#e6dcc0', '碧绿凿花砖': '#5f7a66', '方砖地': '#b7afa2', '夯土地': '#9a8663', '白灰墙': '#e6e2d8',
    '油壁': '#6e4b38', '炭': '#2a2420', '铁': '#3a3a3a', '陶': '#8a5a3a', '稻草': '#c9b070',
}


def _hex(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


class Kit:
    def __init__(self, bid):
        self.id = bid
        self.M = Matrix.Identity(4)
        self.geo = {}          # material -> bmesh
        self.cols = []         # [x0,y0,z0,x1,y1,z1,walk]
        self.rng = random.Random(hash(bid) & 0xffff)

    # ---------------- transforms ----------------
    @contextmanager
    def at(self, x=0, y=0, z=0, rot=0):
        """局部坐标：平移后绕 Z 旋转 rot 度。"""
        old = self.M
        self.M = old @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, 'Z')
        try:
            yield
        finally:
            self.M = old

    def _bm(self, m):
        if m not in self.geo:
            self.geo[m] = bmesh.new()
        return self.geo[m]

    def _add(self, m, src, mat):
        """把临时 bmesh src 以 mat 变换并入材质 m。"""
        src.transform(self.M @ mat)
        me = bpy.data.meshes.new('tmp')
        src.to_mesh(me)
        src.free()
        self._bm(m).from_mesh(me)
        bpy.data.meshes.remove(me)

    # ---------------- primitives ----------------
    def box(self, m, x0, y0, z0, x1, y1, z1, col=False):
        b = bmesh.new()
        bmesh.ops.create_cube(b, size=1.0)
        mat = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)) @ Matrix.Diagonal(
            (max(abs(x1 - x0), 1e-4), max(abs(y1 - y0), 1e-4), max(abs(z1 - z0), 1e-4), 1))
        self._add(m, b, mat)
        if col:
            self.col(x0, y0, z0, x1, y1, z1)

    def boxc(self, m, cx, cy, z0, sx, sy, sz, col=False):
        self.box(m, cx - sx / 2, cy - sy / 2, z0, cx + sx / 2, cy + sy / 2, z0 + sz, col)

    def cyl(self, m, x, y, z0, z1, r, seg=12, r2=None):
        b = bmesh.new()
        bmesh.ops.create_cone(b, cap_ends=True, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=z1 - z0)
        self._add(m, b, Matrix.Translation((x, y, (z0 + z1) / 2)))

    def rod(self, m, p0, p1, r, seg=8):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        if L < 1e-5:
            return
        b = bmesh.new()
        bmesh.ops.create_cone(b, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=L)
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        self._add(m, b, Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4())

    def bar(self, m, p0, p1, w, h):
        """方截面杆（宽 w 高 h），从 p0 到 p1，截面一边保持水平。"""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        L = d.length
        if L < 1e-5:
            return
        ax = d.normalized()
        up = Vector((0, 0, 1)) if abs(ax.z) < 0.95 else Vector((1, 0, 0))
        side = ax.cross(up).normalized()
        up2 = side.cross(ax).normalized()
        R = Matrix((side, up2, ax)).transposed().to_4x4()
        b = bmesh.new()
        bmesh.ops.create_cube(b, size=1.0)
        self._add(m, b, Matrix.Translation((p0 + p1) / 2) @ R @ Matrix.Diagonal((w, h, L, 1)))

    def sph(self, m, x, y, z, rx, ry=None, rz=None, seg=10):
        b = bmesh.new()
        bmesh.ops.create_uvsphere(b, u_segments=seg, v_segments=max(4, seg // 2), radius=1.0)
        self._add(m, b, Matrix.Translation((x, y, z)) @ Matrix.Diagonal((rx, ry or rx, rz or rx, 1)))

    def lathe(self, m, x, y, z0, prof, seg=16, cap=True):
        """prof: [(r, dz), ...] 自下而上。"""
        b = bmesh.new()
        rings = []
        for r, dz in prof:
            ring = [b.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), dz)) for i in range(seg)]
            rings.append(ring)
        for a, c in zip(rings, rings[1:]):
            for i in range(seg):
                j = (i + 1) % seg
                b.faces.new((a[i], a[j], c[j], c[i]))
        if cap:
            for ring, flip in ((rings[0], True), (rings[-1], False)):
                if ring[0].co.xy.length > 1e-4:
                    b.faces.new(ring[::-1] if flip else ring)
        self._add(m, b, Matrix.Translation((x, y, z0)))

    def poly_panel(self, m, outer, holes, t, y=0.0):
        """XZ 平面上的板（厚 t，沿 Y 居中于 y）：outer 为外轮廓点列，holes 为内孔点列表。
        用“外框—孔”径向条带三角化：每个孔须为凸形且位于外框内；多孔时外框需事先切成单孔格子。"""
        assert len(holes) == 1
        hole = holes[0]
        n = len(hole)
        cx = sum(p[0] for p in hole) / n
        cz = sum(p[1] for p in hole) / n
        # 外框按孔的每个点做射线求交 → 一一对应的外点
        def ray(px, pz):
            dx, dz = px - cx, pz - cz
            best = None
            for k in range(len(outer)):
                ax, az = outer[k]
                bx, bz = outer[(k + 1) % len(outer)]
                ex, ez = bx - ax, bz - az
                den = dx * ez - dz * ex
                if abs(den) < 1e-9:
                    continue
                tt = ((ax - cx) * ez - (az - cz) * ex) / den
                uu = ((ax - cx) * dz - (az - cz) * dx) / den
                if tt > 0 and -1e-6 <= uu <= 1 + 1e-6 and (best is None or tt < best):
                    best = tt
            return (cx + dx * best, cz + dz * best)
        # 外框角点也要保住：把外框角点插入对应角度位置
        pts = []  # (angle, inner(x,z) or None, outer(x,z))
        for (px, pz) in hole:
            pts.append((math.atan2(pz - cz, px - cx), (px, pz), ray(px, pz)))
        for (ox, oz) in outer:
            a = math.atan2(oz - cz, ox - cx)
            pts.append((a, None, (ox, oz)))
        pts.sort(key=lambda p: p[0])
        # 角点的内点：在孔边上插值
        def hole_at(a):
            for k in range(n):
                p, q = hole[k], hole[(k + 1) % n]
                a0 = math.atan2(p[1] - cz, p[0] - cx)
                a1 = math.atan2(q[1] - cz, q[0] - cx)
                da = (a1 - a0) % (2 * math.pi)
                d = (a - a0) % (2 * math.pi)
                if d <= da + 1e-9:
                    f = d / da if da > 1e-9 else 0
                    return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
            return hole[0]
        ring = [(p[1] if p[1] else hole_at(p[0]), p[2]) for p in pts]
        b = bmesh.new()
        N = len(ring)
        F = [(b.verts.new((i[0], y - t / 2, i[1])), b.verts.new((o[0], y - t / 2, o[1]))) for i, o in ring]
        B = [(b.verts.new((i[0], y + t / 2, i[1])), b.verts.new((o[0], y + t / 2, o[1]))) for i, o in ring]
        for k in range(N):
            j = (k + 1) % N
            b.faces.new((F[k][0], F[j][0], F[j][1], F[k][1]))
            b.faces.new((B[k][1], B[j][1], B[j][0], B[k][0]))
            b.faces.new((F[k][0], B[k][0], B[j][0], F[j][0]))  # 孔壁
            b.faces.new((F[j][1], B[j][1], B[k][1], F[k][1]))  # 外壁
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        self._add(m, b, Matrix.Identity(4))

    def col(self, x0, y0, z0, x1, y1, z1, walk=False):
        pts = [self.M @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
        mn = [min(p[i] for p in pts) for i in range(3)]
        mx = [max(p[i] for p in pts) for i in range(3)]
        self.cols.append(mn + mx + [walk])

    # ---------------- 家具 ----------------
    def table(self, m, w, d, h, top=0.04, leg=0.05, apron=0.07, col=True, horse=True, stretch=False):
        """方桌/条桌（局部原点在桌面投影中心，桌面高 h）。"""
        self.box(m, -w / 2, -d / 2, h - top, w / 2, d / 2, h)
        self.box(m, -w / 2 + 0.02, -d / 2 + 0.02, h - top - 0.025, w / 2 - 0.02, d / 2 - 0.02, h - top)  # 束腰
        ins = 0.03
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (w / 2 - ins - leg / 2), sy * (d / 2 - ins - leg / 2)
                self.box(m, x - leg / 2, y - leg / 2, 0.0, x + leg / 2, y + leg / 2, h - top)
                if horse:
                    self.box(m, x - leg / 2 - sx * 0.0 - 0.006, y - leg / 2 - 0.006, 0, x + leg / 2 + 0.006, y + leg / 2 + 0.006, 0.05)
        for sy in (-1, 1):
            self.box(m, -w / 2 + ins, sy * (d / 2 - ins) - 0.01, h - top - 0.025 - apron, w / 2 - ins, sy * (d / 2 - ins) + 0.01, h - top - 0.025)
        for sx in (-1, 1):
            self.box(m, sx * (w / 2 - ins) - 0.01, -d / 2 + ins, h - top - 0.025 - apron, sx * (w / 2 - ins) + 0.01, d / 2 - ins, h - top - 0.025)
        if stretch:
            for sy in (-1, 1):
                self.box(m, -w / 2 + ins, sy * (d / 2 - ins - leg / 2) - 0.012, 0.12, w / 2 - ins, sy * (d / 2 - ins - leg / 2) + 0.012, 0.15)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, h)

    def qiaotou(self, m, w, d, h, col=True):
        """翘头案：平头案两端翘起，案腿缩进，带牙头。"""
        self.box(m, -w / 2, -d / 2, h - 0.05, w / 2, d / 2, h)
        for sx in (-1, 1):
            self.box(m, sx * w / 2 - (0.12 if sx > 0 else 0), -d / 2, h, sx * w / 2 + (0 if sx > 0 else 0.12), d / 2, h + 0.03)
            self.box(m, sx * w / 2 - (0.05 if sx > 0 else 0), -d / 2, h + 0.03, sx * w / 2 + (0 if sx > 0 else 0.05), d / 2, h + 0.07)
            x = sx * (w / 2 - 0.22)
            for sy in (-1, 1):
                self.box(m, x - 0.03, sy * (d / 2 - 0.06) - 0.025, 0, x + 0.03, sy * (d / 2 - 0.06) + 0.025, h - 0.05)
            self.box(m, x - 0.02, -d / 2 + 0.06, 0.03, x + 0.02, d / 2 - 0.06, 0.22)  # 托泥/挡板
            self.box(m, x - 0.015, -d / 2 + 0.08, 0.22, x + 0.015, d / 2 - 0.08, h - 0.12)
        for sy in (-1, 1):
            self.box(m, -w / 2 + 0.12, sy * (d / 2 - 0.05) - 0.012, h - 0.15, w / 2 - 0.12, sy * (d / 2 - 0.05) + 0.012, h - 0.05)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, h)

    def chair(self, m, style='guanmao', cushion=None, col=True):
        """官帽椅 / 圈椅（面朝 -Y，即椅背在 +Y）。"""
        W, D, S = 0.58, 0.46, 0.50
        lg = 0.035
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (W / 2 - lg), sy * (D / 2 - lg)
                top = S if sy < 0 else S + (0.55 if style == 'guanmao' else 0.42)
                if sy < 0:
                    top = S + (0.26 if style == 'guanmao' else 0.3)  # 前腿上延为鹅脖
                self.box(m, x - lg / 2, y - lg / 2, 0, x + lg / 2, y + lg / 2, top)
        self.box(m, -W / 2, -D / 2, S - 0.035, W / 2, D / 2, S)
        self.box(m, -W / 2 + 0.03, -D / 2 - 0.005, S - 0.11, W / 2 - 0.03, -D / 2 + 0.015, S - 0.035)  # 券口牙子
        for sy in (-1, 1):
            self.box(m, -W / 2 + lg, sy * (D / 2 - lg) - 0.012, 0.1, W / 2 - lg, sy * (D / 2 - lg) + 0.012, 0.13)  # 步步高赶枨
        for sx in (-1, 1):
            self.box(m, sx * (W / 2 - lg) - 0.012, -D / 2 + lg, 0.13, sx * (W / 2 - lg) + 0.012, D / 2 - lg, 0.16)
        # 靠背板（略后仰）
        self.bar(m, (0, D / 2 - 0.05, S), (0, D / 2 - 0.0, S + (0.52 if style == 'guanmao' else 0.4)), 0.16, 0.02)
        if style == 'guanmao':
            self.bar(m, (-W / 2 - 0.04, D / 2 - lg, S + 0.56), (W / 2 + 0.04, D / 2 - lg, S + 0.56), 0.04, 0.04)  # 搭脑出头
            for sx in (-1, 1):
                self.bar(m, (sx * (W / 2 - lg), D / 2 - lg, S + 0.26), (sx * (W / 2 + 0.02), -D / 2 + lg - 0.03, S + 0.26), 0.03, 0.03)
        else:
            # 圈椅：马蹄形扶手圈
            R = W / 2 - lg
            pts = []
            for i in range(13):
                a = math.pi * (i / 12)
                pts.append((-R * math.cos(a) * 1.05, D / 2 - lg - (R * 1.3) * (1 - math.sin(a)) * 0.9 + 0.0, S + 0.3 + 0.12 * math.sin(a)))
            pts = [(-W / 2 - 0.03, -D / 2 + 0.03, S + 0.3)] + pts + [(W / 2 + 0.03, -D / 2 + 0.03, S + 0.3)]
            for a, b in zip(pts, pts[1:]):
                self.rod(m, a, b, 0.018)
        if cushion:
            self.box(cushion, -W / 2 + 0.03, -D / 2 + 0.03, S, W / 2 - 0.03, D / 2 - 0.05, S + 0.04)
        if col:
            self.col(-W / 2, -D / 2, 0, W / 2, D / 2, S + 0.5)

    def stool(self, m, top=None, h=0.46, r=0.19, col=True):
        """绣墩（鼓墩）。"""
        prof = [(r * 0.8, 0), (r * 0.92, 0.04), (r, h * 0.3), (r * 1.02, h * 0.5), (r, h * 0.7), (r * 0.92, h - 0.04), (r * 0.8, h)]
        self.lathe(m, 0, 0, 0, prof, seg=16)
        for z in (0.05, h - 0.05):
            for i in range(14):
                a = 2 * math.pi * i / 14
                rr = r * 0.95
                self.sph(top or m, rr * math.cos(a), rr * math.sin(a), z, 0.012, seg=6)
        if col:
            self.col(-r, -r, 0, r, r, h)

    def kang(self, m, w, d, h=0.45, mat_cushion='锦缎', back=0.4, col=True):
        """罗汉床：三面围子，面朝 -Y。"""
        self.table(m, w, d, h, top=0.06, leg=0.07, apron=0.08, col=False)
        self.box(mat_cushion, -w / 2 + 0.05, -d / 2 + 0.05, h, w / 2 - 0.05, d / 2 - 0.12, h + 0.06)
        self.box(m, -w / 2, d / 2 - 0.05, h, w / 2, d / 2, h + back)  # 后围
        for sx in (-1, 1):
            self.box(m, sx * w / 2 - (0.05 if sx > 0 else 0), -d / 2 + 0.05, h, sx * w / 2 + (0 if sx > 0 else 0.05), d / 2, h + back * 0.75)
        # 围子上的攒接透格
        for i in range(1, 8):
            x = -w / 2 + i * w / 8
            self.box(m, x - 0.008, d / 2 - 0.055, h + 0.04, x + 0.008, d / 2 - 0.045, h + back - 0.04)
        # 炕桌
        with self.at(0, 0.02, h + 0.06):
            self.table(m, 0.8, 0.5, 0.3, top=0.03, leg=0.035, apron=0.05, col=False)
        # 靠背引枕
        for sx in (-1, 1):
            with self.at(sx * (w / 2 - 0.25), d / 2 - 0.18, h + 0.16, 90):
                self.cyl(mat_cushion, 0, 0, -0.18, 0.18, 0.09, seg=12)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, h + 0.1)

    def bed(self, m, w=2.1, d=1.5, h=0.5, H=2.3, curtain='锦帐', quilt='锦缎', pillow='锦缎黄', canopy=True,
            gauze_open=True, frieze=None, col=True):
        """架子床（拔步床式），床口朝 -Y。frieze：挂檐/门围子的材质（默认同木）。"""
        fz = frieze or m
        self.table(m, w, d, h, top=0.08, leg=0.08, apron=0.1, col=False)
        # 立柱
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.box(m, sx * (w / 2 - 0.04) - 0.035, sy * (d / 2 - 0.04) - 0.035, h, sx * (w / 2 - 0.04) + 0.035, sy * (d / 2 - 0.04) + 0.035, H)
        for sx in (-0.3, 0.3):
            self.box(m, sx * w - 0.03, -d / 2 + 0.01, h, sx * w + 0.03, -d / 2 + 0.07, H)  # 门柱
        # 顶架
        self.box(m, -w / 2, -d / 2, H - 0.05, w / 2, d / 2, H)
        self.box(m, -w / 2 + 0.05, -d / 2 + 0.05, H - 0.02, w / 2 - 0.05, d / 2 - 0.05, H - 0.01)
        # 挂檐（四面透雕）：上下框 + 竖棂
        for sy in (-1, 1):
            y = sy * (d / 2 - 0.02)
            self.box(fz, -w / 2, y - 0.02, H - 0.32, w / 2, y + 0.02, H - 0.28)
            n = int(w / 0.07)
            for i in range(n + 1):
                x = -w / 2 + 0.04 + i * (w - 0.08) / n
                self.box(fz, x - 0.007, y - 0.012, H - 0.28, x + 0.007, y + 0.012, H - 0.05)
            for i in range(int(w / 0.25)):
                x = -w / 2 + 0.12 + i * 0.25
                self.sph(fz, x, y, H - 0.17, 0.05, 0.02, 0.05, seg=8)
        for sx in (-1, 1):
            x = sx * (w / 2 - 0.02)
            self.box(fz, x - 0.02, -d / 2, H - 0.32, x + 0.02, d / 2, H - 0.28)
            for i in range(int(d / 0.07) + 1):
                y = -d / 2 + 0.04 + i * (d - 0.08) / int(d / 0.07)
                self.box(fz, x - 0.012, y - 0.007, H - 0.28, x + 0.012, y + 0.007, H - 0.05)
        # 三面围子（背+两侧，下半透格）
        self.box(m, -w / 2 + 0.04, d / 2 - 0.05, h, w / 2 - 0.04, d / 2 - 0.03, h + 0.9)
        for sx in (-1, 1):
            x = sx * (w / 2 - 0.04)
            for i in range(9):
                y = -d / 2 + 0.1 + i * (d - 0.2) / 8
                self.box(m, x - 0.01, y - 0.008, h, x + 0.01, y + 0.008, h + 0.5)
            self.box(m, x - 0.02, -d / 2 + 0.05, h + 0.48, x + 0.02, d / 2 - 0.05, h + 0.52)
        # 门围子（月洞门罩）：两扇站牙
        for sx in (-1, 1):
            x0, x1 = (sx * 0.3 * w, sx * (w / 2 - 0.04))
            for i in range(1, 6):
                x = x0 + (x1 - x0) * i / 6
                self.box(fz, x - 0.008, -d / 2 + 0.02, h, x + 0.008, -d / 2 + 0.05, H - 0.32)
            self.box(fz, min(x0, x1), -d / 2 + 0.02, h + 1.0, max(x0, x1), -d / 2 + 0.05, h + 1.04)
        # 被褥
        self.box(quilt, -w / 2 + 0.08, -d / 2 + 0.12, h, w / 2 - 0.08, d / 2 - 0.08, h + 0.1)
        self.box('素绸', -w / 2 + 0.1, -d / 2 + 0.14, h + 0.1, w / 2 - 0.1, d / 2 - 0.1, h + 0.13)
        # 叠被
        with self.at(0, d / 2 - 0.3, h + 0.13):
            for k, c in enumerate((quilt, '锦缎黄', quilt)):
                self.box(c, -0.55, -0.18, k * 0.07, 0.55, 0.18, k * 0.07 + 0.07)
        with self.at(-w / 2 + 0.35, 0, h + 0.13, 90):
            self.box(pillow, -0.3, -0.12, 0, 0.3, 0.12, 0.13)
        # 帐子：前面两幅挽起
        if curtain:
            for sx in (-1, 1):
                xs = sx * (w / 2 - 0.1)
                # 挽起的帐子：上宽下窄
                self.curtain(curtain, xs - 0.35 * sx, xs, -d / 2 + 0.08, h + 0.2, H - 0.32, gathered=True)
            # 背面与两侧帐子
            self.curtain(curtain, -w / 2 + 0.06, w / 2 - 0.06, d / 2 - 0.07, h + 0.9, H - 0.32)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, H)

    def curtain(self, m, x0, x1, y, z0, z1, gathered=False, folds=None):
        """XZ 面上的褶皱帐幔（之字形条带）。gathered：下端收拢。"""
        if x1 < x0:
            x0, x1 = x1, x0
        w = x1 - x0
        n = folds or max(4, int(w / 0.08))
        b = bmesh.new()
        top, bot = [], []
        cx = (x0 + x1) / 2
        for i in range(n + 1):
            f = i / n
            dy = 0.03 * (1 if i % 2 else -1)
            xt = x0 + w * f
            xb = (cx + (xt - cx) * 0.18) if gathered else xt
            top.append(b.verts.new((xt, y + dy, z1)))
            bot.append(b.verts.new((xb, y + dy * (0.4 if gathered else 1), z0)))
        for i in range(n):
            b.faces.new((bot[i], bot[i + 1], top[i + 1], top[i]))
        self._add(m, b, Matrix.Identity(4))
        if gathered:
            self.box('描金', cx - 0.06, y - 0.04, z0 + 0.35, cx + 0.06, y + 0.04, z0 + 0.39)

    # ---------------- 格架 ----------------
    def shelf(self, m, w, d, h, rows=4, books='书函', col=True, fill=0.75):
        """书架（亮格柜），正面朝 -Y。"""
        t = 0.025
        for sx in (-1, 1):
            self.box(m, sx * w / 2 - (t if sx > 0 else 0), -d / 2, 0, sx * w / 2 + (0 if sx > 0 else t), d / 2, h)
        self.box(m, -w / 2, d / 2 - 0.01, 0.08, w / 2, d / 2, h)
        self.box(m, -w / 2, -d / 2, h - t, w / 2, d / 2, h)
        self.box(m, -w / 2, -d / 2, 0, w / 2, d / 2, 0.08)
        zs = [0.08 + (h - 0.1) * i / rows for i in range(rows + 1)]
        for z in zs[1:-1]:
            self.box(m, -w / 2, -d / 2, z - t / 2, w / 2, d / 2, z + t / 2)
        for z0, z1 in zip(zs, zs[1:]):
            self.books(books, -w / 2 + t, w / 2 - t, -d / 2 + 0.03, d / 2 - 0.03, z0 + t / 2, z1 - t / 2 - 0.02, fill)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, h)

    def books(self, m, x0, x1, y0, y1, z0, zmax, fill=0.75):
        """线装书一函函平放成摞。"""
        r = self.rng
        x = x0 + 0.02
        while x < x1 - 0.2:
            bw = r.uniform(0.16, 0.24)
            if r.random() < fill:
                n = r.randint(1, 4)
                z = z0
                bd = min(y1 - y0, r.uniform(0.2, 0.26))
                for k in range(n):
                    bh = r.uniform(0.035, 0.06)
                    if z + bh > zmax:
                        break
                    c = m if r.random() < 0.8 else ('书函黄' if m == '书函' else m)
                    jx = r.uniform(-0.01, 0.01)
                    self.box(c, x + jx, y0, z, x + jx + bw, y0 + bd, z + bh)
                    self.box('书页', x + jx + 0.004, y0 - 0.002, z + 0.005, x + jx + bw - 0.004, y0 + 0.005, z + bh - 0.005)
                    z += bh
            x += bw + r.uniform(0.02, 0.06)

    def duobaoge(self, m, w, d, h, seed=1, col=True, items=True, back=True):
        """多宝格：不规则格子，格内摆瓶、鼎、书、盆景。正面朝 -Y。"""
        r = random.Random(seed)
        t = 0.025
        self.box(m, -w / 2, -d / 2, 0, w / 2, d / 2, 0.1)
        self.box(m, -w / 2, -d / 2, h - 0.06, w / 2, d / 2, h)
        for sx in (-1, 1):
            self.box(m, sx * w / 2 - (t if sx > 0 else 0), -d / 2, 0, sx * w / 2 + (0 if sx > 0 else t), d / 2, h)
        if back:
            self.box(m, -w / 2, d / 2 - 0.012, 0.1, w / 2, d / 2, h - 0.06)
        cells = []

        def split(x0, z0, x1, z1, depth):
            W, H = x1 - x0, z1 - z0
            if depth > 3 or (W < 0.55 and H < 0.55) or (depth >= 2 and r.random() < 0.3):
                cells.append((x0, z0, x1, z1))
                return
            if (W > H * 1.1 and W > 0.5) or H < 0.5:
                f = r.choice((0.35, 0.45, 0.55, 0.65))
                xm = x0 + W * f
                self.box(m, xm - t / 2, -d / 2, z0, xm + t / 2, d / 2, z1)
                split(x0, z0, xm - t / 2, z1, depth + 1)
                split(xm + t / 2, z0, x1, z1, depth + 1)
            else:
                f = r.choice((0.35, 0.45, 0.55, 0.65))
                zm = z0 + H * f
                self.box(m, x0, -d / 2, zm - t / 2, x1, d / 2, zm + t / 2)
                split(x0, z0, x1, zm - t / 2, depth + 1)
                split(x0, zm + t / 2, x1, z1, depth + 1)
        split(-w / 2 + t, 0.1, w / 2 - t, h - 0.06, 0)
        for (x0, z0, x1, z1) in cells:
            W, H = x1 - x0, z1 - z0
            # 格口：随机做成圆、海棠、方
            kind = r.random()
            if W > 0.3 and H > 0.3 and kind < 0.35:
                self.opening(m, x0, z0, x1, z1, -d / 2 + 0.006, 0.012, 'round' if kind < 0.18 else 'kui')
            if not items or H < 0.15:
                continue
            cx, y = (x0 + x1) / 2, 0.0
            pick = r.random()
            if pick < 0.3:
                self.vase(r.choice(('瓷白', '青花', '青瓷', '粉彩')), cx, y, z0, min(H * 0.8, 0.45), r.choice(('meiping', 'danping', 'yuhuchun')))
            elif pick < 0.45 and H > 0.2:
                self.ding('铜', cx, y, z0, min(H * 0.6, 0.25))
            elif pick < 0.65:
                self.books('书函', x0 + 0.01, x1 - 0.01, -d / 2 + 0.03, d / 2 - 0.03, z0, z1 - 0.03, 0.9)
            elif pick < 0.78 and H > 0.25:
                self.penjing(cx, y, z0, min(W * 0.7, 0.4))
            elif pick < 0.9:
                self.lathe(r.choice(('瓷白', '青花', '紫砂')), cx, y, z0, [(0.04, 0), (0.09, 0.03), (0.1, 0.06), (0.0, 0.06)], seg=14)  # 盘碗
            else:
                self.box('玉', cx - 0.12, y - 0.02, z0, cx + 0.12, y + 0.02, z0 + 0.03)  # 如意
                self.sph('玉', cx + 0.12, y, z0 + 0.04, 0.04, 0.03, 0.03, seg=8)
        if col:
            self.col(-w / 2, -d / 2, 0, w / 2, d / 2, h)

    def opening(self, m, x0, z0, x1, z1, y, t, shape='round'):
        """在矩形格口上贴一块带孔的花板（圆光、葵花、海棠）。"""
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        rx, rz = (x1 - x0) / 2 * 0.86, (z1 - z0) / 2 * 0.86
        n = 28
        hole = []
        for i in range(n):
            a = 2 * math.pi * i / n
            k = 1.0
            if shape == 'kui':
                k = 0.9 + 0.1 * abs(math.cos(3 * a))
            rr = min(rx, rz) if shape == 'round' else 1
            hole.append((cx + math.cos(a) * (rr if shape == 'round' else rx * k), cz + math.sin(a) * (rr if shape == 'round' else rz * k)))
        self.poly_panel(m, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], [hole], t, y)

    # ---------------- 器物 ----------------
    VASES = {
        'meiping': [(0.05, 0), (0.08, 0.04), (0.12, 0.35), (0.17, 0.7), (0.15, 0.85), (0.06, 0.93), (0.045, 0.97), (0.06, 1.0)],
        'danping': [(0.07, 0), (0.12, 0.05), (0.15, 0.25), (0.13, 0.4), (0.05, 0.55), (0.035, 0.85), (0.045, 1.0)],
        'yuhuchun': [(0.07, 0), (0.1, 0.04), (0.16, 0.25), (0.14, 0.42), (0.06, 0.6), (0.04, 0.8), (0.08, 1.0)],
        'guan': [(0.1, 0), (0.15, 0.06), (0.2, 0.4), (0.18, 0.75), (0.12, 0.9), (0.12, 1.0)],
        'gu': [(0.12, 0), (0.08, 0.1), (0.07, 0.35), (0.1, 0.5), (0.07, 0.65), (0.17, 1.0)],
    }

    def vase(self, m, x, y, z, h, kind='meiping', flowers=None, fcol='菊黄'):
        prof = [(r * h, dz * h) for r, dz in self.VASES[kind]]
        self.lathe(m, x, y, z, prof, seg=18)
        if flowers:
            r = self.rng
            for i in range(flowers):
                a = r.uniform(0, 2 * math.pi)
                L = r.uniform(0.25, 0.45)
                tip = (x + math.cos(a) * L * 0.45, y + math.sin(a) * L * 0.45, z + h + L)
                self.rod('叶绿', (x, y, z + h * 0.8), tip, 0.006, seg=5)
                self.sph(fcol, *tip, 0.045, 0.045, 0.03, seg=8)
                for k in range(2):
                    b = r.uniform(0.3, 0.7)
                    p = (x + (tip[0] - x) * b, y + (tip[1] - y) * b, z + h + (tip[2] - z - h) * b)
                    self.sph('叶绿', p[0] + 0.03, p[1], p[2], 0.04, 0.02, 0.012, seg=6)

    def ding(self, m, x, y, z, h):
        """三足鼎 / 香炉。"""
        r = h * 0.55
        self.lathe(m, x, y, z + h * 0.3, [(r * 0.6, 0), (r * 0.95, h * 0.15), (r, h * 0.4), (r * 0.9, h * 0.55), (r * 0.95, h * 0.6)], seg=16)
        for i in range(3):
            a = 2 * math.pi * i / 3
            self.rod(m, (x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6, z + h * 0.32), (x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75, z), h * 0.06, seg=6)
        for sx in (-1, 1):
            self.box(m, x + sx * r * 0.75 - 0.01, y - h * 0.15, z + h * 0.85, x + sx * r * 0.75 + 0.01, y + h * 0.15, z + h * 1.1)

    def penjing(self, x, y, z, w, tree=True):
        """石头盆景：长方石盆 + 湖石 + 小树。"""
        self.box('汉白玉', x - w / 2, y - w * 0.3, z, x + w / 2, y + w * 0.3, z + 0.05)
        r = self.rng
        self.sph('太湖石', x - w * 0.1, y, z + 0.05 + w * 0.25, w * 0.15, w * 0.12, w * 0.32, seg=7)
        self.sph('太湖石', x + w * 0.15, y + 0.01, z + 0.05 + w * 0.12, w * 0.1, w * 0.09, w * 0.15, seg=6)
        if tree:
            self.rod('旧木', (x + w * 0.2, y, z + 0.05), (x + w * 0.05, y, z + w * 0.55), 0.008, seg=5)
            for k in range(4):
                self.sph('叶绿', x + w * (0.05 + r.uniform(-0.12, 0.12)), y + r.uniform(-0.04, 0.04), z + w * (0.5 + r.uniform(-0.05, 0.12)), w * 0.1, w * 0.08, w * 0.05, seg=6)

    def teaset(self, x, y, z, m='紫砂', cups=4):
        self.lathe(m, x, y, z, [(0.04, 0), (0.07, 0.03), (0.075, 0.06), (0.05, 0.09), (0.02, 0.1), (0.015, 0.115), (0, 0.12)], seg=14)
        self.rod(m, (x + 0.06, y, z + 0.06), (x + 0.12, y, z + 0.1), 0.008, seg=5)
        for i in range(cups):
            a = 2 * math.pi * i / cups + 0.4
            self.lathe('瓷白', x + math.cos(a) * 0.17, y + math.sin(a) * 0.17, z, [(0.015, 0), (0.03, 0.02), (0.035, 0.045)], seg=10, cap=False)

    def study_set(self, x, y, z, rot=0):
        """文房：砚、笔筒、笔架、镇纸、书。"""
        with self.at(x, y, z, rot):
            self.box('墨', -0.12, -0.08, 0, 0.0, 0.08, 0.025)
            self.box('黑漆', -0.11, -0.07, 0.025, -0.01, 0.07, 0.03)
            self.lathe('紫檀', 0.12, 0.05, 0, [(0.05, 0), (0.05, 0.13)], seg=12)
            for i in range(6):
                a = i * 1.1
                self.rod('竹竿', (0.12 + 0.02 * math.cos(a), 0.05 + 0.02 * math.sin(a), 0.05), (0.12 + 0.04 * math.cos(a), 0.05 + 0.04 * math.sin(a), 0.3), 0.004, seg=4)
            self.box('紫檀', 0.02, -0.1, 0, 0.3, -0.08, 0.012)
            for i in range(5):
                xx = 0.04 + i * 0.06
                self.box('紫檀', xx - 0.01, -0.1, 0.012, xx + 0.01, -0.08, 0.05 + 0.02 * (i % 2))
            self.box('画心', -0.35, -0.12, 0, -0.15, 0.12, 0.003)   # 铺开的纸
            self.box('玉', -0.34, 0.1, 0.003, -0.16, 0.12, 0.018)    # 镇纸

    def lantern(self, x, y, ztop, drop=0.6, kind='hex', shade='窗纸'):
        """宫灯（六方），自梁下垂挂。shade 用发光窗纸材质（夜里亮）。"""
        z1 = ztop - drop
        self.rod('铜', (x, y, ztop), (x, y, z1), 0.006, seg=4)
        R, H = 0.22, 0.42
        z0 = z1 - H
        self.lathe('紫檀', x, y, z1 - 0.06, [(R * 0.7, 0), (R * 1.05, 0.0), (R * 1.05, 0.06), (0.03, 0.06)], seg=6)
        self.lathe(shade, x, y, z0 + 0.04, [(R * 0.92, 0), (R * 0.92, H - 0.1)], seg=6)
        for i in range(6):
            a = 2 * math.pi * i / 6
            self.rod('紫檀', (x + math.cos(a) * R, y + math.sin(a) * R, z0), (x + math.cos(a) * R, y + math.sin(a) * R, z1 - 0.04), 0.012, seg=4)
            self.rod('锦缎', (x + math.cos(a) * R * 1.1, y + math.sin(a) * R * 1.1, z1 - 0.02), (x + math.cos(a) * R * 1.12, y + math.sin(a) * R * 1.12, z0 - 0.25), 0.008, seg=4)
        self.lathe('紫檀', x, y, z0 - 0.02, [(0.03, 0), (R * 1.0, 0.03), (R * 1.0, 0.07), (R * 0.7, 0.07)], seg=6)
        self.rod('锦缎', (x, y, z0 - 0.02), (x, y, z0 - 0.35), 0.012, seg=5)

    def candle_stand(self, x, y, z=0, h=1.3, shade='窗纸'):
        """落地灯台（羊角灯）。"""
        self.lathe('紫檀', x, y, z, [(0.18, 0), (0.18, 0.04), (0.05, 0.08), (0.025, 0.12), (0.025, h - 0.1), (0.07, h - 0.08), (0.07, h - 0.06)], seg=10)
        self.lathe(shade, x, y, z + h - 0.06, [(0.06, 0), (0.12, 0.08), (0.12, 0.24), (0.06, 0.3)], seg=12)

    def screen(self, m, w, h, panels=4, silk='画绢', y=0.0, col=True, fold=0.0):
        """屏风（立于 y 线，面朝 -Y）。fold：每扇折角（度）。"""
        pw = w / panels
        x = -w / 2
        for i in range(panels):
            a = math.radians(fold * (1 if i % 2 else -1))
            with self.at(x + pw / 2, y, 0, math.degrees(a)):
                self.box(m, -pw / 2, -0.025, 0.08, pw / 2, 0.025, h)
                self.box(silk, -pw / 2 + 0.05, -0.03, 0.4, pw / 2 - 0.05, 0.03, h - 0.08)
                self.box(m, -pw / 2 + 0.05, -0.028, 0.12, pw / 2 - 0.05, 0.028, 0.36)
                for sx in (-1, 1):
                    self.box(m, sx * pw / 2 - 0.03, -0.12, 0, sx * pw / 2 + 0.03, 0.12, 0.08)
            x += pw
        if col:
            self.col(-w / 2, y - 0.15, 0, w / 2, y + 0.15, h)

    def scroll(self, x, y, z, w, h, face=-1, mount='绫裱', paint='画心'):
        """挂轴，贴在 y 面上（face=-1 朝 -Y）。"""
        t = 0.008
        o = face * t
        self.box(mount, x - w / 2, y + o - t / 2, z - h, x + w / 2, y + o + t / 2, z)
        self.box(paint, x - w / 2 + 0.06, y + o * 2 - t / 2, z - h + h * 0.18, x + w / 2 - 0.06, y + o * 2 + t / 2, z - h * 0.2)
        self.rod('紫檀', (x - w / 2 - 0.04, y + o * 2, z - h), (x + w / 2 + 0.04, y + o * 2, z - h), 0.015, seg=6)
        self.rod('紫檀', (x - w / 2, y + o, z), (x + w / 2, y + o, z), 0.01, seg=6)

    def carpet(self, m, x0, y0, x1, y1, z, border='描金'):
        self.box(border, x0, y0, z, x1, y1, z + 0.008)
        self.box(m, x0 + 0.12, y0 + 0.12, z + 0.001, x1 - 0.12, y1 - 0.12, z + 0.01)

    def mirror(self, m, w=1.1, h=2.2, frame=0.09, glass='镜面', stand=True, col=True):
        """穿衣镜（大玻璃镜），立于 y=0 线，镜面朝 -Y。"""
        z0 = 0.25 if stand else 0.0
        self.box(m, -w / 2, -0.04, z0, w / 2, 0.04, z0 + frame)
        self.box(m, -w / 2, -0.04, z0 + h - frame, w / 2, 0.04, z0 + h)
        for sx in (-1, 1):
            self.box(m, sx * w / 2 - (frame if sx > 0 else 0), -0.04, z0, sx * w / 2 + (0 if sx > 0 else frame), 0.04, z0 + h)
        self.box(glass, -w / 2 + frame, -0.012, z0 + frame, w / 2 - frame, 0.012, z0 + h - frame)
        # 顶帽（透雕）
        self.box(m, -w / 2 - 0.06, -0.06, z0 + h, w / 2 + 0.06, 0.06, z0 + h + 0.06)
        for i in range(9):
            x = -w / 2 + 0.06 + i * (w - 0.12) / 8
            self.sph('描金', x, -0.06, z0 + h + 0.12, 0.04, 0.012, 0.05, seg=6)
        self.box(m, -w / 2 - 0.02, -0.05, z0 + h + 0.06, w / 2 + 0.02, -0.04, z0 + h + 0.2)
        if stand:
            for sx in (-1, 1):
                self.box(m, sx * w / 2 - 0.06, -0.3, 0, sx * w / 2 + 0.06, 0.3, 0.1)
                self.bar(m, (sx * w / 2, -0.25, 0.1), (sx * w / 2, 0, 0.7), 0.04, 0.04)
            self.box(m, -w / 2, -0.04, 0.1, w / 2, 0.04, z0)
        if col:
            self.col(-w / 2, -0.12, 0, w / 2, 0.12, z0 + h)

    def door_leaf(self, m, w, h, paper='窗纸', t=0.06, gz=0.0):
        """隔扇门一扇：门轴在局部 x=0，向 +x 伸出；格心（方格棂）+ 绦环板 + 裙板。"""
        f = 0.06
        self.box(m, 0, -t / 2, gz, f, t / 2, gz + h)
        self.box(m, w - f, -t / 2, gz, w, t / 2, gz + h)
        for z in (0, h * 0.18, h * 0.3, h * 0.36, h - f):
            self.box(m, 0, -t / 2, gz + z, w, t / 2, gz + z + f)
        self.box(m, f, -t / 4, gz + f, w - f, t / 4, gz + h * 0.18)            # 裙板
        self.box(m, f, -t / 4, gz + h * 0.18 + f, w - f, t / 4, gz + h * 0.3)   # 绦环板
        # 格心：方格棂 + 窗纸
        z0, z1 = gz + h * 0.36 + f, gz + h - f
        self.box(paper, f, -0.004, z0, w - f, 0.004, z1)
        nx = max(2, int((w - 2 * f) / 0.12))
        nz = max(3, int((z1 - z0) / 0.12))
        for i in range(1, nx):
            x = f + (w - 2 * f) * i / nx
            self.box(m, x - 0.008, -0.02, z0, x + 0.008, 0.02, z1)
        for k in range(1, nz):
            z = z0 + (z1 - z0) * k / nz
            self.box(m, f, -0.02, z - 0.008, w - f, 0.02, z + 0.008)

    def lattice_partition(self, m, w, h, y=0.0, t=0.06, paper='碧纱', door=None, step=0.12):
        """碧纱橱：整面槅扇（格心糊纱），door=(x0,x1) 处留门。正面朝 -Y，局部 x 从 -w/2 到 w/2。"""
        x = -w / 2
        n = max(2, round(w / 0.75))
        pw = w / n
        for i in range(n):
            a, b = x + i * pw, x + (i + 1) * pw
            if door and a >= door[0] - 1e-3 and b <= door[1] + 1e-3:
                continue
            with self.at(a, y, 0):
                self.door_leaf(m, pw, h, paper=paper, t=t)
        self.box(m, -w / 2, y - t / 2 - 0.01, h, w / 2, y + t / 2 + 0.01, h + 0.12)  # 上槛
        if door:
            self.col(-w / 2, y - 0.1, 0, door[0], y + 0.1, h)
            self.col(door[1], y - 0.1, 0, w / 2, y + 0.1, h)
        else:
            self.col(-w / 2, y - 0.1, 0, w / 2, y + 0.1, h)

    def luodizhao(self, m, w, h, shape='round', t=0.08, gauze=None, carve=True):
        """落地罩 / 圆光罩：XZ 面上的透雕框，中开圆、八方或葵花门。局部 x ∈ [-w/2,w/2]，z ∈ [0,h]，面在 y=0。"""
        n = 40
        cx, cz = 0.0, h * 0.5
        if shape == 'round':
            R = min(w, h) * 0.46
            hole = [(cx + R * math.cos(2 * math.pi * i / n), max(0.0, cz + R * math.sin(2 * math.pi * i / n))) for i in range(n)]
            hole = self._clip_floor(hole)
        elif shape == 'oct':
            R = min(w, h) * 0.47
            hole = self._clip_floor([(cx + R * math.cos(math.pi / 8 + 2 * math.pi * i / 8) / math.cos(math.pi / 8), cz + R * math.sin(math.pi / 8 + 2 * math.pi * i / 8) / math.cos(math.pi / 8)) for i in range(8)])
        else:  # 'arch' 落地罩：两侧落地，上方弧形
            hw = w * 0.36
            hole = [(-hw, 0.0), (hw, 0.0), (hw, h * 0.62)]
            for i in range(1, n):
                a = math.pi * i / n
                hole.append((hw * math.cos(a), h * 0.62 + (h * 0.24) * math.sin(a)))
            hole.append((-hw, h * 0.62))
        self.fret_panel(m, w, h, hole, t, gold=carve)
        # 碰撞：两侧实体
        xs = sorted(p[0] for p in hole)
        self.col(-w / 2, -t, 0, xs[0], t, h)
        self.col(xs[-1], -t, 0, w / 2, t, h)

    def fret_panel(self, m, w, h, hole, t, step=0.13, frame=0.07, ring=0.08, gold=True):
        """雕空玲珑的罩面：外框 + 门洞周圈实心边 + 其余空透的方格/拐子棂。门洞须为凸形。"""
        n = len(hole)
        cx = sum(p[0] for p in hole) / n
        cz = sum(p[1] for p in hole) / n
        on_floor = min(p[1] for p in hole) < 1e-3
        # 门洞外扩一圈作实心边
        def grow(p, d):
            dx, dz = p[0] - cx, p[1] - cz
            L = math.hypot(dx, dz) or 1
            return (p[0] + dx / L * d, p[1] + (dz / L * d if p[1] > 1e-3 else 0))
        outer = [grow(p, ring) for p in hole]
        if on_floor:
            outer = [(x, max(0.0, z)) for x, z in outer]
        # 外框
        self.box(m, -w / 2, -t / 2, h - frame, w / 2, t / 2, h)
        self.box(m, -w / 2, -t / 2, 0, -w / 2 + frame, t / 2, h)
        self.box(m, w / 2 - frame, -t / 2, 0, w / 2, t / 2, h)
        if not on_floor:
            self.box(m, -w / 2, -t / 2, 0, w / 2, t / 2, frame)
        # 门洞实心边（带描金线）
        self._ring(m, hole, outer, t, on_floor)
        if gold:
            self._ring('描金', hole, [grow(p, 0.015) for p in hole], t + 0.012, on_floor)
        # 格棂：横竖线，剪掉门洞（外扩）以内的部分
        def segs_h(z):
            xs = []
            for k in range(n):
                (x0, z0), (x1, z1) = outer[k], outer[(k + 1) % n]
                if (z0 > z) != (z1 > z):
                    xs.append(x0 + (z - z0) * (x1 - x0) / (z1 - z0))
            lo, hi = -w / 2 + frame, w / 2 - frame
            if len(xs) >= 2:
                a, b = min(xs), max(xs)
                return [(lo, a), (b, hi)]
            return [(lo, hi)]
        def segs_v(x):
            zs = []
            for k in range(n):
                (x0, z0), (x1, z1) = outer[k], outer[(k + 1) % n]
                if (x0 > x) != (x1 > x):
                    zs.append(z0 + (x - x0) * (z1 - z0) / (x1 - x0))
            lo, hi = (0.0 if on_floor else frame), h - frame
            if len(zs) >= 2:
                a, b = min(zs), max(zs)
                return [(lo, a), (b, hi)]
            if len(zs) == 1:  # 落地门洞：竖线只在洞顶以上
                return [(zs[0], hi)]
            return [(lo, hi)]
        bw = 0.022
        z = step
        k = 0
        while z < h - frame:
            for a, b in segs_h(z):
                if b - a > 0.03:
                    self.box(m, a, -t * 0.3, z - bw / 2, b, t * 0.3, z + bw / 2)
            z += step
            k += 1
        x = -w / 2 + frame + step * 0.5
        while x < w / 2 - frame:
            for a, b in segs_v(x):
                if b - a > 0.03:
                    self.box(m, x - bw / 2, -t * 0.3, a, x + bw / 2, t * 0.3, b)
            x += step
        # 每隔一格嵌一个小方“卡子花”
        z = step * 1.5
        i = 0
        while z < h - frame:
            x = -w / 2 + frame + step
            j = 0
            while x < w / 2 - frame - 0.02:
                if (i + j) % 2 == 0 and not self._inside(outer, x, z, 0.05):
                    self.box(m, x - 0.03, -t * 0.32, z - 0.03, x + 0.03, t * 0.32, z + 0.03)
                x += step
                j += 1
            z += step
            i += 1

    def _ring(self, m, inner, outer, t, open_bottom):
        b = bmesh.new()
        n = len(inner)
        F = [(b.verts.new((i[0], -t / 2, i[1])), b.verts.new((o[0], -t / 2, o[1])), b.verts.new((i[0], t / 2, i[1])), b.verts.new((o[0], t / 2, o[1]))) for i, o in zip(inner, outer)]
        for k in range(n):
            j = (k + 1) % n
            if open_bottom and inner[k][1] < 1e-3 and inner[j][1] < 1e-3:
                continue
            a, c = F[k], F[j]
            b.faces.new((a[0], c[0], c[1], a[1]))
            b.faces.new((a[3], c[3], c[2], a[2]))
            b.faces.new((a[2], c[2], c[0], a[0]))
            b.faces.new((a[1], c[1], c[3], a[3]))
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        self._add(m, b, Matrix.Identity(4))

    def ceiling(self, x0, y0, x1, y1, z, cell=0.6, frame='紫檀', panel='天花', dot='描金'):
        """井口天花：木支条方格 + 每格天花板 + 中心圆光。"""
        self.box(panel, x0, y0, z, x1, y1, z + 0.03)
        nx = max(1, round((x1 - x0) / cell))
        ny = max(1, round((y1 - y0) / cell))
        cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
        for i in range(nx + 1):
            x = x0 + i * cw
            self.box(frame, x - 0.035, y0, z - 0.06, x + 0.035, y1, z)
        for j in range(ny + 1):
            y = y0 + j * ch
            self.box(frame, x0, y - 0.035, z - 0.06, x1, y + 0.035, z)
        for i in range(nx):
            for j in range(ny):
                self.cyl(dot, x0 + (i + 0.5) * cw, y0 + (j + 0.5) * ch, z - 0.012, z, min(cw, ch) * 0.28, seg=16)
                self.cyl('天花心', x0 + (i + 0.5) * cw, y0 + (j + 0.5) * ch, z - 0.018, z - 0.006, min(cw, ch) * 0.22, seg=16)

    def wall_finish(self, a, b, z0, z1, face, dado=1.0, wood='紫檀', plaster='白灰墙', t=0.02):
        """贴墙：下护墙板 + 上白灰。a、b 为墙面上两端点 (x,y)，face 为朝室内的单位向量 (fx,fy)。"""
        (ax, ay), (bx, by) = a, b
        fx, fy = face
        def slab(m, za, zb, off, th):
            x0, x1 = min(ax, bx) + fx * off, max(ax, bx) + fx * off
            y0, y1 = min(ay, by) + fy * off, max(ay, by) + fy * off
            self.box(m, x0 - abs(fx) * th / 2, y0 - abs(fy) * th / 2, za, x1 + abs(fx) * th / 2, y1 + abs(fy) * th / 2, zb)
        slab(plaster, z0 + dado, z1, t / 2, t)
        slab(wood, z0, z0 + dado, t, t * 2)
        slab(wood, z0 + dado - 0.04, z0 + dado + 0.02, t * 1.5, t * 3)  # 压条
        slab(wood, z0, z0 + 0.12, t * 1.5, t * 3)                        # 踢脚

    @staticmethod
    def _clip_floor(hole):
        return [(x, max(z, 0.0)) for x, z in hole]

    @staticmethod
    def _inside(poly, x, z, pad=0.0):
        n = len(poly)
        cx = sum(p[0] for p in poly) / n
        cz = sum(p[1] for p in poly) / n
        # 近似：按质心缩放 pad
        inside = False
        j = n - 1
        for i in range(n):
            xi, zi = poly[i]
            xj, zj = poly[j]
            xi, zi = xi + (xi - cx) * pad, zi + (zi - cz) * pad
            xj, zj = xj + (xj - cx) * pad, zj + (zj - cz) * pad
            if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / (zj - zi + 1e-12) + xi):
                inside = not inside
            j = i
        return inside

    # ---------------- 输出 ----------------
    def build_objects(self):
        coll = bpy.data.collections.new('50_室内_' + self.id)
        bpy.context.scene.collection.children.link(coll)
        for m, b in sorted(self.geo.items()):
            me = bpy.data.meshes.new(f'{self.id}_in_{m}')
            bmesh.ops.remove_doubles(b, verts=b.verts[:], dist=1e-5)
            b.to_mesh(me)
            b.free()
            mat = bpy.data.materials.get('M_' + m) or bpy.data.materials.new('M_' + m)
            mat.use_nodes = True
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                c = _hex(COLORS.get(m, '#a0a0a0'))
                bsdf.inputs['Base Color'].default_value = (*[x ** 2.2 for x in c], 1)
                if m in ('镜面', '穿衣镜', '铜', '描金'):
                    bsdf.inputs['Metallic'].default_value = 0.9
                    bsdf.inputs['Roughness'].default_value = 0.05 if m in ('镜面', '穿衣镜') else 0.35
            me.materials.append(mat)
            for p in me.polygons:
                p.use_smooth = False
            ob = bpy.data.objects.new(f'{self.id}_in_{m}', me)
            coll.objects.link(ob)
        self.geo = {}
        return coll

    def tri_count(self):
        n = 0
        for ob in bpy.context.scene.objects:
            if ob.type == 'MESH':
                n += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        return n


def new_file():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def save_and_export(kit, shell_cols_filter=None, extra_cols=None):
    """保存 blender/<id>_in.blend、导出 models/b/<id>_in.wasm、更新 col.json。
    shell_cols_filter(box)->bool：返回 True 的外壳碰撞框会从 col.json[id] 删去（实心房屋块）。
    extra_cols：追加到外壳 id 下的碰撞框（局部 blender 坐标，[x0,y0,z0,x1,y1,z1,walk]）。"""
    coll = kit.build_objects()
    print('tris', kit.tri_count())
    blend = os.path.join(ROOT, 'blender', f'{kit.id}_in.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    glb = f'/tmp/{kit.id}_in.glb'
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True,
                              export_image_format='NONE', export_materials='EXPORT', export_yup=True)
    out = os.path.join(ROOT, 'models', 'b', f'{kit.id}_in.wasm')
    subprocess.run(['node', os.path.join(ROOT, 'blender', 'scripts', 'web', 'pack_glb.mjs'), glb, out], check=True)
    # 碰撞
    cp = os.path.join(ROOT, 'models', 'b', 'col.json')
    C = json.load(open(cp))

    def conv(b):
        x0, y0, z0, x1, y1, z1, walk = b
        # 网页：[lx, lz, hx, hz, top, bot]（lz = -blenderY）
        return [round((x0 + x1) / 2, 3), round(-(y0 + y1) / 2, 3), round(max(abs(x1 - x0) / 2, 0.03), 3),
                round(max(abs(y1 - y0) / 2, 0.03), 3), round(z1, 3), round(z0, 3)]
    if shell_cols_filter:
        before = len(C[kit.id])
        C[kit.id] = [b for b in C[kit.id] if not shell_cols_filter(b)]
        print('shell cols removed', before - len(C[kit.id]))
    C[kit.id + '_in'] = [conv(b) for b in kit.cols] + [conv(b) for b in (extra_cols or [])]
    with open(cp, 'w') as f:
        json.dump(C, f, ensure_ascii=False, separators=(',', ':'))
    print('cols', len(C[kit.id + '_in']))
