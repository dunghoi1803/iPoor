# iPOOR Backend (FastAPI)

Backend dịch vụ cho iPOOR, dùng FastAPI + MySQL. Hỗ trợ các module: xác thực, quản lý hộ, chính sách, nhật ký hoạt động, thu thập dữ liệu, upload file.

## Cấu trúc
- `app/config.py`: cấu hình từ biến môi trường.
- `app/database.py`: kết nối SQLAlchemy.
- `app/constants.py`: enums chung (role, trạng thái).
- `app/models/`: định nghĩa bảng.
- `app/schemas/`: Pydantic schemas.
- `app/routers/`: tuyến API (auth, households, policies, activity logs, data collections, health, files).
- `app/utils/security.py`: hash mật khẩu, tạo JWT.
- `app/main.py`: bootstrap app.

## Thiết lập môi trường
1. Copy `.env.example` thành `.env`, cập nhật `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `JWT_SECRET`, `ALLOWED_ORIGINS`, `UPLOAD_DIR`.
   - DB host: nếu DB chạy trong compose, dùng `DB_HOST=db`; nếu DB trên host và app trong container, dùng `host.docker.internal`.
   - Admin seed: `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME`.
   - CORS: `ALLOWED_ORIGINS` là danh sách domain cách nhau dấu phẩy (ví dụ `http://localhost:3000,http://127.0.0.1:3000`). Dùng `*` chỉ khi dev.
   - Upload: `UPLOAD_DIR` thư mục lưu file (mặc định `uploads`).
2. Cài đặt:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # hoặc .\.venv\Scripts\activate trên Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Docker
- Build/run với MySQL kèm theo:
  ```bash
  cd backend
  docker-compose up --build
  ```
- Nếu dùng MySQL bên ngoài, có thể chỉ chạy app:
  ```bash
  docker build -t ipoor-api .
  docker run --env-file .env -p 8000:8000 ipoor-api
  ```

## Migration (Alembic)
- Tạo DB schema trống `ipoor` trước (đã có). Chạy migration và seed admin:
  ```bash
  cd backend
  alembic upgrade head
  ```
- Mỗi thay đổi schema mới: `alembic revision --autogenerate -m "describe change"` rồi `alembic upgrade head`.
- Lưu ý: bcrypt tối đa 72 byte; giữ `ADMIN_PASSWORD` ngắn/gọn.

## Seed dữ liệu mẫu
- Thêm 5 hộ mẫu:
  ```bash
  cd backend
  python -m app.seeds.sample_households
  ```
- Thêm mẫu chính sách/báo cáo:
  ```bash
  cd backend
  python -m app.seeds.sample_policies
  ```

## Upload file
- Thư mục upload: `UPLOAD_DIR` (mặc định `uploads`), serve tĩnh tại `/files`.
- Endpoint: `POST /files/upload` (JWT), nhận PDF/PNG/JPEG, trả `url` để gắn vào `attachment_url` của policy.

## API chính
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET/POST/PUT/DELETE /households`
- `GET/POST/PUT/DELETE /policies`
- `GET/POST /activity-logs`
- `GET/POST/PUT /data-collections`
- `GET /health`

## Ghi chú triển khai
- Dùng JWT, cần `JWT_SECRET` mạnh. Mật khẩu hash bằng bcrypt.
- Tránh số/chuỗi magic: dùng constants/enums trong `app/constants.py`.
