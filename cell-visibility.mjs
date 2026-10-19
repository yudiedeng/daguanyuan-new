// Conservative, position-cell PVS. Each exclusion retains a real source
// triangle as its witness; courtyard boxes and inferred portals are never solid.
// For one triangle edge, the shadow half-space inequality is bilinear in viewer
// and target position. Testing all eight viewer-cell corners and the extrema of
// the target AABB therefore proves it for EVERY viewer and target in the boxes.
// The viewer cell and target must also lie strictly on opposite triangle sides.
const EPS = 2e-4;
const finiteBox = b => b?.isBox3 && !b.isEmpty() &&
  [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z].every(Number.isFinite);
const materials = o => Array.isArray(o.material) ? o.material : [o.material];
function opaque(T, m) {
  if (!m || m.visible === false || m.transparent || m.opacity !== 1 || m.alphaTest > 0 || m.alphaMap ||
    m.alphaHash || m.alphaToCoverage || m.wireframe || m.displacementMap || m.transmission > 0 ||
    m.depthWrite === false || m.depthTest === false || m.colorWrite === false || m.stencilWrite ||
    m.depthFunc !== T.LessEqualDepth || m.blending !== T.NormalBlending || m.polygonOffset ||
    m.clippingPlanes?.length || m.isShaderMaterial || m.isRawShaderMaterial) return false;
  if (!(m.isMeshBasicMaterial || m.isMeshLambertMaterial || m.isMeshPhongMaterial || m.isMeshStandardMaterial ||
    m.isMeshNormalMaterial || m.isMeshToonMaterial)) return false;
  if (!m.userData?.dgyOcclusionStaticSurface &&
    (m.onBeforeCompile !== T.Material.prototype.onBeforeCompile || m.userData?.shadowDynamic)) return false;
  return [T.FrontSide, T.BackSide, T.DoubleSide].includes(m.side);
}
function keepLargest(heap, value, limit) {
  if (heap.length < limit) {
    let i = heap.length; heap.push(value);
    while (i) { const p = (i - 1) >> 1; if (heap[p].area <= value.area) break; heap[i] = heap[p]; i = p; }
    heap[i] = value;
  } else if (limit && value.area > heap[0].area) {
    let i = 0;
    while (i * 2 + 1 < heap.length) {
      let c = i * 2 + 1; if (c + 1 < heap.length && heap[c + 1].area < heap[c].area) c++;
      if (heap[c].area >= value.area) break; heap[i] = heap[c]; i = c;
    }
    heap[i] = value;
  }
}
const normalAxis = n => Math.abs(n.x) >= Math.abs(n.y) && Math.abs(n.x) >= Math.abs(n.z) ? 0 : Math.abs(n.y) >= Math.abs(n.z) ? 1 : 2;
// A large floor (or repeated roof LODs) must not consume every face slot. The
// three independent normal-axis queues keep both wall directions available.
// This changes only which real triangles are tried, never the proof itself.
function balancedFaces(buckets, limit, score = f => f.area) {
  for (const bucket of buckets) bucket.sort((a, b) => score(b) - score(a));
  const order = buckets.filter(b => b.length).sort((a, b) => score(b[0]) - score(a[0]));
  const result = [];
  for (let i = 0; result.length < limit; i++) {
    let found = false;
    for (const bucket of order) if (i < bucket.length) {
      result.push(bucket[i]); found = true;
      if (result.length >= limit) break;
    }
    if (!found) break;
  }
  return result;
}
function* collectFaces(T, registry, options) {
  const heaps = [[], [], []], a = new T.Vector3(), b = new T.Vector3(), c = new T.Vector3(), e = new T.Vector3(), n = new T.Vector3();
  let work = 0;
  for (const mesh of registry.occluders) {
    if (!registry.isCurrent(mesh) || !mesh.isMesh || mesh.isInstancedMesh || mesh.isSkinnedMesh || mesh.isBatchedMesh ||
      mesh.animations?.length || mesh.userData.dynamic || mesh.onBeforeRender !== T.Object3D.prototype.onBeforeRender) continue;
    const geometry = mesh.geometry, p = geometry?.attributes.position, ix = geometry?.index;
    if (!p || p.isGLBufferAttribute || !(p.array || p.data?.array) || geometry.isInstancedBufferGeometry ||
      Object.keys(geometry.morphAttributes || {}).length) continue;
    const ms = materials(mesh), total = ix ? ix.count : p.count;
    const record = { mesh, geometry, p, ix, pVersion: p.version ?? p.data?.version, ixVersion: ix?.version,
      drawStart: geometry.drawRange.start, drawCount: geometry.drawRange.count,
      groups: JSON.stringify(geometry.groups), determinant: mesh.matrixWorld.determinant() < 0 ? -1 : 1 };
    const locals = [[], [], []], groups = Array.isArray(mesh.material) ? geometry.groups : [{ start: 0, count: total, materialIndex: 0 }];
    for (const group of groups) {
      if (!opaque(T, ms[group.materialIndex])) continue;
      const from = Math.max(record.drawStart, group.start), to = Math.min(total, record.drawStart + record.drawCount, group.start + group.count);
      if (from % 3 || to % 3) continue;
      for (let i = from; i + 2 < to; i += 3) {
        if (++work % 2048 === 0) yield null;
        a.fromBufferAttribute(p, ix ? ix.getX(i) : i).applyMatrix4(mesh.matrixWorld);
        b.fromBufferAttribute(p, ix ? ix.getX(i + 1) : i + 1).applyMatrix4(mesh.matrixWorld);
        c.fromBufferAttribute(p, ix ? ix.getX(i + 2) : i + 2).applyMatrix4(mesh.matrixWorld);
        n.subVectors(b, a).cross(e.subVectors(c, a)); const area = n.length() * .5, axis = normalAxis(n), local = locals[axis];
        if (!(area >= options.minTriangleArea) || !Number.isFinite(area) || !options.maxFacesPerMesh ||
          (local.length >= options.maxFacesPerMesh && area <= local[0].area)) continue;
        n.normalize();
        keepLargest(local, { record, materialIndex: group.materialIndex, area, axis,
          vertices: new Float64Array([...a, ...b, ...c]), normal: n.clone(), constant: -n.dot(a),
          bounds: new T.Box3().setFromPoints([a, b, c]) }, options.maxFacesPerMesh);
      }
    }
    for (const face of balancedFaces(locals, options.maxFacesPerMesh)) keepLargest(heaps[face.axis], face, options.maxFaces);
    yield null;
  }
  return balancedFaces(heaps, options.maxFaces);
}
function minPlane(box, x, y, z, w) {
  return x * (x >= 0 ? box.min.x : box.max.x) + y * (y >= 0 ? box.min.y : box.max.y) + z * (z >= 0 ? box.min.z : box.max.z) + w;
}
function maxPlane(box, x, y, z, w) { return -minPlane(box, -x, -y, -z, -w); }
function shadowVolume(T, face, cell) {
  const n = face.normal, low = minPlane(cell, n.x, n.y, n.z, face.constant), high = maxPlane(cell, n.x, n.y, n.z, face.constant);
  const side = low > EPS ? 1 : high < -EPS ? -1 : 0;
  if (!side) return null;
  // A cell entirely on one side gives every edge/viewer plane the same inward
  // orientation. Before normalization, (edge x (viewer-a)) dot (target-a) is
  // bilinear. Its extrema over cell x targetBox occur at their corner pairs;
  // normalizing by a positive length preserves these inequality signs.
  // The first plane requires the target strictly behind the actual triangle.
  const planes = [-side * n.x, -side * n.y, -side * n.z, -side * face.constant];
  const view = new T.Vector3(), a = new T.Vector3(), b = new T.Vector3(), third = new T.Vector3(), q = new T.Vector3(), normal = new T.Vector3();
  for (let i = 0; i < 8; i++) {
    view.set(i & 1 ? cell.max.x : cell.min.x, i & 2 ? cell.max.y : cell.min.y, i & 4 ? cell.max.z : cell.min.z);
    for (let k = 0; k < 3; k++) {
      a.fromArray(face.vertices, k * 3); b.fromArray(face.vertices, (k + 1) % 3 * 3); third.fromArray(face.vertices, (k + 2) % 3 * 3);
      normal.subVectors(b, a).cross(q.subVectors(view, a)); const length = normal.length();
      if (!(length > 1e-10)) return null;
      normal.multiplyScalar(1 / length); let d = -normal.dot(a), inside = normal.dot(third) + d;
      if (Math.abs(inside) < EPS) return null;
      if (inside < 0) { normal.negate(); d = -d; }
      planes.push(normal.x, normal.y, normal.z, d);
    }
  }
  return { face, side, planes: new Float64Array(planes) };
}
function containsBox(volume, box) {
  const p = volume.planes;
  for (let i = 0; i < p.length; i += 4) if (!(minPlane(box, p[i], p[i + 1], p[i + 2], p[i + 3]) > EPS)) return false;
  return true;
}
const boxValues = b => [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z];
const sameBox = (a, b) => a[0] === b.min.x && a[1] === b.min.y && a[2] === b.min.z && a[3] === b.max.x && a[4] === b.max.y && a[5] === b.max.z;
function optionsFor(options) {
  return { cellSize: 1.5, maxCells: 24, maxFaces: 8192, maxFacesPerMesh: 16, maxFacesPerCell: 48,
    maxPairTests: 30000, maxResultsPerCell: 2048, maxOccluderDistance: 60, maxTargetDistance: 180,
    minTriangleArea: .15, ...options };
}
function bind(T, camera, registry, faces, options, buildMs) {
  const cache = new Map(), eye = new T.Vector3(), centre = new T.Vector3();
  let enabled = true, active = null, layers = camera.layers.mask, validRecords = new WeakMap();
  const stats = { faces: faces.length, faceAxes: faces.reduce((n, f) => (n[f.axis]++, n), [0, 0, 0]), buildMs,
    cellsBuilt: 0, cacheHits: 0, cachedCells: 0, cachedExclusions: 0, seededCells: 0, seededExclusions: 0, seedMs: 0,
    precomputeMs: 0, updateMs: 0, lastPairTests: 0, lastBroadphaseTests: 0, lastBroadphaseRejected: 0,
    lastVolumes: 0, lastCandidatePlanesRejected: 0, lastExclusions: 0, budgetExhausted: false, tested: 0, culled: 0 };
  function coords(position) {
    const s = options.cellSize;
    return [Math.floor(position.x / s), Math.floor(position.y / s), Math.floor(position.z / s)];
  }
  function entry(position) {
    const xyz = coords(position), key = xyz.join(',');
    if (cache.has(key)) { const hit = cache.get(key); cache.delete(key); cache.set(key, hit); stats.cacheHits++; return hit; }
    const start = performance.now(), s = options.cellSize;
    const cell = new T.Box3(new T.Vector3(...xyz).multiplyScalar(s), new T.Vector3(...xyz.map(v => v + 1)).multiplyScalar(s));
    cell.getCenter(centre);
    const targets = [], targetUnion = new T.Box3();
    for (const [object, box] of registry.bounds) if (finiteBox(box) && box.distanceToPoint(centre) <= options.maxTargetDistance) {
      targets.push([object, box]); targetUnion.union(box);
    }
    const candidates = [[], [], []];
    let rejectedPlanes = 0;
    for (const face of faces) {
      const d = face.bounds.distanceToPoint(centre);
      if (d > options.maxOccluderDistance) continue;
      const n = face.normal, low = minPlane(cell, n.x, n.y, n.z, face.constant), high = maxPlane(cell, n.x, n.y, n.z, face.constant);
      const side = low > EPS ? 1 : high < -EPS ? -1 : 0;
      // If even the union of all targets has no point beyond this plane, none
      // can possibly be hidden. Reject before sorting or building 24 edge planes.
      if (!side || !targets.length || maxPlane(targetUnion, -side * n.x, -side * n.y, -side * n.z, -side * face.constant) <= EPS) {
        rejectedPlanes++; continue;
      }
      candidates[face.axis].push({ face, rank: face.area / Math.max(.25, d * d) });
    }
    const volumes = [];
    for (const { face } of balancedFaces(candidates, faces.length, c => c.rank)) {
      if (volumes.length >= options.maxFacesPerCell) break;
      const volume = shadowVolume(T, face, cell); if (volume) volumes.push(volume);
    }
    // Larger hierarchy bounds are attempted first, then the remaining source
    // order. Missing a bounded-work result only retains its normal draw.
    targets.sort((a, b) => Number(!!b[0].userData.dgySpatialWorldBounds) - Number(!!a[0].userData.dgySpatialWorldBounds));
    const results = new Map(), cursors = new Uint32Array(volumes.length);
    let pairs = 0, broadphase = 0, rejected = 0, exhausted = false, remaining = true;
    // One exact proof per volume per round prevents the first face monopolising
    // the pair budget. Cheap separating-plane tests do not consume that budget:
    // e.g. a floor cannot hide an object above it from a viewer also above it.
    // Each target/volume still advances once, bounding broadphase work to N*M.
    outer: while (remaining) {
      remaining = false;
      for (let v = 0; v < volumes.length; v++) {
        const volume = volumes[v], p = volume.planes;
        while (cursors[v] < targets.length) {
          if (pairs >= options.maxPairTests || results.size >= options.maxResultsPerCell) { exhausted = true; break outer; }
          const [object, box] = targets[cursors[v]++];
          if (results.has(object)) continue;
          broadphase++;
          if (!(minPlane(box, p[0], p[1], p[2], p[3]) > EPS)) { rejected++; continue; }
          remaining = true; pairs++;
          if (containsBox(volume, box)) results.set(object, { face: volume.face, side: volume.side, values: boxValues(box) });
          break;
        }
      }
    }
    const value = { key, cell, results }; cache.set(key, value);
    stats.cachedExclusions += results.size;
    while (cache.size > options.maxCells) { const oldest = cache.keys().next().value; stats.cachedExclusions -= cache.get(oldest).results.size; cache.delete(oldest); }
    stats.cachedCells = cache.size; stats.cellsBuilt++; stats.lastPairTests = pairs; stats.lastExclusions = results.size;
    stats.lastBroadphaseTests = broadphase; stats.lastBroadphaseRejected = rejected; stats.lastVolumes = volumes.length;
    stats.lastCandidatePlanesRejected = rejectedPlanes;
    stats.budgetExhausted = exhausted; stats.precomputeMs = performance.now() - start; return value;
  }
  function validFace(witness, view) {
    const record = witness.face.record, mesh = record.mesh;
    if (!validRecords.has(record)) {
      const g = mesh.geometry;
      let valid = registry.isCurrent(mesh) && g === record.geometry && g.attributes.position === record.p && g.index === record.ix &&
        (record.p.version ?? record.p.data?.version) === record.pVersion && record.ix?.version === record.ixVersion &&
        g.drawRange.start === record.drawStart && g.drawRange.count === record.drawCount &&
        (!Array.isArray(mesh.material) || JSON.stringify(g.groups) === record.groups) && mesh.layers.test(view.layers);
      for (let p = mesh; p && valid; p = p.parent) if (!p.visible) valid = false;
      validRecords.set(record, valid);
    }
    if (!validRecords.get(record)) return false;
    const material = materials(mesh)[witness.face.materialIndex];
    return opaque(T, material) && (material.side === T.DoubleSide ||
      (witness.side * record.determinant > 0 ? material.side === T.FrontSide : material.side === T.BackSide));
  }
  const api = {
    stats,
    get enabled() { return enabled; }, set enabled(value) { enabled = !!value; active = null; },
    update(view = camera) {
      const start = performance.now(); stats.tested = stats.culled = 0; validRecords = new WeakMap(); active = null; layers = view?.layers.mask;
      if (enabled && view === camera && view.isPerspectiveCamera) {
        eye.setFromMatrixPosition(view.matrixWorld); if ([eye.x, eye.y, eye.z].every(Number.isFinite)) active = entry(eye);
      }
      stats.updateMs = performance.now() - start; return stats;
    },
    isObjectOccluded(object, view) {
      if (!enabled || !active || view !== camera || !view.isPerspectiveCamera || view.layers.mask !== layers) return false;
      const witness = active.results.get(object);
      if (!witness) return false;
      eye.setFromMatrixPosition(view.matrixWorld); if (!active.cell.containsPoint(eye)) return false;
      const box = registry.bounds.get(object);
      if (!finiteBox(box) || !sameBox(witness.values, box) || !registry.isCurrent(object)) return false;
      stats.tested++; const hidden = validFace(witness, view); if (hidden) stats.culled++;
      return hidden;
    },
    precompute(positions) {
      for (const p of positions) entry(Array.isArray(p) ? new T.Vector3(...p) : p); return stats;
    },
    async precomputeAsync(positions, { yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)), onProgress = () => {} } = {}) {
      const start = performance.now(), before = stats.cellsBuilt, exclusions = stats.cachedExclusions;
      let done = 0;
      for (const p of positions) {
        entry(Array.isArray(p) ? new T.Vector3(...p) : p);
        onProgress({ done: ++done, total: positions.length }); await yieldFrame();
      }
      stats.seededCells = stats.cellsBuilt - before; stats.seededExclusions = stats.cachedExclusions - exclusions;
      stats.seedMs = performance.now() - start; return stats;
    },
    invalidate() { active = null; cache.clear(); validRecords = new WeakMap(); stats.cachedCells = stats.cachedExclusions = 0; },
    dispose() { enabled = false; api.invalidate(); faces.length = 0; },
  };
  return api;
}
function setup({ THREE, camera, registry, ...rest }) {
  if (!THREE || !camera || !registry?.bounds || typeof registry.isCurrent !== 'function') throw new Error('THREE, main camera and certified scene registry are required');
  const options = optionsFor(rest);
  if (!(options.cellSize > 0) || !Number.isFinite(options.cellSize) || !(options.maxCells >= 1)) throw new Error('finite positive cellSize and maxCells >= 1 are required');
  return { THREE, camera, registry, options };
}
// INTER rooms use local [x0,z0,x1,z1,floor,ceiling] coordinates. Model scale and
// rotation belong to localToWorld; walking eye height is a WORLD distance.
// Seed one room per loaded interior before extra rooms in the same building.
export function interiorVisibilitySeeds({ THREE: T, interiors, maxCells = 12, cellSize = 1.5, eyeHeight = 1.296 }) {
  const points = [], keys = new Set(), ceiling = new T.Vector3();
  if (!(cellSize > 0) || !(eyeHeight > 0)) return points;
  const loaded = interiors.filter(i => i.root?.parent && i.rooms?.length);
  for (const interior of loaded) interior.root.updateWorldMatrix(true, false);
  for (let roomIndex = 0; points.length < maxCells; roomIndex++) {
    let found = false;
    for (const { root, rooms } of loaded) {
      const room = rooms[roomIndex]; if (!room) continue; found = true;
      if (!room.slice(0, 6).every(Number.isFinite)) continue;
      const x = (room[0] + room[2]) * .5, z = (room[1] + room[3]) * .5;
      const point = root.localToWorld(new T.Vector3(x, room[4], z));
      root.localToWorld(ceiling.set(x, room[5], z));
      if (![point.x, point.y, point.z, ceiling.y].every(Number.isFinite) || ceiling.y - point.y <= eyeHeight + .1) continue;
      point.y += eyeHeight;
      const key = [point.x, point.y, point.z].map(v => Math.floor(v / cellSize)).join(',');
      if (keys.has(key)) continue; keys.add(key); points.push(point);
      if (points.length >= maxCells) break;
    }
    if (!found) break;
  }
  return points;
}
export function createCellVisibility(args) {
  const { THREE, camera, registry, options } = setup(args), start = performance.now();
  const iterator = collectFaces(THREE, registry, options); let step;
  do { step = iterator.next(); } while (!step.done);
  return bind(THREE, camera, registry, step.value, options, performance.now() - start);
}
export async function prepareCellVisibility(args, { budgetMs = 8, yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)) } = {}) {
  const { THREE, camera, registry, options } = setup(args), start = performance.now(); let slice = start;
  const iterator = collectFaces(THREE, registry, options); let step;
  do {
    step = iterator.next();
    if (!step.done && performance.now() - slice >= budgetMs) { await yieldFrame(); slice = performance.now(); }
  } while (!step.done);
  return bind(THREE, camera, registry, step.value, options, performance.now() - start);
}
