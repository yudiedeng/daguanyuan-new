// Far spatial batching for explicitly static instances. Vertices are never
// expanded; matrices/colours are concatenated once. By default geometry is
// unchanged. Optional audited geometryLODs carry a local Hausdorff error bound;
// the complete cluster must stay below maxGeometryPixels before using one.
export function cylinderRadialError(radius, nearSegments, farSegments) {
  // Both regular polygon sections lie between the same circle and their
  // inscribed circles. End planes/length stay identical. This bounds radial
  // correspondence for side surfaces and caps, even for non-nested polygons.
  if (!(radius > 0) || !Number.isInteger(nearSegments) || !Number.isInteger(farSegments) || nearSegments < 3 || farSegments < 3) return Infinity;
  return radius * (1 - Math.cos(Math.PI / Math.min(nearSegments, farSegments)));
}
export function createStaticInstanceHLOD({ THREE, scene, meshes, markStatic, cellSize = 64, minTiles = 3, minDistance = 110, maxPixels = 450, padding = 0.5,
  geometryLODs = new Map(), maxGeometryPixels = 0.5 }) {
  const groups = new Map(), records = [], matrix = new THREE.Matrix4(), worldMatrix = new THREE.Matrix4(), temp = new THREE.Box3(), point = new THREE.Vector3(), center = new THREE.Vector3(), color = new THREE.Color();
  const stats = { sourceTiles: 0, clusters: 0, activeClusters: 0, savedDraws: 0, instanceBytes: 0, switches: 0, invalidated: 0,
    simplifiedClusters: 0, activeSimplifiedClusters: 0, savedTriangles: 0, maxActiveErrorPixels: 0 };
  const equal = (a, b) => a.every((v, i) => v === b[i]);
  const triangles = geometry => (geometry.index?.count || geometry.attributes.position.count) / 3;
  for (const mesh of meshes) {
    if (!mesh.isInstancedMesh || !mesh.count || Array.isArray(mesh.material) || mesh.visible === false || mesh.onBeforeRender !== THREE.Object3D.prototype.onBeforeRender) continue;
    mesh.updateWorldMatrix(true, false);
    if (!mesh.boundingBox) mesh.computeBoundingBox();
    const bounds = mesh.boundingBox.clone().applyMatrix4(mesh.matrixWorld); bounds.getCenter(center);
    const key = [mesh.geometry.uuid, mesh.material.uuid, mesh.layers.mask, mesh.castShadow, mesh.receiveShadow, mesh.renderOrder,
      mesh.customDepthMaterial?.uuid, mesh.customDistanceMaterial?.uuid, !!mesh.instanceColor, Math.floor(center.x / cellSize), Math.floor(center.z / cellSize)].join('|');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push({ mesh, bounds, matrix: mesh.matrixWorld.elements.slice(), geometry: mesh.geometry, material: mesh.material,
      position: mesh.geometry.attributes.position, positionVersion: (mesh.geometry.attributes.position.data || mesh.geometry.attributes.position).version,
      index: mesh.geometry.index, indexVersion: mesh.geometry.index?.version, layers: mesh.layers.mask, castShadow: mesh.castShadow, receiveShadow: mesh.receiveShadow,
      count: mesh.count, matrixVersion: mesh.instanceMatrix.version, color: mesh.instanceColor, colorVersion: mesh.instanceColor?.version });
  }
  for (const list of groups.values()) {
    const source = list[0].mesh, declaration = geometryLODs.get(source.geometry);
    const lod = declaration?.geometry?.isBufferGeometry && Number.isFinite(declaration.maxLocalError) && declaration.maxLocalError >= 0 &&
      triangles(declaration.geometry) < triangles(source.geometry) ? declaration : null;
    if (list.length < minTiles && !lod) continue;
    const count = list.reduce((n, q) => n + q.count, 0), far = new THREE.InstancedMesh(lod?.geometry || source.geometry, source.material, count);
    far.name = lod ? 'HLOD·' + (lod.name || '静态构件') : 'HLOD·静态石群'; far.castShadow = source.castShadow; far.receiveShadow = source.receiveShadow; far.layers.mask = source.layers.mask;
    far.renderOrder = source.renderOrder; far.customDepthMaterial = source.customDepthMaterial; far.customDistanceMaterial = source.customDistanceMaterial;
    far.frustumCulled = true; far.visible = false; let offset = 0, maxWorldError = 0;
    for (const q of list) for (let i = 0; i < q.count; i++) {
      q.mesh.getMatrixAt(i, matrix); worldMatrix.multiplyMatrices(q.mesh.matrixWorld, matrix); far.setMatrixAt(offset, worldMatrix);
      if (lod) {
        // Frobenius norm bounds the largest singular value, including shear,
        // nonuniform scale and negative scale; never assume unit instances.
        const e = worldMatrix.elements, stretch = Math.hypot(e[0], e[1], e[2], e[4], e[5], e[6], e[8], e[9], e[10]);
        maxWorldError = Math.max(maxWorldError, lod.maxLocalError * stretch);
      }
      if (source.instanceColor) { q.mesh.getColorAt(i, color); far.setColorAt(offset, color); } offset++;
    }
    far.instanceMatrix.needsUpdate = true; if (far.instanceColor) far.instanceColor.needsUpdate = true;
    far.computeBoundingBox();
    // The certificate encloses BOTH authored and simplified surfaces, including
    // all instance transforms. It is fixed before spatial/occlusion registration.
    for (const q of list) far.boundingBox.union(q.bounds);
    far.boundingSphere = far.boundingBox.getBoundingSphere(new THREE.Sphere()); far.boundingSphere.radius += padding;
    const bounds = far.boundingBox.clone().expandByScalar(padding);
    scene.add(far); markStatic?.(far, { padding });
    records.push({ list, far, bounds, active: false, valid: true, maxWorldError, simplified: !!lod,
      savedTriangles: count * (triangles(source.geometry) - triangles(far.geometry)) });
    if (lod) stats.simplifiedClusters++;
    stats.sourceTiles += list.length; stats.instanceBytes += count * (source.instanceColor ? 76 : 64);
  }
  stats.clusters = records.length;
  function valid(r) {
    return r.list.every(q => q.mesh.parent && q.mesh.visible === !r.active && q.mesh.geometry === q.geometry && q.mesh.material === q.material && q.mesh.count === q.count &&
      q.mesh.geometry.attributes.position === q.position && (q.position.data || q.position).version === q.positionVersion && q.geometry.index === q.index && q.index?.version === q.indexVersion &&
      q.mesh.layers.mask === q.layers && q.mesh.castShadow === q.castShadow && q.mesh.receiveShadow === q.receiveShadow &&
      q.mesh.instanceMatrix.version === q.matrixVersion && q.mesh.instanceColor === q.color && q.mesh.instanceColor?.version === q.colorVersion && equal(q.mesh.matrixWorld.elements, q.matrix));
  }
  function update(camera, { height = 900 } = {}) {
    camera.updateMatrixWorld(); point.setFromMatrixPosition(camera.matrixWorld);
    stats.activeClusters = stats.savedDraws = stats.activeSimplifiedClusters = stats.savedTriangles = stats.maxActiveErrorPixels = 0;
    const focal = height * Math.abs(camera.projectionMatrix.elements[5]) * 0.5;
    const maxFocal = height * Math.max(Math.abs(camera.projectionMatrix.elements[5]), Math.abs(camera.projectionMatrix.elements[0]) * (camera.aspect || 1)) * 0.5;
    for (const r of records) {
      if (r.valid && !valid(r)) { r.valid = false; stats.invalidated++; }
      const distance = r.bounds.distanceToPoint(point), sphere = r.far.boundingSphere;
      center.copy(sphere.center).applyMatrix4(camera.matrixWorldInverse);
      const depth = -center.z - sphere.radius;
      const pixels = depth > camera.near ? 2 * sphere.radius * focal / depth : Infinity;
      // Perspective displacement includes the change in depth, not only x/y.
      // For p and p+delta with |delta|<=error, the full cluster's nearest depth
      // and furthest transverse coordinate bound both screen components.
      const error = r.maxWorldError, errorPixels = !r.simplified ? 0 : camera.isPerspectiveCamera && depth > camera.near + error ?
        maxFocal * error / (depth - error) * (1 + (Math.hypot(center.x, center.y) + sphere.radius) / depth) : Infinity;
      const active = r.valid && height > 0 && distance > minDistance * (r.active ? 0.85 : 1) && pixels < maxPixels * (r.active ? 1.12 : 1) &&
        errorPixels < maxGeometryPixels * (r.active ? 1 : 0.8);
      if (active !== r.active) {
        for (const q of r.list) q.mesh.visible = !active;
        r.far.visible = active; r.active = active; stats.switches++;
      }
      if (active) {
        stats.activeClusters++; stats.savedDraws += r.list.length - 1; stats.savedTriangles += r.savedTriangles;
        if (r.simplified) stats.activeSimplifiedClusters++;
        stats.maxActiveErrorPixels = Math.max(stats.maxActiveErrorPixels, errorPixels);
      }
    }
    return stats;
  }
  return { update, stats, restore() { for (const r of records) { if (r.active) for (const q of r.list) q.mesh.visible = true; r.far.removeFromParent(); r.far.dispose(); } records.length = 0; stats.activeClusters = stats.savedDraws = 0; } };
}
