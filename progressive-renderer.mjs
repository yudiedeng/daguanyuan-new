// Prepare the entrance first, then stream GPU work in small, paintable slices.
// Scene ownership, transforms, materials and logical visibility stay with the game.
export function createProgressiveRenderer({
  THREE, renderer, scene, camera, target, sun,
  onProgress = () => {}, yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)),
  now = () => performance.now(), budgetMs = 6, isEntranceObject = () => true,
}) {
  const objects = [], known = new Set(), ready = new Set();
  const preview = new Map(), previewReady = new Set();
  const bounds = new Map(), boundState = new Map(), entrance = new Set(), pending = new Set();
  const warmTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType });
  const frustum = new THREE.Frustum(), matrix = new THREE.Matrix4();
  const states = { shadows: false, post: false, reflections: false };
  const metrics = { objects: 0, entranceObjects: 0, readyAtFirstView: 0, uploads: 0, slices: 0, maxUploadMs: 0, maxCompileCallMs: 0 };
  const begun = now();
  let active = true, running = false, firstView = false, extrasDone = false, finishResolve, postPreparation;
  let didFinish = false, failed = false;
  let reflectionTokens = 1;
  const finished = new Promise(resolve => { finishResolve = resolve; });
  const renderable = o => !!(o.isMesh || o.isPoints || o.isLine || o.isSprite);
  const visible = o => { for (let p = o; p; p = p.parent) if (!p.visible) return false; return true; };
  const materials = o => (Array.isArray(o.material) ? o.material : [o.material]).filter(Boolean);
  function discover() {
    scene.updateMatrixWorld();
    scene.traverse(o => {
      // Small, essential moving cues must draw immediately; their initial bounds
      // do not describe where their instances will be on the next game tick.
      if (!renderable(o) || o.userData.dgyImmediate) return;
      const previous = boundState.get(o);
      if (known.has(o)) {
        if (previous.geometry !== o.geometry) { ready.delete(o); pending.add(o); }
        else if (ready.has(o) || (previous.count === o.count && previous.matrix.equals(o.matrixWorld))) return;
      } else { known.add(o); objects.push(o); pending.add(o); }
      let box = new THREE.Box3();
      if (o.isInstancedMesh) {
        // Keep authored wind margins and bounds shared with reflection meshes.
        const authored = o.boundingSphere;
        o.boundingSphere = null;
        try {
          o.computeBoundingSphere();
          if (o.boundingSphere) box.setFromCenterAndSize(o.boundingSphere.center, new THREE.Vector3().setScalar(o.boundingSphere.radius * 2)).applyMatrix4(o.matrixWorld);
        } finally { o.boundingSphere = authored; }
      } else if (o.geometry?.attributes.position) {
        if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
        box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld);
        // Grass roots are expanded in the vertex shader. Their CPU positions are
        // all zero, so the deliberately large shader bounds must be respected.
        if (!o.frustumCulled && o.geometry.boundingSphere?.radius > box.getSize(new THREE.Vector3()).length() * 2) {
          const sphere = o.geometry.boundingSphere.clone().applyMatrix4(o.matrixWorld);
          box.setFromCenterAndSize(sphere.center, new THREE.Vector3().setScalar(sphere.radius * 2));
        }
      } else box.setFromCenterAndSize(o.getWorldPosition(new THREE.Vector3()), new THREE.Vector3(1, 1, 1));
      bounds.set(o, box);
      boundState.set(o, { geometry: o.geometry, count: o.count, matrix: o.matrixWorld.clone() });
    });
    metrics.objects = objects.length;
  }
  function updateFrustum() {
    camera.updateMatrixWorld();
    matrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    frustum.setFromProjectionMatrix(matrix);
  }
  function distance(o) { return bounds.get(o).distanceToPoint(camera.position); }
  function prioritized(list) {
    updateFrustum();
    const score = o => (visible(o) ? 0 : 10000) + (frustum.intersectsBox(bounds.get(o)) ? 0 : 2000) + distance(o);
    return list.sort((a, b) => score(a) - score(b));
  }
  function interested() {
    updateFrustum();
    const radius = Math.max(95, Math.min(650, camera.position.y * 2.5));
    return [...pending].filter(o => o.parent && visible(o) && distance(o) < radius && frustum.intersectsBox(bounds.get(o)));
  }
  function previewMaterial(o) {
    const make = material => new THREE.MeshBasicMaterial({
      color: o.name === 'terrain' ? 0x8a956d : material.color?.clone() || 0xffffff,
      map: material.map || null, alphaMap: material.alphaMap || null,
      alphaTest: material.alphaTest || 0, side: material.side,
      transparent: material.transparent, opacity: material.opacity,
      vertexColors: o.name !== 'terrain' && material.vertexColors,
      depthWrite: material.depthWrite, depthTest: material.depthTest,
    });
    return Array.isArray(o.material) ? o.material.map(make) : make(o.material);
  }
  // Hide pending geometry only for a draw; LOD/season/game logic can keep updating
  // its own visible flags between frames. Always restore, including on failure.
  function mask(only = null) {
    const changed = [], swapped = [];
    for (const o of objects) {
      if ((only ? !only.has(o) : !ready.has(o) && !previewReady.has(o)) && o.visible) { changed.push(o); o.visible = false; }
      if (!only && previewReady.has(o) && !ready.has(o)) { swapped.push([o, o.material]); o.material = preview.get(o); }
    }
    return () => { for (const [o, material] of swapped) o.material = material; for (const o of changed) o.visible = true; };
  }
  async function compile(o, shadows, depthMaterial = null) {
    const oldTarget = renderer.getRenderTarget(), oldShadows = renderer.shadowMap.enabled;
    const material = o.material, children = o.children;
    let work;
    try {
      // compileAsync traverses descendants; a batch must contain just this object.
      o.children = [];
      if (depthMaterial) o.material = depthMaterial;
      renderer.shadowMap.enabled = shadows;
      renderer.setRenderTarget(target());
      const start = now();
      work = renderer.compileAsync(o, camera, scene);
      metrics.maxCompileCallMs = Math.max(metrics.maxCompileCallMs, now() - start);
    } finally {
      o.material = material; o.children = children;
      renderer.shadowMap.enabled = oldShadows; renderer.setRenderTarget(oldTarget);
    }
    await work;
  }
  function upload(o, override = null) {
    const selected = new Set([o]);
    // A mesh can itself contain meshes (water's depth-only surface, for example).
    for (let p = o.parent; p && p !== scene; p = p.parent) if (renderable(p)) selected.add(p);
    const restoreMask = mask(selected), ancestors = [], callbacks = [];
    const oldTarget = renderer.getRenderTarget(), oldShadows = renderer.shadowMap.enabled;
    const oldFrustum = o.frustumCulled, originalMaterial = o.material;
    const start = now();
    try {
      for (let p = o; p && p !== scene; p = p.parent) {
        if (!p.visible) { ancestors.push(p); p.visible = true; }
        if (renderable(p)) { callbacks.push([p, p.onBeforeRender, p.onAfterRender]); p.onBeforeRender = () => {}; p.onAfterRender = () => {}; }
      }
      o.frustumCulled = false;
      if (override) o.material = override;
      renderer.shadowMap.enabled = false;
      renderer.setRenderTarget(warmTarget);
      renderer.render(scene, camera);
      metrics.uploads++;
    } finally {
      o.frustumCulled = oldFrustum;
      o.material = originalMaterial;
      for (const [p, before, after] of callbacks) { p.onBeforeRender = before; p.onAfterRender = after; }
      for (const p of ancestors) p.visible = false;
      restoreMask();
      renderer.shadowMap.enabled = oldShadows; renderer.setRenderTarget(oldTarget);
      metrics.maxUploadMs = Math.max(metrics.maxUploadMs, now() - start);
    }
  }
  async function prepareObjects(list, label) {
    let slice = now(), done = 0;
    onProgress({ label, done, total: list.length, firstView, metrics });
    for (const o of list) {
      if (!o.parent) { pending.delete(o); continue; }
      await compile(o, states.shadows);
      if (states.shadows && o.castShadow && renderer.shadowMap.dgyDepthMaterial) {
        for (const material of materials(o)) await compile(o, true, renderer.shadowMap.dgyDepthMaterial(o, material, sun));
      }
      upload(o); ready.add(o); pending.delete(o); done++;
      if (preview.has(o)) {
        const old = preview.get(o);
        for (const material of Array.isArray(old) ? old : [old]) material.dispose();
        preview.delete(o); previewReady.delete(o);
      }
      onProgress({ label, done, total: list.length, firstView, metrics });
      if (now() - slice >= budgetMs) { metrics.slices++; await yieldFrame(); slice = now(); }
    }
    // Even a fully cached batch must allow the loading text to paint.
    await yieldFrame();
  }
  async function prepareEntrance() {
    discover(); updateFrustum();
    for (const o of objects) if (isEntranceObject(o) && visible(o) && frustum.intersectsBox(bounds.get(o)) && distance(o) < 65) entrance.add(o);
    metrics.entranceObjects = entrance.size;
    let done = 0, slice = now();
    onProgress({ label: '布置园门', done, total: entrance.size, firstView, metrics });
    for (const o of prioritized([...entrance])) {
      const material = previewMaterial(o); preview.set(o, material);
      await compile(o, false, material); upload(o, material); previewReady.add(o);
      onProgress({ label: '布置园门', done: ++done, total: entrance.size, firstView, metrics });
      if (now() - slice >= budgetMs) { metrics.slices++; await yieldFrame(); slice = now(); }
    }
    await yieldFrame();
    metrics.entrancePreparationMs = now() - begun;
  }
  async function prepareShadows() {
    let slice = now(), done = 0;
    for (const o of prioritized([...ready])) {
      await compile(o, true);
      if (o.castShadow && renderer.shadowMap.dgyDepthMaterial) {
        for (const material of materials(o)) {
          const depth = renderer.shadowMap.dgyDepthMaterial(o, material, sun);
          await compile(o, true, depth);
        }
      }
      onProgress({ label: '添上光影', done: ++done, total: ready.size, firstView, metrics });
      if (now() - slice >= budgetMs) { metrics.slices++; await yieldFrame(); slice = now(); }
    }
    states.shadows = true;
    await yieldFrame();
  }
  async function runBackground(preparePost) {
    if (running || failed) return;
    running = true; active = true; postPreparation = preparePost;
    try {
      while (active) {
        discover();
        const wanted = interested();
        if (wanted.length) { await prepareObjects(prioritized(wanted), '铺开远景'); continue; }
        if (!states.shadows) { await prepareShadows(); continue; }
        if (!states.post) { await preparePost(); states.post = true; await yieldFrame(); continue; }
        if (!states.reflections) { states.reflections = true; await yieldFrame(); continue; }
        if (!extrasDone) { await new Promise(resolve => setTimeout(resolve, 50)); continue; }
        active = false;
        metrics.backgroundMs = now() - begun;
        metrics.preparedObjects = ready.size;
        onProgress({ label: '园景已就绪', done: metrics.objects, total: metrics.objects, firstView, metrics });
        if (!didFinish) { didFinish = true; finishResolve(metrics); }
      }
    } catch (error) {
      // A failed optional warm-up must never leave part of the garden hidden.
      active = false; failed = true; states.shadows = states.post = states.reflections = true;
      for (const o of objects) ready.add(o);
      pending.clear();
      for (const material of preview.values()) for (const m of Array.isArray(material) ? material : [material]) m.dispose();
      preview.clear(); previewReady.clear();
      warmTarget.dispose(); finishResolve({ ...metrics, error: String(error) });
      console.warn('分批准备未完成，恢复正常绘制', error);
      onProgress({ label: '园景已就绪', done: metrics.objects, total: metrics.objects, firstView, metrics });
    } finally { running = false; }
  }
  function beforeFrame() {
    reflectionTokens = 1;
    if (failed) return () => {};
    discover();
    if (!running && postPreparation && interested().length) queueMicrotask(() => runBackground(postPreparation));
    return mask();
  }
  return {
    states, metrics, finished, prepareEntrance, beforeFrame,
    get active() { return active; },
    markFirstView() { firstView = true; metrics.readyAtFirstView = previewReady.size + ready.size; metrics.firstViewMs = now() - begun; },
    startBackground: runBackground,
    finishExtras() { extrasDone = true; },
    allowReflection() {
      if (!states.reflections) return false;
      if (!active) return true;
      if (reflectionTokens <= 0) return false;
      reflectionTokens--; return true;
    },
  };
}
