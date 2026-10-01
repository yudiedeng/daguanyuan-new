/* Character appearance only. Movement, terrain and quests stay on hero.g. */
export const CHARACTER_MODELS = {
  daiyu: { url: new URL('./models/characters/lin-daiyu-v6.glb', import.meta.url).href,
    height: 1.74, yaw: -Math.PI / 2, walkSpeed: 1.35, fastSpeed: 2.3 }
};

export function createCharacterVisuals({ THREE, hero, loader, onStatus = () => {}, groundHeight = null }) {
  const fallback = [...hero.g.children];
  const mount = new THREE.Group();
  mount.name = 'character-visual';
  hero.g.add(mount);
  const cache = new Map();
  const runtimes = new WeakMap();
  let runtime = null;
  let selected = null;
  let active = null;
  let request = 0;

  function show(root) {
    if (runtime) { restoreCloth(); for (const b of runtime.cloth?.bones || []) b.lift = 0; runtime.mixer.stopAllAction(); runtime.current = null; }
    mount.clear();
    active = root;
    runtime = root ? runtimes.get(root) : null;
    if (root) mount.add(root);
    for (const child of fallback) child.visible = !root;
  }

  function load(key) {
    if (cache.has(key)) return cache.get(key);
    const config = CHARACTER_MODELS[key];
    const pending = loader.loadAsync(config.url).then(gltf => {
      const model = gltf.scene;
      model.rotation.y += config.yaw;
      model.updateMatrixWorld(true);
      const bounds = new THREE.Box3().setFromObject(model);
      const size = bounds.getSize(new THREE.Vector3());
      if (!Number.isFinite(size.y) || size.y <= 0) throw new Error('Invalid character bounds');
      const center = bounds.getCenter(new THREE.Vector3());
      // Separate wrappers avoid changing imported node transforms or future bone tracks.
      const origin = new THREE.Group();
      origin.add(model);
      origin.position.set(-center.x, -bounds.min.y, -center.z);
      const root = new THREE.Group();
      root.name = `character-${key}`;
      root.scale.setScalar(config.height / size.y);
      root.add(origin);
      root.userData.character = key;
      root.userData.animations = gltf.animations;
      root.traverse(object => {
        if (!object.isMesh) return;
        object.castShadow = true;
        object.receiveShadow = true;
      });
      if (gltf.animations.length) {
        const mixer = new THREE.AnimationMixer(model);
        const actions = Object.fromEntries(gltf.animations.map(clip => [clip.name, mixer.clipAction(clip)]));
        runtimes.set(root, { mixer, actions, current: null, cloth: makeCloth(root) });
      }
      return root;
    }).catch(error => { cache.delete(key); throw error; });
    cache.set(key, pending);
    return pending;
  }

  // Sample the hem spatially, keeping the lowest point in each 3 cm cell.
  // Only the lowest skirt bones move; the book, shoulders and head retain their pose.
  function makeCloth(root) {
    const bones = [], samples = [], point = new THREE.Vector3();
    root.updateMatrixWorld(true);
    root.traverse(b => { if (b.isBone && /^Skirt_\d+_2$/.test(b.name))
      bones.push({ bone: b, applied: new THREE.Vector3(), lift: 0 }); });
    if (!bones.length) return null;
    const lookup = new Map(bones.map((b, i) => [b.bone, i]));
    root.traverse(mesh => {
      if (!mesh.isSkinnedMesh) return;
      mesh.skeleton.update();
      const cells = new Map(), indices = mesh.geometry.attributes.skinIndex;
      const weights = mesh.geometry.attributes.skinWeight;
      for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
        mesh.getVertexPosition(i, point).applyMatrix4(mesh.matrixWorld);
        if (point.y > .28) continue;
        const influences = [];
        for (let k = 0; k < 4; k++) {
          const j = lookup.get(mesh.skeleton.bones[indices.getComponent(i, k)]);
          const w = weights.getComponent(i, k);
          if (j !== undefined && w > .001) influences.push([j, w]);
        }
        if (!influences.length) continue;
        const key = Math.floor(point.x / .03) + ',' + Math.floor(point.z / .03);
        if (!cells.has(key) || point.y < cells.get(key).y)
          cells.set(key, { mesh, index: i, influences, y: point.y });
      }
      samples.push(...cells.values());
    });
    return { bones, samples, meshes: [...new Set(samples.map(s => s.mesh))], point, inverse: new THREE.Matrix4(), delta: new THREE.Vector3(), zero: new THREE.Vector3() };
  }

  function restoreCloth() {
    for (const b of runtime?.cloth?.bones || []) {
      b.bone.position.sub(b.applied); b.applied.set(0, 0, 0);
    }
  }

  function fitCloth(dt, grounded) {
    const c = runtime.cloth;
    if (!c || !groundHeight) return;
    const apply = () => {
      for (const b of c.bones) {
        b.bone.position.sub(b.applied);
        c.inverse.copy(b.bone.parent.matrixWorld).invert();
        c.delta.set(0, b.lift, 0).applyMatrix4(c.inverse);
        c.zero.set(0, 0, 0).applyMatrix4(c.inverse);
        b.applied.copy(c.delta).sub(c.zero);
        b.bone.position.add(b.applied);
      }
      hero.g.updateMatrixWorld(true);
      for (const mesh of c.meshes) mesh.skeleton.update();
    };
    hero.g.updateMatrixWorld(true);
    for (const b of c.bones) b.lift *= Math.exp(-12 * dt);
    apply();
    if (!grounded) return;
    for (let pass = 0; pass < 3; pass++) {
      const raises = c.bones.map(() => 0);
      for (const s of c.samples) {
        s.mesh.getVertexPosition(s.index, c.point).applyMatrix4(s.mesh.matrixWorld);
        // Cover the cell around a probe so a sharp step cannot slip between samples.
        let ground = groundHeight(c.point.x, c.point.z, hero.g.position.y);
        for (const dx of [-.035, .035]) for (const dz of [-.035, .035])
          ground = Math.max(ground, groundHeight(c.point.x + dx, c.point.z + dz, hero.g.position.y));
        const depth = ground + .008 - c.point.y;
        if (!Number.isFinite(depth) || depth <= 0 || ground > hero.g.position.y + .52) continue;
        const weight = s.influences.reduce((sum, [, w]) => sum + w, 0);
        for (const [j] of s.influences) raises[j] = Math.max(raises[j], depth / weight);
      }
      if (!raises.some(v => v > .001)) break;
      for (let j = 0; j < raises.length; j++) c.bones[j].lift = Math.min(.65, c.bones[j].lift + raises[j]);
      apply();
    }
  }

  async function select(key) {
    selected = key;
    const ticket = ++request;
    show(null);
    if (!CHARACTER_MODELS[key]) return false;
    onStatus({ key, state: 'loading' });
    try {
      const root = await load(key);
      if (ticket !== request || selected !== key) return false;
      show(root);
      onStatus({ key, state: 'ready' });
      return true;
    } catch (error) {
      if (ticket === request) onStatus({ key, state: 'error', error });
      return false;
    }
  }

  function update(dt, { speed = 0, run = false, grounded = true } = {}) {
    if (!runtime) return;
    const name = !grounded || speed < .05 ? 'Idle' : run ? 'FastWalk' : 'Walk';
    const next = runtime.actions[name] || runtime.actions.Idle;
    if (!next) return;
    if (runtime.current !== next) {
      if (runtime.current) runtime.current.fadeOut(.18);
      next.reset().setEffectiveWeight(1).fadeIn(.18).play();
      runtime.current = next;
    }
    const config = CHARACTER_MODELS[selected];
    const reference = run ? config.fastSpeed : config.walkSpeed;
    next.setEffectiveTimeScale(name === 'Idle' ? 1 : Math.max(.5, Math.min(1.8, speed / reference)));
    restoreCloth();
    runtime.mixer.update(Math.min(dt, .05));
    fitCloth(dt, grounded);
  }

  return { select, update, get animation() { return runtime?.current?.getClip().name || null; }, get active() { return active !== null; }, get selected() { return selected; } };
}
