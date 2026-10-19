// Explicitly opt-in, static scene hierarchy. The renderer tests each node's
// world-space Box3 against the current pass's frustum, then retains its usual
// per-mesh test. No camera-dependent visibility state is stored here.
export const SPATIAL_BOUNDS_KEY = 'dgySpatialWorldBounds';
const STATIC_KEY = 'dgySpatialStatic';

// Call only for a mesh whose complete instance set and transform are fixed.
// `padding` is additional WORLD-space displacement allowance, not a replacement
// for the builder's existing wind padding. Visibility/material changes are fine.
export function markStaticSpatial(mesh, { padding = 0 } = {}) {
  mesh.userData[STATIC_KEY] = { padding: Math.max(0, padding) };
  return mesh;
}

const finiteSphere = sphere => sphere && Number.isFinite(sphere.radius) && sphere.radius >= 0 &&
  Number.isFinite(sphere.center.x) && Number.isFinite(sphere.center.y) && Number.isFinite(sphere.center.z);
const finiteBox = box => box?.isBox3 && !box.isEmpty() &&
  [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z].every(Number.isFinite);

function eligible(mesh, scene) {
  return mesh?.parent === scene && mesh.isMesh && !mesh.isSkinnedMesh && !mesh.isBatchedMesh &&
    !mesh.userData.dynamic && !mesh.animations?.length &&
    !mesh.geometry?.isInstancedBufferGeometry && !mesh.geometry?.morphAttributes?.position?.length &&
    mesh.children.length === 0 && mesh.frustumCulled !== false;
}

// TG layoutLOD uses subsets of a fixed list, reordered by distance. Bounds are
// built from that COMPLETE list, never from current count/instanceMatrix.
export function treeEntryWorldBounds({ THREE, scene, group, entry, mesh = entry.m, treeScale, windPadding = 2 }) {
  const geometry = mesh?.geometry;
  if (!geometry || !group?.list?.length || typeof treeScale !== 'function' || !Number.isFinite(windPadding) || windPadding < 0) return null;
  if (!geometry.boundingBox) {
    if (!(geometry.attributes.position?.array || geometry.attributes.position?.data?.array)) return null;
    geometry.computeBoundingBox();
  }
  if (!finiteBox(geometry.boundingBox)) return null;
  const bounds = new THREE.Box3(), matrix = new THREE.Matrix4(), rotation = new THREE.Quaternion();
  const position = new THREE.Vector3(), scale = new THREE.Vector3(), transformed = new THREE.Box3(), up = new THREE.Vector3(0, 1, 0);
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
    transformed.copy(geometry.boundingBox).applyMatrix4(matrix); bounds.union(transformed);
    // All nonzero seasonal scales are scalar contractions toward this anchor.
    // Including it contains the full interval [0,maxScale], including crowns
    // whose local geometry is above the origin. scale=0's makeScale(0) at world
    // origin creates only zero-area triangles, so no visible geometry is lost.
    bounds.expandByPoint(position.applyMatrix4(mesh.matrixWorld));
  }
  if (!finiteBox(bounds)) return null;
  // World-space shader displacement is bounded by 2m for production TG:
  // ordinary crown X <= .337m; willow hang + crown X <= 1.587m for gWind<=1.
  // Impostors are fixed crossed planes, not camera-facing vertex billboards.
  // Do not union the old 80m batch sphere: its horizontal spread inflated its
  // vertical extent too, forcing invisible trees through all renderer passes.
  return bounds.expandByScalar(windPadding + 1e-4);
}

export function createSceneSpatialIndex({ THREE, scene, treeGroups = [], treeScale, leafSize = 12, windPadding = 2 } = {}) {
  if (treeGroups.length && typeof treeScale !== 'function') throw new Error('treeScale must evaluate the production seasonal scale for all four seasons');
  const started = performance.now(), originalChildren = [...scene.children], members = new Map(), nodes = [];
  scene.updateMatrixWorld(true);
  const add = (mesh, bounds, kind) => {
    if (!eligible(mesh, scene) || !bounds || bounds.isEmpty() || members.has(mesh)) return;
    members.set(mesh, { mesh, bounds, center: bounds.getCenter(new THREE.Vector3()), kind });
  };
  for (const mesh of originalChildren) {
    const declaration = mesh.userData?.[STATIC_KEY];
    if (!declaration || !eligible(mesh, scene)) continue;
    const source = mesh.isInstancedMesh ? mesh.boundingSphere : mesh.geometry.boundingSphere;
    if (!finiteSphere(source)) continue;
    const sphere = source.clone().applyMatrix4(mesh.matrixWorld);
    const bounds = sphere.getBoundingBox(new THREE.Box3()).expandByScalar(declaration.padding);
    add(mesh, bounds, 'static');
  }
  for (const group of treeGroups) {
    for (const entry of [...group.near, ...group.far]) {
      for (const mesh of [entry.m, entry.rm]) {
        if (!eligible(mesh, scene)) continue;
        const bounds = treeEntryWorldBounds({ THREE, scene, group, entry, mesh, treeScale, windPadding });
        // TG entries override a generic mark: their mutable current instance
        // subset cannot certify a full-season bound.
        members.delete(mesh); add(mesh, bounds, 'tree');
      }
    }
  }
  const entries = [...members.values()], minimumLeaf = Math.max(2, leafSize | 0);
  function build(list, depth = 0) {
    const node = new THREE.Object3D(), bounds = new THREE.Box3();
    node.name = 'spatial-' + depth + '-' + nodes.length;
    node.matrixAutoUpdate = false; node.layers.enableAll();
    for (const entry of list) bounds.union(entry.bounds);
    node.userData[SPATIAL_BOUNDS_KEY] = bounds; node.userData.dgySpatialCount = list.length;
    nodes.push(node);
    if (list.length <= minimumLeaf) {
      for (const entry of list) node.add(entry.mesh);
    } else {
      const centers = new THREE.Box3(); for (const entry of list) centers.expandByPoint(entry.center);
      const extent = centers.getSize(new THREE.Vector3());
      const axis = extent.x >= extent.z && extent.x >= extent.y ? 'x' : extent.z >= extent.y ? 'z' : 'y';
      list.sort((a, b) => a.center[axis] - b.center[axis]);
      const middle = list.length >> 1;
      node.add(build(list.slice(0, middle), depth + 1), build(list.slice(middle), depth + 1));
    }
    return node;
  }
  // Object3D rather than Group: projectObject's groupOrder inheritance remains
  // unchanged. Identity ancestors also preserve every mesh's world transform.
  const root = entries.length > 1 ? build(entries) : null;
  if (root) scene.add(root);
  const certificates = new Map(nodes.map(node => [node, node.userData[SPATIAL_BOUNDS_KEY]])), priorLeafBounds = new Map();
  for (const entry of entries) if (entry.kind === 'tree') {
    const mesh = entry.mesh;
    priorLeafBounds.set(mesh, { had: Object.hasOwn(mesh.userData, SPATIAL_BOUNDS_KEY), value: mesh.userData[SPATIAL_BOUNDS_KEY] });
    certificates.set(mesh, entry.bounds); mesh.userData[SPATIAL_BOUNDS_KEY] = entry.bounds;
  }
  const volume = box => (box.max.x - box.min.x) * (box.max.y - box.min.y) * (box.max.z - box.min.z);
  let treeVolume = 0, legacyTreeSphereVolume = 0;
  for (const entry of entries) if (entry.kind === 'tree') {
    treeVolume += volume(entry.bounds);
    if (finiteSphere(entry.mesh.boundingSphere)) legacyTreeSphereVolume += volume(entry.mesh.boundingSphere.clone().applyMatrix4(entry.mesh.matrixWorld).getBoundingBox(new THREE.Box3()));
  }
  const stats = {
    members: root ? entries.length : 0, trees: root ? entries.filter(e => e.kind === 'tree').length : 0,
    static: root ? entries.filter(e => e.kind === 'static').length : 0,
    nodes: nodes.length, rootChildrenBefore: originalChildren.length, rootChildrenAfter: scene.children.length,
    treeLeafCertificates: priorLeafBounds.size, treeVolume, legacyTreeSphereVolume, buildMs: performance.now() - started,
  };
  let enabled = true;
  const invalid = new Set(), listeners = [];
  function invalidate(object = root) {
    if (!object) { for (const target of certificates.keys()) { invalid.add(target); target.userData[SPATIAL_BOUNDS_KEY] = null; } return; }
    // Call this after a deliberate future edit to static geometry/transforms or
    // before animating a registered leaf. Reparenting and child edits below are
    // detected automatically. Fail open at the leaf AND along its ancestor path.
    object.traverse(o => { if (certificates.has(o)) { invalid.add(o); o.userData[SPATIAL_BOUNDS_KEY] = null; } });
    for (let node = object; node; node = node.parent) {
      if (certificates.has(node)) { invalid.add(node); node.userData[SPATIAL_BOUNDS_KEY] = null; }
      if (node === root) break;
    }
  }
  for (const object of [...nodes, ...entries.map(e => e.mesh)]) {
    const changed = () => invalidate(object);
    for (const event of ['childadded', 'childremoved', 'added', 'removed']) {
      object.addEventListener(event, changed); listeners.push([object, event, changed]);
    }
  }
  return {
    root, nodes, stats, entries, invalidate,
    get enabled() { return enabled; },
    set enabled(value) { enabled = !!value; for (const [object, box] of certificates) object.userData[SPATIAL_BOUNDS_KEY] = enabled && !invalid.has(object) ? box : null; },
    dispose() {
      for (const [object, event, changed] of listeners) object.removeEventListener(event, changed);
      for (const [mesh, prior] of priorLeafBounds) {
        if (prior.had) mesh.userData[SPATIAL_BOUNDS_KEY] = prior.value; else delete mesh.userData[SPATIAL_BOUNDS_KEY];
      }
      enabled = false;
      if (!root) return;
      for (const entry of entries) {
        let p = entry.mesh.parent; while (p && p !== root) p = p.parent;
        if (p === root) scene.add(entry.mesh);
      }
      root.removeFromParent();
      const order = new Map(originalChildren.map((child, i) => [child, i]));
      scene.children.sort((a, b) => (order.get(a) ?? Infinity) - (order.get(b) ?? Infinity));
      for (const node of nodes) node.userData[SPATIAL_BOUNDS_KEY] = null;
    },
  };
}
