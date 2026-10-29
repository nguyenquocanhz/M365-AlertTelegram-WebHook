"""
M365 → Telegram/Teams alert.

Đọc mailbox nội bộ qua Microsoft Graph (app-only, Mail.Read + admin consent),
lọc theo từ khóa, rồi gửi cảnh báo kèm tiêu đề / người gửi / link sang
Telegram và/hoặc Teams.
"""
import json
import os
import pathlib
import sys
import time

import msal
import requests

import notifiers

try:                                   # in tiếng Việt không lỗi trên Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- Cấu hình (đặt qua biến môi trường / file .env) ----
MOCK = os.environ.get("MOCK", "0") == "1"       # test không cần M365 thật
TENANT = os.environ.get("TENANT_ID", "")
CLIENT = os.environ.get("CLIENT_ID", "")
SECRET = os.environ.get("CLIENT_SECRET", "")
MAILBOX = os.environ.get("MAILBOX", "test@example.com")  # vd: support@congty.com

CHANNELS = [c.strip().lower() for c in
            os.environ.get("CHANNELS", "telegram").split(",") if c.strip()]
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
TEAMS_HOOK = os.environ.get("TEAMS_WEBHOOK", "")

KEYWORDS = [k.strip().lower() for k in
            os.environ.get("KEYWORDS", "").split(",") if k.strip()]
SCAN_BODY = os.environ.get("SCAN_BODY", "0") == "1"
POLL_SEC = int(os.environ.get("POLL_SEC", "30"))
STATE_FILE = pathlib.Path(os.environ.get("STATE_FILE", "delta_state.json"))

# Cho phép trỏ sang mock server khi test (vd http://localhost:8080/v1.0)
GRAPH = os.environ.get("GRAPH_BASE", "https://graph.microsoft.com/v1.0")


def get_token():
    if MOCK:                       # test: không gọi Microsoft thật
        return "mock-token"
    app = msal.ConfidentialClientApplication(
        CLIENT, authority=f"https://login.microsoftonline.com/{TENANT}",
        client_credential=SECRET)
    r = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in r:
        raise RuntimeError(r.get("error_description", r))
    return r["access_token"]


def matched(msg):
    if not KEYWORDS:
        return True
    text = (msg.get("subject") or "").lower()
    if SCAN_BODY:
        text += " " + (msg.get("bodyPreview") or "").lower()
    return any(k in text for k in KEYWORDS)


def notify(msg):
    if "telegram" in CHANNELS:
        notifiers.send_telegram(TG_TOKEN, TG_CHAT, msg, MAILBOX)
    if "teams" in CHANNELS:
        notifiers.send_teams(TEAMS_HOOK, msg, MAILBOX)


def load_delta():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text()).get("delta")
    return None


def save_delta(link):
    STATE_FILE.write_text(json.dumps({"delta": link}))


def run():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}",
               "Prefer": "odata.maxpagesize=50"}
    delta_link = load_delta()
    first_sync = delta_link is None   # lần đầu chỉ đồng bộ, không spam mail cũ
    url = delta_link or f"{GRAPH}/users/{MAILBOX}/mailFolders/inbox/messages/delta"
    print(f"Bắt đầu theo dõi {MAILBOX} | kênh={CHANNELS} | từ khóa={KEYWORDS or 'tất cả'}")

    while True:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 401:
            token = get_token()
            headers["Authorization"] = f"Bearer {token}"
            continue
        r.raise_for_status()
        data = r.json()

        for m in data.get("value", []):
            if "@removed" in m or first_sync:
                continue
            if matched(m):
                try:
                    notify(m)
                    print("Đã gửi:", m.get("subject"))
                except Exception as e:
                    print("Lỗi gửi cảnh báo:", e)

        if "@odata.nextLink" in data:
            url = data["@odata.nextLink"]
            continue
        if "@odata.deltaLink" in data:
            url = data["@odata.deltaLink"]
            save_delta(url)
        first_sync = False
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    run()
