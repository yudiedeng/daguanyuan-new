// The imported building shells, hi/lo geometry and painted furnishings never
// change Object3D transforms after loadBuildings/fitInterior finish. Cache only
// those branches. Props, reflectors and custom/dynamic objects keep updating.
const installed = new WeakMap();
const equals = (a, b) => { for (let i = 0; i < 16; i++) if (a[i] !== b[i]) return false; return true; };
function changedTRS(o, a) {
  const p = o.position, q = o.quaternion, s = o.scale;
  return p.x !== a[0] || p.y !== a[1] || p.z !== a[2] || q.x !== a[3] || q.y !== a[4] || q.z !== a[5] || q.w !== a[6] || s.x !== a[7] || s.y !== a[8] || s.z !== a[9];
}
function saveTRS(o, a) {
  const p = o.position, q = o.quaternion, s = o.scale;
  a[0] = p.x; a[1] = p.y; a[2] = p.z; a[3] = q.x; a[4] = q.y; a[5] = q.z; a[6] = q.w; a[7] = s.x; a[8] = s.y; a[9] = s.z;
}

export function installBuildingTransformCache({ THREE, buildings }) {
  const handles = [], stats = { buildings: 0, staticNodes: 0, reused: 0, refreshed: 0 };
  const standardWorld = THREE.Object3D.prototype.updateMatrixWorld;
  const standardLocal = THREE.Object3D.prototype.updateMatrix;
  const standardBefore = THREE.Object3D.prototype.onBeforeRender;
  function staticBranch(branch) {
    let ok = true, count = 0;
    branch.traverse(o => {
      count++;
      if (o.isLOD || o.isCamera || o.isLight || o.isSkinnedMesh || o.isBone || o.isReflector ||
        o.userData.rcKind || o.userData.dynamic || o.userData.dgyImmediate || /^PROP_/.test(o.name) ||
        o.animations?.length || o.updateMatrixWorld !== standardWorld || o.updateMatrix !== standardLocal ||
        o.onBeforeRender !== standardBefore) ok = false;
    });
    return ok ? count : 0;
  }
  for (const { root } of buildings) {
    if (installed.has(root)) { handles.push(installed.get(root)); continue; }
    if (root.updateMatrixWorld !== standardWorld || root.updateMatrix !== standardLocal) continue;
    const branches = new Map(), listeners = [];
    for (const child of root.children) { const count = staticBranch(child); if (count) branches.set(child, count); }
    if (!branches.size) continue;
    let dirty = true, parent = null, auto = root.matrixAutoUpdate, worldAuto = root.matrixWorldAutoUpdate;
    const trs = new Float64Array(10), local = new Float64Array(16), world = new Float64Array(16), parentWorld = new Float64Array(16);
    const listen = (node, type, fn) => { node.addEventListener(type, fn); listeners.push([node, type, fn]); };
    const invalidate = () => { dirty = true; };
    // A late child may be animated. Keep its complete top-level branch live
    // instead of assuming a newly attached subtree is another static model.
    for (const [branch] of branches) {
      const added = () => { branches.delete(branch); dirty = true; };
      branch.traverse(o => { listen(o, 'childadded', added); listen(o, 'childremoved', invalidate); });
    }
    listen(root, 'childadded', e => { branches.delete(e.child); dirty = true; });
    listen(root, 'childremoved', invalidate);
    function update(force) {
      if (this !== root) return standardWorld.call(this, force);
      const changed = dirty || root.updateMatrix !== standardLocal || changedTRS(root, trs) ||
        root.matrixAutoUpdate !== auto || root.matrixWorldAutoUpdate !== worldAuto || parent !== root.parent ||
        !equals(root.matrix.elements, local) || !equals(root.matrixWorld.elements, world) ||
        (root.parent !== null && !equals(root.parent.matrixWorld.elements, parentWorld));
      if (changed) {
        dirty = false; standardWorld.call(root, true); stats.refreshed++;
        saveTRS(root, trs); local.set(root.matrix.elements); world.set(root.matrixWorld.elements);
        parent = root.parent; if (parent) parentWorld.set(parent.matrixWorld.elements);
        auto = root.matrixAutoUpdate; worldAuto = root.matrixWorldAutoUpdate;
      } else {
        // Match the original root dirty-flag result without descending into
        // immutable geometry. Visibility/layers/materials are never cached.
        root.matrixWorldNeedsUpdate = false;
        for (const child of root.children) {
          if (branches.has(child)) stats.reused += branches.get(child);
          else child.updateMatrixWorld(force || root.matrixAutoUpdate);
        }
      }
    }
    const handle = {
      root, invalidate,
      restore() {
        if (root.updateMatrixWorld === update) root.updateMatrixWorld = standardWorld;
        for (const [node, type, fn] of listeners) node.removeEventListener(type, fn);
        installed.delete(root);
      },
    };
    root.updateMatrixWorld = update; installed.set(root, handle); handles.push(handle);
    stats.buildings++; for (const count of branches.values()) stats.staticNodes += count;
  }
  return {
    stats,
    // Use after a deliberate future edit to an imported static leaf transform.
    invalidate(root) { for (const handle of handles) if (!root || handle.root === root) handle.invalidate(); },
    restore() { for (const handle of handles) handle.restore(); },
  };
}

// For explicitly static spatial groups created by the vegetation BVH builder.
// Shader wind, instance matrices, colors and LOD visibility remain independent.
export function installStaticBranchTransformCache({ THREE, roots }) {
  return installBuildingTransformCache({ THREE, buildings: roots.map(root => ({ root })) });
}
