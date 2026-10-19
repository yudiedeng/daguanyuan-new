// Authored bmat() recipes audited in index.html. These change surface shading,
// not topology, opacity or vertex positions. Use actual mesh triangles, never
// a courtyard's encompassing box (which would seal gates and windows).
export const STATIC_SURFACE_FLAG = 'dgyOcclusionStaticSurface';
const SURFACES = new Set([
  '旧木', '本色木', '本色楠木', '楠木', '紫檀', '花梨', '黄花梨', '朱漆', '绿漆', '黑漆',
  '栗色柱', '栗壳漆', '栗壳漆_柱', '栗壳漆_棂', '槅扇', '油壁', '枋青', '枋绿', '彩画青',
  'daguan_彩画青', 'daguan_彩画绿', 'daguan_室内暗', '天花', '天花心',
  '白灰墙', '雪洞白', '赭墙', '黄泥墙', '青砖', '水磨砖', '方砖地', '金砖地', '金砖',
  // Imported bmat('苔地') only adds triplanar ground colour. This does not
  // whitelist buildTerrain's separately patched material with river discard.
  '苔地',
  '青石', '青石_水渍', '石', '山石', '太湖石', '湖石', 'HW_玲珑石', '石雕', '汉白玉', '汉白玉_水渍', '虎皮石', '大理石',
  '灰瓦', '亭顶瓦', '花堵瓦', '屋脊灰', '沁芳脊', '黄琉璃瓦', '黄琉璃瓦.001_底瓦', '绿琉璃瓦', '绿琉璃瓦.001_底瓦', 'YH_灰瓦',
  '茅草', '茅草旧', '茅草新',
  'XS_旧白灰墙', 'XS_屋脊青灰', 'XS_门窗深褐木', 'XS_顶棚暖木', 'MAT_暗褐旧木_顺纹', 'SAMPLE2_深绿漆',
  'MAT_柱础青石_养护旧化_column', 'MAT_青灰石_微风化_养护旧化_steps',
  'MAT_青灰石_微风化_养护旧化_coping', 'MAT_青灰石_微风化_养护旧化_footing',
  'MAT_青灰石_微风化_养护旧化_wall', 'MAT_台帮青砖块_养护旧化_wall', 'MAT_廊面青砖_养护旧化_paving',
  ...Array.from({ length: 7 }, (_, i) => 'XS_灰瓦色差_' + i),
]);
const SPATIAL_BOUNDS = 'dgySpatialWorldBounds';

const finiteBox = box => box?.isBox3 && !box.isEmpty() &&
  [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z].every(Number.isFinite);
const finiteSphere = sphere => sphere?.radius >= 0 &&
  [sphere.radius, sphere.center.x, sphere.center.y, sphere.center.z].every(Number.isFinite);
const materials = mesh => Array.isArray(mesh.material) ? mesh.material : [mesh.material];

function recipeKey(material) {
  try { return material.customProgramCacheKey(); } catch { return ''; }
}

const materialState = material => ({ material, compile: material.onBeforeCompile, key: recipeKey(material),
  displacement: material.displacementMap, scale: material.displacementScale, bias: material.displacementBias });
const sameMaterialState = (material, state) => material === state.material && material.onBeforeCompile === state.compile &&
  recipeKey(material) === state.key && material.displacementMap === state.displacement &&
  material.displacementScale === state.scale && material.displacementBias === state.bias;

function bmatRecipe(material) {
  if (!material?.isMeshStandardMaterial || typeof material.name !== 'string' || !material.name) return null;
  const name = material.name, key = recipeKey(material);
  // Exact suffix matters: a random custom shader called "白灰墙" is insufficient.
  const suffix = key.replace(/^p\d+bm_/, '');
  if (suffix === key || (suffix !== name && suffix !== name + '_ao')) return null;
  return { name, ao: key.endsWith('bm_' + name + '_ao') };
}

function hasFixedVertices(material, THREE) {
  if (!material || material.isShaderMaterial || material.displacementMap || material.clippingPlanes?.length) return false;
  const recipe = bmatRecipe(material);
  // AO bmat's vWorld only forwards vertex color: vWx=color.rgb. patch() still
  // marks it shadowDynamic, although it does not move vertices.
  if (recipe) return !material.userData.shadowDynamic || recipe.ao;
  return !material.userData.shadowDynamic && material.onBeforeCompile === THREE.Material.prototype.onBeforeCompile;
}

export function isAuditedBuildingOccluderMaterial(material) {
  const recipe = bmatRecipe(material);
  if (!recipe) return false;
  const name = recipe.name.replace(/^(?:hw|yh)B_/, '');
  if (!SURFACES.has(name)) return false;
  if (material.visible === false || material.transparent || material.opacity < 1 || material.alphaTest > 0 ||
    material.alphaMap || material.alphaHash || material.alphaToCoverage || material.displacementMap ||
    material.depthWrite === false || material.depthTest === false || material.colorWrite === false ||
    material.stencilWrite || material.clippingPlanes?.length || material.wireframe || material.transmission > 0 || material.polygonOffset ||
    (material.userData.shadowDynamic && !recipe.ao)) return false;
  // Current listed bmat recipes never use a base-color alpha texture; additions
  // must explicitly certify RGB images. Do not infer opacity from PNG/JPEG names.
  if (material.map && material.map.userData?.dgyOpaque !== true) return false;
  return true;
}

function isStaticLeaf(mesh, THREE) {
  return mesh.isMesh && !mesh.isInstancedMesh && !mesh.isSkinnedMesh && !mesh.isBatchedMesh &&
    mesh.children.length === 0 && mesh.geometry?.attributes.position && !mesh.geometry.isInstancedBufferGeometry &&
    !Object.keys(mesh.geometry.morphAttributes || {}).length && !mesh.morphTargetInfluences &&
    !mesh.animations?.length && !mesh.userData.dynamic && !mesh.userData.dgyImmediate && !mesh.isReflector && !mesh.userData.rcKind &&
    mesh.onBeforeRender === THREE.Object3D.prototype.onBeforeRender &&
    materials(mesh).every(m => hasFixedVertices(m, THREE));
}

function excludedBranch(object, stop) {
  for (let node = object; node && node !== stop; node = node.parent) {
    if (/^PROP_/.test(node.name) || node.userData.dynamic || node.userData.dgyImmediate ||
      node.animations?.length || node.isBone || node.isSkinnedMesh || node.isReflector || node.userData.rcKind) return true;
  }
  return false;
}

/** Occlusion-only bounds for the complete tree population. Unlike the renderer's
 * compatibility frustum bounds, this does not union the old batch sphere: that
 * sphere adds the whole 80 m cell width to vertical extent too. A transformed
 * geometry box plus the planting anchor encloses all scalar seasonal contractions.
 * Existing renderer bounds, groups, instance buffers and draw calls stay intact.
 */
export function treeOcclusionWorldBounds({ THREE, group, entry, mesh = entry.m, treeScale, windPadding = 2 }) {
  const geometry = mesh?.geometry;
  if (!geometry || typeof treeScale !== 'function' || !group?.list?.length || !Number.isFinite(windPadding) || windPadding < 0) return null;
  if (!geometry.boundingBox) {
    if (!(geometry.attributes.position?.array || geometry.attributes.position?.data?.array)) return null;
    geometry.computeBoundingBox();
  }
  if (!finiteBox(geometry.boundingBox)) return null;
  const result = new THREE.Box3(), transformed = new THREE.Box3(), matrix = new THREE.Matrix4();
  const position = new THREE.Vector3(), scale = new THREE.Vector3(), rotation = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  mesh.updateWorldMatrix(true, false);
  for (const tree of group.list) {
    let maxScale = 0;
    for (let season = 0; season < 4; season++) {
      const value = treeScale(group, entry, tree, season);
      if (!Number.isFinite(value) || value < 0) return null;
      maxScale = Math.max(maxScale, value);
    }
    const s = tree.s * maxScale, vertical = entry.uni ? 1 : 0.9 + ((tree.x * 7.3) % 0.2);
    if (!Number.isFinite(s) || s < 0 || !(vertical > 0) || ![tree.x, tree.y, tree.z, tree.ry, entry.dy || 0].every(Number.isFinite)) return null;
    position.set(tree.x, tree.y + (entry.dy || 0), tree.z);
    rotation.setFromAxisAngle(up, tree.ry); scale.set(s, s * vertical, s);
    matrix.compose(position, rotation, scale).premultiply(mesh.matrixWorld);
    transformed.copy(geometry.boundingBox).applyMatrix4(matrix); result.union(transformed);
    result.expandByPoint(position.applyMatrix4(mesh.matrixWorld));
  }
  if (!finiteBox(result)) return null;
  return result.expandByScalar(windPadding + 1e-4);
}

export function createOcclusionSceneRegistry({ THREE, scene, buildings = [], spatial, treeGroups = [], treeScale, windPadding = 2 } = {}) {
  if (treeGroups.length && typeof treeScale !== 'function') throw new Error('Occlusion tree bounds require the production four-season treeScale function.');
  const started = performance.now(), occluders = [], bounds = new Map(), listeners = [], snapshots = new Map(), treeMaterials = new Map();
  const stats = { occluders: 0, buildingMeshes: 0, spatialNodes: 0, spatialEntries: 0, treeEntries: 0, tightTreeEntries: 0,
    tightSpatialNodes: 0, treeVolumeBefore: 0, treeVolumeAfter: 0, staticInstances: 0, excludedBuildingMeshes: 0, buildMs: 0 };
  scene.updateMatrixWorld(true);
  const addBounds = (object, box, kind, mutableInstances = false) => {
    if (!finiteBox(box) || bounds.has(object)) return;
    // Query boxes are independent from the renderer's frustum boxes. Remember
    // the live source identity/values separately: null or replacement fails open.
    bounds.set(object, box.clone().expandByScalar(1e-4)); stats[kind]++;
    const liveSpatial = object.userData?.[SPATIAL_BOUNDS];
    snapshots.set(object, { parent: object.parent, world: object.matrixWorld.elements.slice(), kind,
      sourceSpatialBounds: finiteBox(liveSpatial) ? liveSpatial : null,
      sourceSpatialValues: finiteBox(liveSpatial) ? [...liveSpatial.min.toArray(), ...liveSpatial.max.toArray()] : null,
      geometry: object.geometry, position: object.geometry?.attributes.position,
      positionVersion: object.geometry?.attributes.position?.version,
      index: object.geometry?.index, indexVersion: object.geometry?.index?.version,
      mutableInstances, instanceMatrix: object.instanceMatrix, instanceVersion: object.instanceMatrix?.version, count: object.count,
      materialVariants: object.isMesh ? treeMaterials.get(object) || [materials(object).map(materialState)] : null });
  };
  for (const { root } of buildings) {
    root.traverse(mesh => {
      if (!mesh.isMesh) return;
      if (excludedBranch(mesh, root.parent) || !isStaticLeaf(mesh, THREE)) { stats.excludedBuildingMeshes++; return; }
      const geometry = mesh.geometry;
      if (!geometry.boundingBox) {
        if (!(geometry.attributes.position.array || geometry.attributes.position.data?.array)) return;
        geometry.computeBoundingBox();
      }
      if (!finiteBox(geometry.boundingBox)) return;
      addBounds(mesh, geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld), 'buildingMeshes');
      const cpuTriangles = (geometry.attributes.position.array || geometry.attributes.position.data?.array) && (!geometry.index || geometry.index.array);
      if (cpuTriangles && materials(mesh).every(isAuditedBuildingOccluderMaterial)) {
        for (const material of materials(mesh)) material.userData[STATIC_SURFACE_FLAG] = true;
        occluders.push(mesh);
      }
    });
  }
  // These declarations already cover full tree populations, all seasonal scales
  // and wind. Current layoutLOD instance matrices do not provide such a bound.
  const treeBounds = new Map();
  for (const group of treeGroups) for (const entry of [...group.near, ...group.far]) {
    for (const mesh of [entry.m, entry.rm]) {
      if (!mesh) continue;
      const box = treeOcclusionWorldBounds({ THREE, group, entry, mesh, treeScale, windPadding });
      if (box) {
        treeBounds.set(mesh, box);
        const variants = [materials(mesh).map(materialState)];
        for (const swap of group.swap || []) if (swap.m === mesh) for (const option of [swap.base?.[0], swap.alt?.[0]]) {
          if (option) variants.push((Array.isArray(option) ? option : [option]).map(materialState));
        }
        treeMaterials.set(mesh, variants);
      }
    }
  }
  const volume = box => (box.max.x - box.min.x) * (box.max.y - box.min.y) * (box.max.z - box.min.z);
  for (const node of spatial?.nodes || []) addBounds(node, node.userData?.[SPATIAL_BOUNDS], 'spatialNodes');
  for (const entry of spatial?.entries || []) {
    const tight = treeBounds.get(entry.mesh);
    addBounds(entry.mesh, tight || entry.bounds, 'spatialEntries', entry.kind === 'tree');
    if (tight) { stats.tightTreeEntries++; stats.treeVolumeBefore += volume(entry.bounds); stats.treeVolumeAfter += volume(tight); }
  }
  for (const [mesh, box] of treeBounds) if (!bounds.has(mesh)) {
    addBounds(mesh, box, 'treeEntries', true); stats.tightTreeEntries++;
  }
  scene.traverse(mesh => {
    if (bounds.has(mesh) || !mesh.isInstancedMesh || mesh.children.length || mesh.isSkinnedMesh || mesh.morphTexture || excludedBranch(mesh, scene)) return;
    const declaration = mesh.userData.dgySpatialStatic;
    const crop = /^作物·/.test(mesh.name) && materials(mesh).every(m => /^p\d+crop(?:3d|rape|veg)$/.test(recipeKey(m)));
    if (!declaration && !crop) return;
    if (!finiteSphere(mesh.boundingSphere)) return;
    const sphere = mesh.boundingSphere.clone().applyMatrix4(mesh.matrixWorld);
    addBounds(mesh, sphere.getBoundingBox(new THREE.Box3()).expandByScalar(declaration?.padding || 0), 'staticInstances');
  });
  // Bottom-up union of certified query bounds tightens hierarchy traversal too.
  // It never changes dgySpatialWorldBounds or the main/shadow/reflection frustum.
  for (const node of [...(spatial?.nodes || [])].reverse()) {
    if (!bounds.has(node) || !node.children.length) continue;
    const query = new THREE.Box3(); let complete = true;
    for (const child of node.children) {
      const childBox = bounds.get(child);
      if (!finiteBox(childBox)) { complete = false; break; }
      query.union(childBox);
    }
    if (complete && finiteBox(query) && volume(query) < volume(bounds.get(node))) {
      bounds.set(node, query.expandByScalar(1e-4)); stats.tightSpatialNodes++;
    }
  }

  // Call invalidate(object) after any future position/geometry change. Late
  // children automatically invalidate their candidate ancestor bounds. LOD
  // visible toggles need no rebuild: engine checks live ancestor visibility.
  function invalidate(object) {
    if (!object) { bounds.clear(); occluders.length = 0; return; }
    const descendants = new Set(); object.traverse(node => descendants.add(node));
    for (let node = object; node; node = node.parent) bounds.delete(node);
    for (const node of descendants) bounds.delete(node);
    for (let i = occluders.length - 1; i >= 0; i--) if (descendants.has(occluders[i])) occluders.splice(i, 1);
  }
  function isCurrent(object) {
    const saved = snapshots.get(object);
    if (!saved || !bounds.has(object) || object.parent !== saved.parent) return false;
    let ancestor = object; while (ancestor && ancestor !== scene) ancestor = ancestor.parent;
    if (ancestor !== scene) return false;
    if (saved.kind === 'spatialNodes' || saved.sourceSpatialBounds) {
      const source = object.userData[SPATIAL_BOUNDS];
      if (source !== saved.sourceSpatialBounds || !finiteBox(source)) return false;
      const values = [source.min.x, source.min.y, source.min.z, source.max.x, source.max.y, source.max.z];
      for (let i = 0; i < 6; i++) if (values[i] !== saved.sourceSpatialValues[i]) return false;
    }
    if (!finiteBox(bounds.get(object))) return false;
    for (let i = 0; i < 16; i++) if (object.matrixWorld.elements[i] !== saved.world[i]) return false;
    if (object.geometry !== saved.geometry || object.geometry?.attributes.position !== saved.position ||
      object.geometry?.attributes.position?.version !== saved.positionVersion || object.geometry?.index !== saved.index ||
      object.geometry?.index?.version !== saved.indexVersion) return false;
    if (!saved.mutableInstances && (object.instanceMatrix !== saved.instanceMatrix || object.instanceMatrix?.version !== saved.instanceVersion || object.count !== saved.count)) return false;
    if (saved.materialVariants) {
      const current = materials(object);
      // needsUpdate/alphaToCoverage changes Material.version during normal
      // compilation and quality switching but do not move a single vertex.
      if (!saved.materialVariants.some(states => states.length === current.length && current.every((m, i) => sameMaterialState(m, states[i])))) return false;
    }
    return true;
  }
  for (const object of bounds.keys()) {
    const changed = () => invalidate(object);
    object.addEventListener('childadded', changed); object.addEventListener('childremoved', changed);
    listeners.push([object, changed]);
  }
  stats.occluders = occluders.length; stats.buildMs = performance.now() - started;
  return { occluders, bounds, stats, invalidate, isCurrent, dispose() {
    for (const [object, changed] of listeners) { object.removeEventListener('childadded', changed); object.removeEventListener('childremoved', changed); }
    invalidate();
  } };
}
