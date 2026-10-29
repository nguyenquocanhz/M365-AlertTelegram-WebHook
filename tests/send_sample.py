"""Gửi 1 mail mẫu thẳng sang Telegram/Teams — test delivery, không cần M365.

Chạy:
  export CHANNELS=telegram TG_TOKEN=... TG_CHAT=...
  python tests/send_sample.py
"""
import os
import sys

try:                                   # in tiếng Việt không lỗi trên Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import notifiers  # noqa: E402

SAMPLE = {
    "subject": "Báo giá hợp đồng tháng 10",
    "from": {"emailAddress": {
        "name": "Nguyễn Văn A", "address": "a.nguyen@khachhang.com"}},
    "bodyPreview": "Kính gửi anh/chị, em gửi báo giá đơn hàng... (nội dung mẫu để test).",
    "webLink": "https://outlook.office.com/mail/inbox/id/EXAMPLE",
}

mailbox = os.environ.get("MAILBOX", "support@congty.com")
channels = [c.strip().lower() for c in
            os.environ.get("CHANNELS", "telegram").split(",") if c.strip()]

if "telegram" in channels:
    notifiers.send_telegram(os.environ["TG_TOKEN"], os.environ["TG_CHAT"],
                            SAMPLE, mailbox)
    print("Đã gửi Telegram")
if "teams" in channels:
    notifiers.send_teams(os.environ["TEAMS_WEBHOOK"], SAMPLE, mailbox)
    print("Đã gửi Teams")
