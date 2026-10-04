#!/usr/bin/env python3
"""用 Tripo 文字生成 3D 道具（.glb）。
用法：python3 tools/tripo_text.py tools/props.json out_dir [name ...]
props.json：{"名": {"prompt": "...", "faces": 8000}, ...}；只生成 out_dir 里还没有的。
鉴权：TRIPO_API_KEY 环境变量 / .env；云端会话由代理自动注入，可不设。"""
import json, os, sys, time, urllib.request, urllib.error, concurrent.futures as cf
API = "https://api.tripo3d.ai/v2/openapi"
KEY = os.environ.get("TRIPO_API_KEY", "proxy")

def call(method, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: res = json.load(r)
    if res.get("code") != 0: raise RuntimeError(res)
    return res["data"]

def gen(name, spec, out):
    dst = os.path.join(out, name + ".glb")
    if os.path.exists(dst): return name, "exists"
    tf = os.path.join(out, name + ".task")   # 记下任务号：下载失败时重跑只取结果，不重复扣积分
    tid = open(tf).read().strip() if os.path.exists(tf) else None
    if not tid:
      tid = call("POST", "/task", {"type": "text_to_model", "prompt": spec["prompt"],
                                 "negative_prompt": spec.get("neg", "low quality, base, ground plane, text"),
                                 "face_limit": spec.get("faces", 8000), "texture": True, "pbr": True})["task_id"]
      open(tf, "w").write(tid)
    while True:
        time.sleep(8); d = call("GET", f"/task/{tid}")
        if d["status"] in ("success",): break
        if d["status"] in ("failed", "cancelled", "banned", "expired", "unknown"): return name, "FAILED " + d["status"]
    o = d["output"]; url = o.get("pbr_model") or o.get("model") or o.get("base_model")
    urllib.request.urlretrieve(url, dst)
    if o.get("rendered_image"): urllib.request.urlretrieve(o["rendered_image"], os.path.join(out, name + ".webp"))
    return name, f"ok {os.path.getsize(dst)//1024}KB"

if __name__ == "__main__":
    props = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    names = sys.argv[3:] or list(props)
    with cf.ThreadPoolExecutor(6) as ex:
        for f in cf.as_completed([ex.submit(gen, n, props[n], out) for n in names]):
            try: print(*f.result(), flush=True)
            except Exception as e: print("ERR", e, flush=True)
