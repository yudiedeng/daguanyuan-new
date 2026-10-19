import { finishTask, startTask } from './cooperative-task.mjs';
/* 人物与引路共用的步行规则；寻路不包含跳跃或按 E 穿门。 */
export const WALK_RULES = Object.freeze({ step: 0.45, bodyHeight: 1.7, minGround: 0.2 });
export function blocksWalking(c, feet) {
  return !c.walk && c.top > feet + WALK_RULES.step && c.bot <= feet + WALK_RULES.bodyHeight;
}

export function createWalkSurface({ groundAt, terrainHeight, collidersAt, inBounds, radius }) {
  // 半个采样间距的余量，避免在两个采样点之间漏掉薄墙或栏杆。
  const spacing = 0.12;
  function blocked(x, z, feet, padding = spacing / 2) {
    const r = radius() + padding;
    for (const c of collidersAt(x, z)) {
      if (!blocksWalking(c, feet)) continue;
      const dx = x - c.x, dz = z - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c;
      if (Math.hypot(Math.max(0, Math.abs(lx) - c.hx), Math.max(0, Math.abs(lz) - c.hz)) < r - 1e-7) return true;
    }
    return false;
  }
  function point(x, z, feet, padding = spacing / 2) {
    if (feet == null) {
      if (!Number.isFinite(x + z) || !inBounds(x, z)) return null;
      // 先找最低的可站立层。直接从高处向下取最高面，会把门楼顶、游廊顶误当成地面。
      const terrain = terrainHeight(x, z), levels = [terrain], solids = [], max = Math.max(terrain, 0) + 4.12;
      for (const c of collidersAt(x, z)) {
        const dx = x - c.x, dz = z - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c;
        if (Math.abs(lx) <= c.hx + .02 && Math.abs(lz) <= c.hz + .02) {
          solids.push(c);
          if (c.top > terrain && c.top <= max) levels.push(c.top);
        }
      }
      for (const y of levels.sort((a, b) => a - b)) {
        const floor = point(x, z, y, padding);
        // walk 只表示可以站在顶面，台基内部的旧地形不是另一个可走层。
        if (floor != null && !solids.some(c => c.bot <= floor + .01 && c.top > floor + .05)) return floor;
      }
      return null;
    }
    if (!Number.isFinite(x + z + feet) || !inBounds(x, z)) return null;
    const [y, terrain] = groundAt(x, z, feet);
    if (!Number.isFinite(y) || (terrain && y < WALK_RULES.minGround) || blocked(x, z, y, padding)) return null;
    return y;
  }
  function segment(a, b, { roadsOnly = false, linearHeight = false, isLawn = () => false, startPadding = spacing / 2, endPadding = spacing / 2 } = {}) {
    const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
    // 人物可以贴到墙上；接入路径图的前后 0.6 米逐渐恢复额外余量，始终保留人物本身的半径。
    const paddingAt = t => Math.min(spacing / 2, startPadding + length * t * .1, endPadding + length * (1 - t) * .1);
    let y = point(a[0], a[1], a[2], paddingAt(0));
    if (y == null || (a[2] != null && Math.abs(y - a[2]) > 0.05)) return false;
    const n = Math.max(1, Math.ceil(length / (Math.min(startPadding, endPadding) < spacing / 2 ? .025 : spacing)));
    let px = a[0], pz = a[1];
    for (let i = 1; i <= n; i++) {
      const x = a[0] + (b[0] - a[0]) * i / n, z = a[1] + (b[1] - a[1]) * i / n;
      const padding = paddingAt(i / n), next = point(x, z, y, padding);
      // pushOut 先按上一步的脚高处理碰撞，groundAt 才抬脚；两端都检查，边才能双向通行。
      // 高度不变时，point 已检查当前落点，上一步也已检查；不重复查询同一碰撞体。
      if (next == null || Math.abs(next - y) > WALK_RULES.step ||
          (next !== y && (blocked(x, z, y, padding) || blocked(px, pz, next, paddingAt((i - 1) / n))))) return false;
      if (linearHeight && Math.abs(next - (a[2] + (b[2] - a[2]) * i / n)) > 0.04) return false;
      if (roadsOnly && Math.min(i, n - i) * length / n > 2.5 && isLawn(x, z, next)) return false;
      px = x; pz = z; y = next;
    }
    return b[2] == null || Math.abs(y - b[2]) < 0.05;
  }
  // 三维空间诊断：按小体积检查墙、栏杆和顶板；穿墙显示的转向提示不使用这项限制。
  function space(a, b, padding = 0.025) {
    const length = Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]), n = Math.max(1, Math.ceil(length / 0.05)), r = padding + length / n / 2;
    for (let i = 0; i <= n; i++) {
      const x = a[0] + (b[0] - a[0]) * i / n, z = a[1] + (b[1] - a[1]) * i / n, y = a[2] + (b[2] - a[2]) * i / n;
      if (!Number.isFinite(x + z + y) || y < terrainHeight(x, z) + padding) return false;
      for (const c of collidersAt(x, z)) {
        const dx = x - c.x, dz = z - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c;
        if (Math.hypot(Math.max(0, Math.abs(lx) - c.hx), Math.max(0, Math.abs(lz) - c.hz), Math.max(0, c.bot - y, y - c.top)) < r) return false;
      }
    }
    return true;
  }
  return { point, segment, blocked, space };
}

/* 按需生成并缓存的可走路径图：节点是能容纳人物的落脚点，边是逐段验证过的路。
   覆盖全园（包括东南侧 z=190 的怡红院），室内加载或人物尺寸变化时整图失效。 */
export function createNavigation({ surface, version, isLawn = () => false, onRoute = () => {}, requestSearch,
  bounds = [-156, -186, 156, 196], cell = 0.6 }) {
  const [x0, z0, x1, z1] = bounds, nx = Math.floor((x1 - x0) / cell) + 1, nz = Math.floor((z1 - z0) / cell) + 1;
  const nodes = new Map(), edges = new Map(), routes = [], validated = new WeakMap(); let stamp;
  function sync() {
    const next = version();
    if (next !== stamp) { stamp = next; nodes.clear(); edges.clear(); }
    return stamp;
  }
  function node(i, j) {
    if (i < 0 || j < 0 || i >= nx || j >= nz) return null;
    const key = i * nz + j;
    if (nodes.has(key)) return nodes.get(key);
    const x = x0 + i * cell, z = z0 + j * cell, y = surface.point(x, z);
    const value = y == null ? null : { key, i, j, p: [x, z, y], cost: isLawn(x, z, y) ? 6 : 1 };
    nodes.set(key, value); return value;
  }
  function linked(a, b) {
    const key = Math.min(a.key, b.key) * nx * nz + Math.max(a.key, b.key);
    if (!edges.has(key)) edges.set(key, surface.segment(a.p, b.p) && surface.segment(b.p, a.p));
    return edges.get(key);
  }
  function* candidates(x, z, r, exact, feet, accept, playerStart = false) {
    const out = [], i0 = Math.round((x - x0) / cell), j0 = Math.round((z - z0) / cell), n = Math.ceil(r / cell);
    for (let di = -n; di <= n; di++) for (let dj = -n; dj <= n; dj++) {
      yield;
      const v = node(i0 + di, j0 + dj);
      if (!v || Math.hypot(v.p[0] - x, v.p[1] - z) > r || (accept && !accept(v.p))) continue;
      // 接入网格也必须走得过去，不能把起终点吸附到墙另一侧。
      if (exact && (!surface.segment([x, z, feet], v.p, playerStart ? { startPadding: 0 } : {}) || !surface.segment(v.p, [x, z, feet], playerStart ? { endPadding: 0 } : {}))) continue;
      out.push(v);
    }
    return out;
  }
  function remember(path, bx, bz) {
    if (path.length < 2 || Math.hypot(path[0][0] - bx, path[0][1] - bz) < 12) return;
    const old = routes.findIndex(r => Math.hypot(r.goal[0] - bx, r.goal[1] - bz) < .01 &&
      Math.hypot(r.path[0][0] - path[0][0], r.path[0][1] - path[0][1]) < 3.6);
    if (old >= 0) routes.splice(old, 1);
    const route = { goal: [bx, bz], path: path.map(p => p.slice()) };
    routes.push(route); validated.set(route, stamp);
    if (routes.length > 48) routes.shift(); onRoute();
  }
  function* reuse(ax, az, ay, bx, bz, by) {
    for (let r = routes.length - 1; r >= 0; r--) {
      const route = routes[r], path = route.path;
      if (Math.hypot(route.goal[0] - bx, route.goal[1] - bz) > .001 || Math.abs(path.at(-1)[2] - by) > .05) continue;
      const joins = [];
      for (let i = 1; i < path.length; i++) {
        const a = path[i - 1], b = path[i], dx = b[0] - a[0], dz = b[1] - a[1], length2 = dx * dx + dz * dz;
        const t = Math.max(0, Math.min(1, ((ax - a[0]) * dx + (az - a[1]) * dz) / (length2 || 1)));
        const p = [a[0] + dx * t, a[1] + dz * t, a[2] + (b[2] - a[2]) * t], d = Math.hypot(p[0] - ax, p[1] - az);
        if (d <= 3.6) joins.push({ i, p, d });
      }
      if (!joins.length) continue;
      if (validated.get(route) !== stamp) {
        let valid = true;
        for (let i = 1; i < path.length; i++) {
          yield;
          if (!surface.segment(path[i - 1], path[i]) || !surface.segment(path[i], path[i - 1])) { valid = false; break; }
        }
        if (!valid) { routes.splice(r, 1); continue; }
        validated.set(route, stamp);
      }
      joins.sort((a, b) => a.d - b.d || b.i - a.i);
      for (const join of joins) {
        yield;
        const y = surface.point(join.p[0], join.p[1], join.p[2]);
        if (y == null) continue;
        join.p[2] = y; const start = [ax, az, ay];
        if (!surface.segment(start, join.p, { startPadding: 0 }) || !surface.segment(join.p, start, { endPadding: 0 })) continue;
        return [start, join.p, ...path.slice(join.i).map(p => p.slice())].filter((p, i, all) => !i || Math.hypot(p[0] - all[i - 1][0], p[1] - all[i - 1][1]) > 1e-6);
      }
    }
    return null;
  }
  function* findPathSteps(ax, az, bx, bz, { maxNodes = 400000, startY, goalY, goalRadius = 0, acceptGoal, useCache = true, remote = true } = {}) {
    sync();
    const ay = surface.point(ax, az, startY, 0), by = goalRadius ? null : surface.point(bx, bz, goalY);
    if (ay == null || (!goalRadius && by == null)) return null;
    if (useCache && !goalRadius && !acceptGoal) {
      const cached = yield* reuse(ax, az, ay, bx, bz, by);
      if (cached) return cached;
    }
    if (requestSearch && remote && !acceptGoal) {
      const path = yield requestSearch([ax, az, bx, bz], { maxNodes, startY, goalY, goalRadius, useCache });
      if (path !== undefined) { if (path?.length > 1 && !goalRadius) remember(path, bx, bz); return path; }
    }
    const starts = yield* candidates(ax, az, cell * 2, true, ay, null, true);
    const goals = yield* candidates(bx, bz, goalRadius || cell * 2, !goalRadius, by, acceptGoal);
    if (!starts.length || !goals.length) return null;
    const target = new Set(goals.map(n => n.key)), scores = new Map(), from = new Map(), closed = new Set(), heap = [];
    // 八向网格到目标候选包围盒的最短距离，比欧氏距离更贴近实际步数，仍不高估代价。
    const minI = Math.min(...goals.map(n => n.i)), maxI = Math.max(...goals.map(n => n.i)),
      minJ = Math.min(...goals.map(n => n.j)), maxJ = Math.max(...goals.map(n => n.j));
    const heuristic = n => {
      const dx = Math.max(0, minI - n.i, n.i - maxI), dz = Math.max(0, minJ - n.j, n.j - maxJ);
      return cell * (Math.max(dx, dz) + (Math.SQRT2 - 1) * Math.min(dx, dz));
    };
    function push(n, g) {
      const entry = { n, g, f: g + heuristic(n) }; heap.push(entry); let i = heap.length - 1;
      while (i) { const p = (i - 1) >> 1; if (heap[p].f <= entry.f) break; heap[i] = heap[p]; i = p; } heap[i] = entry;
    }
    function pop() {
      const first = heap[0], last = heap.pop();
      if (heap.length) { let i = 0; while (2 * i + 1 < heap.length) { let c = 2 * i + 1;
        if (c + 1 < heap.length && heap[c + 1].f < heap[c].f) c++;
        if (heap[c].f >= last.f) break; heap[i] = heap[c]; i = c;
      } heap[i] = last; } return first;
    }
    for (const n of starts) { const g = Math.hypot(n.p[0] - ax, n.p[1] - az) * n.cost; scores.set(n.key, g); push(n, g); }
    let end = null, count = 0;
    while (heap.length && count < maxNodes) {
      const { n, g } = pop(); if (closed.has(n.key) || g !== scores.get(n.key)) continue;
      closed.add(n.key); count++;
      if (target.has(n.key)) { end = n; break; }
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
        yield;
        if (!di && !dj) continue;
        const next = node(n.i + di, n.j + dj);
        if (!next || closed.has(next.key)) continue;
        if (di && dj && (!node(n.i + di, n.j) || !node(n.i, n.j + dj))) continue;
        if (!linked(n, next)) continue;
        const score = g + Math.hypot(di, dj) * cell * (n.cost + next.cost) / 2;
        if (score >= (scores.get(next.key) ?? Infinity)) continue;
        scores.set(next.key, score); from.set(next.key, n.key); push(next, score);
      }
    }
    if (!end) return null;
    const path = [];
    for (let k = end.key; k != null; k = from.get(k)) path.push(nodes.get(k).p);
    path.reverse(); path.unshift([ax, az, ay]); if (!goalRadius) path.push([bx, bz, by]);
    // 拉直只允许经过同样验证的通路，限制前探距离，避免长路线二次方开销。
    const out = [path[0]];
    for (let i = 0; i < path.length - 1;) {
      const connector = i === 0 ? { startPadding: 0 } : {};
      let j = Math.min(path.length - 1, i + 40);
      while (j > i + 1) {
        yield;
        if (surface.segment(path[i], path[j], { roadsOnly: true, linearHeight: true, isLawn, ...connector })) break;
        j--;
      }
      if (!surface.segment(path[i], path[j], connector)) return null;
      if (Math.hypot(path[j][0] - out.at(-1)[0], path[j][1] - out.at(-1)[1]) > 1e-6) out.push(path[j]);
      i = j;
    }
    if (!goalRadius && !acceptGoal) remember(out, bx, bz);
    return out;
  }
  function findPath(...args) { args[4] = { ...args[4], remote: false }; return finishTask(findPathSteps(...args)); }
  function findPathAsync(...args) {
    const original = sync();
    return startTask(findPathSteps(...args), { isCurrent: () => sync() === original }).promise;
  }
  function importRoutes(records) {
    for (const route of (Array.isArray(records) ? records : []).slice(-48)) {
      if (!Array.isArray(route.goal) || route.goal.length !== 2 || !route.goal.every(Number.isFinite) ||
          !Array.isArray(route.path) || route.path.length < 2 || route.path.length > 2048 ||
          !route.path.every(p => Array.isArray(p) && p.length === 3 && p.every(Number.isFinite))) continue;
      const end = route.path.at(-1);
      if (Math.hypot(end[0] - route.goal[0], end[1] - route.goal[1]) > .001) continue;
      routes.push({ goal: route.goal.slice(), path: route.path.map(p => p.slice()) });
    }
    if (routes.length > 48) routes.splice(0, routes.length - 48);
  }
  return { findPath, findPathSteps, findPathAsync, importRoutes,
    exportRoutes: () => routes.map(r => ({ goal: r.goal.slice(), path: r.path.map(p => p.slice()) })),
    surface, get version() { return sync(); }, get size() { return nodes.size; } };
}
