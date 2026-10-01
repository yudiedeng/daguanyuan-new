"""检查道路：每条路在哪里跨水（会自动架桥）、是否穿过院落。用法：python3 tools/layout/check_paths.py"""
import json, os, numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
a = np.asarray(Image.open(os.path.join(ROOT, 'tex', 'layout.png'))).astype(float)
W = a[..., 0] / 255; H = a[..., 1] / 255 * 12
S = json.load(open(os.path.join(HERE, 'sites.json')))
P = json.load(open(os.path.join(HERE, 'paths.json')))
def cr(pts, step=0.8):
    pts = [pts[0]] + pts + [pts[-1]]; out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = map(np.array, pts[i - 1:i + 3]); n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for k in range(n):
            t = k / n; out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(pts[-2])); return out
def at(g, x, z): return g[int(round(z + 200)), int(round(x + 170))]
for k, p in enumerate(P):
    sp = cr(p['pts']); wet = [at(W, x, z) > 0.37 for x, z in sp]; runs = []; s = None
    for i, w in enumerate(wet + [False]):
        if w and s is None: s = i
        if not w and s is not None:
            runs.append((round(len(sp[s:i]) * 0.8, 1), tuple(np.round(sp[(s + i) // 2]).astype(int)))); s = None
    hits = set()
    for x, z in sp[3:-3]:
        for st in S:
            if st['id'] in ('rock',): continue
            if abs(x - st['x']) < st['hw'] - 1 and abs(z - st['z']) < st['hd'] - 1: hits.add(st['id'])
    hmax = max(at(H, x, z) for x, z in sp)
    print(f"#{k} {p.get('name','')}: 跨水 {runs}  穿院 {sorted(hits)}  最高 {hmax:.1f}m")
