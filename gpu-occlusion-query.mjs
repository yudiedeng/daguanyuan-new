// Optional stationary-view WebGL2 occlusion queries. No readPixels, finish,
// fences, waiting loops, or modification of the authored scene's visibility.
// update() runs BEFORE the main render, after scene/camera matrices and LOD.
// Results apply only to the exact view, viewport/MSAA and live occluder cohort
// that produced them. A missing/unavailable/invalid result always retains draw.
const eq16 = (a, b) => { for (let i = 0; i < 16; i++) if (a[i] !== b[i]) return false; return true; };
const values = b => [b.min.x, b.min.y, b.min.z, b.max.x, b.max.y, b.max.z];
const sameBox = (v, b) => v && v[0] === b.min.x && v[1] === b.min.y && v[2] === b.min.z && v[3] === b.max.x && v[4] === b.max.y && v[5] === b.max.z;
const finiteBox = b => b?.isBox3 && !b.isEmpty() && Number.isFinite(b.min.x) && Number.isFinite(b.min.y) &&
  Number.isFinite(b.min.z) && Number.isFinite(b.max.x) && Number.isFinite(b.max.y) && Number.isFinite(b.max.z);
const distanceSq = (b, p) => {
  const x = Math.max(b.min.x - p.x, 0, p.x - b.max.x), y = Math.max(b.min.y - p.y, 0, p.y - b.max.y), z = Math.max(b.min.z - p.z, 0, p.z - b.max.z);
  return x * x + y * y + z * z;
};
const sameGroups = (groups, saved) => groups.length * 3 === saved.length && groups.every((g, i) =>
  g.start === saved[i * 3] && g.count === saved[i * 3 + 1] && g.materialIndex === saved[i * 3 + 2]);
const materials = o => Array.isArray(o.material) ? o.material : [o.material];
function shown(object, camera) {
  if (!object.layers.test(camera.layers)) return false;
  for (let p = object; p; p = p.parent) if (!p.visible) return false;
  return true;
}
function opaque(T, m) {
  if (!m || m.visible === false || m.transparent || m.opacity !== 1 || m.alphaTest > 0 || m.alphaMap || m.alphaHash ||
    m.alphaToCoverage || m.wireframe || m.displacementMap || m.transmission > 0 || m.polygonOffset || m.stencilWrite ||
    m.depthWrite === false || m.depthTest === false || m.colorWrite === false || m.depthFunc !== T.LessEqualDepth ||
    m.blending !== T.NormalBlending || m.clippingPlanes?.length || m.isShaderMaterial || m.isRawShaderMaterial) return false;
  if (!(m.isMeshBasicMaterial || m.isMeshStandardMaterial || m.isMeshLambertMaterial || m.isMeshPhongMaterial || m.isMeshNormalMaterial || m.isMeshToonMaterial)) return false;
  return !!m.userData?.dgyOcclusionStaticSurface ||
    (m.onBeforeCompile === T.Material.prototype.onBeforeCompile && !m.userData?.shadowDynamic);
}
function depthSafe(T, object) {
  return object.isMesh && !object.isReflector && !object.userData.rcKind && object.onBeforeRender === T.Object3D.prototype.onBeforeRender &&
    materials(object).every(m => m && m.depthTest !== false && m.depthFunc === T.LessEqualDepth && !m.polygonOffset && !m.stencilWrite &&
      !m.clippingPlanes?.length && !m.isShaderMaterial && !m.isRawShaderMaterial);
}
export function gpuOcclusionSupport(renderer) {
  const gl = renderer?.getContext?.();
  if (!gl || renderer.capabilities?.isWebGL2 !== true) return { supported: false, reason: 'WebGL2 is required' };
  if (renderer.capabilities?.reverseDepthBuffer || renderer.capabilities?.logarithmicDepthBuffer) return { supported: false, reason: 'This prototype requires ordinary depth' };
  if (typeof gl.ANY_SAMPLES_PASSED_CONSERVATIVE !== 'number' ||
    ['createQuery', 'deleteQuery', 'beginQuery', 'endQuery', 'getQuery', 'getQueryParameter'].some(k => typeof gl[k] !== 'function')) {
    return { supported: false, reason: 'Native conservative occlusion queries are unavailable' };
  }
  return { supported: true, reason: '' };
}

export function createGpuOcclusionQueries({ THREE: T, renderer, camera, registry, getMainTarget,
  enabled: initiallyEnabled = false, queriesPerFrame = 16, maxPendingQueries = 32, maxCandidates = 1024,
  maxMembersPerCandidate = 24, settleFrames = 2, maxExternalBoxes = 128, proxyPadding = .005,
  maxOccluderDistance = 120 } = {}) {
  if (!T || !renderer || !camera || !registry?.bounds || typeof registry.isCurrent !== 'function' || typeof getMainTarget !== 'function') {
    throw new Error('THREE, renderer, main camera, certified registry and getMainTarget are required');
  }
  const support = gpuOcclusionSupport(renderer), gl = renderer.getContext(), queryType = gl?.ANY_SAMPLES_PASSED_CONSERVATIVE;
  queriesPerFrame = Math.max(0, queriesPerFrame | 0); maxPendingQueries = Math.max(0, maxPendingQueries | 0); settleFrames = Math.max(1, settleFrames | 0);
  const stats = { ...support, enabled: !!initiallyEnabled, generation: 0, stableFrames: 0, sourceMeshes: 0, targetCandidates: 0,
    depthPasses: 0, queriesIssued: 0, queriesResolved: 0, pending: 0, pooledQueries: 0, hiddenResults: 0,
    tested: 0, culled: 0, updateMs: 0, skippedNear: 0, errors: 0,
    scopedSourceMeshes: 0, sourceChecks: 0, registryChecks: 0, allTargetCandidates: 0, idle: false };
  const sourceScene = new T.Scene(), queryScene = new T.Scene(), view = camera.clone();
  sourceScene.matrixWorldAutoUpdate = queryScene.matrixWorldAutoUpdate = false;
  view.parent = null; view.matrixAutoUpdate = view.matrixWorldAutoUpdate = false;
  const depthMaterials = new Map(), boxGeometry = new T.BoxGeometry(1, 1, 1);
  const proxyMaterial = new T.MeshBasicMaterial({ colorWrite: false, depthWrite: false, depthTest: true, side: T.DoubleSide, toneMapped: false, fog: false,
    polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2 });
  const sources = [], targets = [], pool = [], external = new Map(), results = new Map();
  const world = new Float64Array(16), projection = new Float64Array(16), frustum = new T.Frustum(), matrix = new T.Matrix4();
  const eye = new T.Vector3(), corner = new T.Vector3(), centre = new T.Vector3(), extent = new T.Vector3();
  let enabled = !!initiallyEnabled, disposed = false, ready = false, generation = 0, stable = 0, mask = 0, descriptorKey = '';
  let target = null, descriptor = null, nextCandidate = 0, depthReady = false, activeQuery = null;
  let memberCache = new WeakMap(), currentCache = new WeakMap(), materialCache = new WeakMap(), scopedSources = [], viewTargets = [], selectionDirty = true;
  function depthMaterial(side) {
    if (!depthMaterials.has(side)) depthMaterials.set(side, new T.MeshBasicMaterial({ side, colorWrite: false, depthWrite: true, toneMapped: false, fog: false,
      polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 2 }));
    return depthMaterials.get(side);
  }
  for (const mesh of registry.occluders) {
    if (!mesh.isMesh || mesh.isSkinnedMesh || mesh.isInstancedMesh || mesh.isBatchedMesh || mesh.children.length ||
      mesh.onBeforeRender !== T.Object3D.prototype.onBeforeRender || !materials(mesh).every(m => opaque(T, m))) continue;
    const copy = new T.Mesh(mesh.geometry, materials(mesh).map(m => depthMaterial(m.side)));
    if (!Array.isArray(mesh.material)) copy.material = copy.material[0];
    copy.matrixAutoUpdate = copy.matrixWorldAutoUpdate = false; copy.matrix.copy(mesh.matrixWorld); copy.matrixWorld.copy(mesh.matrixWorld);
    copy.layers.mask = mesh.layers.mask; copy.visible = false; sourceScene.add(copy);
    sources.push({ mesh, copy, geometry: mesh.geometry, drawStart: mesh.geometry.drawRange.start,
      drawCount: mesh.geometry.drawRange.count, groups: mesh.geometry.groups.flatMap(g => [g.start, g.count, g.materialIndex]),
      active: false, sides: materials(mesh).map(m => m.side) });
  }
  for (const [object, box] of registry.bounds) {
    if (!finiteBox(box)) continue;
    const members = []; let safe = true;
    object.traverse(node => {
      if (node.isLight || node.isLOD || node.isCamera || node.isSprite || node.isPoints || node.isLine) safe = false;
      if (node.isMesh) { if (!depthSafe(T, node) || !registry.bounds.has(node)) safe = false; members.push(node); }
    });
    if (!safe || !members.length || members.length > maxMembersPerCandidate) continue;
    const triangles = members.reduce((sum, m) => sum + (m.geometry.index?.count || m.geometry.attributes.position?.count || 0) / 3 * Math.max(1, m.count || 1), 0);
    targets.push({ key: object, object, members, box, priority: members.length * 100000 + triangles });
  }
  // Keep every certified definition. The finite query budget is chosen from
  // the CURRENT frustum, never from a global list that could omit this room.
  stats.allTargetCandidates = targets.length;
  function readDescriptor() {
    const rt = getMainTarget();
    if (!rt?.isWebGLRenderTarget || rt.isWebGLCubeRenderTarget || rt.depthBuffer === false || !(rt.width > 0 && rt.height > 0)) return null;
    const viewport = rt.viewport, scissor = rt.scissor;
    if (!viewport || !scissor) return null;
    const samples = Math.min(rt.samples || 0, renderer.capabilities.maxSamples ?? rt.samples ?? 0);
    const d = { width: rt.width, height: rt.height, samples, viewport: viewport.clone(), scissor: scissor.clone(), scissorTest: !!rt.scissorTest,
      depthType: rt.depthTexture?.type ?? T.UnsignedIntType, depthFormat: rt.depthTexture?.format ?? T.DepthFormat };
    if (d.depthFormat !== T.DepthFormat) return null;
    d.key = [d.width, d.height, samples, ...d.viewport, ...d.scissor, d.scissorTest, d.depthType, d.depthFormat].join(','); return d;
  }
  function deleteQueries() {
    for (const slot of pool) { if (slot.query) gl.deleteQuery(slot.query); slot.proxy.removeFromParent(); }
    pool.length = 0; stats.pending = stats.pooledQueries = 0;
  }
  function invalidate() {
    ready = depthReady = false; generation++; stats.generation = generation;
    results.clear(); deleteQueries(); nextCandidate = 0; stats.hiddenResults = 0;
  }
  function current(viewCamera) {
    return enabled && !disposed && support.supported && ready && viewCamera === camera && camera.layers.mask === mask &&
      eq16(camera.matrixWorld.elements, world) && eq16(camera.projectionMatrix.elements, projection);
  }
  function certified(object) {
    if (!currentCache.has(object)) { stats.registryChecks++; currentCache.set(object, registry.isCurrent(object)); }
    return currentCache.get(object);
  }
  function opaqueNow(material) {
    if (!materialCache.has(material)) materialCache.set(material, opaque(T, material));
    return materialCache.get(material);
  }
  function selectView() {
    // Bounds only limit which real surfaces may contribute depth. A moved or
    // otherwise invalid surface is still rejected by certified() each frame;
    // omitting any surface simply leaves more objects visible.
    sourceScene.clear(); scopedSources = [];
    const limitSq = Math.max(0, maxOccluderDistance) ** 2;
    for (const r of sources) {
      r.copy.visible = r.active = false;
      const box = registry.bounds.get(r.mesh);
      if (!finiteBox(box) || distanceSq(box, eye) > limitSq || !frustum.intersectsBox(box)) continue;
      scopedSources.push(r); sourceScene.add(r.copy);
    }
    stats.scopedSourceMeshes = scopedSources.length; selectionDirty = false;
  }
  function selectTargets() {
    viewTargets = [];
    for (const job of targets) {
      if (!registry.bounds.has(job.object) || !finiteBox(job.box) || !frustum.intersectsBox(job.box) || !shown(job.object, camera)) continue;
      // Prefer costly, nearby visible groups. Full bounds/geometry/material
      // certificates are checked lazily before issuing each query.
      job.viewPriority = job.priority / (1 + Math.sqrt(distanceSq(job.box, eye)) / 120);
      viewTargets.push(job);
    }
    viewTargets.sort((a, b) => b.viewPriority - a.viewPriority);
    viewTargets.length = Math.min(viewTargets.length, Math.max(0, maxCandidates | 0));
    stats.targetCandidates = viewTargets.length; nextCandidate = 0;
  }
  function sourceState() {
    let changed = false, count = 0;
    for (const r of scopedSources) {
      const m = r.mesh, g = m.geometry, ms = materials(m);
      stats.sourceChecks++;
      const valid = shown(m, camera) && certified(m) && g === r.geometry && g.drawRange.start === r.drawStart &&
        g.drawRange.count === r.drawCount && (!Array.isArray(m.material) || sameGroups(g.groups, r.groups)) && ms.every(opaqueNow);
      if (valid !== r.active) changed = true;
      r.copy.visible = r.active = valid;
      if (!valid) continue;
      const sidesChanged = ms.length !== r.sides.length || ms.some((mat, i) => mat.side !== r.sides[i]);
      if (sidesChanged) {
        changed = true; r.sides = ms.map(mat => mat.side);
        r.copy.material = Array.isArray(m.material) ? ms.map(mat => depthMaterial(mat.side)) : depthMaterial(ms[0].side);
      }
      r.copy.layers.mask = m.layers.mask; count++;
    }
    stats.sourceMeshes = count; return changed;
  }
  function safeMember(m) {
    if (!memberCache.has(m)) memberCache.set(m, certified(m) && depthSafe(T, m));
    return memberCache.get(m);
  }
  function validCandidate(job, fromMainHook = false) {
    return finiteBox(job.box) && (!job.object || (fromMainHook ? registry.isCurrent(job.object) : certified(job.object)) && shown(job.object, camera) && job.members.every(safeMember));
  }
  function proxyBox(box) {
    const b = box.clone(); box.getSize(extent); b.expandByScalar(Math.max(proxyPadding, extent.length() * 1e-5));
    if (b.containsPoint(eye)) { stats.skippedNear++; return null; }
    // A clipped, uncapped cube can lose its nearest face. Until a certified
    // near-cap path is added, retain those candidates, including wide water
    // reader chunks spanning the camera. Raw GPU clipping alone is insufficient.
    for (let i = 0; i < 8; i++) {
      corner.set(i & 1 ? b.max.x : b.min.x, i & 2 ? b.max.y : b.min.y, i & 4 ? b.max.z : b.min.z).applyMatrix4(camera.matrixWorldInverse);
      if (corner.z >= -camera.near - 1e-4) { stats.skippedNear++; return null; }
    }
    return frustum.intersectsBox(b) ? b : null;
  }
  function slot() {
    let free = pool.find(s => !s.pending); if (free || pool.length >= maxPendingQueries) return free;
    const query = gl.createQuery(); if (!query) return null;
    const proxy = new T.Mesh(boxGeometry, proxyMaterial); proxy.name = 'gpu-occlusion-query'; proxy.frustumCulled = false; proxy.visible = false; proxy.layers.enableAll();
    free = { query, proxy, pending: false, job: null, generation: 0, submitted: false };
    proxy.onBeforeRender = () => { activeQuery = free; gl.beginQuery(queryType, query); free.submitted = true; };
    proxy.onAfterRender = () => { gl.endQuery(queryType); activeQuery = null; };
    queryScene.add(proxy); pool.push(free); stats.pooledQueries = pool.length; return free;
  }
  function poll() {
    for (const s of pool) if (s.pending && gl.getQueryParameter(s.query, gl.QUERY_RESULT_AVAILABLE)) {
      // QUERY_RESULT is never requested until the driver says it is available.
      const samples = gl.getQueryParameter(s.query, gl.QUERY_RESULT);
      if (s.generation === generation && validCandidate(s.job) && sameBox(s.job.values, s.job.box)) {
        const hidden = samples === false || samples === 0; results.set(s.job.key, { ...s.job, hidden, generation });
      }
      s.pending = false; s.job = null; stats.queriesResolved++;
    }
    stats.pending = pool.filter(s => s.pending).length;
    stats.hiddenResults = [...results.values()].filter(r => r.hidden).length;
  }
  function ensureTarget(d) {
    if (target && descriptor?.key === d.key) return;
    target?.dispose();
    target = new T.WebGLRenderTarget(d.width, d.height, { samples: d.samples, minFilter: T.NearestFilter, magFilter: T.NearestFilter,
      depthBuffer: true, stencilBuffer: false, depthTexture: new T.DepthTexture(d.width, d.height, d.depthType) });
    // Keep explicit multisample depth storage across stationary batches. An
    // implicit multisampled-render-to-texture attachment may discard samples
    // when unbound; reusing its resolved depth could close subpixel openings.
    if (renderer.properties?.get) renderer.properties.get(target).__useRenderToTexture = false;
    target.texture.generateMipmaps = false; target.viewport.copy(d.viewport); target.scissor.copy(d.scissor); target.scissorTest = d.scissorTest;
    stats.width = d.width; stats.height = d.height; stats.samples = d.samples;
    descriptor = d; depthReady = false;
  }
  function renderBatch(batch) {
    const prior = renderer.getRenderTarget(), face = renderer.getActiveCubeFace?.() || 0, level = renderer.getActiveMipmapLevel?.() || 0;
    const autoClear = renderer.autoClear, shadows = renderer.shadowMap.enabled;
    try {
      renderer.autoClear = false; renderer.shadowMap.enabled = false; renderer.setRenderTarget(target);
      view.copy(camera, false); view.parent = null; view.matrixAutoUpdate = view.matrixWorldAutoUpdate = false;
      view.matrixWorld.copy(camera.matrixWorld); view.matrixWorldInverse.copy(camera.matrixWorldInverse);
      if (!depthReady) { renderer.clear(false, true, false); renderer.render(sourceScene, view); depthReady = true; stats.depthPasses++; }
      for (const s of batch) s.proxy.visible = true;
      renderer.render(queryScene, view);
      for (const s of batch) if (s.submitted) { s.pending = true; stats.queriesIssued++; }
    } finally {
      if (activeQuery) { gl.endQuery(queryType); activeQuery = null; }
      for (const s of batch) s.proxy.visible = false;
      renderer.autoClear = autoClear; renderer.shadowMap.enabled = shadows; renderer.setRenderTarget(prior, face, level);
    }
  }
  const api = {
    stats, support,
    get enabled() { return enabled; }, set enabled(value) { enabled = !!value; stats.enabled = enabled; stable = 0; invalidate(); },
    update(viewCamera = camera) {
      const started = performance.now(); stats.tested = stats.culled = stats.sourceChecks = stats.registryChecks = stats.updateMs = 0;
      if (!enabled || disposed || !support.supported || viewCamera !== camera) return stats;
      try {
        if (gl.isContextLost?.() || renderer.xr?.isPresenting || renderer.clippingPlanes?.length || gl.getQuery(queryType, gl.CURRENT_QUERY)) {
          invalidate(); stable = 0; return stats;
        }
        const d = readDescriptor(); if (!d) { invalidate(); stable = 0; stats.reason = 'A matching ordinary-depth main render target is required'; return stats; }
        const same = eq16(camera.matrixWorld.elements, world) && eq16(camera.projectionMatrix.elements, projection) && mask === camera.layers.mask && descriptorKey === d.key;
        if (!same) {
          invalidate(); selectionDirty = true; stable = 1; world.set(camera.matrixWorld.elements); projection.set(camera.projectionMatrix.elements); mask = camera.layers.mask; descriptorKey = d.key;
        } else stable++;
        stats.stableFrames = stable; if (stable < settleFrames) return stats;
        // O(1) generation change: no full-world member walk just to clear a
        // cache. Source auditing, polling and new queries share certificates.
        memberCache = new WeakMap(); currentCache = new WeakMap(); materialCache = new WeakMap();
        eye.setFromMatrixPosition(camera.matrixWorld);
        frustum.setFromProjectionMatrix(matrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
        const newView = selectionDirty; if (newView) selectView();
        const changed = sourceState(); if (changed) invalidate();
        stats.idle = stats.sourceMeshes === 0;
        if (stats.idle) { ready = false; stats.targetCandidates = 0; return stats; }
        if (newView || changed) selectTargets();
        ready = true; ensureTarget(d);
        poll(); const batch = [];
        while (batch.length < queriesPerFrame) {
          const free = slot(); if (!free) break;
          const job = external.size ? (() => { const key = external.keys().next().value, item = external.get(key); external.delete(key); return item; })() : viewTargets[nextCandidate++];
          if (!job) break;
          if (!validCandidate(job)) continue;
          const bounds = proxyBox(job.box); if (!bounds) continue;
          const duplicate = results.has(job.key) || pool.some(s => s.pending && s.job?.key === job.key); if (duplicate) continue;
          free.job = { ...job, values: values(job.box) }; free.generation = generation; free.submitted = false;
          bounds.getCenter(centre); bounds.getSize(extent); free.proxy.position.copy(centre); free.proxy.scale.copy(extent); free.proxy.updateMatrixWorld(true);
          free.proxy.userData.gpuOcclusionKey = job.key; batch.push(free);
          // Reserve slots before issuing their GPU work so a batch cannot reuse one.
          free.pending = true;
        }
        if (batch.length) renderBatch(batch);
        stats.pending = pool.filter(s => s.pending).length; stats.reason = '';
      } catch (error) {
        stats.errors++; stats.reason = String(error?.message || error); enabled = false; stats.enabled = false; invalidate();
      } finally { stats.updateMs = performance.now() - started; }
      return stats;
    },
    isObjectOccluded(object, viewCamera) {
      if (!enabled || disposed || viewCamera !== camera) return false;
      const result = results.get(object);
      if (!result?.hidden || result.generation !== generation || !current(viewCamera)) return false;
      const box = registry.bounds.get(object);
      if (!finiteBox(box) || !sameBox(result.values, box) || !validCandidate(result, true)) return false;
      stats.tested++; stats.culled++; return true;
    },
    enqueueBox(box, key = box) {
      if (!finiteBox(box) || !key || external.size >= maxExternalBoxes) return false;
      if (!results.has(key) && !external.has(key)) external.set(key, { key, box, object: null, members: [] }); return true;
    },
    isOccluded(box, viewCamera, key = box) {
      if (!current(viewCamera) || !finiteBox(box)) return false;
      const result = results.get(key);
      if (result && sameBox(result.values, box)) return result.generation === generation && result.hidden;
      if (result) results.delete(key); api.enqueueBox(box, key); return false;
    },
    invalidate() { stable = 0; selectionDirty = true; invalidate(); },
    dispose() {
      if (disposed) return; disposed = true; enabled = false; stats.enabled = false; invalidate(); external.clear();
      target?.dispose(); target = null; boxGeometry.dispose(); proxyMaterial.dispose(); for (const m of depthMaterials.values()) m.dispose();
      sourceScene.clear(); queryScene.clear(); sources.length = targets.length = 0;
    },
  };
  return api;
}
