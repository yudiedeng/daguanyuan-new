// CPU-only spatial records made from the source's ORIGINAL triangles. No
// enclosing box, simplified face or inferred solid ever becomes an occluder.
// This lets a nearby portion of a dense rock fit the moving-camera budget.
// Each output carries the same live source certificates as its input.
export function* partitionOcclusionSurface({ THREE: T, record, cellSize = 2, maxTriangles = 2048 }) {
  if (!(cellSize > 0) || !Number.isFinite(cellSize) || !(maxTriangles >= 1)) throw new Error('positive finite patch limits required');
  const limit = Math.floor(maxTriangles), cells = new Map(), v = record.vertices, tris = record.triangles;
  for (let t = 0; t < record.count; t++) {
    if (record.materialIds[t] < 0) continue;
    const a = tris[t * 3] * 3, b = tris[t * 3 + 1] * 3, c = tris[t * 3 + 2] * 3;
    const key = [0, 1, 2].map(k => Math.floor((v[a + k] + v[b + k] + v[c + k]) / (3 * cellSize))).join(',');
    let list = cells.get(key); if (!list) cells.set(key, list = []); list.push(t);
    if ((t & 2047) === 2047) yield null;
  }
  const result = [], p = new T.Vector3();
  for (const list of cells.values()) for (let from = 0; from < list.length; from += limit) {
    const selected = list.slice(from, from + limit), vertices = [], remap = new Map(), edges = [], edgeMap = new Map();
    const triangles = new Uint32Array(selected.length * 3), edgeIds = new Int32Array(selected.length * 3);
    const planes = new Float64Array(selected.length * 4), materialIds = new Int32Array(selected.length), bounds = new T.Box3();
    const vertex = old => {
      let id = remap.get(old); if (id !== undefined) return id;
      id = vertices.length / 3; remap.set(old, id);
      vertices.push(v[old * 3], v[old * 3 + 1], v[old * 3 + 2]);
      bounds.expandByPoint(p.fromArray(v, old * 3)); return id;
    };
    const edge = (a, b) => {
      const lo = Math.min(a, b), hi = Math.max(a, b), key = lo + ',' + hi;
      let id = edgeMap.get(key); if (id === undefined) { id = edges.length / 2; edges.push(lo, hi); edgeMap.set(key, id); }
      return (id + 1) * (a < b ? 1 : -1);
    };
    for (let i = 0; i < selected.length; i++) {
      const old = selected[i], a = vertex(tris[old * 3]), b = vertex(tris[old * 3 + 1]), c = vertex(tris[old * 3 + 2]);
      triangles.set([a, b, c], i * 3); edgeIds.set([edge(a, b), edge(b, c), edge(c, a)], i * 3);
      planes.set(record.planes.subarray(old * 4, old * 4 + 4), i * 4); materialIds[i] = record.materialIds[old];
    }
    bounds.expandByScalar(1e-4);
    result.push({ ...record, count: selected.length, bounds, vertices: new Float64Array(vertices),
      screen: new Float64Array(vertices.length), valid: new Uint8Array(vertices.length / 3),
      edges: new Uint32Array(edges), balance: new Int32Array(edges.length / 2), backBalance: new Int32Array(edges.length / 2),
      triangles, edgeIds, planes, materialIds, surfacePatch: true, sourceBounds: record.sourceBounds || record.bounds });
    yield null;
  }
  return result;
}
