# Portfolio — hướng dẫn cập nhật

Cấu trúc:
- `index.html`      giao diện (không cần sửa)
- `data/site.js`    tên, email, mạng xã hội, đoạn About, Contact
- `data/categories.js`  các category hiện trên trang chủ (slider) — mỗi category là một gallery ảnh
- `data/projects.js`    danh sách project
- `images/`         (tuỳ chọn) thư mục ảnh của bạn
- `download-images.py`  tải toàn bộ ảnh từ web cũ về `images/` và đổi đường dẫn trong data sang ảnh local

## Thêm project mới
Mở `data/projects.js`, thêm một khối vào ĐẦU danh sách (project mới nhất lên trước):

```js
{
  "slug": "ten-du-an",              // không dấu, không khoảng trắng — dùng làm link
  "title": "Tên dự án",
  "year": 2026,
  "client": "Tên khách hàng",
  "description": "Một hai câu mô tả.",
  "credits": { "Stylist": "Tên", "Assistant": "Tên" },
  "cover": "images/ten-du-an/01.jpg",
  "images": [
    { "src": "images/ten-du-an/01.jpg", "w": 2000, "h": 3000 },
    { "src": "images/ten-du-an/02.jpg", "w": 3000, "h": 2000 }
  ]
},
```
`w`/`h` là kích thước ảnh (pixel); ảnh ngang (w > h) tự trải hết bề ngang.

## Thêm category
Mở `data/categories.js`, thêm `{ "slug", "name", "cover", "images": [...] }` — cùng định dạng ảnh như trên.

## Xem thử
Mở `index.html` bằng trình duyệt là chạy được ngay, không cần server.

## Đưa lên mạng (miễn phí)
GitHub Pages / Cloudflare Pages / Netlify: kéo thả cả thư mục này lên là xong.
