// A certificate covers an entire axis-aligned eye cell, not an old camera frame.
// For a fixed ray direction, its intersection with one plane is affine in the
// eye position. All eight cell corners hitting the SAME convex triangle proves
// that every eye in the cell hits it. Independent scene-depth maps at the eight
// corners do NOT have that property (different pillars can hide only corners).
//
// Geometry returned here is already in WebGL NDC. Render with
// gl_Position=vec4(position,1.0), no transform, no culling, no blending, full
// viewport, ordinary >=24-bit depth, and no MSAA. Source: depthWrite=true;
// target: depthWrite=false. Both: depthTest=true, LessEqualDepth. The source
// covers whole pixel ray bundles and writes far depth; targets cover every
// intersected pixel and write near depth. Query false is consequently a
// continuous geometric proof, independent of the main camera's sampling.
const materialList = o => Array.isArray(o.material) ? o.material : [o.material];
const attrVersion = a => (a?.data || a)?.version;
const equal16 = (a, b) => a.every((v, i) => v === b[i]);
const finiteBox = b => b?.isBox3 && !b.isEmpty() && [...b.min, ...b.max].every(Number.isFinite);
const boxValues = b => [...b.min, ...b.max];
const now = () => performance.now();
function opaque(T, m) {
  return !!m && m.visible !== false && !m.transparent && m.opacity === 1 && !(m.alphaTest > 0) &&
    !m.alphaMap && !m.alphaHash && !m.alphaToCoverage && !m.wireframe && !m.displacementMap && !(m.transmission > 0) &&
    m.depthWrite !== false && m.depthTest !== false && m.colorWrite !== false && !m.stencilWrite && !m.polygonOffset &&
    m.depthFunc === T.LessEqualDepth && m.blending === T.NormalBlending && !m.clippingPlanes?.length &&
    !m.isShaderMaterial && !m.isRawShaderMaterial && [T.FrontSide, T.BackSide, T.DoubleSide].includes(m.side) &&
    (m.userData?.dgyOcclusionStaticSurface || m.onBeforeCompile === T.Material.prototype.onBeforeCompile && !m.userData?.shadowDynamic);
}
function shown(mesh, mask) {
  if (!(mesh.layers.mask & mask)) return false;
  for (let p = mesh; p; p = p.parent) if (!p.visible) return false;
  return true;
}
function currentRecord(T, r, registry = r.registry) {
  const m = r.mesh, g = m.geometry;
  return registry.isCurrent(m) && g === r.geometry && g.attributes.position === r.position && g.index === r.index &&
    attrVersion(r.position) === r.positionVersion && attrVersion(r.index) === r.indexVersion && r.position.count === r.positionCount && r.index?.count === r.indexCount &&
    g.drawRange.start === r.drawStart && g.drawRange.count === r.drawCount && JSON.stringify(g.groups) === r.groups &&
    equal16(m.matrixWorld.elements, r.matrix) && m.onBeforeRender === T.Object3D.prototype.onBeforeRender &&
    !m.userData.dynamic && !m.animations?.length && materialList(m).length === r.materials.length &&
    materialList(m).every((mat, i) => mat === r.materials[i].material && mat.side === r.materials[i].side &&
      mat.onBeforeCompile === r.materials[i].compile && opaque(T, mat));
}
function largest(heap, item, limit) {
  if (!limit) return;
  if (heap.length < limit) {
    let i = heap.length; heap.push(item);
    while (i) { const p = (i - 1) >> 1; if (heap[p].area <= item.area) break; heap[i] = heap[p]; i = p; }
    heap[i] = item;
  } else if (item.area > heap[0].area) {
    let i = 0;
    while (i * 2 + 1 < heap.length) {
      let c = i * 2 + 1; if (c + 1 < heap.length && heap[c + 1].area < heap[c].area) c++;
      if (heap[c].area >= item.area) break; heap[i] = heap[c]; i = c;
    }
    heap[i] = item;
  }
}
function* extract({ THREE: T, registry, maxFaces = 8192, maxFacesPerMesh = 16, minTriangleArea = .5 } = {}) {
  if (!T || !registry?.occluders || typeof registry.isCurrent !== 'function') throw new Error('THREE and certified registry required');
  const start = now(), heaps = [[], [], []], a = new T.Vector3(), b = new T.Vector3(), c = new T.Vector3(), n = new T.Vector3(), e = new T.Vector3();
  const stats = { examinedTriangles: 0, sourceMeshes: 0, faces: 0, prepareMs: 0 };
  const perAxis = Math.max(0, Math.ceil(maxFaces / 3));
  for (const mesh of registry.occluders) {
    if (!registry.isCurrent(mesh) || !mesh.isMesh || mesh.isInstancedMesh || mesh.isSkinnedMesh || mesh.isBatchedMesh ||
      mesh.children.length || mesh.animations?.length || mesh.userData.dynamic || mesh.onBeforeRender !== T.Object3D.prototype.onBeforeRender) continue;
    const g = mesh.geometry, p = g?.attributes.position, ix = g?.index, ms = materialList(mesh);
    if (!p || p.isGLBufferAttribute || !(p.array || p.data?.array) || g.isInstancedBufferGeometry || Object.keys(g.morphAttributes || {}).length || !ms.every(m => opaque(T, m))) continue;
    const determinant = mesh.matrixWorld.determinant(); if (!Number.isFinite(determinant) || Math.abs(determinant) < 1e-12) continue;
    const r = { mesh, registry, geometry: g, position: p, index: ix, positionVersion: attrVersion(p), indexVersion: attrVersion(ix), positionCount: p.count, indexCount: ix?.count,
      drawStart: g.drawRange.start, drawCount: g.drawRange.count, groups: JSON.stringify(g.groups), matrix: mesh.matrixWorld.elements.slice(),
      determinantSign: determinant < 0 ? -1 : 1, materials: ms.map(material => ({ material, side: material.side, compile: material.onBeforeCompile })) };
    const total = ix?.count ?? p.count, local = [[], [], []], groups = Array.isArray(mesh.material) ? g.groups : [{ start: 0, count: total, materialIndex: 0 }];
    for (const group of groups) {
      const from = Math.max(r.drawStart, group.start), to = Math.min(total, r.drawStart + r.drawCount, group.start + group.count);
      if (from % 3 || to % 3 || !ms[group.materialIndex]) continue;
      for (let i = from; i + 2 < to; i += 3) {
        if (++stats.examinedTriangles % 1024 === 0) yield null;
        a.fromBufferAttribute(p, ix ? ix.getX(i) : i).applyMatrix4(mesh.matrixWorld);
        b.fromBufferAttribute(p, ix ? ix.getX(i + 1) : i + 1).applyMatrix4(mesh.matrixWorld);
        c.fromBufferAttribute(p, ix ? ix.getX(i + 2) : i + 2).applyMatrix4(mesh.matrixWorld);
        n.subVectors(b, a).cross(e.subVectors(c, a)); const area = n.length() * .5;
        if (!(area >= minTriangleArea) || !Number.isFinite(area)) continue;
        const axis = Math.abs(n.x) >= Math.abs(n.y) && Math.abs(n.x) >= Math.abs(n.z) ? 0 : Math.abs(n.y) >= Math.abs(n.z) ? 1 : 2;
        if (local[axis].length >= maxFacesPerMesh && area <= (local[axis][0]?.area ?? Infinity)) continue;
        largest(local[axis], { record: r, materialIndex: group.materialIndex, area, axis,
          vertices: new Float64Array([...a, ...b, ...c]), normal: n.clone().normalize(), constant: -n.clone().normalize().dot(a),
          bounds: new T.Box3().setFromPoints([a, b, c]) }, maxFacesPerMesh);
      }
    }
    local.forEach(h => h.sort((a, b) => b.area - a.area)); let kept = 0;
    for (let i = 0; kept < maxFacesPerMesh; i++) {
      let any = false;
      for (let axis = 0; axis < 3 && kept < maxFacesPerMesh; axis++) if (local[axis][i]) { largest(heaps[axis], local[axis][i], perAxis); kept++; any = true; }
      if (!any) break;
    }
    stats.sourceMeshes++; yield null;
  }
  heaps.forEach(h => h.sort((a, b) => b.area - a.area)); const faces = [];
  for (let i = 0; faces.length < maxFaces; i++) { let any = false; for (const h of heaps) if (h[i] && faces.length < maxFaces) { faces.push(h[i]); any = true; } if (!any) break; }
  // Index actual triangle bounds, never solid approximations of their boxes.
  // A bucket sorted by world area can spend the entire cell budget on distant
  // roofs before reaching a small nearby wall in the same bucket. This BVH
  // permits best-first projected-area ranking across the whole source pool.
  const spatialIndex = { cells: new Map(), large: [], root: null }; let indexed = 0;
  function* node(items) {
    const bounds = new T.Box3(), centers = new T.Box3(), point = new T.Vector3(); let maxArea = 0;
    for (const face of items) { bounds.union(face.bounds); centers.expandByPoint(face.bounds.getCenter(point)); maxArea = Math.max(maxArea, face.area); }
    if (++indexed % 64 === 0) yield null;
    if (items.length <= 8) return { bounds, maxArea, faces: items };
    const size = centers.getSize(point), axis = size.x >= size.y && size.x >= size.z ? 'x' : size.y >= size.z ? 'y' : 'z';
    items.sort((a, b) => a.bounds.min[axis] + a.bounds.max[axis] - b.bounds.min[axis] - b.bounds.max[axis]);
    const mid = items.length >> 1;
    return { bounds, maxArea, left: yield* node(items.slice(0, mid)), right: yield* node(items.slice(mid)) };
  }
  if (faces.length) spatialIndex.root = yield* node(faces.slice());
  faces.spatialIndex = spatialIndex;
  stats.faces = faces.length; stats.prepareMs = now() - start; return { faces, stats };
}
export function collectMovingOcclusionFaces(options) {
  const it = extract(options); let step; do { step = it.next(); } while (!step.done); return step.value;
}
export async function prepareMovingOcclusionFaces(options, { budgetMs = 8, yieldFrame = () => new Promise(resolve => setTimeout(resolve, 0)) } = {}) {
  const it = extract(options); let step, start = now();
  do { step = it.next(); if (!step.done && now() - start >= budgetMs) { await yieldFrame(); start = now(); } } while (!step.done);
  return step.value;
}
function clip(poly, A, B, C) {
  const out = []; let prev = poly[poly.length - 1], d0 = A * prev[0] + B * prev[1] + C;
  for (const point of poly) {
    const d1 = A * point[0] + B * point[1] + C;
    if ((d0 >= 0) !== (d1 >= 0)) {
      const t = d0 / (d0 - d1); out.push([prev[0] + t * (point[0] - prev[0]), prev[1] + t * (point[1] - prev[1])]);
    }
    if (d1 >= 0) out.push(point); prev = point; d0 = d1;
  }
  return out;
}
function area2(poly) { let sum = 0; for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) sum += poly[j][0] * poly[i][1] - poly[i][0] * poly[j][1]; return Math.abs(sum); }
const depthNDC = (camera, depth) => -camera.projectionMatrix.elements[10] + camera.projectionMatrix.elements[14] / depth;
function nearRadius(T, camera) {
  if (!camera?.isPerspectiveCamera || camera.coordinateSystem !== T.WebGLCoordinateSystem ||
    !camera.projectionMatrix.elements.every(Number.isFinite) || !camera.matrixWorld.elements.every(Number.isFinite)) return Infinity;
  const projection = camera.projectionMatrix;
  if (Math.abs(projection.determinant()) < 1e-12) return Infinity;
  const inverse = new T.Matrix4().copy(projection).invert().premultiply(camera.matrixWorld);
  const eye = new T.Vector3().setFromMatrixPosition(camera.matrixWorld), p = new T.Vector3(); let radius = 0;
  for (const x of [-1, 1]) for (const y of [-1, 1]) {
    p.set(x, y, -1).applyMatrix4(inverse); if (![...p].every(Number.isFinite)) return Infinity;
    radius = Math.max(radius, p.distanceTo(eye));
  }
  return radius + Math.max(1e-4, radius * 1e-6);
}
function geometryFrom(T, positions, geometry) {
  const data = new Float32Array(positions);
  if (!geometry) geometry = new T.BufferGeometry();
  const attr = geometry.getAttribute('position');
  if (attr?.array.length === data.length) { attr.array.set(data); attr.needsUpdate = true; }
  else geometry.setAttribute('position', new T.BufferAttribute(data, 3));
  geometry.setIndex(null); geometry.setDrawRange(0, data.length / 3); return geometry;
}
function* nearbyFaces(faces, center, distance, frustum, stopped) {
  const index = faces.spatialIndex;
  if (!index?.root) { yield* faces; return; }
  const queue = [];
  function add(value, face = false) {
    const d = value.bounds.distanceToPoint(center);
    if (d > distance || !frustum.intersectsBox(value.bounds)) return;
    // A node's nearest distance and largest face area give an upper bound
    // for every descendant's ranking, allowing globally ordered traversal.
    const entry = { value, face, score: (face ? value.area : value.maxArea) / Math.max(1, d * d) };
    let i = queue.length; queue.push(entry);
    while (i) { const p = (i - 1) >> 1; if (queue[p].score >= entry.score) break; queue[i] = queue[p]; i = p; } queue[i] = entry;
  }
  add(index.root);
  while (queue.length && !stopped()) {
    const entry = queue[0], last = queue.pop();
    if (queue.length) {
      let i = 0;
      while (i * 2 + 1 < queue.length) {
        let child = i * 2 + 1; if (child + 1 < queue.length && queue[child + 1].score > queue[child].score) child++;
        if (queue[child].score <= last.score) break; queue[i] = queue[child]; i = child;
      }
      queue[i] = last;
    }
    if (entry.face) yield entry.value;
    else if (entry.value.faces) for (const face of entry.value.faces) add(face, true);
    else { add(entry.value.left); add(entry.value.right); }
  }
}

export function buildMovingOcclusionCertificate({ THREE: T, faces, camera, width = 256, height = 144, halfExtent = .6,
  center: suppliedCenter, referenceFov = 90, referenceNear = .05, referenceFar = 4000, maxFaces = 512,
  maxSourceDistance = 120, maxBuildMs = 3, depthEpsilonNdc = 4e-6, pixelGuard = .01, clock = now } = {}) {
  if (!T || !Array.isArray(faces) || !camera?.isPerspectiveCamera) return null;
  if (!(width > 0 && height > 0 && Number.isInteger(width) && Number.isInteger(height) && referenceFov > 0 && referenceFov < 170 && referenceNear > 0 && referenceFar > referenceNear && pixelGuard >= .001 && depthEpsilonNdc >= 2e-6)) return null;
  const start = clock(), mainNearRadius = nearRadius(T, camera), center = suppliedCenter?.clone() || new T.Vector3().setFromMatrixPosition(camera.matrixWorld);
  if (!Number.isFinite(mainNearRadius)) return null;
  const half = typeof halfExtent === 'number' ? new T.Vector3(halfExtent, halfExtent, halfExtent) : halfExtent?.clone();
  if (!half || ![...center, ...half].every(Number.isFinite) || Math.min(...half) < 0) return null;
  const cell = new T.Box3(center.clone().sub(half), center.clone().add(half));
  const referenceCamera = new T.PerspectiveCamera(referenceFov, width / height, referenceNear, referenceFar);
  referenceCamera.position.copy(center); camera.getWorldQuaternion(referenceCamera.quaternion); referenceCamera.layers.mask = camera.layers.mask; referenceCamera.updateMatrixWorld(true);
  const corners = [], offset = new T.Vector3(), vertex = new T.Vector3(), forward = new T.Vector3(0, 0, -1).applyQuaternion(referenceCamera.quaternion);
  for (let i = 0; i < 8; i++) corners.push(new T.Vector3(i & 1 ? cell.max.x : cell.min.x, i & 2 ? cell.max.y : cell.min.y, i & 4 ? cell.max.z : cell.min.z));
  const extraDepth = Math.abs(forward.x) * half.x + Math.abs(forward.y) * half.y + Math.abs(forward.z) * half.z;
  const fx = referenceCamera.projectionMatrix.elements[0] * width / 2, fy = referenceCamera.projectionMatrix.elements[5] * height / 2;
  const stats = { considered: 0, testedFaces: 0, coveredFaces: 0, sourceMeshes: 0, budgetExhausted: false, selectionTruncated: false, selectionMs: 0, buildMs: 0 };
  const sourceValidity = new Map(), positions = [], patches = [], sources = new Set(); let minSourceDistance = Infinity;
  const frustum = new T.Frustum().setFromProjectionMatrix(new T.Matrix4().multiplyMatrices(referenceCamera.projectionMatrix, referenceCamera.matrixWorldInverse));
  const stopped = () => { if (clock() - start < maxBuildMs) return false; stats.budgetExhausted = stats.selectionTruncated = true; return true; };
  // Build proofs as the best candidates emerge instead of consuming a fixed
  // selection slice first. Traversal and live source auditing share the same
  // deadline; truncation can only omit a real surface.
  const iterator = nearbyFaces(faces, center, maxSourceDistance, frustum, stopped);
  while (stats.testedFaces < maxFaces && !stopped()) {
    const selectionStart = clock(), step = iterator.next();
    stats.selectionMs += clock() - selectionStart;
    if (step.done) break;
    const face = step.value; stats.considered++;
    const d = face.bounds.distanceToPoint(center); if (d > maxSourceDistance || !frustum.intersectsBox(face.bounds)) continue;
    // Cheap geometric rejection precedes the material/geometry live audit.
    // The full proof repeats these conditions below before emitting depth.
    const centerDistance = face.normal.dot(center) + face.constant;
    const cellRadius = Math.abs(face.normal.x) * half.x + Math.abs(face.normal.y) * half.y + Math.abs(face.normal.z) * half.z;
    const sideHint = centerDistance > cellRadius + 1e-4 ? 1 : centerDistance < -cellRadius - 1e-4 ? -1 : 0;
    const materialSideHint = face.record.materials[face.materialIndex].side, frontHint = sideHint * face.record.determinantSign > 0;
    if (!sideHint || Math.abs(centerDistance) - cellRadius <= mainNearRadius || materialSideHint === T.FrontSide && !frontHint || materialSideHint === T.BackSide && frontHint) continue;
    const r = face.record;
    if (!sourceValidity.has(r)) sourceValidity.set(r, shown(r.mesh, camera.layers.mask) && currentRecord(T, r));
    if (!sourceValidity.get(r)) continue;
    if (stats.testedFaces >= maxFaces || clock() - start >= maxBuildMs) { stats.budgetExhausted = true; break; }
    stats.testedFaces++;
    const planeDistances = corners.map(e => face.normal.dot(e) + face.constant);
    const side = Math.min(...planeDistances) > 1e-4 ? 1 : Math.max(...planeDistances) < -1e-4 ? -1 : 0;
    const materialSide = face.record.materials[face.materialIndex].side, front = side * face.record.determinantSign > 0;
    if (!side || materialSide === T.FrontSide && !front || materialSide === T.BackSide && front) continue;
    const sourceDistance = Math.min(...planeDistances.map(Math.abs));
    // Geometry in front of the MAIN camera's near plane cannot hide anything
    // in its actual image. A radial lower bound remains valid after rotation.
    if (!(sourceDistance > mainNearRadius)) continue;
    const local = [0, 3, 6].map(i => new T.Vector3().fromArray(face.vertices, i).applyMatrix4(referenceCamera.matrixWorldInverse));
    const minDepth = Math.min(...local.map(p => -p.z)) - extraDepth, farDepth = Math.max(...local.map(p => -p.z)) + extraDepth;
    if (!(minDepth > referenceNear + 1e-4 && farDepth < referenceFar - 1e-4)) continue;
    const ndcDepth = depthNDC(referenceCamera, farDepth + Math.max(1e-4, farDepth * 1e-6)) + depthEpsilonNdc;
    if (!(ndcDepth > -1 && ndcDepth < 1)) continue;
    let poly = [[0, 0], [width, 0], [width, height], [0, height]];
    for (const eye of corners) {
      offset.copy(eye).applyMatrix4(referenceCamera.matrixWorldInverse);
      const projected = local.map(p => { vertex.copy(p).sub(offset); return [fx * vertex.x / -vertex.z + width / 2, fy * vertex.y / -vertex.z + height / 2]; });
      if (!projected.flat().every(v => Number.isFinite(v) && Math.abs(v) < 1e6)) { poly = []; break; }
      for (let i = 0; i < 3 && poly.length; i++) {
        const a = projected[i], b = projected[(i + 1) % 3], c = projected[(i + 2) % 3];
        let A = a[1] - b[1], B = b[0] - a[0], C = a[0] * b[1] - a[1] * b[0];
        if (A * c[0] + B * c[1] + C < 0) { A = -A; B = -B; C = -C; }
        const length = Math.hypot(A, B); if (!(length > 1e-8)) { poly = []; break; }
        A /= length; B /= length; C /= length;
        // L-infinity half-pixel footprint plus float/edge rounding guard.
        C -= .5 * (Math.abs(A) + Math.abs(B)) + pixelGuard;
        poly = clip(poly, A, B, C);
      }
      if (!poly.length) break;
    }
    if (poly.length < 3 || area2(poly) < .01 || !poly.flat().every(Number.isFinite)) continue;
    for (let i = 1; i + 1 < poly.length; i++) for (const p of [poly[0], poly[i], poly[i + 1]]) positions.push(2 * p[0] / width - 1, 2 * p[1] / height - 1, ndcDepth);
    patches.push({ polygon: poly, face, farDepth, ndcDepth }); sources.add(face.record); minSourceDistance = Math.min(minSourceDistance, sourceDistance); stats.coveredFaces++;
  }
  stats.sourceMeshes = sources.size; stats.buildMs = clock() - start;
  return { THREE: T, geometry: geometryFrom(T, positions), referenceCamera, cell, center, halfExtent: half, width, height,
    layers: camera.layers.mask, sources: [...sources], patches, depthEpsilonNdc, minSourceDistance, stats, disposed: false };
}

export function isMovingCertificateCurrent(certificate, camera, registry, recordCache) {
  if (!certificate || certificate.disposed || camera.layers.mask !== certificate.layers || !certificate.sources.length) return false;
  const e = camera.matrixWorld.elements, c = certificate.cell;
  if (![e[12], e[13], e[14]].every(Number.isFinite) || !(certificate.minSourceDistance > nearRadius(certificate.THREE, camera))) return false;
  if (e[12] < c.min.x || e[12] > c.max.x || e[13] < c.min.y || e[13] > c.max.y || e[14] < c.min.z || e[14] > c.max.z) return false;
  return certificate.sources.every(r => {
    if (recordCache?.has(r)) return recordCache.get(r);
    const valid = shown(r.mesh, certificate.layers) && currentRecord(certificate.THREE, r, registry || r.registry);
    recordCache?.set(r, valid); return valid;
  });
}

export function buildMovingOcclusionTarget(certificate, worldBox, existingGeometry) {
  if (!certificate || certificate.disposed || !finiteBox(worldBox) || !certificate.sources.length) return null;
  const { THREE: T, referenceCamera: camera, halfExtent: half, width, height } = certificate;
  const expanded = worldBox.clone(); expanded.min.sub(half); expanded.max.add(half);
  const p = new T.Vector3(); let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, nearDepth = Infinity;
  const fx = camera.projectionMatrix.elements[0] * width / 2, fy = camera.projectionMatrix.elements[5] * height / 2;
  for (let i = 0; i < 8; i++) {
    p.set(i & 1 ? expanded.max.x : expanded.min.x, i & 2 ? expanded.max.y : expanded.min.y, i & 4 ? expanded.max.z : expanded.min.z).applyMatrix4(camera.matrixWorldInverse);
    const depth = -p.z; if (!(depth > camera.near + 1e-4 && depth < camera.far - 1e-4)) return null;
    nearDepth = Math.min(nearDepth, depth); const x = fx * p.x / depth + width / 2, y = fy * p.y / depth + height / 2;
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
  }
  // Complete angular containment is required for later rotation. Never clamp
  // a partly unqueried object to the old viewport and call the whole box hidden.
  x0 = Math.floor(x0 - .01); y0 = Math.floor(y0 - .01); x1 = Math.ceil(x1 + .01); y1 = Math.ceil(y1 + .01);
  if (!(x0 >= 0 && y0 >= 0 && x1 <= width && y1 <= height && x1 > x0 && y1 > y0)) return null;
  const ndcDepth = depthNDC(camera, nearDepth - Math.max(1e-4, nearDepth * 1e-6)) - certificate.depthEpsilonNdc;
  if (!(ndcDepth > -1 && ndcDepth < 1)) return null;
  const rect = [x0, y0, x1, y1], points = [[x0, y0], [x1, y0], [x1, y1], [x0, y0], [x1, y1], [x0, y1]], positions = [];
  for (const p of points) positions.push(2 * p[0] / width - 1, 2 * p[1] / height - 1, ndcDepth);
  return { geometry: geometryFrom(T, positions, existingGeometry), rect, nearDepth, ndcDepth, boxValues: boxValues(worldBox) };
}

export function disposeMovingOcclusionCertificate(certificate) {
  if (!certificate || certificate.disposed) return; certificate.disposed = true; certificate.geometry.dispose();
}
