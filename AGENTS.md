# AGENTS.md — hướng dẫn cho agent (Google Antigravity)

Site portfolio nhiếp ảnh SLOWP: tĩnh, không build, không server. Mở `index.html` là chạy.

## Cấu trúc
- `index.html` — giao diện + router theo hash (`#/`, `#/projects`, `#/work/<slug>`, `#/category/<slug>`, `#/about`, `#/contact`).
- `data/site.js` — mọi nội dung/SEO của site và trang About: `about`, `tagline`, `services`, `clients`, `portrait`, `social`, `seo_description`, `url`, `job_title`, `area`, `about_cta`.
- `data/projects.js`, `data/categories.js` — dữ liệu project và category (định dạng xem `README.md`).
- `images/` — ảnh local; `download-images.py` tải ảnh từ Pixieset cũ.

## Quy tắc
- Sửa nội dung ở `data/*.js`, chỉ sửa `index.html` khi đổi giao diện/logic.
- Giữ phong cách: nền kem (`--bg #f6f1e6`), chữ nhỏ, tối giản, nhiều khoảng trắng. Dùng biến CSS ở `:root`.
- Ảnh luôn có `width`, `height`, `alt` và `loading="lazy"` (trừ ảnh đầu trang).
- Trang About: render bởi `renderAbout()`; SEO per-route qua `setSeo()` và JSON-LD Person (`personSchema()`).
- Không thêm framework/bundler. Thêm project theo hướng dẫn trong `README.md`.
- Khi đổi `url` trong `site.js` thành domain thật, canonical và schema tự cập nhật.
