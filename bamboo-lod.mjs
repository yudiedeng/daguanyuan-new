import { projectedHLODError } from './building-hlod.mjs';

// Only bamboo culms opt in. Leaves, instance transforms, colour, materials and
// wind shaders are unchanged. Each spatial batch owns a tiny geometry wrapper;
// all batches of a variant share the exact attributes and combined index buffer.
export function createBambooLODController({ THREE, pixelBudgets = [0.9, 0.7, 0.55], minDistance = 45, windErrorMultiplier = 3 }) {
  const entries = [], buffers = new WeakMap(), matrix = new THREE.Matrix4(), world = new THREE.Box3(), temp = new THREE.Box3(), point = new THREE.Vector3();
  const stats = { batches: 0, near: 0, far: 0, fullTriangles: 0, selectedTriangles: 0, savedTriangles: 0, maxProjectedError: 0, switches: 0 };
  function register(mesh, lod) {
    const source = mesh.geometry, p = source?.attributes.position;
    if (!mesh.isInstancedMesh || !lod || lod.vertices !== p?.count || !Number.isFinite(lod.error) || lod.error < 0) return false;
    const oldCount = source.index?.count ?? p.count;
    if (oldCount !== lod.inputTriangles * 3 || !Array.isArray(lod.indices) || lod.indices.length !== lod.outputTriangles * 3 || lod.indices.length >= oldCount ||
      lod.indices.some(i => !Number.isInteger(i) || i < 0 || i >= p.count)) return false;
    let index = buffers.get(source);
    if (!index) {
      const array = new (p.count > 65535 ? Uint32Array : Uint16Array)(oldCount + lod.indices.length);
      for (let i = 0; i < oldCount; i++) array[i] = source.index ? source.index.getX(i) : i;
      array.set(lod.indices, oldCount); index = new THREE.BufferAttribute(array, 1); buffers.set(source, index);
    }
    if (!source.boundingBox) source.computeBoundingBox();
    if (!source.boundingSphere) source.computeBoundingSphere();
    const geometry = new THREE.BufferGeometry();
    for (const [name, a] of Object.entries(source.attributes)) geometry.setAttribute(name, a);
    geometry.setIndex(index); geometry.boundingBox = source.boundingBox.clone(); geometry.boundingSphere = source.boundingSphere.clone();
    geometry.setDrawRange(0, oldCount); mesh.geometry = geometry;
    const bounds = new THREE.Box3(); let maxScale = 0;
    for (let i = 0; i < mesh.count; i++) { mesh.getMatrixAt(i, matrix); bounds.union(temp.copy(source.boundingBox).applyMatrix4(matrix)); maxScale = Math.max(maxScale, matrix.getMaxScaleOnAxis()); }
    bounds.expandByScalar(2);
    entries.push({ mesh, geometry, source, bounds, error: lod.error * maxScale * windErrorMultiplier, oldCount, lowCount: lod.indices.length, far: false });
    stats.batches = entries.length;
    mesh.userData.dgyBambooLOD = true;
    return true;
  }
  function update(camera, { height = 900, quality = 2 } = {}) {
    camera.updateMatrixWorld(); point.setFromMatrixPosition(camera.matrixWorld);
    const budget = pixelBudgets[Math.max(0, Math.min(2, quality | 0))];
    stats.near = stats.far = stats.fullTriangles = stats.selectedTriangles = stats.maxProjectedError = 0;
    for (const e of entries) {
      world.copy(e.bounds).applyMatrix4(e.mesh.matrixWorld);
      const pixels = projectedHLODError({ THREE, box: world, camera, height, worldError: e.error * e.mesh.matrixWorld.getMaxScaleOnAxis() });
      const far = world.distanceToPoint(point) > minDistance * (e.far ? 0.85 : 1) && pixels <= budget * (e.far ? 1.12 : 1);
      if (far !== e.far) { stats.switches++; e.far = far; e.geometry.setDrawRange(far ? e.oldCount : 0, far ? e.lowCount : e.oldCount); }
      const count = e.mesh.count; stats.fullTriangles += count * e.oldCount / 3;
      stats.selectedTriangles += count * (far ? e.lowCount : e.oldCount) / 3;
      stats[far ? 'far' : 'near']++; if (far) stats.maxProjectedError = Math.max(stats.maxProjectedError, pixels);
    }
    stats.savedTriangles = stats.fullTriangles - stats.selectedTriangles;
    return stats;
  }
  return { register, update, stats, restore() { for (const e of entries) { e.mesh.geometry = e.source; e.geometry.dispose(); } entries.length = 0; stats.batches = 0; } };
}
