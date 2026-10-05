"""大观楼改样（在 blender/daguan.blend 上修改；先跑过 daguan_doors.py。只能跑一次：已有 daguan_改样标记 就退出）。
用法：python3 blender/scripts/sites/daguan_rebuild.py
      flock /tmp/coljson.lock python3 blender/scripts/sites/daguan_cols.py
  然后：python3 blender/scripts/web/export_glb.py blender/daguan.blend /tmp/daguan.glb
        node blender/scripts/web/pack_glb.mjs /tmp/daguan.glb models/b/daguan.wasm models/b/daguan.wasm
  并跑 daguan_in_shift.py（殿内陈设随正殿前移）。

依据（第十七、十八回）：“只见正面现出一座玉石牌坊来，上面龙蟠螭护，玲珑凿就”；“正殿……一带复道萦纡，青松拂檐，玉兰绕砌，
金辉兽面，彩焕螭头”；“正楼曰大观楼，东面飞楼曰缀锦阁，西面斜楼曰含芳阁”。

原模型把顾恩思义殿与大观楼摞成一座两层楼。改成：
  1. 正殿（顾恩思义殿）前移 16 m（Blender y −16），自身改重檐歇山：下檐不动，加一层上檐（借大观楼上檐放大）、上檐下一圈槅扇/彩画。
  2. 大观楼立在正殿后面一座 4.5 m 高的须弥座白石台上，三层逐层收分：首层七开间殿身带下檐（顾恩思义殿副本），
     二层五开间楼身带平座与匾（原大观楼楼身），三层再收 0.8，顶上歇山、金宝顶；整座等比放大 1.15，顶脊约 33 m，正殿约 18 m。
  3. 缀锦阁、含芳阁加成三层飞楼（底层不动）；两条双层复道后移 2.5 m，接到大观楼首层两山。
  4. 前面：两层白石台基、正中石阶；台基前一条汉白玉甬路，两旁矮白石栏杆、石灯座；甬路尽头玉石牌坊（Tripo，网页里放），
     牌坊两侧石狮（Tripo）；甬路两旁两方水池，池岸山石。玉兰、青松由网页种。
  5. 屋面全部改灰色筒瓦（M_灰瓦），脊饰金色不变。
  6. 原地面、月台、牌坊、鼎燎删去。
  7. Tripo 件处放 TRIPO占位 块（网页隐藏，只供生成碰撞）；水池上也放一块占位，人走不进池里。
  8. 外壳碰撞框另跑 daguan_cols.py（可重复执行）。
坐标：Blender 坐标（网页 x→X，网页 z→−Y，网页 y→Z），正面朝 −Y。
"""
import bpy, bmesh, os, json, math, random
from mathutils import Vector, Matrix

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'daguan.blend'))
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
bpy.ops.wm.open_mainfile(filepath=SRC)
O = bpy.data.objects
if 'daguan_改样标记' in O:
    raise SystemExit('daguan.blend 已改过样')
random.seed(17)
COLL = O['daguan_顾恩思义殿_marble'].users_collection[0]

DH = -16.0                 # 正殿前移
T = 4.5                    # 大观楼台高（须弥座）
TY = 24.8                  # 大观楼中心 y
U = 1.15                   # 大观楼整座等比放大（只等比，不拉伸：开间、斗拱、窗格比例不变）
PH3 = 4.9                  # 缀锦阁、含芳阁一层层高（加第三层用）


def names(prefix):
    return [o for o in O if o.name.startswith(prefix)]


def mat(name, color=(0.8, 0.8, 0.8)):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name); m.use_nodes = True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*color, 1)
        m.diffuse_color = (*color, 1)
    return m


def bake(o, M):
    """把矩阵 M 直接烤进网格（世界坐标），对象矩阵保持原样。"""
    if o.type == 'MESH':
        o.data.transform(o.matrix_world.inverted() @ M @ o.matrix_world)
        o.data.update()
    else:
        o.matrix_world = M @ o.matrix_world


def dup(o, suffix):
    c = o.copy()
    if o.data is not None: c.data = o.data.copy()
    c.name = o.name + suffix
    for col in o.users_collection: col.objects.link(c)
    return c


def scale_about(cx, cy, cz, sx, sy, sz):
    return Matrix.Translation((cx, cy, cz)) @ Matrix.Diagonal((sx, sy, sz, 1)) @ Matrix.Translation((-cx, -cy, -cz))


def move(dx, dy, dz):
    return Matrix.Translation((dx, dy, dz))


# ============================================================ 0. 删去旧件
for p in ('daguan_地面_marble', 'daguan_地面_mud', 'daguan_地面_stone', 'daguan_月台_', 'daguan_牌坊', 'daguan_省亲别墅匾', 'daguan_鼎燎'):
    for o in names(p):
        bpy.data.objects.remove(o, do_unlink=True)

# ============================================================ 1. 分组
HALL = [o for o in O if o.name.startswith(('daguan_顾恩思义殿_', 'daguan_下檐_', 'daguan_垫板_', 'daguan_顾恩思义匾'))]
STOREY = [o for o in O if o.name.startswith(('daguan_大观楼_', 'daguan_上垫板_'))]
TOPROOF = names('daguan_上檐_')
PLAQUE = names('daguan_大观楼匾')
EAVE = names('daguan_下檐_')

# ---- 大观楼用的原件副本（要在正殿前移之前，按原坐标复制） ----
T_HALL = [dup(o, '_楼1') for o in O if o.name.startswith(('daguan_顾恩思义殿_', 'daguan_下檐_', 'daguan_垫板_'))]
T_EAVE2 = [dup(o, '_楼腰2') for o in EAVE]
T_STOREY3 = [dup(o, '_楼3') for o in STOREY]

# ---- 正殿上檐：借原上檐放大（先复制，原件之后给大观楼用） ----
for o in TOPROOF:
    c = dup(o, '_正殿')
    bake(c, move(0, DH, 12.5 - 16.3) @ scale_about(0, 20, 16.3, 1.18, 1.12, 1.0))
# 上檐下的一圈楼身（槅扇窗、彩画额枋）：正殿下檐与上檐之间
for o in names('daguan_大观楼_'):
    if o.name.endswith(('_dark',)): continue
    c = dup(o, '_正殿腰')
    # 原楼身 13.1…16.5（平座以上）压成 9.4…12.9，面阔放大到正殿上檐下
    bake(c, move(0, 20 + DH, 9.4) @ Matrix.Diagonal((1.18, 1.12, (12.9 - 9.4) / (16.5 - 13.1), 1)) @ Matrix.Translation((0, -20, -13.1)))
    # 平座（13.1 以下）随之压到 7.5…9.4，藏在殿内天花之上、下檐之下
for o in HALL:
    bake(o, move(0, DH, 0))

# ============================================================ 2. 大观楼（三层，逐层收分）
# 原件就是“顾恩思义殿 + 下檐 + 大观楼楼身 + 上檐”摞成的两层楼，比例是对的；这里整座等比放大 U，
#   首层：七开间殿身（顾恩思义殿副本）+ 下檐；二层：五开间楼身（原大观楼楼身，带平座与匾）；
#   三层：楼身再收 0.8；二三层之间腰檐（下檐等比 0.74）；顶上歇山（上檐等比 0.8）、正脊中央金宝顶。
# TW：原坐标 (0, 20, 1.5)（殿台底）→ 楼台面 (0, TY, T)
TW = move(0, TY, T) @ Matrix.Scale(U, 4) @ move(0, -20, -1.5)
W = lambda x, y, z: TW @ Vector((x, y, z))
for o in T_HALL + STOREY + PLAQUE:
    bake(o, TW)
for o in T_EAVE2:
    o.name = o.name.replace('daguan_下檐_', 'daguan_大观楼腰檐_')
    bake(o, TW @ move(0, 0, 16.1 - 8.8) @ scale_about(0, 20, 8.8, 0.74, 0.74, 0.74))
Z3 = 16.1 + 2.5 * 0.77                       # 三层平座底（与腰檐的高差同原件，等比缩）
for o in T_STOREY3:
    bake(o, TW @ move(0, 0, Z3 - 11.3) @ scale_about(0, 20, 11.3, 0.8, 0.8, 0.8))
Z3T = Z3 + (16.5 - 11.3) * 0.8               # 三层楼身顶
for o in TOPROOF:
    bake(o, TW @ move(0, 0, Z3T - 0.2 - 16.3) @ scale_about(0, 20, 16.3, 0.8, 0.8, 0.8))
RIDGE = Z3T - 0.2 + (21.7 - 16.3) * 0.8      # 顶脊高（原坐标系）
print('大观楼 顶脊', round(W(0, 20, RIDGE).z, 2), 'm')

# ---- 楼层之间的填充（腰檐里面，挡住缝） ----
RED = mat('M_朱漆'); CAI = mat('M_daguan_彩画青'); MARBLE = mat('M_汉白玉'); TILE = mat('M_灰瓦', (0.43, 0.44, 0.44))
STONE = mat('M_青石'); ROCK = mat('M_山石', (0.55, 0.53, 0.5)); WATER = mat('M_YZ_泉水', (0.27, 0.38, 0.35))
POOL = mat('M_青石_水渍', (0.56, 0.58, 0.56)); PH = mat('M_TRIPO占位', (0.5, 0.5, 0.5)); GOLD = mat('M_描金')

BOX_BM = {}


def add_box(key, m, x0, y0, z0, x1, y1, z1):
    """把一个盒子加到名为 daguan_<key> 的网格里（同名累积）。"""
    if key not in BOX_BM: BOX_BM[key] = (bmesh.new(), m)
    bm = BOX_BM[key][0]
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))


def add_geom(key, m, verts, faces):
    if key not in BOX_BM: BOX_BM[key] = (bmesh.new(), m)
    bm = BOX_BM[key][0]
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        try: bm.faces.new([vs[i] for i in f])
        except ValueError: pass


def flush():
    for key, (bm, m) in BOX_BM.items():
        me = bpy.data.meshes.new('daguan_' + key)
        bm.normal_update(); bm.to_mesh(me); bm.free()
        me.materials.append(m)
        o = bpy.data.objects.new('daguan_' + key, me); COLL.objects.link(o)
    BOX_BM.clear()


# 二、三层之间（腰檐里面）
a_, b_ = W(-10.9 * 0.8 + 0.2, 20 - 4.6 * 0.8 + 0.2, 16.2), W(10.9 * 0.8 - 0.2, 20 + 4.6 * 0.8 - 0.2, Z3 + 0.3)
add_box('大观楼层间_lacquer_red', RED, *a_, *b_)
# 首层明间门已开（原 daguan_doors），里面是空壳：放一块暗盒
a_, b_ = W(-14.3, 15.3, 2.2), W(14.3, 26.6, 9.0)
add_box('大观楼首层暗_dark', mat('M_daguan_室内暗'), *a_, *b_)
# 金宝顶：须弥座 + 宝珠，立在正脊中央
def lathe(key, m, prof, cx, cy, z0, n=16):
    if key not in BOX_BM: BOX_BM[key] = (bmesh.new(), m)
    bm = BOX_BM[key][0]; rings = []
    for r, z in prof:
        rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n), z0 + z)) for i in range(n)])
    for ra, rb in zip(rings[:-1], rings[1:]):
        for i in range(n): bm.faces.new((ra[i], ra[(i + 1) % n], rb[(i + 1) % n], rb[i]))
top = W(0, 20, RIDGE - 0.15)
lathe('大观楼宝顶_gold', GOLD, [(0.55, 0), (0.7, 0.25), (0.45, 0.45), (0.5, 0.75), (0.75, 1.0), (0.85, 1.35), (0.6, 1.75), (0.25, 2.0), (0.32, 2.2), (0.12, 2.6), (0.01, 2.75)], top.x, top.y, top.z)
# 正殿重檐：上下檐之间的一圈墙（楼身压扁件之外再垫一层，防漏缝）
add_box('正殿重檐_lacquer_red', RED, -12.6, 20 + DH - 5.0, 9.3, 12.6, 20 + DH + 5.0, 12.6)

# ============================================================ 3. 复道：后移、加长，接大观楼首层两山
for o in names('daguan_复道'):
    s = 1 if o.name.startswith(('daguan_复道东', 'daguan_复道顶东')) else -1
    end = 14.9 * U                          # 大观楼首层山墙
    f = (28.5 - end) / (28.5 - 14.6)
    bake(o, move(0, 2.5, 0) @ scale_about(s * 28.5, 0, 0, f, 1, 1))

# ============================================================ 3b. 缀锦阁、含芳阁加一层（三层飞楼）
# 楼上那一层（z > 5.6 的面）复制一份抬高一层；腰檐复制一份放到新旧两层之间；上檐、匾整体抬高。底层（第四十回宴席处）不动。
for name in ('缀锦阁', '含芳阁'):
    for o in [o for o in O if o.type == 'MESH' and o.name.startswith(f'daguan_{name}_') and not o.name.startswith((f'daguan_{name}_上檐', f'daguan_{name}_腰檐'))]:
        c = dup(o, '_三层')
        bm = bmesh.new(); bm.from_mesh(c.data); mw = c.matrix_world
        dead = [f for f in bm.faces if (mw @ f.calc_center_median()).z < 5.6]
        bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(c.data); bm.free()
        bake(c, move(0, 0, PH3))
    for o in names(f'daguan_{name}_腰檐'):
        bake(dup(o, '_三层'), move(0, 0, PH3))
    for o in names(f'daguan_{name}_上檐') + names(f'daguan_{name}匾'):
        bake(o, move(0, 0, PH3))

# ============================================================ 4. 屋面改灰瓦
for o in O:
    if o.type != 'MESH': continue
    for i, m in enumerate(o.data.materials):
        if m and m.name.startswith(('M_黄琉璃瓦', 'M_绿琉璃瓦')):
            o.data.materials[i] = TILE

# ============================================================ 5. 台基、台阶、栏杆


def balustrade(key, pts, z, h=0.95, step=1.5):
    """白石栏杆：望柱 + 地栿 + 栏板 + 寻杖；pts 为折线（闭合与否由调用方给）。"""
    for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
        L = math.hypot(xb - xa, yb - ya)
        if L < 0.3: continue
        n = max(1, round(L / step)); ux, uy = (xb - xa) / L, (yb - ya) / L
        for i in range(n + 1):
            px, py = xa + ux * L * i / n, ya + uy * L * i / n
            add_box(key, MARBLE, px - 0.12, py - 0.12, z, px + 0.12, py + 0.12, z + h)
            add_box(key, MARBLE, px - 0.15, py - 0.15, z + h, px + 0.15, py + 0.15, z + h + 0.14)       # 柱头
            add_box(key, MARBLE, px - 0.09, py - 0.09, z + h + 0.14, px + 0.09, py + 0.09, z + h + 0.26)
        # 一段段的栏板（沿线方向的薄盒；斜线用多边形）
        nx, ny = -uy, ux

        def slab(t0, t1, za, zb, w):
            p0 = (xa + ux * t0, ya + uy * t0); p1 = (xa + ux * t1, ya + uy * t1)
            vs = [(p0[0] + nx * w, p0[1] + ny * w, za), (p1[0] + nx * w, p1[1] + ny * w, za), (p1[0] - nx * w, p1[1] - ny * w, za), (p0[0] - nx * w, p0[1] - ny * w, za)]
            vs += [(x, y, zb) for x, y, _ in vs]
            add_geom(key, MARBLE, vs, [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
        slab(0, L, z, z + 0.14, 0.11)                       # 地栿
        slab(0, L, z + 0.14, z + 0.62, 0.05)                # 栏板
        slab(0, L, z + 0.74, z + 0.84, 0.07)                # 寻杖
        for i in range(n):                                  # 荷叶净瓶（栏板与寻杖之间的短柱）
            t = L * (i + 0.5) / n
            slab(t - 0.1, t + 0.1, z + 0.62, z + 0.74, 0.05)


def platform(key, x0, y0, x1, y1, z0, z1):
    add_box(key, MARBLE, x0, y0, z0, x1, y1, z1)
    add_box(key, MARBLE, x0 - 0.06, y0 - 0.06, z1 - 0.12, x1 + 0.06, y1 + 0.06, z1)   # 压面石出沿
    add_box(key, MARBLE, x0 - 0.05, y0 - 0.05, z0, x1 + 0.05, y1 + 0.05, z0 + 0.18)   # 土衬


def stairs(key, xc, w, y_edge, z0, z1, direction=-1, tread=0.36, axis='y', rise=0.15):
    """从台沿 y_edge 向外（direction）下的台阶；带两侧垂带。axis='x' 时沿 x 方向。"""
    n = max(1, round((z1 - z0) / rise)); rise = (z1 - z0) / n
    for i in range(n):
        zt = z1 - rise * i; d0 = tread * i; d1 = tread * (i + 1)
        if axis == 'y':
            ya, yb = sorted((y_edge + direction * d0, y_edge + direction * d1))
            add_box(key, MARBLE, xc - w / 2, ya, z0, xc + w / 2, yb, zt - rise)
            add_box(key, MARBLE, xc - w / 2, ya, zt - rise, xc + w / 2, yb, zt)
        else:
            xa, xb = sorted((y_edge + direction * d0, y_edge + direction * d1))
            add_box(key, MARBLE, xa, xc - w / 2, z0, xb, xc + w / 2, zt)
    run = tread * n
    for s in (-1, 1):   # 垂带（斜面）
        if axis == 'y':
            xa = xc + s * (w / 2 + 0.25)
            vs = [(xa - 0.25, y_edge, z0), (xa + 0.25, y_edge, z0), (xa + 0.25, y_edge + direction * run, z0), (xa - 0.25, y_edge + direction * run, z0),
                  (xa - 0.25, y_edge, z1 + 0.05), (xa + 0.25, y_edge, z1 + 0.05), (xa + 0.25, y_edge + direction * run, z0 + 0.12), (xa - 0.25, y_edge + direction * run, z0 + 0.12)]
        else:
            ya = xc + s * (w / 2 + 0.25)
            vs = [(y_edge, ya - 0.25, z0), (y_edge, ya + 0.25, z0), (y_edge + direction * run, ya + 0.25, z0), (y_edge + direction * run, ya - 0.25, z0),
                  (y_edge, ya - 0.25, z1 + 0.05), (y_edge, ya + 0.25, z1 + 0.05), (y_edge + direction * run, ya + 0.25, z0 + 0.12), (y_edge + direction * run, ya - 0.25, z0 + 0.12)]
        add_geom(key, MARBLE, vs, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    return run


# 正殿台基两层：一层 0…0.75，二层 0.75…1.5（正殿自带的台明 1.5…2.1 在其上）
P1 = (-25.0, -12.0, 25.0, 14.0); P2 = (-21.5, -8.5, 21.5, 14.0)
platform('台基_marble', *P1, 0.0, 0.75)
platform('台基_marble', *P2, 0.75, 1.5)
SW = 7.0
r1 = stairs('台阶_marble', 0, SW, P1[1], 0.0, 0.75)
r2 = stairs('台阶_marble', 0, SW, P2[1], 0.75, 1.5)
# 正殿自带台明前的踏跺（原月台上就有，随正殿前移）；台面铺方砖
add_box('台面_pave', mat('M_方砖地'), P2[0] + 0.1, P2[1] + 0.1, 1.5, P2[2] - 0.1, P2[3], 1.505)
add_box('台面_pave', mat('M_方砖地'), P1[0] + 0.1, P1[1] + 0.1, 0.75, P1[2] - 0.1, P1[3], 0.755)
g = SW / 2 + 0.55
balustrade('台基栏杆_marble', [(-g, P1[1]), (P1[0], P1[1]), (P1[0], P1[3])], 0.75)
balustrade('台基栏杆_marble', [(g, P1[1]), (P1[2], P1[1]), (P1[2], P1[3])], 0.75)
balustrade('台基栏杆_marble', [(-g, P2[1]), (P2[0], P2[1]), (P2[0], 9.6)], 1.5)
balustrade('台基栏杆_marble', [(g, P2[1]), (P2[2], P2[1]), (P2[2], 9.6)], 1.5)

# 大观楼台：4.5 m 须弥座（土衬、圭角、束腰、上枭、台面），台前两侧各一道踏跺从正殿二层台上去
P3 = (-21.0, 13.4, 21.0, 35.2)
x0, y0, x1, y1 = P3
add_box('楼台_marble', MARBLE, x0 - 0.35, y0 - 0.35, 0.0, x1 + 0.35, y1 + 0.35, 0.35)          # 土衬
add_box('楼台_marble', MARBLE, x0 - 0.2, y0 - 0.2, 0.35, x1 + 0.2, y1 + 0.2, 0.9)             # 圭角
add_box('楼台_marble', MARBLE, x0 - 0.05, y0 - 0.05, 0.9, x1 + 0.05, y1 + 0.05, 1.25)         # 下枭
add_box('楼台_marble', MARBLE, x0 + 0.2, y0 + 0.2, 1.25, x1 - 0.2, y1 - 0.2, T - 1.0)         # 束腰
for k in range(int((x1 - x0) / 2.4) + 1):                                                      # 束腰上的间柱
    x = x0 + 0.2 + k * (x1 - x0 - 0.4) / int((x1 - x0) / 2.4)
    add_box('楼台_marble', MARBLE, x - 0.18, y0 + 0.08, 1.25, x + 0.18, y0 + 0.3, T - 1.0)
add_box('楼台_marble', MARBLE, x0 - 0.05, y0 - 0.05, T - 1.0, x1 + 0.05, y1 + 0.05, T - 0.45)  # 上枭
add_box('楼台_marble', MARBLE, x0 - 0.25, y0 - 0.25, T - 0.45, x1 + 0.25, y1 + 0.25, T)       # 台面压面石
add_box('台面_pave', mat('M_方砖地'), x0, y0, T, x1, y1, T + 0.005)
for s_ in (-1, 1):
    # 台面高过 1.8 m 的地坪格在网页里从下面算墙，每级须低于 0.2 m 才上得去
    stairs('台阶_marble', s_ * 20.15, 1.6, P3[1] - 0.25, 1.5, T, direction=-1, tread=0.45, rise=0.125)   # 踏面宽过 0.4 m 碰撞格，每格最多升一级
balustrade('楼台栏杆_marble', [(-19.1, P3[1] - 0.1), (-12.0, P3[1] - 0.1)], T)
balustrade('楼台栏杆_marble', [(12.0, P3[1] - 0.1), (19.1, P3[1] - 0.1)], T)
for s_ in (-1, 1):
    balustrade('楼台栏杆_marble', [(s_ * (P3[2] + 0.1), P3[1]), (s_ * (P3[2] + 0.1), 18.8)], T)
    balustrade('楼台栏杆_marble', [(s_ * (P3[2] + 0.1), 24.2), (s_ * (P3[2] + 0.1), P3[3] + 0.1), (0, P3[3] + 0.1)], T)

# ============================================================ 6. 甬路、石灯座、水池
Y0, Y1 = -34.0, P1[1] - r1          # 甬路从院门到台阶脚
PW = 2.2
add_box('甬路_marble', MARBLE, -PW, Y0, 0.0, PW, Y1, 0.14)
for i in range(int((Y1 - Y0) / 1.2)):          # 甬路中线一路方石缝（细一点的浅槽感：铺一道略低的条石）
    y = Y0 + 0.6 + i * 1.2
    add_box('甬路_stone', STONE, -PW + 0.05, y - 0.012, 0.139, PW - 0.05, y + 0.012, 0.142)
PF = -22.0                                   # 牌坊位置
for s in (-1, 1):
    x = s * (PW + 0.25)
    balustrade('甬路栏杆_marble', [(x, Y0 + 1.5), (x, PF - 2.0)], 0.14, h=0.6, step=1.6)
    balustrade('甬路栏杆_marble', [(x, PF + 2.0), (x, Y1 - 0.4)], 0.14, h=0.6, step=1.6)

# 两方水池（略高出地面的池子，池岸叠山石），池上放 TRIPO占位 挡人
PONDS = [(s * 11.6, -28.4, 7.2, 4.2) for s in (-1, 1)]
for (cx, cy, rx, ry) in PONDS:
    n = 40
    ring = [(cx + rx * math.cos(2 * math.pi * i / n) * (1 + 0.06 * math.sin(5 * i * 0.7)), cy + ry * math.sin(2 * math.pi * i / n) * (1 + 0.05 * math.cos(3 * i * 0.9))) for i in range(n)]
    add_geom('水池_water', WATER, [(x, y, 0.24) for x, y in ring], [tuple(range(n))])
    add_geom('水池底_stone', POOL, [(x, y, 0.03) for x, y in ring], [tuple(range(n))])
    for i in range(n):        # 池岸：一圈山石
        a = 2 * math.pi * (i + random.random() * 0.4) / n
        r = 1.0 + random.uniform(-0.03, 0.05)
        x = cx + rx * math.cos(a) * r; y = cy + ry * math.sin(a) * r
        w = random.uniform(0.6, 1.2); d = random.uniform(0.5, 0.9); h = random.uniform(0.35, 0.8)
        bm_key = '池岸_rock'
        if bm_key not in BOX_BM: BOX_BM[bm_key] = (bmesh.new(), ROCK)
        bm = BOX_BM[bm_key][0]
        rr = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.5)
        rot = Matrix.Rotation(a + random.uniform(-0.4, 0.4), 4, 'Z')
        for v in rr['verts']:
            co = Vector((v.co.x * w * random.uniform(0.85, 1.15), v.co.y * d * random.uniform(0.85, 1.15), max(v.co.z, -0.1) * h * 2))
            v.co = (rot @ co) + Vector((x, y, 0.0))
    add_box('水池挡_tripo', PH, cx - rx, cy - ry, 0.0, cx + rx, cy + ry, 1.6)

# ============================================================ 7. Tripo 占位（牌坊柱、石狮、石灯座、香炉；网页 PROPS.daguan 放模型）
for x in (-7.0, -2.8, 2.8, 7.0):            # 牌坊四柱（paifang_build.py：明间柱 ±2.8、次间柱 ±7.0）
    add_box('牌坊柱_tripo', PH, x - 0.75, PF - 0.75, 0.0, x + 0.75, PF + 0.75, 6.0)
LIONS = [(s * 3.7, PF - 1.9) for s in (-1, 1)]   # 石狮蹲在明间柱前（参考图）
for x, y in LIONS:
    add_box('石狮_tripo', PH, x - 0.85, y - 0.7, 0.0, x + 0.85, y + 0.7, 2.6)
LAMPS = [(s * 3.35, y) for s in (-1, 1) for y in (-31.5, -26.5, -17.6)]
for x, y in LAMPS:
    add_box('石灯_tripo', PH, x - 0.45, y - 0.45, 0.0, x + 0.45, y + 0.45, 2.6)

flush()

# ============================================================ 8. 标记（碰撞另跑 daguan_cols.py）
mk = bpy.data.objects.new('daguan_改样标记', None); COLL.objects.link(mk)

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print('saved')
