// A distant overview needs more depth precision than a first-person camera.
// Limit the near plane by height above ground so low orbit views stay usable.
export function cameraNear(distance, clearance, walking = false) {
  if (walking) return 0.1;
  return Math.max(0.3, Math.min(12, distance * 0.04, clearance * 0.25));
}

// The imported paving is sometimes less than a millimetre above the terrain.
// Give these authored ground surfaces priority without moving their geometry.
export function groundDepthMaterial(material, cache) {
  if (!cache.has(material)) {
    const copy = material.clone();
    copy.onBeforeCompile = material.onBeforeCompile;
    copy.customProgramCacheKey = material.customProgramCacheKey;
    copy.polygonOffset = true;
    copy.polygonOffsetFactor = -1;
    copy.polygonOffsetUnits = -2;
    cache.set(material, copy);
  }
  return cache.get(material);
}
