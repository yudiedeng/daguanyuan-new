import { createGpuOcclusionQueries, gpuOcclusionSupport } from './gpu-occlusion-query.mjs';
import { prepareMovingOcclusionFaces, buildMovingOcclusionCertificate, buildMovingOcclusionTarget,
  isMovingCertificateCurrent, disposeMovingOcclusionCertificate } from './moving-occlusion-certificate.mjs';

const finiteBox = b => b?.isBox3 && !b.isEmpty() && [...b.min, ...b.max].every(Number.isFinite);
const sameBox = (a, b) => a && a[0] === b.min.x && a[1] === b.min.y && a[2] === b.min.z && a[3] === b.max.x && a[4] === b.max.y && a[5] === b.max.z;
const boxValues = b => [...b.min, ...b.max];
const materials = m => Array.isArray(m.material) ? m.material : [m.material];
const equal16 = (a, b) => a.every((v, i) => v === b[i]);
function shown(o, mask) {
  if (!(o.layers.mask & mask)) return false;
  for (let p = o; p; p = p.parent) if (!p.visible) return false;
  return true;
}
function safeDepth(T, m) {
  return m.isMesh && !m.isReflector && !m.userData.rcKind && m.onBeforeRender === T.Object3D.prototype.onBeforeRender &&
    materials(m).every(a => a && a.depthTest !== false && a.depthFunc === T.LessEqualDepth && !a.polygonOffset && !a.stencilWrite &&
      !a.clippingPlanes?.length && !a.isShaderMaterial && !a.isRawShaderMaterial);
}

/** Moving certificates and the existing stationary fallback share a HARD
 * query budget. By default fallback reserves 8 issues/16 pending, moving gets
 * the remaining 48 pending and can borrow unused per-frame issue slots. */
export async function prepareMovingGpuOcclusionQueries({ THREE: T, renderer, camera, registry, getMainTarget,
  enabled: initiallyEnabled = true, queriesPerFrame = 32, maxPendingQueries = 64, maxCells = 3,
  maxCandidates = 1024, maxMembersPerCandidate = 24, maxExternalBoxes = 128,
  maxQueryAttemptsPerFrame = 128, maxQueryWorkMs = 2,
  halfExtent = .6, cellTravel = .27, sectorAngle = 25, certificateOptions = {}, faceOptions = {}, facePool,
  stationaryQueriesPerFrame = 8, stationaryMaxPending = 16 } = {}, scheduling = {}) {
  if (!T || !renderer || !camera || !registry?.bounds || typeof registry.isCurrent !== 'function') throw new Error('THREE, renderer, main camera and registry required');
  queriesPerFrame = Math.max(0, queriesPerFrame | 0); maxPendingQueries = Math.max(0, maxPendingQueries | 0); maxCells = Math.max(1, maxCells | 0);
  const oldIssueLimit = Math.min(queriesPerFrame, Math.max(0, stationaryQueriesPerFrame | 0));
  const oldPendingLimit = Math.min(maxPendingQueries, Math.max(0, stationaryMaxPending | 0)), movingPendingLimit = maxPendingQueries - oldPendingLimit;
  const support = gpuOcclusionSupport(renderer), gl = renderer.getContext(), type = gl?.ANY_SAMPLES_PASSED_CONSERVATIVE;
  let registryCache = new WeakMap(), memberCache = new WeakMap(), sourceCache = new WeakMap(), inUpdate = false;
  let enabled = !!initiallyEnabled, disposed = false, movingFailed = false, frame = 0, frameReady = false, serial = 0, activeQuery = null;
  const moving = { supported: support.supported, enabled, cells: 0, activeCells: 0, certificatesBuilt: 0, emptyCertificates: 0,
    queriesIssued: 0, queriesResolved: 0, pending: 0, pooledQueries: 0, depthPasses: 0, hiddenResults: 0,
    tested: 0, culled: 0, sourceMeshes: 0, sourceChecks: 0, registryChecks: 0, targetCandidates: 0, allTargetCandidates: 0,
    updateMs: 0, buildMs: 0, queryAttempts: 0, coverageRejected: 0, queryBudgetExhausted: false, errors: 0, reason: '', idle: true, preparation: null, lastCertificate: null };
  const cachedRegistry = { ...registry, isCurrent(object) {
    if (!inUpdate) return registry.isCurrent(object);
    if (!registryCache.has(object)) { moving.registryChecks++; registryCache.set(object, registry.isCurrent(object)); }
    return registryCache.get(object);
  } };
  const prepared = facePool || await prepareMovingOcclusionFaces({ THREE: T, registry: cachedRegistry, ...faceOptions }, scheduling);
  moving.preparation = prepared.stats;
  const stationary = createGpuOcclusionQueries({ THREE: T, renderer, camera, registry: cachedRegistry, getMainTarget,
    enabled, queriesPerFrame: oldIssueLimit, maxPendingQueries: oldPendingLimit, maxCandidates, maxMembersPerCandidate, maxExternalBoxes });
  const stats = { ...stationary.stats, moving, stationary: stationary.stats };
  const cells = [], slots = [], external = new Map(), targets = [];
  const eye = new T.Vector3(), forward = new T.Vector3(), lastEye = new T.Vector3(), lastForward = new T.Vector3();
  const matrix = new T.Matrix4(), frustum = new T.Frustum(); let lastAttempt = -Infinity, haveAttempt = false, frameMask = camera.layers.mask;
  const frameProjection = new Float64Array(16), frameWorld = new Float64Array(16);
  const vertexShader = 'void main(){gl_Position=vec4(position,1.0);}';
  const fragmentShader = 'void main(){gl_FragColor=vec4(0.0);}';
  const sourceMaterial = new T.ShaderMaterial({ vertexShader, fragmentShader, depthWrite: true, depthTest: true,
    depthFunc: T.LessEqualDepth, colorWrite: false, side: T.DoubleSide, blending: T.NoBlending, toneMapped: false, fog: false });
  const targetMaterial = sourceMaterial.clone(); targetMaterial.depthWrite = false;
  let yieldStart = performance.now();
  for (const [object, box] of registry.bounds) {
    if (!finiteBox(box)) continue;
    const members = [], stack = [object]; let safe = true;
    while (stack.length && safe) {
      const node = stack.pop();
      if (node.isLight || node.isLOD || node.isCamera || node.isSprite || node.isPoints || node.isLine) { safe = false; break; }
      if (node.isMesh) {
        if (!safeDepth(T, node) || !registry.bounds.has(node) || members.length >= maxMembersPerCandidate) { safe = false; break; }
        members.push(node);
      }
      for (const child of node.children) stack.push(child);
    }
    if (safe && members.length) {
      const triangles = members.reduce((n, m) => n + (m.geometry.index?.count ?? m.geometry.attributes.position?.count ?? 0) / 3 * Math.max(1, m.count || 1), 0);
      targets.push({ key: object, object, members, box, priority: members.length * 100000 + triangles });
    }
    if (performance.now() - yieldStart >= (scheduling.budgetMs ?? 8)) {
      await (scheduling.yieldFrame || (() => new Promise(resolve => setTimeout(resolve, 0))))(); yieldStart = performance.now();
    }
  }
  moving.allTargetCandidates = targets.length;
  function validMember(m, fresh) {
    if (fresh) return registry.isCurrent(m) && safeDepth(T, m);
    if (!memberCache.has(m)) memberCache.set(m, cachedRegistry.isCurrent(m) && safeDepth(T, m));
    return memberCache.get(m);
  }
  function validJob(job, fresh = false) {
    return finiteBox(job.box) && (!job.object || (fresh ? registry.isCurrent(job.object) : cachedRegistry.isCurrent(job.object)) &&
      shown(job.object, frameMask) && job.members.every(m => validMember(m, fresh)));
  }
  function syncStats() {
    moving.cells = cells.length; moving.activeCells = cells.filter(c => c.validFrame === frame).length;
    moving.pending = slots.filter(s => s.pending).length; moving.pooledQueries = slots.length;
    moving.hiddenResults = cells.reduce((n, c) => n + [...c.results.values()].filter(r => r.hidden).length, 0);
    moving.idle = !moving.activeCells;
    const totalMs = stats.updateMs;
    Object.assign(stats, stationary.stats, { enabled, moving, stationary: stationary.stats,
      queriesIssued: stationary.stats.queriesIssued + moving.queriesIssued,
      queriesResolved: stationary.stats.queriesResolved + moving.queriesResolved,
      pending: stationary.stats.pending + moving.pending, pooledQueries: stationary.stats.pooledQueries + moving.pooledQueries,
      depthPasses: stationary.stats.depthPasses + moving.depthPasses, hiddenResults: stationary.stats.hiddenResults + moving.hiddenResults,
      tested: stationary.stats.tested + moving.tested, culled: stationary.stats.culled + moving.culled,
      sourceMeshes: stationary.stats.sourceMeshes + moving.sourceMeshes, errors: stationary.stats.errors + moving.errors,
      idle: stationary.stats.idle && moving.idle, updateMs: totalMs });
  }
  function deleteSlot(slot) {
    if (slot.query) gl.deleteQuery(slot.query); slot.proxy.removeFromParent(); slot.proxy.geometry.dispose();
    if (slot.cell && slot.job) slot.cell.pending.delete(slot.job.key);
    const i = slots.indexOf(slot); if (i >= 0) slots.splice(i, 1);
  }
  function retire(cell) {
    for (const s of [...slots]) if (s.cell === cell) deleteSlot(s);
    cell.target?.dispose(); disposeMovingOcclusionCertificate(cell.certificate); cell.depthScene.clear(); cell.queryScene.clear();
    cell.results.clear(); cell.pending.clear(); cell.rejected.clear(); cell.jobs.length = 0;
    const i = cells.indexOf(cell); if (i >= 0) cells.splice(i, 1);
  }
  function clearMoving() {
    for (const c of [...cells]) retire(c); for (const s of [...slots]) deleteSlot(s);
    haveAttempt = false; frameReady = false; moving.sourceMeshes = 0;
  }
  function currentMain(viewCamera) {
    return enabled && !disposed && viewCamera === camera && frameReady && camera.layers.mask === frameMask &&
      equal16(camera.projectionMatrix.elements, frameProjection) && equal16(camera.matrixWorld.elements, frameWorld);
  }
  function eyeInside(cell) {
    const e = camera.matrixWorld.elements, b = cell.certificate.cell;
    return [e[12], e[13], e[14]].every(Number.isFinite) && e[12] >= b.min.x && e[12] <= b.max.x && e[13] >= b.min.y && e[13] <= b.max.y && e[14] >= b.min.z && e[14] <= b.max.z;
  }
  function selectJobs(cell) {
    const reference = cell.certificate.referenceCamera, referenceFrustum = new T.Frustum().setFromProjectionMatrix(new T.Matrix4().multiplyMatrices(reference.projectionMatrix, reference.matrixWorldInverse));
    const ranked = [];
    for (const job of targets) {
      if (!registry.bounds.has(job.object) || !shown(job.object, frameMask) || !frustum.intersectsBox(job.box) || !referenceFrustum.intersectsBox(job.box) || cell.results.has(job.key) || cell.pending.has(job.key) || cell.rejected.has(job.key)) continue;
      ranked.push({ job, rank: job.priority / (1 + job.box.distanceToPoint(eye) / 120) });
    }
    ranked.sort((a, b) => b.rank - a.rank); cell.jobs = ranked.slice(0, maxCandidates).map(q => q.job); cell.cursor = 0; cell.selectedAt = frame;
    moving.targetCandidates = cell.jobs.length;
  }
  function createCell() {
    lastAttempt = frame; haveAttempt = true; lastEye.copy(eye); lastForward.copy(forward);
    const certificate = buildMovingOcclusionCertificate({ THREE: T, faces: prepared.faces, camera, halfExtent, maxBuildMs: 3, ...certificateOptions });
    if (!certificate) return;
    moving.buildMs += certificate.stats.buildMs; moving.lastCertificate = certificate.stats;
    if (!certificate.sources.length) { moving.emptyCertificates++; disposeMovingOcclusionCertificate(certificate); return; }
    const depthScene = new T.Scene(), queryScene = new T.Scene(), mesh = new T.Mesh(certificate.geometry, sourceMaterial);
    mesh.frustumCulled = false; mesh.layers.enableAll(); mesh.matrixAutoUpdate = false; depthScene.add(mesh);
    // No depth exists outside the union's enclosing rectangle. A target whose
    // whole query rectangle extends beyond it cannot be fully hidden by this
    // certificate; retain it without spending a native GPU query.
    const coverage = [Infinity, Infinity, -Infinity, -Infinity];
    for (const patch of certificate.patches) for (const point of patch.polygon) {
      coverage[0] = Math.min(coverage[0], point[0]); coverage[1] = Math.min(coverage[1], point[1]);
      coverage[2] = Math.max(coverage[2], point[0]); coverage[3] = Math.max(coverage[3], point[1]);
    }
    const cell = { id: ++serial, certificate, coverage, depthScene, queryScene, target: null, depthReady: false,
      results: new Map(), pending: new Map(), rejected: new Map(), jobs: [], cursor: 0, selectedAt: frame, validFrame: frame };
    cells.push(cell); moving.certificatesBuilt++; selectJobs(cell);
    while (cells.length > maxCells) retire(cells[0]);
  }
  function getSlot() {
    let slot = slots.find(s => !s.pending); if (slot || slots.length >= movingPendingLimit) return slot;
    const query = gl.createQuery(); if (!query) return null;
    const proxy = new T.Mesh(new T.BufferGeometry(), targetMaterial); proxy.frustumCulled = false; proxy.visible = false; proxy.layers.enableAll(); proxy.matrixAutoUpdate = false;
    slot = { query, proxy, cell: null, job: null, pending: false, submitted: false };
    proxy.onBeforeRender = () => { activeQuery = slot; gl.beginQuery(type, query); slot.submitted = true; };
    proxy.onAfterRender = () => { gl.endQuery(type); activeQuery = null; };
    slots.push(slot); return slot;
  }
  function poll() {
    for (const slot of slots) if (slot.pending && gl.getQueryParameter(slot.query, gl.QUERY_RESULT_AVAILABLE)) {
      const result = gl.getQueryParameter(slot.query, gl.QUERY_RESULT), cell = slot.cell, job = slot.job;
      if (cell.validFrame === frame && sameBox(job.values, job.box) && validJob(job)) cell.results.set(job.key, { ...job, hidden: result === false || result === 0 });
      cell.pending.delete(job.key); slot.pending = false; slot.job = null; moving.queriesResolved++;
    }
  }
  function ensureTarget(cell) {
    if (cell.target) return;
    const { width, height } = cell.certificate;
    cell.target = new T.WebGLRenderTarget(width, height, { samples: 0, minFilter: T.NearestFilter, magFilter: T.NearestFilter,
      depthBuffer: true, stencilBuffer: false, depthTexture: new T.DepthTexture(width, height, T.UnsignedIntType) });
    cell.target.texture.generateMipmaps = false; cell.target.viewport.set(0, 0, width, height); cell.target.scissor.set(0, 0, width, height); cell.target.scissorTest = false;
  }
  function renderBatch(cell, batch) {
    ensureTarget(cell);
    const prior = renderer.getRenderTarget(), face = renderer.getActiveCubeFace?.() || 0, level = renderer.getActiveMipmapLevel?.() || 0;
    const autoClear = renderer.autoClear, shadows = renderer.shadowMap.enabled;
    try {
      renderer.autoClear = false; renderer.shadowMap.enabled = false; renderer.setRenderTarget(cell.target);
      if (!cell.depthReady) { renderer.clear(false, true, false); renderer.render(cell.depthScene, cell.certificate.referenceCamera); cell.depthReady = true; moving.depthPasses++; }
      for (const s of batch) s.proxy.visible = true;
      renderer.render(cell.queryScene, cell.certificate.referenceCamera);
      for (const s of batch) {
        if (s.submitted) moving.queriesIssued++;
        else { cell.pending.delete(s.job.key); s.pending = false; s.job = null; }
      }
    } finally {
      if (activeQuery) { gl.endQuery(type); activeQuery = null; }
      for (const s of batch) s.proxy.visible = false;
      renderer.autoClear = autoClear; renderer.shadowMap.enabled = shadows; renderer.setRenderTarget(prior, face, level);
    }
  }
  function nextExternal(cell) {
    for (const job of external.values()) {
      const saved = cell.results.get(job.key), rejected = cell.rejected.get(job.key);
      if (saved && !sameBox(saved.values, job.box)) cell.results.delete(job.key);
      if (rejected && !sameBox(rejected, job.box)) cell.rejected.delete(job.key);
      if (!cell.results.has(job.key) && !cell.pending.has(job.key) && !cell.rejected.has(job.key)) return job;
    }
    return null;
  }
  function issue(allowance) {
    const started = performance.now(); let attempts = 0;
    for (const cell of [...cells].reverse()) {
      if (allowance <= 0 || cell.validFrame !== frame) break;
      if (cell.cursor >= cell.jobs.length && frame - cell.selectedAt >= 8) selectJobs(cell);
      const batch = [];
      while (batch.length < allowance) {
        if (attempts >= maxQueryAttemptsPerFrame || performance.now() - started >= maxQueryWorkMs) { moving.queryBudgetExhausted = true; break; }
        attempts++; moving.queryAttempts++;
        const job = nextExternal(cell) || cell.jobs[cell.cursor++]; if (!job) break;
        if (cell.results.has(job.key) || cell.pending.has(job.key) || cell.rejected.has(job.key)) continue;
        if (!validJob(job) || !frustum.intersectsBox(job.box)) { cell.rejected.set(job.key, boxValues(job.box)); continue; }
        const slot = getSlot(); if (!slot) break;
        const proxy = buildMovingOcclusionTarget(cell.certificate, job.box, slot.proxy.geometry);
        if (!proxy) { cell.rejected.set(job.key, boxValues(job.box)); continue; }
        const rect = proxy.rect, cover = cell.coverage;
        if (rect[0] < cover[0] - .01 || rect[1] < cover[1] - .01 || rect[2] > cover[2] + .01 || rect[3] > cover[3] + .01) {
          moving.coverageRejected++; cell.rejected.set(job.key, boxValues(job.box)); continue;
        }
        slot.cell = cell; slot.job = { ...job, values: proxy.boxValues }; slot.pending = true; slot.submitted = false;
        slot.proxy.geometry = proxy.geometry; cell.queryScene.add(slot.proxy); cell.pending.set(job.key, slot); batch.push(slot);
      }
      if (batch.length) { renderBatch(cell, batch); allowance -= batch.length; }
      if (moving.queryBudgetExhausted) break;
    }
  }
  const api = {
    stats, support,
    get enabled() { return enabled; }, set enabled(value) { enabled = !!value; moving.enabled = enabled; stationary.enabled = enabled; clearMoving(); syncStats(); },
    update(viewCamera = camera) {
      const started = performance.now(); if (!enabled || disposed || viewCamera !== camera) return stats;
      frame++; frameReady = false; registryCache = new WeakMap(); memberCache = new WeakMap(); sourceCache = new WeakMap(); inUpdate = true;
      moving.tested = moving.culled = moving.sourceChecks = moving.registryChecks = moving.buildMs = moving.updateMs = moving.queryAttempts = 0;
      moving.queryBudgetExhausted = false;
      const beforeIssues = stationary.stats.queriesIssued;
      try {
        stationary.update(camera);
        if (!support.supported || movingFailed || gl.isContextLost?.() || renderer.xr?.isPresenting || renderer.clippingPlanes?.length || gl.getQuery(type, gl.CURRENT_QUERY)) { clearMoving(); return stats; }
        frameMask = camera.layers.mask; frameProjection.set(camera.projectionMatrix.elements); frameWorld.set(camera.matrixWorld.elements); eye.setFromMatrixPosition(camera.matrixWorld); forward.set(0, 0, -1).transformDirection(camera.matrixWorld);
        frustum.setFromProjectionMatrix(matrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
        let invalidated = false;
        for (const cell of [...cells]) {
          moving.sourceChecks += cell.certificate.sources.length;
          if (!isMovingCertificateCurrent(cell.certificate, camera, cachedRegistry, sourceCache)) { retire(cell); invalidated = true; }
          else cell.validFrame = frame;
        }
        poll();
        const latest = cells[cells.length - 1], turned = haveAttempt && lastForward.dot(forward) < Math.cos(sectorAngle * Math.PI / 180);
        if (!haveAttempt || eye.distanceToSquared(lastEye) > cellTravel * cellTravel || turned || !latest && (invalidated || frame - lastAttempt >= 8)) createCell();
        moving.sourceMeshes = cells.reduce((n, c) => n + c.certificate.sources.length, 0);
        issue(Math.max(0, queriesPerFrame - (stationary.stats.queriesIssued - beforeIssues)));
        frameReady = true; moving.reason = '';
      } catch (error) {
        moving.errors++; moving.reason = String(error?.message || error); movingFailed = true; clearMoving();
      } finally {
        inUpdate = false; moving.updateMs = performance.now() - started - stationary.stats.updateMs;
        stats.updateMs = performance.now() - started; syncStats();
      }
      return stats;
    },
    isObjectOccluded(object, viewCamera) {
      if (!enabled || disposed || viewCamera !== camera) return false;
      for (let i = cells.length - 1; i >= 0; i--) {
        const cell = cells[i], result = cell.results.get(object);
        if (!result?.hidden || cell.validFrame !== frame || !currentMain(viewCamera) || !eyeInside(cell)) continue;
        const bounds = registry.bounds.get(object);
        if (!finiteBox(bounds) || !sameBox(result.values, bounds) || !validJob(result, true)) continue;
        moving.tested++; moving.culled++; stats.tested++; stats.culled++; return true;
      }
      if (stationary.isObjectOccluded(object, viewCamera)) { stats.tested++; stats.culled++; return true; }
      return false;
    },
    enqueueBox(box, key = box) {
      if (!finiteBox(box) || !key || !external.has(key) && external.size >= maxExternalBoxes) return false;
      external.set(key, { key, box, object: null, members: [] }); stationary.enqueueBox(box, key); return true;
    },
    isOccluded(box, viewCamera, key = box) {
      if (!enabled || disposed || viewCamera !== camera || !finiteBox(box)) return false;
      if (currentMain(viewCamera)) for (const cell of cells) {
        const result = cell.results.get(key);
        if (result?.hidden && cell.validFrame === frame && eyeInside(cell) && sameBox(result.values, box)) return true;
      }
      if (stationary.isOccluded(box, viewCamera, key)) return true;
      api.enqueueBox(box, key); return false;
    },
    invalidate() { stationary.invalidate(); clearMoving(); syncStats(); },
    dispose() {
      if (disposed) return; disposed = true; enabled = moving.enabled = false; clearMoving(); stationary.dispose();
      sourceMaterial.dispose(); targetMaterial.dispose(); external.clear(); targets.length = 0;
      if (!facePool) { prepared.faces.length = 0; prepared.faces.spatialIndex = null; }
      syncStats();
    },
  };
  syncStats(); return api;
}
