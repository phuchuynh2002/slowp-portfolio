# Portfolio — hướng dẫn cập nhật

Cấu trúc:
- `index.html`      giao diện (không cần sửa)
- `data/site.js`    tên, email, mạng xã hội, đoạn About, Contact
- `data/categories.js`  các category hiện trên trang chủ (slider) — mỗi category là một gallery ảnh
- `data/projects.js`    danh sách project
- `images/`         (tuỳ chọn) thư mục ảnh của bạn
- `download-images.py`  tải toàn bộ ảnh từ web cũ về `images/` và đổi đường dẫn trong data sang ảnh local
- `tools/prompt.html`  công cụ riêng: dựng prompt + tạo hình bằng Gemini (xem cuối file)

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

## Hệ thống studio trong Obsidian
`python3 tools/sync-obsidian.py` đọc `data/*.js` và ghi sang vault Obsidian đang mở (hoặc `--vault "/đường/dẫn"`; thêm `--dry-run` để xem trước):
- `Studio/00 - Studio Hub.md` — trang điều hướng, nhúng bảng pipeline, portfolio và khách hàng.
- `Studio/Dự án/` — mỗi project trên site một ghi chú; `Clients/` — mỗi khách hàng một hồ sơ.
- `Studio/Phân tích/Phân tích portfolio.md` — số liệu và các phát hiện cần xử lý.
- `Studio/Bảng dự án.base`, `Studio/Bảng khách hàng.base` — bảng Bases (pipeline, doanh thu, chất lượng dữ liệu).

Chạy lại sau mỗi lần sửa `data/*.js`. Script chỉ thay phần giữa `SITE:BEGIN`/`SITE:END` và các thuộc tính lấy từ site; ghi chú tự viết và các ô `status`, `fee`, `cost`, `shoot_date`… được giữ nguyên. Job chưa lên site: tạo ghi chú mới từ template `Studio - Dự án mới`.

## Prompt studio (công cụ riêng)
Mở `tools/prompt.html` — không có link từ menu portfolio và đã đặt `noindex`.
1. Mở "Cài đặt API", dán Gemini API key (lấy ở https://aistudio.google.com/api-keys). Key chỉ lưu trong trình duyệt của bạn, không nằm trong code.
2. Nhập chủ thể, chọn góc máy / ánh sáng / ống kính… → prompt tự ghép; sửa tay tự do.
3. "AI viết lại": gõ yêu cầu (tiếng Việt cũng được) để AI chỉnh prompt; "Hoàn tác" để quay lại.
4. Chọn tỉ lệ, kích thước, số ảnh, thêm ảnh tham chiếu nếu cần → "Tạo hình" → "Tải về".

Thêm/sửa lựa chọn của bộ dựng prompt: mảng `GROUPS` trong `tools/prompt.html` (`["Nhãn hiển thị", "cụm tiếng Anh đưa vào prompt"]`).
