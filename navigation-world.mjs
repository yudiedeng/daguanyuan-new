import { createNavigation, createWalkSurface } from './navigation.js';
// Numeric terrain/collision snapshot shared with the background pathfinder.
export function createNavigationWorld({ HG, COL, paths = [], scale = .8, version = 1 }) {
  const hash = new Map(), pathHash = new Map(), cell = 4;
  for (const c of COL) {
    const r = Math.hypot(c.hx, c.hz);
    for (let i = Math.floor((c.x - r) / cell); i <= Math.floor((c.x + r) / cell); i++)
      for (let j = Math.floor((c.z - r) / cell); j <= Math.floor((c.z + r) / cell); j++) {
        const key = i + ',' + j; if (!hash.has(key)) hash.set(key, []); hash.get(key).push(c);
      }
  }
  for (const p of paths) { const key = Math.floor(p[0] / 4) + ',' + Math.floor(p[1] / 4);
    if (!pathHash.has(key)) pathHash.set(key, []); pathHash.get(key).push(p); }
  function hq(x, z) {
    const fx = Math.max(0, Math.min(HG.nx - 1.001, x - HG.x0)), fz = Math.max(0, Math.min(HG.nz - 1.001, z - HG.z0));
    const i = fx | 0, j = fz | 0, tx = fx - i, tz = fz - j, d = HG.data, n = HG.nx;
    const a = d[j * n + i], b = d[j * n + i + 1], c = d[(j + 1) * n + i], e = d[(j + 1) * n + i + 1];
    const mix = (a, b, t) => a + (b - a) * t;
    return mix(mix(a, b, tx), mix(c, e, tx), tz);
  }
  function groundAt(x, z, feet) {
    let g = hq(x, z), terrain = true;
    for (const c of hash.get(Math.floor(x / 4) + ',' + Math.floor(z / 4)) || []) {
      const dx = x - c.x, dz = z - c.z, lx = dx * c.c - dz * c.s, lz = dx * c.s + dz * c.c;
      if (Math.abs(lx) <= c.hx + .02 && Math.abs(lz) <= c.hz + .02 && c.top <= feet + .52 && c.top > g) { g = c.top; terrain = false; }
    }
    return [g, terrain];
  }
  function collidersAt(x, z) {
    const r = .3 * scale + .06, x0 = Math.floor((x - r) / 4), x1 = Math.floor((x + r) / 4), z0 = Math.floor((z - r) / 4), z1 = Math.floor((z + r) / 4);
    if (x0 === x1 && z0 === z1) return hash.get(x0 + ',' + z0) || [];
    const out = new Set();
    for (let i = x0; i <= x1; i++) for (let j = z0; j <= z1; j++) for (const c of hash.get(i + ',' + j) || []) out.add(c);
    return out;
  }
  function inBounds(x, z) {
    const m = .7;
    return (Math.abs(x) <= 150 - m && z >= -180 + m && z <= 120 - m) ||
      (x >= 20.6 + m && x <= 150 - m && z >= -180 + m && z <= 190 - m) || (Math.abs(x) < 7.5 && z > 118 && z < 138);
  }
  function nearPath(x, z, r = 1.7) {
    const ix = Math.floor(x / 4), iz = Math.floor(z / 4), rr = Math.ceil(r / 4);
    for (let a = -rr; a <= rr; a++) for (let b = -rr; b <= rr; b++)
      for (const p of pathHash.get((ix + a) + ',' + (iz + b)) || []) if ((p[0] - x) ** 2 + (p[1] - z) ** 2 < r * r) return true;
    return false;
  }
  const surface = createWalkSurface({ groundAt, terrainHeight: hq, collidersAt, inBounds, radius: () => .3 * scale });
  const nav = createNavigation({ surface, version: () => version, isLawn: (x, z, y) => groundAt(x, z, y)[1] && !nearPath(x, z) });
  return { surface, nav, hq, groundAt, inBounds, nearPath };
}
