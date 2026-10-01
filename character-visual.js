/* Character appearance only. Movement, terrain and quests stay on hero.g. */
export const CHARACTER_MODELS = {
  daiyu: { url: new URL('./models/characters/lin-daiyu-web.glb', import.meta.url).href,
    height: 1.74, yaw: -Math.PI / 2, walkSpeed: 1.35, fastSpeed: 2.3 }
};

export function createCharacterVisuals({ THREE, hero, loader, onStatus = () => {} }) {
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
    if (runtime) { runtime.mixer.stopAllAction(); runtime.current = null; }
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
        runtimes.set(root, { mixer, actions, current: null });
      }
      return root;
    }).catch(error => { cache.delete(key); throw error; });
    cache.set(key, pending);
    return pending;
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
    runtime.mixer.update(Math.min(dt, .05));
  }

  return { select, update, get animation() { return runtime?.current?.getClip().name || null; }, get active() { return active !== null; }, get selected() { return selected; } };
}
