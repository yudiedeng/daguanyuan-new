// Far courtyard HLOD. The offline assets preserve material/UV/colour semantics;
// runtime selects them by projected additional simplification error in pixels.
export const HLOD_BUILDINGS = new Set(['daguan', 'daoxiang', 'longcui', 'ouxiang', 'qinfang', 'qiushuang', 'tubi', 'xiaoxiang', 'xiaoxiang_ct', 'yihong', 'hengwu', 'gate', 'cuizhang', 'luxue', 'aojing', 'daoxiang_tian']);

export function attachBuildingHLOD({ THREE, building, hlod }) {
  if (!building.hi || !hlod?.userData.dgyHLOD || !(hlod.userData.dgyHLOD.maxError >= 0))
    throw new Error('HLOD requires the original hi branch and an audited offline asset.');
  if (building.hlod) throw new Error('HLOD already attached.');
  const source = building.lo || null;
  if (source) {
    // b.lo remains the branch selected by the existing reflection save/restore
    // code. Its children select ordinary LOD versus the farther HLOD.
    const container = new THREE.Group(); container.name = 'lo';
    container.visible = source.visible; source.name = 'lo-detail'; source.visible = true;
    container.add(source, hlod); building.root.add(container); building.lo = container;
  } else {
    building.root.add(hlod); building.lo = hlod;
  }
  hlod.name = 'hlod'; hlod.visible = false;
  building.hlod = hlod; building.hlodSource = source;
  building.hlodError = hlod.userData.dgyHLOD.maxError;
  return building;
}

// Conservative perspective amplification: account for the closest box depth
// and its off-axis extent, rather than only distance to a courtyard centre.
export function projectedHLODError({ THREE, box, camera, height, worldError }) {
  if (!Number.isFinite(height) || height <= 0 || !Number.isFinite(worldError) || worldError < 0 || box.isEmpty()) return Infinity;
  const center = box.getCenter(new THREE.Vector3()), extent = box.getSize(new THREE.Vector3()).multiplyScalar(0.5);
  const e = camera.matrixWorldInverse.elements; center.applyMatrix4(camera.matrixWorldInverse);
  const x = Math.abs(e[0]) * extent.x + Math.abs(e[4]) * extent.y + Math.abs(e[8]) * extent.z;
  const y = Math.abs(e[1]) * extent.x + Math.abs(e[5]) * extent.y + Math.abs(e[9]) * extent.z;
  const z = Math.abs(e[2]) * extent.x + Math.abs(e[6]) * extent.y + Math.abs(e[10]) * extent.z;
  const depth = -center.z - z - worldError;
  if (depth <= Math.max(camera.near || 0, 0.01)) return Infinity;
  const focal = height * Math.abs(camera.projectionMatrix.elements[5]) * 0.5;
  if (camera.isOrthographicCamera) return worldError * focal;
  return worldError * focal / depth * (1 + Math.max(Math.abs(center.x) + x, Math.abs(center.y) + y) / depth);
}

export function createBuildingHLODController({ THREE, buildings, pixelBudgets = [1.6, 1.15, 0.85], nearDistance = 70, getLegacyDistance }) {
  const records = new Map(), point = new THREE.Vector3(), local = new THREE.Box3(), inverse = new THREE.Matrix4(), sphere = new THREE.Sphere();
  const stats = { hi: 0, lo: 0, hlod: 0, switches: 0, maxProjectedError: 0, candidates: 0 };
  function record(building) {
    let r = records.get(building);
    if (r) return r;
    building.root.updateWorldMatrix(true, true);
    inverse.copy(building.root.matrixWorld).invert();
    const box = new THREE.Box3();
    building.hi.traverse(mesh => {
      if (!mesh.isMesh || !mesh.geometry?.attributes.position) return;
      if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
      local.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld).applyMatrix4(inverse); box.union(local);
    });
    r = { local: box, world: new THREE.Box3(), far: false, level: 'hi' }; records.set(building, r); return r;
  }
  function update(camera, { height = 900, quality = 2 } = {}) {
    camera.updateMatrixWorld(); point.setFromMatrixPosition(camera.matrixWorld);
    stats.hi = stats.lo = stats.hlod = stats.maxProjectedError = stats.candidates = 0;
    const budget = pixelBudgets[Math.max(0, Math.min(2, quality | 0))];
    for (const b of buildings) {
      if (!b.hi || !b.lo) continue;
      const r = record(b); b.root.updateWorldMatrix(true, false);
      r.world.copy(r.local).applyMatrix4(b.root.matrixWorld);
      const distance = r.world.distanceToPoint(point);
      let level;
      if (b.hlod) {
        stats.candidates++;
        const e = b.root.matrixWorld.elements;
        const scale = Math.max(Math.hypot(e[0], e[1], e[2]), Math.hypot(e[4], e[5], e[6]), Math.hypot(e[8], e[9], e[10]));
        const pixels = projectedHLODError({ THREE, box: r.world, camera, height, worldError: b.hlodError * scale });
        const far = distance > nearDistance * (r.far ? 0.85 : 1) && pixels <= budget * (r.far ? 1.12 : 1);
        r.far = far;
        if (far) { level = 'hlod'; stats.maxProjectedError = Math.max(stats.maxProjectedError, pixels); }
        else if (!b.hlodSource) level = 'hi';
      }
      if (!level) {
        const legacyDistance = getLegacyDistance ? getLegacyDistance(b, camera) : (r.world.getBoundingSphere(sphere), point.distanceTo(sphere.center) - sphere.radius);
        level = legacyDistance > (b.hi.visible ? 55 : 45) ? 'lo' : 'hi';
      }
      b.hi.visible = level === 'hi'; b.lo.visible = level !== 'hi';
      if (b.hlodSource) { b.hlodSource.visible = level !== 'hlod'; b.hlod.visible = level === 'hlod'; }
      if (level !== r.level) { stats.switches++; r.level = level; }
      stats[level]++;
    }
    return stats;
  }
  return { update, stats, invalidate(building) { if (building) records.delete(building); else records.clear(); } };
}
