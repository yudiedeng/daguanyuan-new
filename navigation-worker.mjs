import { createNavigationWorld } from './navigation-world.mjs';
let world, revision;
self.onmessage = ({ data }) => {
  if (data.type === 'world') { revision = data.world.version; world = createNavigationWorld(data.world); return; }
  if (data.type !== 'route') return;
  const started = performance.now();
  try { const path = world.nav.findPath(...data.args, data.options);
    self.postMessage({ id: data.id, version: revision, path, elapsedMs: performance.now() - started });
  } catch (_) { self.postMessage({ id: data.id, version: revision, unavailable: true }); }
};
