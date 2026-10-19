/* Grass distance LOD. Keep every planted blade, its UVs and the close geometry.
 * The existing grass scheduler puts only cells >=16 m away in parts[1/2].
 * Those blades can use their bottom/top vertices instead of three segments.
 * Before that boundary, the vertex shader continuously straightens the strip;
 * switching index buffers therefore does not suddenly straighten the grass.
 */
const STRIP = [0, 1, 3, 0, 3, 2, 2, 3, 5, 2, 5, 4, 4, 5, 7, 4, 7, 6];
const ENDPOINTS = [0, 1, 7, 0, 7, 6];

export function grassEndpointIndices(source, count = source.length) {
  if (!Number.isInteger(count) || count < 0 || count > source.length || count % STRIP.length) {
    throw new Error('Grass LOD requires complete three-segment strips.');
  }
  const out = new source.constructor(count / 3);
  for (let p = 0, q = 0; p < count; p += STRIP.length) {
    const base = source[p];
    for (let k = 0; k < STRIP.length; k++) {
      if (source[p + k] !== base + STRIP[k]) throw new Error('Unknown grass strip topology.');
    }
    for (const offset of ENDPOINTS) out[q++] = base + offset;
  }
  return out;
}

const POSITION = 'vec3 ob=o0+disp;';
const NORMAL = 'vec3 objectNormal=normalize(nb*0.35+vec3(0.0,1.0,0.0)+side*across*0.25);';
const SHADE = 'vGS=mix(0.35,1.0,smoothstep(0.0,0.7,hf));';

export function grassDistanceVertexShader(source) {
  for (const token of [POSITION, NORMAL, SHADE]) {
    if (!source.includes(token)) throw new Error('Grass distance LOD shader hook is missing.');
  }
  return source.replace(POSITION, `${POSITION}
    float grassSegmentLod=smoothstep(12.0,16.0,dist);
    float endOut=(sin(lean)+curv)*Hh;
    vec3 end0=vec3(dir.x*endOut,(cos(lean)-0.35*curv)*Hh,dir.y*endOut);
    vec3 endOb=end0+(vec3(wd.x,0.0,wd.y)*bend+vec3(-wd.y,0.0,wd.x)*flut)*max(length(end0),Hh*0.6);
    ob=mix(ob,endOb*hf,grassSegmentLod);`)
    .replace(NORMAL, `${NORMAL}
    vec3 farTangent=normalize(endOb+vec3(0.0,1e-3,0.0));
    vec3 farNormal=normalize(cross(side,farTangent)*0.35+vec3(0.0,1.0,0.0)+side*across*0.25);
    objectNormal=mix(objectNormal,farNormal,grassSegmentLod);`)
    .replace(SHADE, `${SHADE}vGS=mix(vGS,mix(0.35,1.0,hf),grassSegmentLod);`);
}

/** Install immediately after buildGrass(), before upload/shader preparation.
 * No per-frame work, object/material additions, instance uploads, or season hooks.
 * Each tier keeps its fixed drawRange; the existing scheduler only changes
 * geometry.instanceCount and the per-cell offsets, never these index buffers.
 */
export function installGrassDistanceLOD({ THREE, grass }) {
  if (!grass?.parts || grass.parts.length !== 3) throw new Error('Expected three grass distance tiers.');
  if (grass.distanceLOD) return grass.distanceLOD;
  const material = grass.parts[0].mesh.material;
  if (grass.parts.some(p => p.mesh.material !== material)) throw new Error('Grass tiers must share a material.');

  // Validate everything before modifying shared scene state.
  const replacements = grass.parts.slice(1).map(({ mesh }) => {
    const geometry = mesh.geometry;
    if (geometry.drawRange.start !== 0) throw new Error('Unexpected grass index offset.');
    const oldCount = Math.min(geometry.index.count, geometry.drawRange.count);
    return { geometry, oldCount, indices: grassEndpointIndices(geometry.index.array, oldCount) };
  });
  const beforeCompile = material.onBeforeCompile;
  const cacheKey = material.customProgramCacheKey.bind(material);
  material.onBeforeCompile = function (shader, renderer) {
    beforeCompile.call(this, shader, renderer);
    shader.vertexShader = grassDistanceVertexShader(shader.vertexShader);
  };
  material.customProgramCacheKey = () => cacheKey() + ':grass-distance-segments-v1';
  material.needsUpdate = true;
  for (const { geometry, indices } of replacements) {
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.setDrawRange(0, indices.length);
  }
  grass.distanceLOD = {
    transitionMeters: [12, 16],
    fullDetailMeters: 12,
    trianglesPerCellBefore: [grass.parts[0].mesh.geometry.index.count / 3, ...replacements.map(r => r.oldCount / 3)],
    trianglesPerCellAfter: grass.parts.map(({ mesh }) => Math.min(mesh.geometry.index.count, mesh.geometry.drawRange.count) / 3),
  };
  return grass.distanceLOD;
}

/** Partition a static instance batch once at construction, keeping every plant.
 * Each result shares geometry/material and gets a conservative animated bound.
 * Attach the returned meshes to the original parent; do not also attach source.
 * Tiny/card batches stay whole: more draw calls would cost more than their few
 * triangles. Dynamic instance sets and skinned/morphed plants are not supported.
 */
export function partitionStaticVegetationInstances({ THREE, mesh, cellSize = 16, padding = 1, minTriangles = 20000 }) {
  if (!mesh?.isInstancedMesh) throw new Error('Vegetation partition requires an InstancedMesh.');
  if (!(cellSize > 0) || !Number.isFinite(cellSize) || !(padding >= 0) || !Number.isFinite(padding)) {
    throw new Error('Invalid vegetation cell size or animation margin.');
  }
  const geometry = mesh.geometry;
  const triangles = (geometry.index?.count ?? geometry.attributes.position.count) / 3;
  if (!mesh.count || mesh.count * triangles < minTriangles || mesh.morphTexture || Object.keys(geometry.morphAttributes).length) {
    return [mesh];
  }
  mesh.updateWorldMatrix(true, false);
  const cells = new Map(), matrix = new THREE.Matrix4(), position = new THREE.Vector3();
  for (let i = 0; i < mesh.count; i++) {
    mesh.getMatrixAt(i, matrix);
    position.setFromMatrixPosition(matrix).applyMatrix4(mesh.matrixWorld);
    const key = Math.floor(position.x / cellSize) + ',' + Math.floor(position.z / cellSize);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(i);
  }
  if (cells.size < 2) return [mesh];

  const result = [], color = new THREE.Color();
  for (const [key, indices] of cells) {
    const part = new THREE.InstancedMesh(geometry, mesh.material, indices.length);
    // Object3D properties include transform, layers, renderOrder and shadows.
    // Avoid InstancedMesh.copy(), which would duplicate the whole source buffer.
    THREE.Object3D.prototype.copy.call(part, mesh, false);
    part.name = (mesh.name || '作物') + '·' + key;
    part.customDepthMaterial = mesh.customDepthMaterial;
    part.customDistanceMaterial = mesh.customDistanceMaterial;
    part.onBeforeRender = mesh.onBeforeRender;
    part.onAfterRender = mesh.onAfterRender;
    part.onBeforeShadow = mesh.onBeforeShadow;
    part.onAfterShadow = mesh.onAfterShadow;
    part.instanceMatrix.setUsage(mesh.instanceMatrix.usage);
    indices.forEach((sourceIndex, i) => {
      mesh.getMatrixAt(sourceIndex, matrix); part.setMatrixAt(i, matrix);
      if (mesh.instanceColor) { mesh.getColorAt(sourceIndex, color); part.setColorAt(i, color); }
    });
    part.instanceMatrix.needsUpdate = true;
    if (part.instanceColor) {
      part.instanceColor.setUsage(mesh.instanceColor.usage);
      part.instanceColor.needsUpdate = true;
    }
    part.computeBoundingSphere(); part.boundingSphere.radius += padding;
    part.computeBoundingBox(); part.boundingBox.expandByScalar(padding);
    part.frustumCulled = true;
    result.push(part);
  }
  return result;
}
