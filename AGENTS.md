# AGENTS.md — Kịch bản cho AI Agent

Playbook để một AI agent dựng, test và chạy hệ thống **cảnh báo mail M365 theo
từ khóa → Telegram/Teams**. Đọc hết phần "Nguyên tắc" trước khi làm bất cứ bước nào.

---

## 0. Nguyên tắc bắt buộc (guardrails)

1. **Chỉ áp dụng cho mailbox mà tổ chức sở hữu và được phép giám sát** — hộp dùng
   chung như `support@`, `sales@`, `info@`. KHÔNG dùng để đọc lén hộp thư cá nhân
   của người khác, KHÔNG forward OTP/mã xác thực của bên thứ ba.
2. **Phải qua admin consent.** App Graph app-only cần admin của tenant cấp quyền
   `Mail.Read` → hợp lệ, audit và thu hồi được. Nếu người dùng không phải admin,
   dừng lại và yêu cầu admin thực hiện bước đăng ký app.
3. **Không bao giờ commit secret.** `CLIENT_SECRET`, `TG_TOKEN`, `TEAMS_WEBHOOK`
   chỉ nằm trong `.env` (đã gitignore). Nếu lỡ lộ → xoay (rotate) ngay.
4. **Giới hạn phạm vi mailbox** bằng Application Access Policy (bước 4B). Mặc định
   app-only `Mail.Read` đọc được MỌI mailbox trong tenant — phải thu hẹp.
5. Ưu tiên **test bằng MOCK trước** khi đụng tenant thật.

---

## 1. Mục tiêu & kiến trúc

```
Graph API (đọc mailbox, delta) → lọc từ khóa → Telegram Bot API / Teams webhook
```

Thành phần trong repo:
- `src/main.py` — vòng lặp poll Graph (delta), lọc từ khóa, gọi notifier.
- `src/notifiers.py` — gửi Telegram (HTML) và Teams (Adaptive Card), kèm
  tiêu đề / người gửi / link (`webLink`).
- `tests/mock_graph.py` — giả lập endpoint Graph để test end-to-end.
- `tests/send_sample.py` — gửi 1 mail mẫu thẳng ra kênh.

---

## 2. Thông tin cần thu thập từ người dùng

Hỏi và điền vào `.env` (copy từ `.env.example`):

| Biến | Lấy ở đâu | Bắt buộc khi |
|---|---|---|
| `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET` | App registration (bước 4) | Chạy thật |
| `MAILBOX` | Địa chỉ hộp cần theo dõi | Luôn |
| `CHANNELS` | `telegram`, `teams`, hoặc `telegram,teams` | Luôn |
| `TG_TOKEN`, `TG_CHAT` | BotFather + getUpdates (bước 5) | Dùng Telegram |
| `TEAMS_WEBHOOK` | Incoming Webhook/Workflows (bước 6) | Dùng Teams |
| `KEYWORDS` | Từ khóa, phân tách bằng dấu phẩy (trống = tất cả) | Tùy |
| `SCAN_BODY` | `1` = dò cả nội dung | Tùy |

---

## 3. Cài môi trường

```bash
cd M365-AlertTelegram-WebHook
pip install -r requirements.txt
cp .env.example .env     # rồi điền giá trị
```
**Verify:** `python -c "import msal, requests; print('ok')"` in ra `ok`.

---

## 4. Thiết lập Microsoft 365 (admin, 1 lần)

Nếu chưa có tenant: đăng ký free tại
https://developer.microsoft.com/en-us/microsoft-365/dev-program (E5 90 ngày).

**4A. Đăng ký app**
1. Vào https://entra.microsoft.com → App registrations → New registration
   (Single tenant). Lưu `Application (client) ID` và `Directory (tenant) ID`.
2. Certificates & secrets → New client secret → lưu **Value** ngay (chỉ hiện 1 lần).
3. API permissions → Add → Microsoft Graph → **Application permissions** →
   `Mail.Read` → **Grant admin consent**.

**4B. Giới hạn phạm vi mailbox (bắt buộc)** — Exchange Online PowerShell:
```powershell
New-ApplicationAccessPolicy -AppId <CLIENT_ID> `
  -PolicyScopeGroupId monitored-mailboxes@congty.com `
  -AccessRight RestrictAccess -Description "Chi doc mailbox giam sat"
```
(`monitored-mailboxes@` là mail-enabled security group chứa các mailbox cần theo dõi.)

**Verify:** mở https://developer.microsoft.com/graph/graph-explorer, đăng nhập
tenant, chạy `GET /users/<MAILBOX>/mailFolders/inbox/messages?$top=1` → trả 200.

---

## 5. Thiết lập Telegram (nếu dùng)

1. Nhắn https://t.me/BotFather → `/newbot` → lấy `TG_TOKEN`.
2. Tạo group, thêm bot vào, gửi 1 tin bất kỳ trong group.
3. Mở `https://api.telegram.org/bot<TG_TOKEN>/getUpdates` → lấy `chat.id` → `TG_CHAT`.

**Verify:** `python tests/send_sample.py` (với `CHANNELS=telegram`) → group nhận card.

---

## 6. Thiết lập Teams (nếu dùng)

- Channel → ⋯ → Connectors → Incoming Webhook → copy URL vào `TEAMS_WEBHOOK`.
- Nếu tenant tắt Connectors: dùng Workflows
  https://support.microsoft.com/en-us/office/8ae491c7-0394-4861-ba59-055e33f75498

**Verify (không cần Teams):** đặt `TEAMS_WEBHOOK` = 1 URL từ https://webhook.site
rồi chạy `tests/send_sample.py` → xem JSON card.

---

## 7. Test không cần M365 (làm trước khi chạy thật)

**Chỉ test gửi kênh:**
```bash
CHANNELS=telegram TG_TOKEN=... TG_CHAT=... python tests/send_sample.py
```

**Test end-to-end bằng mock Graph:**
```bash
# Terminal 1
python tests/mock_graph.py
# Terminal 2
MOCK=1 GRAPH_BASE=http://localhost:8080/v1.0 \
  CHANNELS=telegram TG_TOKEN=... TG_CHAT=... \
  KEYWORDS="báo giá" POLL_SEC=5 python src/main.py
```
**Kỳ vọng:** bỏ qua mail cũ ở lần đồng bộ đầu, sau đó gửi đúng 1 cảnh báo
"Báo giá hợp đồng mới" có tiêu đề + người gửi + link. Chạy lại → xoá `delta_state.json`.

---

## 8. Chạy thật

```bash
# đã điền đủ TENANT_ID/CLIENT_ID/CLIENT_SECRET/MAILBOX vào .env
python src/main.py
```
Hoặc Docker:
```bash
docker compose up -d --build
docker compose logs -f
```
**Verify:** gửi 1 mail có từ khóa tới `MAILBOX` → trong ~`POLL_SEC` giây kênh nhận cảnh báo.

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| `invalid_client` / `AADSTS7000215` | `CLIENT_SECRET` sai hoặc hết hạn |
| `403 ErrorAccessDenied` khi đọc mail | Chưa Grant admin consent, hoặc bị Application Access Policy chặn mailbox |
| Không có cảnh báo | `KEYWORDS` không khớp; thử `SCAN_BODY=1` hoặc để trống `KEYWORDS` |
| Gửi trùng sau restart | Mất `delta_state.json` (map volume `./data` khi chạy Docker) |
| Log crash UTF-8 trên Windows | Đã xử lý bằng reconfigure stdout; chạy Python 3.9+ |

---

## 10. Checklist hoàn tất

- [ ] `.env` đã điền, KHÔNG commit
- [ ] Admin consent `Mail.Read` đã cấp
- [ ] Application Access Policy đã giới hạn mailbox
- [ ] Test MOCK pass
- [ ] Test gửi kênh pass
- [ ] Chạy thật nhận được cảnh báo
- [ ] (Nếu Docker) volume `./data` giữ `delta_state.json`

---

## Link tham khảo

- M365 Developer Program: https://developer.microsoft.com/en-us/microsoft-365/dev-program
- Đăng ký app: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
- Graph app-only auth: https://learn.microsoft.com/en-us/graph/auth-v2-service
- Message delta: https://learn.microsoft.com/en-us/graph/api/message-delta
- Giới hạn mailbox: https://learn.microsoft.com/en-us/graph/auth-limit-mailbox-access
- Graph Explorer: https://developer.microsoft.com/en-us/graph/graph-explorer
- Telegram Bot API: https://core.telegram.org/bots/api
- Teams Incoming Webhook: https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
- Adaptive Cards Designer: https://adaptivecards.io/designer/
- webhook.site: https://webhook.site
