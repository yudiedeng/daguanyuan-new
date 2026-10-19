// Shared by the browser and offline generation checks. No DOM or WebGL needed.
export function rasterInfluence(buckets, grid, cellSize, radius) {
  const { x0, z0, nx, nz } = grid;
  const data = new Float64Array(nx * nz);
  // The old per-pixel lookup visited buckets in x/z order. Keep the same sum
  // order, including its 3x3 bucket boundary, so half-float shading stays exact.
  const ordered = [...buckets].map(([key, points]) => ({
    cell: key.split(',').map(Number), points,
  })).sort((a, b) => a.cell[0] - b.cell[0] || a.cell[1] - b.cell[1]);
  for (const { cell: [bx, bz], points } of ordered) {
    for (const [px, pz] of points) {
      const ix0 = Math.max(0, Math.ceil(px - radius - x0), Math.ceil((bx - 1) * cellSize - x0));
      const ix1 = Math.min(nx - 1, Math.floor(px + radius - x0), Math.ceil((bx + 2) * cellSize - x0) - 1);
      const iz0 = Math.max(0, Math.ceil(pz - radius - z0), Math.ceil((bz - 1) * cellSize - z0));
      const iz1 = Math.min(nz - 1, Math.floor(pz + radius - z0), Math.ceil((bz + 2) * cellSize - z0) - 1);
      for (let j = iz0; j <= iz1; j++) {
        for (let i = ix0; i <= ix1; i++) {
          data[j * nx + i] += Math.max(0, 1 - Math.hypot(px - (x0 + i), pz - (z0 + j)) / radius);
        }
      }
    }
  }
  return data;
}

export function generateTerrainGeometry(THREE, heightAt, streamPoints) {
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const smooth = (a, b, value) => { const t = clamp((value - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
  const geometry = new THREE.PlaneGeometry(340, 410, 340, 410);
  geometry.rotateX(-Math.PI / 2);
  geometry.translate(0, 0, 5);
  const p = geometry.attributes.position;
  const heights = new Float32Array(341 * 411);
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i), h = heightAt(x, z);
    p.setY(i, h);
    heights[Math.round(z + 200) * 341 + Math.round(x + 170)] = h;
  }
  // Dig the visible stream bed without lowering walking/vegetation heights.
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i);
    if (x < 0 || x > 18 || z < 56 || z > 94) continue;
    let distance = 99;
    for (const point of streamPoints) distance = Math.min(distance, Math.hypot(point.x - x, point.z - z));
    if (distance < 1.7) p.setY(i, p.getY(i) - 0.45 * smooth(1.7, 0.95, distance));
  }
  geometry.computeVertexNormals();
  const normals = geometry.attributes.normal;
  const colors = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const h = p.getY(i);
    colors[i * 3] = smooth(0.62, 0.12, h);
    colors[i * 3 + 1] = clamp((1 - normals.getY(i) - 0.12) * 2.2, 0, 1);
    colors[i * 3 + 2] = smooth(2, 9, h);
  }
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  return { geometry, heights };
}

export function restoreGeometry(THREE, data, prefix = '') {
  const geometry = new THREE.BufferGeometry();
  for (const [name, size] of [['position', 3], ['normal', 3], ['uv', 2], ['color', 3]]) {
    const array = data.arrays[prefix + name];
    if (array) geometry.setAttribute(name, new THREE.BufferAttribute(array, size));
  }
  geometry.setIndex(new THREE.BufferAttribute(data.arrays[prefix + 'index'], 1));
  return geometry;
}

export function waterDistances(heightAt) {
  const nx = 85, nz = 103, pad = 6, width = nx + pad * 2;
  const wet = new Uint8Array(width * (nz + pad * 2));
  for (let j = -pad; j < nz + pad; j++) {
    for (let i = -pad; i < nx + pad; i++) {
      wet[(j + pad) * width + i + pad] = heightAt(-170 + i * 4, -200 + j * 4) < 0.1;
    }
  }
  const offsets = [];
  for (let a = -pad; a <= pad; a++) for (let b = -pad; b <= pad; b++) {
    offsets.push({ offset: b * width + a, distance: Math.hypot(a, b) * 4 });
  }
  offsets.sort((a, b) => a.distance - b.distance);
  const out = new Float32Array(nx * nz);
  for (let j = 0; j < nz; j++) for (let i = 0; i < nx; i++) {
    const base = (j + pad) * width + i + pad;
    let distance = 99;
    for (const point of offsets) if (wet[base + point.offset]) { distance = point.distance; break; }
    out[j * nx + i] = distance;
  }
  return out;
}

export function rasterCircles(points, grid) {
  const { x0, z0, nx, nz } = grid;
  const data = new Uint8Array(nx * nz);
  for (const [px, pz, radius] of points) {
    const r2 = radius * radius;
    const ix0 = Math.max(0, Math.ceil(px - radius - x0)), ix1 = Math.min(nx - 1, Math.floor(px + radius - x0));
    const iz0 = Math.max(0, Math.ceil(pz - radius - z0)), iz1 = Math.min(nz - 1, Math.floor(pz + radius - z0));
    for (let j = iz0; j <= iz1; j++) for (let i = ix0; i <= ix1; i++) {
      if ((px - (x0 + i)) ** 2 + (pz - (z0 + j)) ** 2 < r2) data[j * nx + i] = 1;
    }
  }
  return data;
}

export function rasterZones(zones, grid, margin) {
  const { x0, z0, nx, nz } = grid;
  const data = new Uint8Array(nx * nz);
  for (const zone of zones) {
    const ix0 = Math.max(0, Math.floor(zone.x - zone.hw - margin - x0) + 1);
    const ix1 = Math.min(nx - 1, Math.ceil(zone.x + zone.hw + margin - x0) - 1);
    const iz0 = Math.max(0, Math.floor(zone.z - zone.hd - margin - z0) + 1);
    const iz1 = Math.min(nz - 1, Math.ceil(zone.z + zone.hd + margin - z0) - 1);
    if (ix0 > ix1) continue;
    for (let j = iz0; j <= iz1; j++) data.fill(1, j * nx + ix0, j * nx + ix1 + 1);
  }
  return data;
}

// A small binary container: padded JSON describes typed arrays, followed by the
// array bytes. Offline artifacts are gzipped; the browser decodes them as a stream.
export function packGenerated(meta, arrays) {
  const entries = {};
  let length = 0;
  for (const [name, array] of Object.entries(arrays)) {
    length = Math.ceil(length / 8) * 8;
    entries[name] = { type: array.constructor.name, offset: length, length: array.length };
    length += array.byteLength;
  }
  const json = new TextEncoder().encode(JSON.stringify({ ...meta, arrays: entries }));
  const headerSize = Math.ceil((4 + json.length) / 8) * 8;
  const bytes = new Uint8Array(headerSize + length);
  new DataView(bytes.buffer).setUint32(0, json.length, true);
  bytes.set(json, 4);
  for (const [name, array] of Object.entries(arrays)) {
    bytes.set(new Uint8Array(array.buffer, array.byteOffset, array.byteLength), headerSize + entries[name].offset);
  }
  return bytes;
}

export function unpackGenerated(buffer) {
  const length = new DataView(buffer).getUint32(0, true);
  const meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, length)));
  const headerSize = Math.ceil((4 + length) / 8) * 8;
  const types = { Float32Array, Float64Array, Uint16Array, Uint32Array, Uint8Array };
  const arrays = {};
  for (const [name, entry] of Object.entries(meta.arrays)) {
    const Type = types[entry.type];
    if (!Type) throw new Error('Unsupported generated array: ' + entry.type);
    arrays[name] = new Type(buffer, headerSize + entry.offset, entry.length);
  }
  return { meta, arrays };
}

export async function loadGenerated(url) {
  const controller = new AbortController();
  // A large precomputed file should not hold up slower network deployments.
  const timeout = setTimeout(() => controller.abort(), 2500);
  try {
    if (typeof DecompressionStream !== 'function') return null;
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) return null;
    const buffer = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    return unpackGenerated(buffer);
  } catch (error) {
    console.warn('预生成数据不可用，使用原生成流程', url, error);
    return null;
  } finally {
    clearTimeout(timeout);
  }
}
