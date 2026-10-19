// Two local font faces share this CSS family: the original subset and its supplement.
let loaded = false;
export const calligraphyReady = (globalThis.document?.fonts?.load
  ? document.fonts.load('124px "DGY Calligraphy"', '大嶒')
  : Promise.resolve()).then(() => { loaded = true; }, error => {
    console.warn('书法字体加载失败，暂用系统字体', error);
  });

const pendingCanvases = new WeakMap();

// These painters use fixed seeds. Reset the context before repainting so late font
// arrival replaces fallback letters instead of stamping a second set over them.
export function calligraphyCanvas(width, height, draw, ready = calligraphyReady) {
  const canvas = document.createElement('canvas');
  const paint = () => {
    canvas.width = width;
    canvas.height = height;
    draw(canvas.getContext('2d'), width, height);
  };
  paint();
  if (!loaded || ready !== calligraphyReady) {
    pendingCanvases.set(canvas, ready.then(paint));
  }
  return canvas;
}

export function refreshCalligraphyTexture(canvas, texture) {
  const pending = pendingCanvases.get(canvas);
  if (pending) pending.then(() => { texture.needsUpdate = true; });
  return texture;
}
