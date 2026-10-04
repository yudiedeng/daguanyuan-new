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
  2. 大观楼立在正殿后面一座 3 m 高的白石台上，三层：首层、二层、三层各一节楼身（借原大观楼楼身，面阔放大 1.25 倍），
     层间腰檐（借正殿下檐缩小），顶上重檐歇山（原上檐）。全组最高。
  3. 缀锦阁、含芳阁不动；两条双层复道后移 2.5 m、加长，接到大观楼首层两山。
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
T = 3.0                    # 大观楼台高
TY = 23.5                  # 大观楼中心 y
SX, SY = 1.25, 1.1         # 大观楼楼身放大


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

# ============================================================ 2. 大观楼（三层）
TOWER = scale_about(0, 20, 0, SX, SY, 1.0)
TOWER = move(0, TY - 20, 0) @ TOWER
floors = [T - 13.1, None, None]             # 首层：平座面落在台面
eave_dz = [T + 3.0 - 8.8, None]             # 腰檐一：檐口 z = T+3.0
storey_top = lambda dz: 16.5 + dz
eave_dz[0] = storey_top(floors[0]) - 0.4 - 8.8
floors[1] = eave_dz[0]                      # 原件里楼身(11.3)与下檐(8.8)的高差保持不变
eave_dz[1] = storey_top(floors[1]) - 0.4 - 8.8
floors[2] = eave_dz[1]
print('大观楼 层 dz', floors, '腰檐 dz', eave_dz)

for k, dz in enumerate(floors):
    src = STOREY if k == 2 else [dup(o, f'_{k + 1}层') for o in STOREY]
    for o in src:
        bake(o, move(0, 0, dz) @ TOWER)
for o in TOPROOF:
    bake(o, move(0, 0, floors[2]) @ TOWER)
for o in PLAQUE:     # 匾只平移，贴到放大后的楼身前檐
    bake(o, move(0, (14.7 - 20) * (SY - 1) + TY - 20, floors[2]))
# 腰檐：借正殿下檐，缩到大观楼楼身
for k, dz in enumerate(eave_dz):
    for o in EAVE:
        c = dup(o, f'_大观楼腰{k + 1}')
        c.name = c.name.replace('daguan_下檐_', f'daguan_大观楼腰檐{k + 1}_')
        # 下檐已随正殿前移 DH，先移回原处再缩放
        bake(c, move(0, TY - 20, dz) @ scale_about(0, 20, 8.8, 0.93, 0.8, 1.0) @ move(0, -DH, 0))

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


bx, by = 10.9 * SX - 0.25, 4.6 * SY - 0.25
for k in range(2):
    z0 = storey_top(floors[k]) - 0.3; z1 = 11.3 + floors[k + 1] + 0.3
    add_box('大观楼层间_lacquer_red', RED, -bx, TY - by, z0, bx, TY + by, z1)
# 正殿重檐：上下檐之间的一圈墙（楼身压扁件之外再垫一层，防漏缝）
add_box('正殿重檐_lacquer_red', RED, -12.6, 20 + DH - 5.0, 9.3, 12.6, 20 + DH + 5.0, 12.6)

# ============================================================ 3. 复道：后移、加长，接大观楼首层两山
for o in names('daguan_复道'):
    s = 1 if o.name.startswith(('daguan_复道东', 'daguan_复道顶东')) else -1
    end = 10.9 * SX
    f = (28.5 - end) / (28.5 - 14.6)
    bake(o, move(0, 2.5, 0) @ scale_about(s * 28.5, 0, 0, f, 1, 1))

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
P1 = (-22.0, -12.0, 22.0, 14.0); P2 = (-18.5, -8.5, 18.5, 14.0)
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

# 大观楼台：3 m，台前两侧各一道踏跺从正殿二层台上去
P3 = (-18.0, 13.6, 18.0, 31.0)
platform('楼台_marble', *P3, 0.0, T)
add_box('台面_pave', mat('M_方砖地'), P3[0] + 0.1, P3[1] + 0.1, T, P3[2] - 0.1, P3[3] - 0.1, T + 0.005)
for s in (-1, 1):
    # 台面高过 1.8 m 的地坪格在网页里从下面算墙，每级须低于 0.2 m 才上得去
    stairs('台阶_marble', s * 17.2, 1.6, P3[1], 1.5, T, direction=-1, tread=0.4, rise=0.125)
balustrade('楼台栏杆_marble', [(-16.2, P3[1]), (-12.0, P3[1])], T)
balustrade('楼台栏杆_marble', [(12.0, P3[1]), (16.2, P3[1])], T)
for s in (-1, 1):
    balustrade('楼台栏杆_marble', [(s * P3[2], P3[1]), (s * P3[2], 18.8)], T)
    balustrade('楼台栏杆_marble', [(s * P3[2], 24.2), (s * P3[2], P3[3]), (0, P3[3])], T)

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
PF_H = 12.0
for xn in (-0.46, -0.21, 0.21, 0.46):
    x = xn * PF_H
    add_box('牌坊柱_tripo', PH, x - 0.55, PF - 0.55, 0.0, x + 0.55, PF + 0.55, 6.0)
LIONS = [(s * 7.0, PF - 1.6) for s in (-1, 1)]
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
