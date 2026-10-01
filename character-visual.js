/* Character appearance only. Movement, terrain and quests stay on hero.g. */
export const CHARACTER_MODELS = {
  daiyu: { url: new URL('./models/characters/lin-daiyu-v1.glb', import.meta.url).href,
    height: 1.74, yaw: -Math.PI / 2 }
};

export function createCharacterVisuals({ THREE, hero, loader, onStatus = () => {} }) {
  const fallback = [...hero.g.children];
  const mount = new THREE.Group();
  mount.name = 'character-visual';
  hero.g.add(mount);
  const cache = new Map();
  let selected = null;
  let active = null;
  let request = 0;

  function show(root) {
    mount.clear();
    active = root;
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

  return { select, get active() { return active !== null; }, get selected() { return selected; } };
}
