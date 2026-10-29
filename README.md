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
