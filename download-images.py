"""Tải toàn bộ ảnh về thư mục images/ và ghi lại data/*.js trỏ sang ảnh local.
Chạy:  python3 download-images.py   (cần Python 3, không cần cài thêm gì)"""
import json, re, os, urllib.request, urllib.parse
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def load(name):
    txt = open(f"data/{name}.js", encoding="utf-8").read()
    return json.loads(txt[txt.index("=")+1:].rstrip().rstrip(";"))
def save(var, name, obj):
    open(f"data/{name}.js","w",encoding="utf-8").write(f"// Sửa file này để cập nhật.\nwindow.{var} = "+json.dumps(obj, ensure_ascii=False, indent=2)+";\n")

def fetch(url, folder, k):
    if not url.startswith("http"): return url
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1] or ".jpg"
    os.makedirs(f"images/{folder}", exist_ok=True)
    out = f"images/{folder}/{k:02d}{ext}"
    if not os.path.exists(out):
        print("↓", out)
        urllib.request.urlretrieve(url.replace("?format=1500w", "?format=2500w"), out)
    return out

cats = load("categories")
for c in cats:
    for k, i in enumerate(c["images"], 1): i["src"] = fetch(i["src"], c["slug"], k)
    c["cover"] = c["images"][0]["src"]
save("CATEGORIES", "categories", cats)

projs = load("projects")
for p in projs:
    for k, i in enumerate(p["images"], 1): i["src"] = fetch(i["src"], p["slug"], k)
    p["cover"] = fetch(p["cover"], p["slug"], 0)
save("PROJECTS", "projects", projs)
print("Xong. Ảnh nằm trong images/, data đã trỏ sang ảnh local.")
