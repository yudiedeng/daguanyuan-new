#!/usr/bin/env python3
"""用 Tripo API 把三视图生成 3D 模型（.glb）。

用法：
  export TRIPO_API_KEY=tsk_xxx        # 或在仓库根目录 .env 里写 TRIPO_API_KEY=...
  python3 tools/tripo_generate.py ref/baoyu            # 多视图：front/side/back.png
  python3 tools/tripo_generate.py ref/baoyu --single   # 只用正面图

产物保存为 models/<目录名>.glb。只用标准库，无需安装依赖。
"""
import json, os, sys, time, uuid, urllib.request, urllib.error

API = "https://api.tripo3d.ai/v2/openapi"


def load_key():
    key = os.environ.get("TRIPO_API_KEY")
    env = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not key and os.path.exists(env):
        for line in open(env):
            if line.startswith("TRIPO_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("缺少 TRIPO_API_KEY（环境变量或 .env）")
    return key


def call(method, path, key, body=None, headers=None):
    req = urllib.request.Request(API + path, data=body, method=method,
                                 headers={"Authorization": f"Bearer {key}", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:500]}")
    if res.get("code") != 0:
        sys.exit(f"{method} {path} -> {res}")
    return res["data"]


def upload(path, key):
    boundary = uuid.uuid4().hex
    data = open(path, "rb").read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: image/png\r\n\r\n").encode() \
        + data + f"\r\n--{boundary}--\r\n".encode()
    d = call("POST", "/upload", key, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print("uploaded", path)
    return {"type": "png", "file_token": d["image_token"]}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    folder = sys.argv[1].rstrip("/")
    single = "--single" in sys.argv
    key = load_key()

    front = upload(os.path.join(folder, "front.png"), key)
    if single:
        task = {"type": "image_to_model", "file": front}
    else:
        # Tripo 多视图顺序为 [front, left, back, right]，缺的视图传 {}。
        # 参考图的侧面像人物朝画面右侧，露出的是人物右侧，放在 right 位。
        side = os.path.join(folder, "side.png")
        back = os.path.join(folder, "back.png")
        task = {"type": "multiview_to_model", "files": [
            front, {},
            upload(back, key) if os.path.exists(back) else {},
            upload(side, key) if os.path.exists(side) else {},
        ]}
    task.update({"texture": True, "pbr": True})

    tid = call("POST", "/task", key, json.dumps(task).encode(), {"Content-Type": "application/json"})["task_id"]
    print("task", tid)
    while True:
        d = call("GET", f"/task/{tid}", key)
        print(f"  {d['status']} {d.get('progress', 0)}%")
        if d["status"] == "success":
            break
        if d["status"] in ("failed", "cancelled", "banned", "expired", "unknown"):
            sys.exit(f"任务失败：{d}")
        time.sleep(5)

    out = d.get("output", {})
    url = out.get("pbr_model") or out.get("model") or out.get("base_model")
    if isinstance(url, dict):
        url = url.get("url")
    dest = os.path.join(os.path.dirname(__file__), "..", "models", os.path.basename(folder) + ".glb")
    urllib.request.urlretrieve(url, dest)
    print("saved", os.path.normpath(dest))
    if out.get("rendered_image"):
        print("preview", out["rendered_image"])


if __name__ == "__main__":
    main()
