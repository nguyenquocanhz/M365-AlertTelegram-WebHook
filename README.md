# M365-AlertTelegram-WebHook

Theo dõi **mailbox nội bộ** (Microsoft 365) qua Microsoft Graph, lọc mail theo
**từ khóa**, rồi gửi cảnh báo kèm **tiêu đề / người gửi / link mở mail** sang
**Telegram** và/hoặc **Teams**.

> Công cụ dùng cho mailbox mà tổ chức sở hữu và được phép giám sát
> (hộp dùng chung như `support@`, `sales@`, `info@`). Chạy qua Graph app-only
> nên **admin tenant phải đăng ký app và cấp consent** — hợp lệ, audit và thu hồi được.

## Cài đặt

```bash
pip install -r requirements.txt
cp .env.example .env   # rồi điền giá trị
```

## Cấu hình phía Microsoft 365 (admin làm 1 lần)

1. **Entra ID → App registrations → New registration** (single tenant) → lấy
   `Client ID`, `Tenant ID`.
2. **Certificates & secrets → New client secret** → lấy `Client Secret`.
3. **API permissions → Microsoft Graph → Application → `Mail.Read`** →
   **Grant admin consent**.
4. (Nên làm) Giới hạn app chỉ đọc đúng mailbox cần, qua Exchange Online PowerShell:
   ```powershell
   New-ApplicationAccessPolicy -AppId <client-id> `
     -PolicyScopeGroupId monitored-mailboxes@congty.com `
     -AccessRight RestrictAccess -Description "Chi doc mailbox giam sat"
   ```

## Kênh nhận

- **Telegram:** nhắn `@BotFather` → `/newbot` → lấy `TG_TOKEN`; thêm bot vào group,
  lấy `TG_CHAT` (gọi `getUpdates`).
- **Teams:** channel → **⋯ → Connectors → Incoming Webhook** → copy URL vào
  `TEAMS_WEBHOOK`. (Tenant tắt Connectors thì dùng **Workflows** để lấy URL.)

Chọn kênh bằng biến `CHANNELS` (`telegram`, `teams`, hoặc `telegram,teams`).

## Chạy

```bash
# nạp biến từ .env rồi:
python src/main.py
```

Lần chạy đầu chỉ đồng bộ vị trí (không gửi mail cũ). `delta_state.json` nhớ
điểm đã đọc → restart không trùng, không sót.

## Chạy bằng Docker

Đã có `Dockerfile` + `docker-compose.yml`. Trạng thái delta lưu ra thư mục
`./data` (volume) nên restart container không gửi trùng.

### Dùng docker compose (khuyến nghị)

```bash
cp .env.example .env     # điền giá trị thật
docker compose up -d --build        # build + chạy nền
docker compose logs -f              # xem log
docker compose down                 # dừng
```

Sửa `.env` xong thì nạp lại:

```bash
docker compose up -d --build
```

### Chạy bằng docker thuần (không compose)

```bash
docker build -t m365-alert-telegram-webhook .

docker run -d --name m365-alert --restart unless-stopped \
  --env-file .env \
  -e STATE_FILE=/data/delta_state.json \
  -v "$(pwd)/data:/data" \
  m365-alert-telegram-webhook

docker logs -f m365-alert          # xem log
docker rm -f m365-alert            # dừng + xóa container
```

> Windows PowerShell: thay `$(pwd)` bằng `${PWD}`.

## Test không cần M365 Business

Có 3 cách, từ nhanh tới đầy đủ.

### Cách 1 — Chỉ test gửi Telegram/Teams (nhanh nhất)

Không đụng tới Graph. Gửi 1 mail mẫu thẳng ra kênh:

```bash
export CHANNELS=telegram TG_TOKEN=... TG_CHAT=...
python tests/send_sample.py
```

- **Telegram** hoàn toàn free (chỉ cần tạo bot qua `@BotFather`).
- **Teams** không có cũng test được: đổi `TEAMS_WEBHOOK` thành một URL
  [webhook.site](https://webhook.site) để xem đúng JSON card gửi đi.

### Cách 2 — Test end-to-end bằng mock Graph (không cần mailbox thật)

Giả lập endpoint delta của Graph bằng server nội bộ:

```bash
# Terminal 1: chạy mock
python tests/mock_graph.py

# Terminal 2: chạy app trỏ vào mock
MOCK=1 GRAPH_BASE=http://localhost:8080/v1.0 \
  CHANNELS=telegram TG_TOKEN=... TG_CHAT=... \
  KEYWORDS="báo giá" POLL_SEC=5 python src/main.py
```

`MOCK=1` bỏ qua đăng nhập Microsoft; mock trả 1 mail mới có từ khóa để app
lọc và bắn cảnh báo. Chạy lại từ đầu thì xoá `delta_state.json`.

### Cách 3 — Dùng tenant thật MIỄN PHÍ (test đúng Graph)

Đăng ký **[Microsoft 365 Developer Program](https://developer.microsoft.com/microsoft-365/dev-program)**:
nhận sandbox **E5 free 90 ngày (tự gia hạn)**, có sẵn ~25 user + mailbox thật.
Làm app registration + `Mail.Read` trên tenant này y như production — đây là
cách kiểm thử sát thực tế nhất mà không tốn tiền.

## Biến môi trường

| Biến | Ý nghĩa |
|---|---|
| `TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` | App registration |
| `MAILBOX` | Mailbox cần theo dõi |
| `CHANNELS` | `telegram`, `teams` hoặc cả hai |
| `TG_TOKEN` / `TG_CHAT` | Telegram bot + group |
| `TEAMS_WEBHOOK` | Incoming Webhook URL |
| `KEYWORDS` | Từ khóa, phân cách bằng dấu phẩy (trống = lấy tất cả) |
| `SCAN_BODY` | `1` = lọc cả nội dung, không chỉ tiêu đề |
| `POLL_SEC` | Chu kỳ kiểm tra (giây) |
| `MOCK` | `1` = chế độ test, bỏ qua đăng nhập Microsoft |
| `GRAPH_BASE` | Đổi endpoint Graph (vd trỏ mock server khi test) |
