// Lossless spatial aggregation of the explicitly tagged, fixed town BATCH
// tiles. No vertex is simplified/transformed, and all original tiles remain.
// Build after layer assignment, before spatial bounds/matrix/occlusion caches.
// A future deliberate static edit may call invalidate(mesh) before rendering.
const ATTRIBUTES = [['position', 3], ['normal', 3], ['uv', 2], ['color', 3]];
const equal16 = (a, b) => { for (let i = 0; i < 16; i++) if (a[i] !== b[i]) return false; return true; };
const version = a => (a.data || a).version;
const triangles = g => (g.index?.count ?? g.attributes.position.count) / 3;
const bytes = g => Object.values(g.attributes).reduce((n, a) => n + a.array.byteLength, 0) + (g.index?.array.byteLength || 0);
function solid(T, m) { return m && !Array.isArray(m) && !m.transparent && m.opacity === 1 && !(m.transmission > 0) && m.depthTest !== false && m.depthWrite !== false && m.blending === T.NormalBlending; }
function standardCallbacks(T, o) { return ['onBeforeRender', 'onAfterRender', 'onBeforeShadow', 'onAfterShadow'].every(k => o[k] === T.Object3D.prototype[k]); }
function compatibleGeometry(g) {
  if (!g?.isBufferGeometry || g.isInstancedBufferGeometry || Object.keys(g.morphAttributes || {}).length || Object.keys(g.attributes).length !== ATTRIBUTES.length) return false;
  if (!ATTRIBUTES.every(([name, size]) => {
    const a = g.attributes[name]; return a && !a.isInterleavedBufferAttribute && a.array instanceof Float32Array && a.itemSize === size && !a.normalized && a.count === g.attributes.position.count;
  })) return false;
  const count = g.index?.count ?? g.attributes.position.count;
  return count > 0 && count % 3 === 0 && g.drawRange.start === 0 && g.drawRange.count >= count && (!g.index || g.index.array && !g.index.normalized);
}

function* prepareTown({ THREE: T, scene, meshes, mergeGeometries, markStatic,
  cellSize = 96, minTiles = 4, minDistance = 110, maxPixels = 700, maxAddedBufferBytes = 60 * 1024 * 1024, padding = .01 } = {}) {
  if (!T || !scene || !Array.isArray(meshes) || typeof mergeGeometries !== 'function') throw new Error('THREE, scene, explicit town meshes and mergeGeometries are required');
  const groups = new Map(), records = [], byMesh = new WeakMap(), center = new T.Vector3(), eye = new T.Vector3(), inverseScene = new T.Matrix4();
  const stats = { inputTiles: meshes.length, eligibleTiles: 0, sourceTiles: 0, clusters: 0, potentialSavedDraws: 0,
    addedBufferBytes: 0, addedBufferMiB: 0, sourceTriangles: 0, mergedTriangles: 0, skippedMemory: 0,
    activeClusters: 0, savedDraws: 0, activeTriangles: 0, switches: 0, invalidated: 0, updateMs: 0, mergeMs: 0, maxMergeMs: 0 };
  let enabled = true, disposed = false;
  scene.updateMatrixWorld(true); inverseScene.copy(scene.matrixWorld).invert();
  let prepared = 0;
  for (const mesh of meshes) {
    if (++prepared % 16 === 0) yield null;
    if (mesh.parent !== scene || !mesh.userData.dgyTownTile || !mesh.isMesh || mesh.isInstancedMesh || mesh.isSkinnedMesh || mesh.isBatchedMesh ||
      mesh.children.length || mesh.animations?.length || mesh.userData.dynamic || mesh.isReflector || mesh.userData.rcKind || !mesh.visible ||
      !standardCallbacks(T, mesh) || !solid(T, mesh.material) || !compatibleGeometry(mesh.geometry)) continue;
    const geometry = mesh.geometry; if (!geometry.boundingBox) geometry.computeBoundingBox();
    const bounds = geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld); if (bounds.isEmpty()) continue; bounds.getCenter(center);
    // Same matrix preserves local/world shader coordinates and winding exactly.
    // It also avoids rebaking attributes or introducing float rounding in them.
    const key = [mesh.material.uuid, mesh.layers.mask, mesh.castShadow, mesh.receiveShadow, mesh.renderOrder, mesh.frustumCulled,
      mesh.customDepthMaterial?.uuid, mesh.customDistanceMaterial?.uuid, ...mesh.matrixWorld.elements,
      Math.floor(center.x / cellSize), Math.floor(center.z / cellSize)].join('|');
    if (!groups.has(key)) groups.set(key, []);
    const attrs = ATTRIBUTES.map(([name]) => [name, geometry.attributes[name], version(geometry.attributes[name])]);
    groups.get(key).push({ mesh, geometry, bounds, matrix: mesh.matrixWorld.elements.slice(), material: mesh.material, attrs,
      index: geometry.index, indexVersion: geometry.index?.version, drawStart: geometry.drawRange.start, drawCount: geometry.drawRange.count,
      layers: mesh.layers.mask, castShadow: mesh.castShadow, receiveShadow: mesh.receiveShadow, renderOrder: mesh.renderOrder, frustumCulled: mesh.frustumCulled,
      depth: mesh.customDepthMaterial, distance: mesh.customDistanceMaterial });
    stats.eligibleTiles++;
  }
  const plans = [...groups.values()].filter(list => list.length >= minTiles).map(list => ({ list,
    estimate: list.reduce((n, q) => n + q.geometry.attributes.position.count * 44 + (q.geometry.index?.count ?? q.geometry.attributes.position.count) * 4, 0) }));
  plans.sort((a, b) => (b.list.length - 1) / b.estimate - (a.list.length - 1) / a.estimate);
  for (const { list, estimate } of plans) {
    if (stats.addedBufferBytes + estimate > maxAddedBufferBytes) { stats.skippedMemory++; continue; }
    const mergeStart = performance.now(), geometry = mergeGeometries(list.map(q => q.geometry)), mergeMs = performance.now() - mergeStart;
    stats.mergeMs += mergeMs; stats.maxMergeMs = Math.max(stats.maxMergeMs, mergeMs); if (!geometry) continue;
    const originalTriangles = list.reduce((n, q) => n + triangles(q.geometry), 0), added = bytes(geometry);
    if (triangles(geometry) !== originalTriangles || stats.addedBufferBytes + added > maxAddedBufferBytes) { geometry.dispose(); stats.skippedMemory++; continue; }
    geometry.computeBoundingBox(); geometry.computeBoundingSphere(); geometry.boundingSphere.radius += padding;
    const source = list[0].mesh, far = new T.Mesh(geometry, source.material);
    far.name = 'HLOD·园外镇子·' + (source.userData.dgyTownMaterialKey || source.material.name || source.material.type);
    far.matrixAutoUpdate = false; far.matrix.multiplyMatrices(inverseScene, source.matrixWorld);
    far.castShadow = source.castShadow; far.receiveShadow = source.receiveShadow; far.layers.mask = source.layers.mask;
    far.renderOrder = source.renderOrder; far.frustumCulled = source.frustumCulled;
    far.customDepthMaterial = source.customDepthMaterial; far.customDistanceMaterial = source.customDistanceMaterial;
    // The source tiles already passed smallToL2. Do not reclassify a differently
    // sized aggregate and accidentally change lake/refraction/shadow layers.
    far.userData.ls = 1; far.visible = false; scene.add(far); far.updateMatrixWorld(true); markStatic?.(far, { padding });
    const bounds = new T.Box3(); for (const q of list) bounds.union(q.bounds); bounds.expandByScalar(padding);
    const record = { list, far, geometry, farMatrix: far.matrixWorld.elements.slice(), bounds, sphere: bounds.getBoundingSphere(new T.Sphere()), active: false, valid: true, triangles: originalTriangles };
    records.push(record); for (const q of list) byMesh.set(q.mesh, record);
    stats.addedBufferBytes += added; stats.sourceTriangles += originalTriangles; stats.mergedTriangles += triangles(geometry);
    stats.sourceTiles += list.length; stats.potentialSavedDraws += list.length - 1;
    yield null;
  }
  stats.clusters = records.length; stats.addedBufferMiB = stats.addedBufferBytes / 1048576;
  function attachedVisible(object) {
    let parent = object.parent;
    for (; parent && parent !== scene; parent = parent.parent) if (!parent.visible) return false;
    return parent === scene;
  }
  function valid(r) {
    const far = r.far, source = r.list[0];
    if (far.visible !== r.active || !attachedVisible(far) || far.geometry !== r.geometry || far.material !== source.material ||
      !equal16(far.matrixWorld.elements, r.farMatrix) || far.children.length || !standardCallbacks(T, far) ||
      far.layers.mask !== source.layers || far.castShadow !== source.castShadow || far.receiveShadow !== source.receiveShadow ||
      far.renderOrder !== source.renderOrder || far.frustumCulled !== source.frustumCulled ||
      far.customDepthMaterial !== source.depth || far.customDistanceMaterial !== source.distance) return false;
    for (const q of r.list) {
      const m = q.mesh, g = m.geometry;
      if (!attachedVisible(m) || m.visible !== !r.active || g !== q.geometry || m.material !== q.material || !solid(T, m.material) ||
        m.children.length || !standardCallbacks(T, m) || m.layers.mask !== q.layers || m.castShadow !== q.castShadow || m.receiveShadow !== q.receiveShadow ||
        m.renderOrder !== q.renderOrder || m.frustumCulled !== q.frustumCulled || m.customDepthMaterial !== q.depth || m.customDistanceMaterial !== q.distance ||
        g.drawRange.start !== q.drawStart || g.drawRange.count !== q.drawCount || g.index !== q.index || g.index?.version !== q.indexVersion ||
        !equal16(m.matrixWorld.elements, q.matrix)) return false;
      for (const [name, attribute, savedVersion] of q.attrs) if (g.attributes[name] !== attribute || version(attribute) !== savedVersion) return false;
    }
    return true;
  }
  function activate(r, active, force = false) {
    if (r.active === active && !force) return;
    for (const q of r.list) q.mesh.visible = !active;
    r.far.visible = active; if (r.active !== active) stats.switches++; r.active = active;
  }
  const api = {
    stats,
    get enabled() { return enabled; }, set enabled(v) { enabled = !!v; if (!enabled) for (const r of records) activate(r, false, true); },
    update(camera, { height = 900 } = {}) {
      const start = performance.now(); stats.activeClusters = stats.savedDraws = stats.activeTriangles = 0;
      if (disposed || !enabled) return stats;
      camera.updateMatrixWorld(); eye.setFromMatrixPosition(camera.matrixWorld);
      const focal = height * Math.abs(camera.projectionMatrix.elements[5]) * .5;
      for (const r of records) {
        center.copy(r.sphere.center).applyMatrix4(camera.matrixWorldInverse);
        const depth = -center.z - r.sphere.radius, pixels = camera.isPerspectiveCamera && depth > camera.near ? 2 * r.sphere.radius * focal / depth : Infinity;
        let active = r.valid && height > 0 && r.bounds.distanceToPoint(eye) > minDistance * (r.active ? .85 : 1) && pixels < maxPixels * (r.active ? 1.12 : 1);
        // Near clusters have no aggregate on screen, so skip their member walk.
        // A prospective transition and every active aggregate are certified.
        if (r.valid && (r.far.visible !== r.active || (active || r.active) && !valid(r))) {
          r.valid = false; active = false; stats.invalidated++; activate(r, false, true);
        }
        activate(r, active);
        if (active) { stats.activeClusters++; stats.savedDraws += r.list.length - 1; stats.activeTriangles += r.triangles; }
      }
      stats.updateMs = performance.now() - start; return stats;
    },
    invalidate(mesh) { const selected = mesh ? [byMesh.get(mesh)].filter(Boolean) : records; for (const r of selected) { if (r.valid) stats.invalidated++; r.valid = false; activate(r, false, true); } },
    dispose() { if (disposed) return; disposed = true; enabled = false; for (const r of records) { activate(r, false, true); r.far.removeFromParent(); r.geometry.dispose(); } records.length = 0; stats.activeClusters = stats.savedDraws = stats.activeTriangles = 0; },
  };
  return api;
}

export function createStaticTownHLOD(args) {
  const iterator = prepareTown(args); let step;
  do { step = iterator.next(); } while (!step.done);
  return step.value;
}

export async function prepareStaticTownHLOD(args, { budgetMs = 8, yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)) } = {}) {
  const iterator = prepareTown(args); let step, slice = performance.now();
  do {
    step = iterator.next();
    if (!step.done && performance.now() - slice >= budgetMs) { await yieldFrame(); slice = performance.now(); }
  } while (!step.done);
  return step.value;
}
