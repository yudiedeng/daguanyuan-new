// Prepare every scene object while the loading screen is still visible.
// This never changes visibility, materials, LOD, or the scene hierarchy.
export async function prepareFullScene({
  THREE, renderer, scene, camera, target, sun,
  onProgress = () => {}, budgetMs = 8, batchSize = 128,
  yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)),
  now = () => performance.now(),
}) {
  const begun = now(), objects = [], textures = new Set(), materials = new Set();
  const metrics = { objects: 0, textures: 0, batches: 0, maxTaskMs: 0, stages: [] };
  scene.traverse(o => {
    if (!(o.isMesh || o.isPoints || o.isLine || o.isSprite)) return;
    objects.push(o);
    for (const m of Array.isArray(o.material) ? o.material : [o.material]) if (m) materials.add(m);
    if (o.customDepthMaterial) materials.add(o.customDepthMaterial);
  });
  function texture(value) {
    if (value?.isTexture && !value.isRenderTargetTexture && value.image) textures.add(value);
    else if (Array.isArray(value)) value.forEach(texture);
  }
  for (const m of materials) {
    Object.values(m).forEach(texture);
    if (m.uniforms) for (const u of Object.values(m.uniforms)) texture(u.value);
  }
  metrics.objects = objects.length; metrics.textures = textures.size;
  async function stage(label, items, run, parallel = 1) {
    const start = now(); let slice = now();
    const pending = new Set(); let done = 0, failure;
    onProgress({ label, done: 0, total: items.length });
    await yieldFrame();
    for (let i = 0; i < items.length; i++) {
      const task = now(), work = run(items[i]);
      metrics.maxTaskMs = Math.max(metrics.maxTaskMs, now() - task);
      const promise = Promise.resolve(work).then(() => {
        onProgress({ label, done: ++done, total: items.length });
      }, error => { failure = error; }).finally(() => pending.delete(promise));
      pending.add(promise);
      if (pending.size >= parallel) await Promise.race(pending);
      if (failure) { await Promise.all(pending); throw failure; }
      if (now() - slice >= budgetMs) { await yieldFrame(); slice = now(); }
    }
    await Promise.all(pending);
    if (failure) throw failure;
    metrics.stages.push({ label, ms: now() - start });
    await yieldFrame();
  }
  // Upload buffers directly instead of rendering the whole garden once per mesh.
  // Three's own upload path keeps shared-buffer/version/disposal bookkeeping.
  await stage('上传全园模型', objects, o => {
    if (o.geometry && renderer.dgyPrepareGeometry) renderer.dgyPrepareGeometry(o);
  });
  await stage('上传全园贴图', [...textures], t => renderer.initTexture(t));
  const chunks = [];
  for (let i = 0; i < objects.length; i += batchSize) chunks.push(objects.slice(i, i + batchSize));
  const previousTarget = renderer.getRenderTarget();
  try {
    await stage('编译全园材质', chunks, async chunk => {
      // Shallow compile views preserve instancing/morph/geometry shader features.
      // No reparenting and no onBeforeRender reflection callbacks during compile.
      const batch = new THREE.Group();
      batch.children = chunk.map(o => { const view = Object.create(o); view.children = []; return view; });
      renderer.setRenderTarget(target());
      const work = renderer.compileAsync(batch, camera, scene);
      renderer.setRenderTarget(previousTarget);
      await work; metrics.batches++;
    }, 4);
    if (sun && renderer.shadowMap.dgyDepthMaterial) {
      const casters = objects.filter(o => o.castShadow), shadowChunks = [];
      for (let i = 0; i < casters.length; i += batchSize) shadowChunks.push(casters.slice(i, i + batchSize));
      await stage('编译全园阴影', shadowChunks, async chunk => {
        const batch = new THREE.Group();
        batch.children = chunk.map(o => { const view = Object.create(o); view.children = []; return view; });
        renderer.setRenderTarget(target());
        // Select and compile each exact depth variant inside one native batch.
        // Gather scene lights once, rather than rescanning 6000+ objects per caster.
        const work = renderer.compileAsync(batch, camera, scene, sun);
        renderer.setRenderTarget(previousTarget);
        await work;
      }, 4);
    }
  } finally { renderer.setRenderTarget(previousTarget); }
  metrics.totalMs = now() - begun;
  return metrics;
}
