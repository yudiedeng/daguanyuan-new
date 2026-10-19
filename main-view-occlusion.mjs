import { createConservativeOcclusion, prepareConservativeOcclusionAsync } from './conservative-occlusion.mjs';
import { createOcclusionSceneRegistry } from './occlusion-scene-registry.mjs';

// Occlusion belongs to one camera and one completed synchronous update. Never
// mutate Object3D.visible: shadows and reflection cameras need their own scene.
export function createMainViewOcclusion({ THREE, scene, camera, buildings, spatial, treeGroups, treeScale, ...options }) {
  const registry = createOcclusionSceneRegistry({ THREE, scene, buildings, spatial, treeGroups, treeScale });
  const engine = createConservativeOcclusion({ THREE, occluders: registry.occluders, isOccluderCurrent: registry.isCurrent, maxDistance: 120, ...options });
  return bindMainViewOcclusion({THREE,scene,camera,registry,engine});
}

export async function prepareMainViewOcclusion({ THREE, scene, camera, buildings, spatial, treeGroups, treeScale, ...options }, scheduling) {
  const registry = createOcclusionSceneRegistry({ THREE, scene, buildings, spatial, treeGroups, treeScale });
  const engine = await prepareConservativeOcclusionAsync({ THREE, occluders: registry.occluders, isOccluderCurrent: registry.isCurrent, maxDistance: 120, ...options }, scheduling);
  return bindMainViewOcclusion({THREE,scene,camera,registry,engine});
}

function bindMainViewOcclusion({THREE,scene,camera,registry,engine}) {
  const world = new Float64Array(16), projection = new Float64Array(16);
  let enabled = true, ready = false, layers = camera.layers.mask, objects = new WeakMap(), boxes = new WeakMap();
  let frame = 0, coverageRevision = -1;
  const stats = { tested: 0, culled: 0, updateMs: 0, queryCacheHits: 0, queryCacheMisses: 0,
    coverageRevision: -1, registry: registry.stats, engine: engine.stats };
  // Older engines without a revision retain only per-frame caching. Production
  // revisions change whenever coverage is rebuilt or invalidated, not on time.
  const revision = () => Number.isSafeInteger(engine.stats.coverageRevision) && engine.stats.coverageRevision >= 0 ? engine.stats.coverageRevision : -frame;
  const sameBox = (v, b) => v[0] === b.min.x && v[1] === b.min.y && v[2] === b.min.z &&
    v[3] === b.max.x && v[4] === b.max.y && v[5] === b.max.z;
  function current(viewCamera) {
    if (!enabled || !ready || viewCamera !== camera || camera.layers.mask !== layers || revision() !== coverageRevision) return false;
    for (let i = 0; i < 16; i++) {
      if (camera.matrixWorld.elements[i] !== world[i] || camera.projectionMatrix.elements[i] !== projection[i]) return false;
    }
    return true;
  }
  function queryBox(box) {
    if (!box || box.isEmpty()) return false;
    const cached = boxes.get(box);
    // Bounds may be edited in-place (mirror readers do this). Cache identity
    // alone is never sufficient, even inside one frame.
    if (cached?.revision === coverageRevision && sameBox(cached.values, box)) { stats.queryCacheHits++; return cached.hidden; }
    stats.queryCacheMisses++;
    const hidden = engine.isOccluded(box) === true;
    boxes.set(box, { revision: coverageRevision, values: [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z], hidden });
    return hidden;
  }
  function isOccluded(box, viewCamera) {
    if (!engine.stats.coveredCells || !current(viewCamera)) return false;
    return queryBox(box);
  }
  function isObjectOccluded(object, viewCamera) {
    if (!enabled || !ready || viewCamera !== camera || engine.stats.coveredCells === 0) return false;
    let box = registry.bounds.get(object);
    if (!box) return false;
    if (!current(viewCamera)) return false;
    // The spatial index fails open when a new descendant invalidates a node.
    if (object.name?.startsWith('spatial-') && !object.userData.dgySpatialWorldBounds) return false;
    // Object certificates last only one update. Source certificates are still
    // checked by engine.update every frame, even when its depth is reused.
    let certificate = objects.get(object);
    if (!certificate || certificate.box !== box) {
      certificate = { box, current: registry.isCurrent?.(object) !== false }; objects.set(object, certificate);
      if (certificate.current) stats.tested++;
    }
    if (!certificate.current) return false;
    const hidden = queryBox(box);
    if (hidden && !certificate.counted) { stats.culled++; certificate.counted = true; }
    return hidden;
  }
  return {
    registry, engine, stats, isOccluded, isObjectOccluded,
    get enabled() { return enabled; },
    set enabled(value) { enabled = !!value; ready = false; },
    update(viewCamera = camera) {
      ready = false; objects = new WeakMap(); frame++;
      stats.tested = 0; stats.culled = 0; stats.updateMs = 0; stats.queryCacheHits = stats.queryCacheMisses = 0;
      if (!enabled || viewCamera !== camera) return;
      const start = performance.now();
      engine.update(camera);
      coverageRevision = revision(); stats.coverageRevision = coverageRevision;
      world.set(camera.matrixWorld.elements); projection.set(camera.projectionMatrix.elements); layers = camera.layers.mask;
      stats.engine = engine.stats; stats.updateMs = performance.now() - start; ready = true;
    },
    invalidate(object) { ready = false; boxes = new WeakMap(); registry.invalidate?.(object); engine.invalidate?.(object); },
    dispose() { enabled = false; ready = false; boxes = new WeakMap(); objects = new WeakMap(); engine.dispose?.(); registry.dispose?.(); },
  };
}
