#!/usr/bin/env python3
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError, URLError

PORT = 8000


OPENER = build_opener(ProxyHandler({}))


def forward_json(url: str, method: str = "GET", body: dict | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url=url, method=method, data=data, headers=headers)
    with OPENER.open(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.status, resp.read().decode(charset)


class AppHandler(SimpleHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict | list | str):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if isinstance(payload, (dict, list)):
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.wfile.write(str(payload).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/upbit/markets":
                status, body = forward_json("https://api.upbit.com/v1/market/all?isDetails=false")
                return self._send_json(status, body)
            if parsed.path == "/api/upbit/ticker":
                qs = parse_qs(parsed.query)
                markets = qs.get("markets", [""])[0]
                if not markets:
                    return self._send_json(400, {"error": "markets query is required"})
                target = f"https://api.upbit.com/v1/ticker?{urlencode({'markets': markets})}"
                status, body = forward_json(target)
                return self._send_json(status, body)
            if parsed.path == "/api/upbit/wallet-status":
                status, body = forward_json("https://api.upbit.com/v1/status/wallet")
                return self._send_json(status, body)
            if parsed.path == "/api/bithumb/ticker-all-krw":
                status, body = forward_json("https://api.bithumb.com/public/ticker/ALL_KRW")
                return self._send_json(status, body)
            if parsed.path == "/api/bithumb/assetsstatus-all":
                status, body = forward_json("https://api.bithumb.com/public/assetsstatus/ALL")
                return self._send_json(status, body)

            return super().do_GET()
        except HTTPError as e:
            self._send_json(e.code, {"error": f"upstream http error: {e.code}"})
        except URLError as e:
            self._send_json(502, {"error": f"upstream connection error: {e.reason}"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/telegram/send":
            return self._send_json(404, {"error": "not found"})

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len).decode("utf-8")
            payload = json.loads(raw) if raw else {}
            bot_token = payload.get("botToken", "").strip()
            chat_id = str(payload.get("chatId", "")).strip()
            text = payload.get("text", "")

            if not bot_token or not chat_id or not text:
                return self._send_json(400, {"error": "botToken, chatId, text are required"})

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            body = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
            status, response_body = forward_json(url, method="POST", body=body)
            return self._send_json(status, response_body)
        except HTTPError as e:
            self._send_json(e.code, {"error": f"telegram http error: {e.code}"})
        except URLError as e:
            self._send_json(502, {"error": f"telegram connection error: {e.reason}"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), AppHandler)
    print(f"Serving on http://127.0.0.1:{PORT}")
    server.serve_forever()
