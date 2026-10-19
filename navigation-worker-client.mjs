export function createNavigationWorker(snapshot) {
  let worker, revision, next = 0, unavailable = false;
  const pending = new Map();
  const stats = { requests: 0, worldUploads: 0, lastWorkerMs: 0 };
  function fail() { unavailable = true; worker?.terminate(); for (const resolve of pending.values()) resolve(undefined); pending.clear(); }
  function sync() {
    if (unavailable || typeof Worker === 'undefined') return false;
    try {
      if (!worker) {
        worker = new Worker(new URL('./navigation-worker.mjs', import.meta.url), { type: 'module' });
        worker.onerror = fail;
        worker.onmessage = ({ data }) => { const resolve = pending.get(data.id); pending.delete(data.id);
          stats.lastWorkerMs = data.elapsedMs || 0;
          resolve?.(data.unavailable || data.version !== snapshot().version ? undefined : data.path); };
      }
      const world = snapshot();
      if (revision !== world.version) { revision = world.version; stats.worldUploads++; worker.postMessage({ type: 'world', world }); }
      return true;
    } catch (_) { fail(); return false; }
  }
  sync();
  return { stats, search(args, options) {
    if (!sync()) return Promise.resolve(undefined);
    return new Promise(resolve => { const id = ++next; stats.requests++; pending.set(id, resolve);
      worker.postMessage({ type: 'route', id, args, options }); });
  }, dispose: fail };
}
