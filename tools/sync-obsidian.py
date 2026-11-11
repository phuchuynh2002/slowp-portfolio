#!/usr/bin/env python3
"""Đồng bộ dữ liệu portfolio (data/*.js) sang vault Obsidian thành hệ thống studio + phân tích.

Chạy:  python3 tools/sync-obsidian.py            (tự tìm vault đang mở trong Obsidian)
       python3 tools/sync-obsidian.py --vault "/đường/dẫn/vault"
       python3 tools/sync-obsidian.py --dry-run  (chỉ in ra, không ghi)

Nguyên tắc an toàn:
- Chỉ ghi vào Studio/, Clients/ và Templates/ của vault.
- Trong mỗi ghi chú, script chỉ thay phần giữa hai dấu SITE:BEGIN / SITE:END và các
  thuộc tính (frontmatter) do site quản lý. Mọi thứ bạn tự viết/tự điền được giữ nguyên.
- File .base và template chỉ được tạo khi chưa có (không ghi đè tuỳ chỉnh của bạn).
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "%% SITE:BEGIN — phần này do tools/sync-obsidian.py ghi, đừng sửa tay %%", "%% SITE:END %%"
PROJECT_DIR = "Studio/Dự án"
CLIENT_DIR = "Clients"
LOW_RES = 1000  # cạnh dài dưới mức này coi là ảnh nhỏ


# ---------- đọc dữ liệu site ----------
def load_js(name):
    """Đọc `window.X = <JSON có comment //>;` thành object Python."""
    text = (ROOT / "data" / name).read_text(encoding="utf-8")
    text = text[text.index("=") + 1:].strip().rstrip(";")
    # bỏ comment // nằm ngoài chuỗi
    out, in_str, esc, i = [], False, False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    clean = re.sub(r",(\s*[}\]])", r"\1", "".join(out))  # dấu phẩy thừa
    return json.loads(clean)


def find_vault(arg):
    if arg:
        return Path(arg).expanduser()
    if os.environ.get("SLOWP_VAULT"):
        return Path(os.environ["SLOWP_VAULT"]).expanduser()
    cfg = Path.home() / "Library/Application Support/obsidian/obsidian.json"
    if cfg.exists():
        vaults = list(json.loads(cfg.read_text(encoding="utf-8")).get("vaults", {}).values())
        vaults.sort(key=lambda v: (not v.get("open"), -v.get("ts", 0)))
        if vaults:
            return Path(vaults[0]["path"])
    sys.exit("Không tìm thấy vault Obsidian. Dùng --vault \"/đường/dẫn/vault\".")


# ---------- ghi chú: frontmatter + khối do site quản lý ----------
def yaml_value(v):
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in v) + "]"
    return json.dumps(str(v), ensure_ascii=False)


def split_note(text):
    """-> (danh sách [key, các dòng thô] của frontmatter, phần thân)."""
    if not text.startswith("---\n"):
        return [], text
    end = text.find("\n---", 4)
    if end == -1:
        return [], text
    entries = []
    for line in text[4:end].split("\n"):
        m = re.match(r"^([^\s#:][^:]*):", line)
        if m:
            entries.append([m.group(1), [line]])
        elif entries:
            entries[-1][1].append(line)  # dòng tiếp nối (danh sách nhiều dòng…)
    return entries, text[end + 4:].lstrip("\n")


def merge_note(path, managed, defaults, block, first_body):
    """managed: thuộc tính luôn cập nhật · defaults: chỉ thêm nếu chưa có · block: khối SITE."""
    block_text = f"{BEGIN}\n{block.strip()}\n{END}"
    if path.exists():
        entries, body = split_note(path.read_text(encoding="utf-8"))
        if BEGIN in body and END in body:
            a, b = body.index(BEGIN), body.index(END) + len(END)
            body = body[:a] + block_text + body[b:]
        else:
            body = block_text + "\n\n" + body
    else:
        entries, body = [], first_body.replace("{{SITE}}", block_text)
    keys = [e[0] for e in entries]
    for k, v in managed.items():
        line = f"{k}: {yaml_value(v)}".rstrip()
        if k in keys:
            entries[keys.index(k)][1] = [line]
        else:
            entries.append([k, [line]])
            keys.append(k)
    for k, v in defaults.items():
        if k not in keys:
            entries.append([k, [f"{k}: {yaml_value(v)}".rstrip()]])
            keys.append(k)
    front = "\n".join(l for _, lines in entries for l in lines)
    return f"---\n{front}\n---\n\n{body.rstrip()}\n"


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|#^\[\]]', " ", s).strip()


# ---------- phân tích ----------
def image_stats(images):
    p = sum(1 for i in images if i["h"] > i["w"])
    l = sum(1 for i in images if i["w"] > i["h"])
    return {
        "images": len(images),
        "portrait": p,
        "landscape": l,
        "square": len(images) - p - l,
        "remote": sum(1 for i in images if i["src"].startswith("http")),
        "low_res": sum(1 for i in images if max(i["w"], i["h"]) < LOW_RES),
    }


def client_of(project, featured):
    if project.get("client"):
        return project["client"]
    title = project["title"]
    for c in featured:
        if title.lower().startswith(c.lower()) or c.lower().startswith(title.lower()):
            return c
    return title


def pct(a, b):
    return round(a * 100 / b) if b else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vault")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    site, projects, categories = load_js("site.js"), load_js("projects.js"), load_js("categories.js")
    vault = find_vault(args.vault)
    if not (vault / ".obsidian").is_dir():
        sys.exit(f"{vault} không phải vault Obsidian (thiếu .obsidian).")
    today = datetime.date.today().isoformat()
    base_url = (site.get("url") or "").rstrip("/")
    featured = site.get("clients", [])
    hidden = {c["slug"]: sum(1 for i in c["images"] if i.get("homeHidden")) for c in categories}
    cat_slugs = {c["slug"] for c in categories}
    writes = {}  # đường dẫn tương đối -> nội dung

    # --- dự án ---
    rows, by_client = [], {}
    for p in projects:
        st = image_stats(p["images"])
        client = client_of(p, featured)
        missing = [label for label, ok in [
            ("năm", bool(p.get("year"))),
            ("client", bool(p.get("client"))),
            ("mô tả", bool(p.get("description"))),
            ("credits", bool(p.get("credits"))),
            ("ảnh local", st["remote"] == 0),
        ] if not ok]
        note = f"{safe_name(p['title'])} - Portfolio"
        row = dict(p=p, st=st, client=client, missing=missing, note=note,
                   hidden=hidden.get(p["slug"], 0), complete=pct(5 - len(missing), 5))
        rows.append(row)
        by_client.setdefault(client, []).append(row)
        url = f"{base_url}/#/work/{p['slug']}" if base_url else ""
        cover = p.get("cover", "")
        managed = {
            "type": "project",
            "on_site": True,
            "client": f"[[{safe_name(client)}]]",
            "slug": p["slug"],
            "year": p.get("year") or "",
            "site_url": url,
            "cover": cover if cover.startswith("http") else "",
            "images": st["images"],
            "portrait": st["portrait"],
            "landscape": st["landscape"],
            "square": st["square"],
            "home_hidden": row["hidden"],
            "low_res": st["low_res"],
            "site_completeness": row["complete"],
            "site_missing": missing,
            "synced": today,
        }
        defaults = {"status": "Đã đăng", "service": "", "shoot_date": "", "fee": "", "cost": "",
                    "deliverables": "", "lead_source": ""}
        block = "\n".join(filter(None, [
            f"![]({cover})" if cover.startswith("http") else "",
            f"**{p['title']}** — {p.get('description') or '_chưa có mô tả trên site_'}",
            "",
            f"- Khách hàng: [[{safe_name(client)}]]",
            f"- Trang trên site: {url}" if url else "",
            f"- Ảnh: {st['images']} (dọc {st['portrait']} · ngang {st['landscape']} · vuông {st['square']})"
            f" · ẩn khỏi trang chủ: {row['hidden']}",
            f"- Dữ liệu site đầy đủ {row['complete']}%"
            + (f" — còn thiếu: {', '.join(missing)}" if missing else ""),
            f"- Sửa tại `data/projects.js` (slug `{p['slug']}`), rồi chạy lại `python3 tools/sync-obsidian.py`",
        ]))
        first = ("{{SITE}}\n\n## Ghi chú sản xuất\n"
                 "- Hub dự án: sao chép [[01 - Mẫu Hub dự án hình ảnh]] nếu cần theo dõi chi tiết\n"
                 "- Brief / moodboard / shot list:\n- Ekip & credits:\n\n"
                 "## Bài học sau buổi chụp\n- Điều hiệu quả:\n- Điều cần làm khác:\n")
        path = f"{PROJECT_DIR}/{note}.md"
        writes[path] = merge_note(vault / path, managed, defaults, block, first)

    # --- khách hàng ---
    tpl = vault / "Bộ não hình ảnh AI/01 - Mẫu hồ sơ thương hiệu.md"
    profile = ""
    if tpl.exists():
        profile = "\n".join(tpl.read_text(encoding="utf-8").split("\n")[1:]).strip()
    all_clients = list(dict.fromkeys(featured + list(by_client)))
    for c in all_clients:
        rs = by_client.get(c, [])
        managed = {
            "type": "client",
            "featured_on_site": c in featured,
            "projects": len(rs),
            "site_images": sum(r["st"]["images"] for r in rs),
            "synced": today,
        }
        defaults = {"industry": "", "relationship": "", "contact": "", "last_job": ""}
        lines = [f"- [[{r['note']}]] — {r['st']['images']} ảnh, dữ liệu {r['complete']}%" for r in rs]
        block = "\n".join([
            "**Trên portfolio:** " + ("có trong \"As featured in\"" if c in featured else "chưa nằm trong \"As featured in\""),
            "",
            *(lines or ["- _Chưa có dự án nào trên site_"]),
        ])
        first = (f"# Hồ sơ thương hiệu — {c}\n\n" + "{{SITE}}\n\n"
                 + (profile or "Điền theo [[01 - Mẫu hồ sơ thương hiệu]].") + "\n")
        path = f"{CLIENT_DIR}/{safe_name(c)}.md"
        writes[path] = merge_note(vault / path, managed, defaults, block, first)

    # --- phân tích ---
    tot = {k: sum(r["st"][k] for r in rows) for k in ("images", "portrait", "landscape", "square", "remote", "low_res")}
    n = len(rows)
    tot_hidden = sum(r["hidden"] for r in rows)
    findings = []

    def add(level, text):
        findings.append(f"- **{level}** — {text}")

    if tot["remote"]:
        add("Rủi ro", f"{tot['remote']}/{tot['images']} ảnh ({pct(tot['remote'], tot['images'])}%) vẫn tải từ máy chủ Pixieset cũ. "
            "Nếu tài khoản Pixieset đóng, site mất ảnh. Chạy `python3 download-images.py` để đưa ảnh về `images/`.")
    for label, key in [("năm", "năm"), ("tên client", "client"), ("credits", "credits"), ("mô tả", "mô tả")]:
        miss = [r["p"]["title"] for r in rows if key in r["missing"]]
        if miss:
            add("Dữ liệu", f"{len(miss)}/{n} dự án thiếu {label}: {', '.join(miss)}. Điền trong `data/projects.js`.")
    no_proj = [c for c in featured if not by_client.get(c)]
    if no_proj:
        add("Lệch nội dung", f"{', '.join(no_proj)} có trong \"As featured in\" nhưng chưa có dự án nào trên site.")
    not_feat = [c for c in by_client if c not in featured]
    if not_feat:
        add("Lệch nội dung", f"{', '.join(not_feat)} có dự án trên site nhưng không nằm trong \"As featured in\" (`clients` ở `data/site.js`).")
    if tot["images"] and pct(tot["portrait"], tot["images"]) >= 75:
        add("Hình ảnh", f"{pct(tot['portrait'], tot['images'])}% ảnh là khổ dọc; chỉ {tot['landscape']} ảnh ngang. "
            "Hợp mobile/social, nhưng thiếu ảnh ngang cho hero, banner web và Open Graph.")
    heavy = [f"{r['p']['title']} ({r['hidden']}/{r['st']['images']})" for r in rows
             if r["st"]["images"] and r["hidden"] / r["st"]["images"] > 0.5]
    if heavy:
        add("Trang chủ", f"Hơn nửa số ảnh bị ẩn khỏi trang chủ ở: {', '.join(heavy)}. "
            "Ổn nếu đó là ảnh không gian ẩn có chủ đích, nhưng dịch vụ \"Space photography\" vì thế ít được thấy ở trang chủ.")
    if tot["low_res"]:
        small = [f"{r['p']['title']} ({r['st']['low_res']})" for r in rows if r["st"]["low_res"]]
        add("Chất lượng", f"{tot['low_res']} ảnh có cạnh dài dưới {LOW_RES}px: {', '.join(small)}. Nên thay bằng bản lớn hơn.")
    orphan = sorted({p["slug"] for p in projects} ^ cat_slugs)
    if orphan:
        add("Dữ liệu", f"Project và category không khớp slug: {', '.join(orphan)}.")
    if not site.get("formspree"):
        add("Liên hệ", "`formspree` trong `data/site.js` còn trống nên form liên hệ chưa có nơi nhận.")
    if not site.get("phone"):
        add("Liên hệ", "Chưa có số điện thoại trong `data/site.js`.")
    services = [s[0] for s in site.get("services", [])]

    table = ["| Dự án | Ảnh | Dọc | Ngang | Vuông | Ẩn trang chủ | Ảnh nhỏ | Dữ liệu đủ | Còn thiếu |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in sorted(rows, key=lambda r: -r["st"]["images"]):
        s = r["st"]
        table.append(f"| [[{r['note']}\\|{r['p']['title']}]] | {s['images']} | {s['portrait']} | {s['landscape']} | "
                     f"{s['square']} | {r['hidden']} | {s['low_res']} | {r['complete']}% | {', '.join(r['missing']) or '—'} |")
    table.append(f"| **Tổng** | **{tot['images']}** | **{tot['portrait']}** | **{tot['landscape']}** | **{tot['square']}** | "
                 f"**{tot_hidden}** | **{tot['low_res']}** | **{pct(sum(r['complete'] for r in rows), n * 100)}%** | |")
    analysis = "\n".join([
        f"_Tính từ `data/*.js` ngày {today}. Chạy lại `python3 tools/sync-obsidian.py` để cập nhật._",
        "",
        "## Tổng quan",
        f"- {n} dự án · {tot['images']} ảnh · {len(all_clients)} khách hàng ({len(featured)} trong \"As featured in\")",
        f"- Khổ ảnh: dọc {pct(tot['portrait'], tot['images'])}% · ngang {pct(tot['landscape'], tot['images'])}% · vuông {pct(tot['square'], tot['images'])}%",
        f"- Ảnh đang hiện ở trang chủ: {tot['images'] - tot_hidden}/{tot['images']}",
        f"- Dịch vụ công bố: {', '.join(services) or '—'}",
        "",
        "## Từng dự án",
        *table,
        "",
        "## Phát hiện",
        *(findings or ["- Không có vấn đề nào theo các quy tắc hiện tại."]),
    ])
    path = "Studio/Phân tích/Phân tích portfolio.md"
    writes[path] = merge_note(vault / path, {"type": "analysis", "synced": today}, {}, analysis,
                              "# Phân tích portfolio\n\n{{SITE}}\n\n## Nhận định của tôi\n- \n")

    # --- hub ---
    hub = "\n".join([
        f"_Đồng bộ từ site ngày {today}: {n} dự án · {tot['images']} ảnh · {len(all_clients)} khách hàng · {len(findings)} phát hiện cần xử lý._",
        "",
        "- Phân tích: [[Phân tích portfolio]]",
        "- Bảng: [[Bảng dự án.base]] · [[Bảng khách hàng.base]]",
        "- Tạo job mới: dùng template [[Studio - Dự án mới]] trong thư mục `Studio/Dự án`",
        "- Quy trình sáng tạo: [[00 - Trung tâm điều hướng]] · [[00 - Quy trình Idea Moodboard Story]]",
        "",
        "## Pipeline",
        "![[Bảng dự án.base#Pipeline]]",
        "",
        "## Portfolio trên site",
        "![[Bảng dự án.base#Portfolio trên site]]",
        "",
        "## Khách hàng",
        "![[Bảng khách hàng.base]]",
    ])
    path = "Studio/00 - Studio Hub.md"
    writes[path] = merge_note(vault / path, {"type": "hub", "synced": today}, {}, hub,
                              "# Studio Hub — Slowp Studio\n\n{{SITE}}\n\n## Việc tuần này\n- [ ] \n")

    # --- file chỉ tạo một lần ---
    once = {
        "Studio/Bảng dự án.base": PROJECT_BASE,
        "Studio/Bảng khách hàng.base": CLIENT_BASE,
        "Templates/Studio - Dự án mới.md": JOB_TEMPLATE,
    }
    for rel, content in once.items():
        if not (vault / rel).exists():
            writes[rel] = content

    changed = 0
    for rel, content in writes.items():
        target = vault / rel
        old = target.read_text(encoding="utf-8") if target.exists() else None
        if old == content:
            continue
        changed += 1
        print(("sẽ ghi  " if args.dry_run else "đã ghi  ") + rel + ("" if old is None else "  (cập nhật)"))
        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    print(f"{changed} file thay đổi, {len(writes) - changed} file giữ nguyên · vault: {vault.name}")


PROJECT_BASE = """filters:
  and:
    - 'type == "project"'
    - not:
        - file.inFolder("Templates")
formulas:
  profit: 'if(fee, fee - if(cost, cost, 0), "")'
  portrait_pct: 'if(images, (portrait / images * 100).round(0), "")'
properties:
  file.name:
    displayName: Dự án
  note.client:
    displayName: Khách hàng
  note.status:
    displayName: Trạng thái
  note.service:
    displayName: Dịch vụ
  note.shoot_date:
    displayName: Ngày chụp
  note.fee:
    displayName: Doanh thu
  note.cost:
    displayName: Chi phí
  formula.profit:
    displayName: Lợi nhuận
  note.lead_source:
    displayName: Nguồn khách
  note.images:
    displayName: Số ảnh
  note.portrait:
    displayName: Dọc
  note.landscape:
    displayName: Ngang
  formula.portrait_pct:
    displayName: "% dọc"
  note.home_hidden:
    displayName: Ẩn trang chủ
  note.low_res:
    displayName: Ảnh nhỏ
  note.site_completeness:
    displayName: "Dữ liệu đủ %"
  note.site_missing:
    displayName: Còn thiếu
  note.site_url:
    displayName: Link site
views:
  - type: table
    name: Pipeline
    groupBy:
      property: note.status
      direction: ASC
    order:
      - file.name
      - note.client
      - note.service
      - note.shoot_date
      - note.fee
      - note.lead_source
    summaries:
      note.fee: Sum
  - type: cards
    name: Portfolio trên site
    filters:
      and:
        - on_site == true
    image: note.cover
    order:
      - file.name
      - note.client
      - note.images
      - note.site_completeness
  - type: table
    name: Chất lượng dữ liệu site
    filters:
      and:
        - on_site == true
    order:
      - file.name
      - note.images
      - note.portrait
      - note.landscape
      - formula.portrait_pct
      - note.home_hidden
      - note.low_res
      - note.site_completeness
      - note.site_missing
      - note.site_url
    sort:
      - property: note.site_completeness
        direction: ASC
    summaries:
      note.images: Sum
      note.home_hidden: Sum
      note.site_completeness: Average
  - type: table
    name: Doanh thu theo khách
    groupBy:
      property: note.client
      direction: ASC
    order:
      - file.name
      - note.status
      - note.shoot_date
      - note.fee
      - note.cost
      - formula.profit
    summaries:
      note.fee: Sum
      note.cost: Sum
      formula.profit: Sum
"""

CLIENT_BASE = """filters:
  and:
    - 'type == "client"'
properties:
  file.name:
    displayName: Khách hàng
  note.featured_on_site:
    displayName: As featured in
  note.projects:
    displayName: Dự án trên site
  note.site_images:
    displayName: Ảnh trên site
  note.industry:
    displayName: Ngành
  note.relationship:
    displayName: Quan hệ
  note.last_job:
    displayName: Job gần nhất
  note.contact:
    displayName: Liên hệ
views:
  - type: table
    name: Khách hàng
    order:
      - file.name
      - note.featured_on_site
      - note.projects
      - note.site_images
      - note.industry
      - note.relationship
      - note.last_job
      - note.contact
    sort:
      - property: note.site_images
        direction: DESC
    summaries:
      note.projects: Sum
      note.site_images: Sum
"""

JOB_TEMPLATE = """---
type: project
on_site: false
client:
status: Lead
service:
shoot_date:
fee:
cost:
deliverables:
lead_source:
---

# {{title}}

> Trạng thái gợi ý: Lead → Báo giá → Đã chốt → Đang chụp → Hậu kỳ → Đã giao → Đã đăng
> `client` ghi dạng "[[Tên ghi chú trong Clients]]"; `fee` và `cost` chỉ ghi số.

## Brief
- Mục tiêu / kênh sử dụng:
- Deliverables & deadline:
- Brief chi tiết: sao chép [[02 - Mẫu brief hình ảnh]]

## Sản xuất
- Hub dự án: sao chép [[01 - Mẫu Hub dự án hình ảnh]]
- Moodboard / shot list / ánh sáng:
- Ekip & credits:

## Bài học sau buổi chụp
- Điều hiệu quả:
- Điều cần làm khác:
"""

if __name__ == "__main__":
    main()
