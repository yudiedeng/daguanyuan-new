import { clone } from 'https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/utils/SkeletonUtils.js';

export function createCharacterShowcase(THREE) {
  const style = document.createElement('style');
  style.textContent = `
  #character-showcase{position:fixed;inset:0;z-index:10000;background:radial-gradient(ellipse at 50% 35%,#f9f5eb,#d8d0c2);color:#433d37;overflow:hidden}
  #character-showcase[hidden]{display:none}
  #character-showcase canvas{position:absolute;inset:0;width:100%;height:100%}
  #character-showcase header{position:absolute;top:max(28px,env(safe-area-inset-top));left:32px;pointer-events:none}
  #character-showcase h2{font:400 36px 'Noto Serif SC',serif;letter-spacing:.25em;margin:0 0 8px}
  #character-showcase p{font-size:13px;letter-spacing:.15em;margin:0;opacity:.7}
  #character-showcase footer{position:absolute;bottom:max(28px,env(safe-area-inset-bottom));left:24px;right:24px;display:flex;align-items:center;justify-content:space-between;gap:16px}
  #character-showcase button{border:1px solid #81776880;border-radius:24px;background:#fff9;backdrop-filter:blur(8px);padding:12px 24px;font:inherit;color:inherit;cursor:pointer}
  #character-showcase .progress{position:absolute;bottom:0;left:0;height:3px;background:#917759;transform-origin:left;width:100%}
  .g-character-view{font:inherit;font-size:12px;border:1px solid #81776870;background:transparent;color:inherit;border-radius:12px;padding:2px 8px;cursor:pointer}
  @media(max-width:600px){#character-showcase header{left:22px;top:max(24px,env(safe-area-inset-top))}#character-showcase h2{font-size:28px}#character-showcase footer p{font-size:11px;letter-spacing:0}}
  `;
  document.head.append(style);
  const el = document.createElement('section');
  el.id = 'character-showcase'; el.hidden = true; el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-label', '林黛玉人物展示');
  el.innerHTML = '<header><h2>林黛玉</h2><p>潇湘馆 · 抱书入园</p></header><footer><p>正脸 · 全身 · 抱书姿态</p><button type="button">跳过 · 入园</button></footer><div class="progress"></div>';
  document.body.append(el);
  let finish = null;
  const cancel = () => finish?.();
  async function play(source) {
    cancel();
    if (!source) return;
    const previousFocus = document.activeElement;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
    el.prepend(renderer.domElement);
    const scene = new THREE.Scene(), model = clone(source);
    model.position.set(0, 0, 0); scene.add(model);
    const mixer = new THREE.AnimationMixer(model);
    const idle = source.userData.animations?.find(c => c.name === 'Idle');
    if (idle) mixer.clipAction(idle).play();
    scene.add(new THREE.HemisphereLight(0xfff7ed, 0x8b8992, 2.1));
    const key = new THREE.DirectionalLight(0xfff5e8, 3); key.position.set(2, 3, 4); scene.add(key);
    const fill = new THREE.DirectionalLight(0xe3ecff, 1.3); fill.position.set(-3, 2, 2); scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffffff, 2); rim.position.set(-1, 3, -2); scene.add(rim);
    const camera = new THREE.PerspectiveCamera(32, 1, .03, 30);
    const resize = () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); };
    resize(); window.addEventListener('resize', resize);
    const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const button = el.querySelector('button'), bar = el.querySelector('.progress');
    let frame = 0, elapsed = 0, last = performance.now();
    window.__characterShowcase = true; el.hidden = false; button.focus();
    return new Promise(resolve => {
      const onKey = e => { e.stopImmediatePropagation(); if (e.key === 'Tab') { e.preventDefault(); button.focus(); return; } if (['Escape', 'Enter', ' '].includes(e.key)) { e.preventDefault(); finish(); } };
      finish = () => {
        cancelAnimationFrame(frame); mixer.stopAllAction(); mixer.uncacheRoot(model);
        window.removeEventListener('resize', resize); window.removeEventListener('keydown', onKey, true);
        renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove(); el.hidden = true; window.__characterShowcase = false;
        finish = null; button.onclick = null;
        if (previousFocus?.isConnected && !previousFocus.closest('[hidden]')) previousFocus.focus();
        resolve();
      };
      button.onclick = () => finish?.();
      window.addEventListener('keydown', onKey, true);
      const tick = now => {
        const dt = Math.min((now - last) / 1000, .1); last = now;
        if (!document.hidden) elapsed += dt;
        const t = reduced ? 1 : Math.min(1, Math.max(0, (elapsed - 1.3) / 3.2));
        const u = t * t * (3 - 2 * t), angle = .24 * u;
        const close = Math.max(1.25, .24 / (Math.tan(Math.PI * 16 / 180) * camera.aspect));
        const far = Math.max(3.9, .58 / (Math.tan(Math.PI * 16 / 180) * camera.aspect));
        const d = close + (far - close) * u, y = 1.48 - .57 * u;
        camera.position.set(Math.sin(angle) * d, y + .04, Math.cos(angle) * d); camera.lookAt(0, y, 0);
        if (!reduced) mixer.update(dt);
        renderer.render(scene, camera); bar.style.transform = `scaleX(${Math.min(1, elapsed / 6)})`;
        if (elapsed >= 6) { finish(); return; }
        frame = requestAnimationFrame(tick);
      };
      tick(last);
    });
  }
  return { play, cancel };
}
