import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import parse, request

HOST = "127.0.0.1"
PORT = 8000

STATE = {
    "active": False,
    "threshold": 5.0,
    "interval": 5,
    "cooldown": 300,
    "telegram_enabled": False,
    "telegram_token": "",
    "telegram_chat_id": "",
    "ignore_when_binance_spot_futures_gap": False,
    "last_alert_time": 0.0,
}
STATE_LOCK = threading.Lock()

DEFAULT_TIMEOUT = 5
MAX_RETRY = 2
BINANCE_GAP_THRESHOLD = 2.0  # 요청사항: 바이낸스 선물-현물 차이 2% 이상이면 알림 비활성화


def request_json(url: str, params=None, method="GET", payload=None):
    """표준 라이브러리 기반 HTTP 요청 + 가벼운 재시도."""
    last_exc = None
    full_url = url
    if params:
        full_url = f"{url}?{parse.urlencode(params)}"

    body = None
    headers = {"User-Agent": "OM-Monitor/1.0"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    for _ in range(MAX_RETRY + 1):
        try:
            req = request.Request(full_url, data=body, method=method, headers=headers)
            with request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
            time.sleep(0.2)
    raise RuntimeError(str(last_exc))


def get_upbit_price(market: str) -> float:
    data = request_json("https://api.upbit.com/v1/ticker", params={"markets": market})
    return float(data[0]["trade_price"])


def get_bithumb_om_price() -> float:
    data = request_json("https://api.bithumb.com/public/ticker/OM_KRW")
    if data.get("status") != "0000":
        raise RuntimeError(f"Bithumb 오류: {data}")
    return float(data["data"]["closing_price"])


def get_binance_spot_omusdt() -> float:
    data = request_json("https://api.binance.com/api/v3/ticker/price", params={"symbol": "OMUSDT"})
    return float(data["price"])


def get_binance_futures_omusdt() -> float:
    data = request_json("https://fapi.binance.com/fapi/v2/ticker/price", params={"symbol": "OMUSDT"})
    return float(data["price"])


def diff_percent(a: float, b: float) -> float:
    if min(a, b) <= 0:
        return 0.0
    return abs(a - b) / min(a, b) * 100.0


def send_telegram_message(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    result = request_json(url, method="POST", payload={"chat_id": chat_id, "text": text})
    if not result.get("ok"):
        raise RuntimeError(str(result))


class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self):
        if self.path == "/":
            html = Path("templates/index.html").read_text(encoding="utf-8")
            return self._send_html(html)
        if self.path == "/api/status":
            with STATE_LOCK:
                return self._send_json({k: v for k, v in STATE.items() if k != "last_alert_time"})
        if self.path.startswith("/api/prices"):
            return self._handle_prices()
        return self._send_json({"ok": False, "message": "Not Found"}, status=404)

    def do_POST(self):
        if self.path == "/api/start":
            payload = self._read_json()
            with STATE_LOCK:
                STATE["active"] = True
                STATE["threshold"] = float(payload.get("threshold", STATE["threshold"]))
                STATE["interval"] = max(3, int(payload.get("interval", STATE["interval"])))
                STATE["cooldown"] = max(10, int(payload.get("cooldown", STATE["cooldown"])))
                STATE["telegram_enabled"] = bool(payload.get("telegram_enabled", False))
                STATE["telegram_token"] = str(payload.get("telegram_token", "")).strip()
                STATE["telegram_chat_id"] = str(payload.get("telegram_chat_id", "")).strip()
                STATE["ignore_when_binance_spot_futures_gap"] = bool(
                    payload.get("ignore_when_binance_spot_futures_gap", False)
                )
            return self._send_json({"ok": True, "message": "모니터링 시작"})

        if self.path == "/api/stop":
            with STATE_LOCK:
                STATE["active"] = False
            return self._send_json({"ok": True, "message": "모니터링 중지"})

        if self.path == "/api/test_alert":
            payload = self._read_json()
            mode = payload.get("mode", "web")
            if mode in ("telegram", "all"):
                token = str(payload.get("telegram_token", "")).strip()
                chat_id = str(payload.get("telegram_chat_id", "")).strip()
                if not token or not chat_id:
                    return self._send_json({"ok": False, "message": "텔레그램 토큰/Chat ID를 입력하세요."}, status=400)
                try:
                    send_telegram_message(token, chat_id, "[테스트] OM 가격 모니터 텔레그램 알림 테스트")
                except Exception as exc:
                    return self._send_json({"ok": False, "message": f"텔레그램 전송 실패: {exc}"}, status=502)
            return self._send_json({"ok": True, "message": f"테스트 알림 요청 성공 (mode={mode})"})

        return self._send_json({"ok": False, "message": "Not Found"}, status=404)

    def _handle_prices(self):
        with STATE_LOCK:
            state = dict(STATE)

        if not state["active"]:
            return self._send_json({"active": False, "message": "중지 상태입니다. [시작] 버튼을 눌러주세요."})

        errors_list = []
        upbit_om = bithumb_om = binance_spot_om_usdt = binance_futures_om_usdt = usdt_krw = None

        for fn, name in [
            (lambda: get_upbit_price("KRW-OM"), "upbit_om"),
            (get_bithumb_om_price, "bithumb_om"),
            (get_binance_spot_omusdt, "binance_spot_om_usdt"),
            (get_binance_futures_omusdt, "binance_futures_om_usdt"),
            (lambda: get_upbit_price("KRW-USDT"), "usdt_krw"),
        ]:
            try:
                val = fn()
                if name == "upbit_om":
                    upbit_om = val
                elif name == "bithumb_om":
                    bithumb_om = val
                elif name == "binance_spot_om_usdt":
                    binance_spot_om_usdt = val
                elif name == "binance_futures_om_usdt":
                    binance_futures_om_usdt = val
                else:
                    usdt_krw = val
            except Exception as exc:
                errors_list.append(f"{name} 실패: {exc}")

        if None in (upbit_om, bithumb_om, binance_spot_om_usdt, binance_futures_om_usdt, usdt_krw):
            return self._send_json(
                {"active": True, "errors": errors_list, "message": "일부 가격을 가져오지 못했습니다."}, status=502
            )

        binance_spot_om_krw = binance_spot_om_usdt * usdt_krw
        spot_futures_gap_percent = diff_percent(binance_spot_om_usdt, binance_futures_om_usdt)

        diffs = {
            "upbit_bithumb": diff_percent(upbit_om, bithumb_om),
            "upbit_binance_spot": diff_percent(upbit_om, binance_spot_om_krw),
            "bithumb_binance_spot": diff_percent(bithumb_om, binance_spot_om_krw),
        }

        suppress_alerts = (
            state.get("ignore_when_binance_spot_futures_gap", False)
            and spot_futures_gap_percent >= BINANCE_GAP_THRESHOLD
        )

        triggered = []
        if not suppress_alerts:
            triggered = [{"pair": k, "diff": v} for k, v in diffs.items() if v >= state["threshold"]]

        telegram_sent = False
        if triggered and state["telegram_enabled"] and state["telegram_token"] and state["telegram_chat_id"]:
            now = time.time()
            with STATE_LOCK:
                cooldown_ok = (now - STATE["last_alert_time"]) >= state["cooldown"]
                if cooldown_ok:
                    STATE["last_alert_time"] = now
            if cooldown_ok:
                try:
                    msg_lines = [
                        "[OM 가격차 알림]",
                        f"업비트 KRW-OM: {upbit_om:,.2f} KRW",
                        f"빗썸 OM_KRW: {bithumb_om:,.2f} KRW",
                        f"바이낸스 현물 OMUSDT: {binance_spot_om_usdt:,.6f} USDT",
                        f"바이낸스 선물 OMUSDT: {binance_futures_om_usdt:,.6f} USDT",
                        f"현물-선물 차이: {spot_futures_gap_percent:.2f}%",
                        "----",
                    ]
                    msg_lines.extend(f"{x['pair']}: {x['diff']:.2f}%" for x in triggered)
                    send_telegram_message(state["telegram_token"], state["telegram_chat_id"], "\n".join(msg_lines))
                    telegram_sent = True
                except Exception as exc:
                    errors_list.append(f"텔레그램 전송 실패: {exc}")

        return self._send_json(
            {
                "active": True,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "prices": {
                    "upbit_om_krw": upbit_om,
                    "bithumb_om_krw": bithumb_om,
                    "binance_spot_om_usdt": binance_spot_om_usdt,
                    "binance_futures_om_usdt": binance_futures_om_usdt,
                    "usdt_krw": usdt_krw,
                    "binance_spot_om_krw": binance_spot_om_krw,
                },
                "diffs": diffs,
                "threshold": state["threshold"],
                "triggered": triggered,
                "telegram_sent": telegram_sent,
                "errors": errors_list,
                "spot_futures_gap_percent": spot_futures_gap_percent,
                "spot_futures_gap_threshold": BINANCE_GAP_THRESHOLD,
                "suppress_alerts": suppress_alerts,
            }
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    print(f"Server running: http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
