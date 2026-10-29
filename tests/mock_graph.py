"""Mock Microsoft Graph delta endpoint — test end-to-end không cần M365.

Chạy mock:
  python tests/mock_graph.py            # lắng nghe :8080

Chạy app trỏ vào mock (terminal khác):
  MOCK=1 GRAPH_BASE=http://localhost:8080/v1.0 \
    CHANNELS=telegram TG_TOKEN=... TG_CHAT=... \
    KEYWORDS="báo giá" POLL_SEC=5 python src/main.py

Kịch bản: lần poll đầu trả 1 mail "cũ" (app bỏ qua khi đồng bộ), lần sau trả
1 mail mới có từ khóa -> app gửi cảnh báo, các lần sau không còn mail mới.
Xoá delta_state.json nếu muốn chạy lại từ đầu.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

try:                                   # in tiếng Việt không lỗi trên Windows
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HOST, PORT = "0.0.0.0", 8080


def msg(mid, subject, name, addr, preview):
    return {
        "id": mid, "subject": subject,
        "from": {"emailAddress": {"name": name, "address": addr}},
        "bodyPreview": preview,
        "webLink": f"https://outlook.office.com/mail/inbox/id/{mid}",
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        u = urlparse(self.path)
        if "/delta" not in u.path:
            self.send_response(404)
            self.end_headers()
            return

        token = parse_qs(u.query).get("$deltatoken", ["0"])[0]
        host = self.headers.get("Host", f"localhost:{PORT}")
        base = f"http://{host}{u.path.split('?')[0]}"

        if token == "0":        # mail cũ -> app bỏ qua khi đồng bộ lần đầu
            values = [msg("old1", "Mail cũ bỏ qua", "Cũ",
                          "old@example.com", "mail cũ")]
            nxt = "1"
        elif token == "1":      # mail mới có từ khóa -> sẽ gửi cảnh báo
            values = [msg("new1", "Báo giá hợp đồng mới", "Khách hàng A",
                          "a@khachhang.com",
                          "Nội dung test có từ khóa báo giá, đơn hàng.")]
            nxt = "2"
        else:                   # hết mail mới
            values = []
            nxt = str(int(token) + 1)

        body = {"value": values, "@odata.deltaLink": f"{base}?$deltatoken={nxt}"}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):   # bớt log ồn
        pass


if __name__ == "__main__":
    print(f"Mock Graph: http://localhost:{PORT}/v1.0  (Ctrl+C để dừng)")
    HTTPServer((HOST, PORT), Handler).serve_forever()
