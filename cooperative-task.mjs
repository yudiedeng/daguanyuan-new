// Short CPU tasks yield between slices so input and rendering can keep running.
const queue = [];
let channel;
function schedule(callback) {
  if (typeof window !== 'undefined' && typeof MessageChannel !== 'undefined') {
    if (!channel) {
      channel = new MessageChannel();
      channel.port1.onmessage = () => queue.shift()?.();
    }
    queue.push(callback); channel.port2.postMessage(0);
  } else setTimeout(callback, 0);
}
export function finishTask(iterator) {
  let result;
  do { result = iterator.next(); } while (!result.done);
  return result.value;
}
export function startTask(iterator, { budgetMs = 4, maxSteps = 128, clock = () => performance.now(),
  yieldTask = schedule, isCurrent = () => true } = {}) {
  let resolve, reject, resume;
  const task = { done: false, cancelled: false, value: null, stats: { slices: 0, maxSliceMs: 0, workMs: 0, awaits: 0 },
    promise: new Promise((a, b) => { resolve = a; reject = b; }),
    cancel() {
      if (task.done) return;
      task.done = task.cancelled = true; iterator.return?.(); resolve(null);
    }
  };
  function slice() {
    if (task.done) return;
    const begun = clock(), until = begun + budgetMs; let steps = 0;
    try {
      do {
        if (!isCurrent()) { task.cancel(); return; }
        const result = iterator.next(resume); resume = undefined;
        if (result.done) { task.done = true; task.value = result.value; resolve(result.value); return; }
        if (result.value && typeof result.value.then === 'function') {
          task.stats.awaits++;
          result.value.then(value => { resume = value; if (!task.done) yieldTask(slice); }, error => { task.done = true; task.error = error; reject(error); });
          return;
        }
      } while (++steps < maxSteps && clock() < until);
      yieldTask(slice);
    } catch (error) { task.done = true; task.error = error; reject(error); }
    finally { const elapsed = clock() - begun; task.stats.slices++; task.stats.workMs += elapsed; task.stats.maxSliceMs = Math.max(task.stats.maxSliceMs, elapsed); }
  }
  slice(); return task;
}
