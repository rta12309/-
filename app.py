"""업비트/빗썸 공통 코인 가격차이 알림기 (Windows 전용 템플릿 v1.0).

- python app.py        : 데스크톱 GUI 실행
- python app.py --web  : 웹 서버 실행
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import traceback
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Tuple

APP_VERSION = "1.0"

UPBIT_MARKET_URL = "https://api.upbit.com/v1/market/all?isDetails=true"
UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"
UPBIT_WALLET_URL = "https://api.upbit.com/v1/status/wallet"
BITHUMB_TICKER_URL = "https://api.bithumb.com/public/ticker/ALL_KRW"
BITHUMB_ASSET_URL = "https://api.bithumb.com/public/assetsstatus/ALL"


@dataclass
class CoinDiff:
    symbol: str
    upbit_price: float
    bithumb_price: float
    diff_percent: float


class PriceMonitorService:
    """업비트/빗썸 데이터 조회 + 조건 필터링 담당."""

    def __init__(self, threshold_percent: float = 5.0):
        self.threshold_percent = threshold_percent

    def _http_get_json(self, url: str, params: Dict[str, str] | None = None):
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        req = urllib.request.Request(
            url=url,
            headers={"User-Agent": f"CoinGapBeginner/{APP_VERSION}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_upbit_krw_symbols(self) -> List[str]:
        rows = self._http_get_json(UPBIT_MARKET_URL)
        out = []
        for row in rows:
            market = row.get("market", "")
            if market.startswith("KRW-"):
                out.append(market.replace("KRW-", ""))
        return sorted(set(out))

    def _get_bithumb_krw_symbols(self) -> List[str]:
        rows = self._http_get_json(BITHUMB_TICKER_URL)
        out = []
        for symbol in rows.get("data", {}).keys():
            if symbol != "date":
                out.append(symbol)
        return sorted(set(out))

    def get_common_symbols(self) -> List[str]:
        return sorted(set(self._get_upbit_krw_symbols()) & set(self._get_bithumb_krw_symbols()))

    def _get_upbit_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        for i in range(0, len(symbols), 100):
            chunk = symbols[i : i + 100]
            markets = ",".join([f"KRW-{s}" for s in chunk])
            rows = self._http_get_json(UPBIT_TICKER_URL, {"markets": markets})
            for row in rows:
                market = row.get("market", "")
                if market.startswith("KRW-"):
                    prices[market.replace("KRW-", "")] = float(row.get("trade_price", 0) or 0)
        return prices

    def _get_bithumb_prices(self, symbols: List[str]) -> Dict[str, float]:
        rows = self._http_get_json(BITHUMB_TICKER_URL)
        data = rows.get("data", {})
        prices: Dict[str, float] = {}
        for symbol in symbols:
            info = data.get(symbol)
            if isinstance(info, dict):
                prices[symbol] = float(info.get("closing_price", 0) or 0)
        return prices

    def _upbit_transfer_map(self) -> Dict[str, bool]:
        rows = self._http_get_json(UPBIT_WALLET_URL)
        out: Dict[str, bool] = {}
        for row in rows:
            symbol = (row.get("currency") or "").upper()
            wallet = (row.get("wallet_state") or "").lower()
            block = (row.get("block_state") or "").lower()
            out[symbol] = wallet in {"working", "normal"} and block in {"working", "normal"}
        return out

    def _bithumb_transfer_map(self) -> Dict[str, bool]:
        rows = self._http_get_json(BITHUMB_ASSET_URL)
        out: Dict[str, bool] = {}
        for symbol, info in rows.get("data", {}).items():
            if symbol == "date" or not isinstance(info, dict):
                continue
            deposit = str(info.get("deposit_status", "0")) == "1"
            withdraw = str(info.get("withdrawal_status", "0")) == "1"
            out[symbol.upper()] = deposit and withdraw
        return out

    def find_alerts(self) -> Tuple[List[CoinDiff], Dict[str, str]]:
        symbols = self.get_common_symbols()
        upbit_prices = self._get_upbit_prices(symbols)
        bithumb_prices = self._get_bithumb_prices(symbols)
        upbit_transfer = self._upbit_transfer_map()
        bithumb_transfer = self._bithumb_transfer_map()

        alerts: List[CoinDiff] = []
        for symbol in symbols:
            up = upbit_prices.get(symbol)
            bt = bithumb_prices.get(symbol)
            if not up or not bt:
                continue
            if not (upbit_transfer.get(symbol, False) and bithumb_transfer.get(symbol, False)):
                continue

            base = min(up, bt)
            if base <= 0:
                continue
            gap = abs(up - bt) / base * 100
            if gap >= self.threshold_percent:
                alerts.append(CoinDiff(symbol=symbol, upbit_price=up, bithumb_price=bt, diff_percent=gap))

        alerts.sort(key=lambda x: x.diff_percent, reverse=True)
        meta = {
            "checked_count": str(len(symbols)),
            "threshold": f"{self.threshold_percent:.2f}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return alerts, meta


class DesktopApp:
    """Tkinter 기반 데스크톱 GUI."""

    def __init__(self):
        import tkinter as tk
        from tkinter import messagebox, scrolledtext

        self.tk = tk
        self.messagebox = messagebox
        self.root = tk.Tk()
        self.root.title(f"코딩템플릿1 코인 가격차이 알림기 v{APP_VERSION}")
        self.root.geometry("900x700")

        self.service = PriceMonitorService()
        self.auto_running = False
        self.auto_thread: threading.Thread | None = None

        self.threshold_var = tk.StringVar(value="5.0")
        self.interval_var = tk.StringVar(value="30")

        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)
        tk.Label(top, text=f"버전: {APP_VERSION}", font=("맑은 고딕", 10, "bold")).pack(side="left", padx=5)
        tk.Label(top, text="알림 기준(%):").pack(side="left")
        tk.Entry(top, width=8, textvariable=self.threshold_var).pack(side="left", padx=5)
        tk.Label(top, text="자동 검사 주기(초):").pack(side="left")
        tk.Entry(top, width=8, textvariable=self.interval_var).pack(side="left", padx=5)

        buttons = tk.Frame(self.root)
        buttons.pack(fill="x", padx=10, pady=5)
        tk.Button(buttons, text="1회 검사", command=self.run_check, width=15).pack(side="left", padx=4)
        tk.Button(buttons, text="자동 시작", command=self.start_auto, width=15).pack(side="left", padx=4)
        tk.Button(buttons, text="자동 중지", command=self.stop_auto, width=15).pack(side="left", padx=4)
        tk.Button(buttons, text="오류 복사", command=self.copy_error, width=15).pack(side="left", padx=4)

        self.result_box = scrolledtext.ScrolledText(self.root, height=20)
        self.result_box.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(self.root, text="오류 로그 (복사/붙여넣기 가능):", anchor="w").pack(fill="x", padx=10)
        self.error_box = scrolledtext.ScrolledText(self.root, height=10, fg="red")
        self.error_box.pack(fill="both", expand=False, padx=10, pady=(0, 10))

    def log_result(self, text: str):
        self.result_box.insert("end", text + "\n")
        self.result_box.see("end")

    def log_error(self, text: str):
        self.error_box.insert("end", text + "\n")
        self.error_box.see("end")

    def copy_error(self):
        text = self.error_box.get("1.0", "end").strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.messagebox.showinfo("안내", "오류 로그를 복사했습니다.")

    def _load_settings(self) -> int:
        threshold = float(self.threshold_var.get())
        interval = int(self.interval_var.get())
        if threshold <= 0:
            raise ValueError("알림 기준(%)은 0보다 커야 합니다.")
        if interval <= 0:
            raise ValueError("자동 검사 주기(초)는 1 이상이어야 합니다.")
        self.service.threshold_percent = threshold
        return interval

    def _beep(self):
        try:
            import winsound

            winsound.Beep(1500, 400)
        except Exception:
            print("\a", end="")

    def run_check(self):
        try:
            self._load_settings()
            alerts, meta = self.service.find_alerts()
            self.log_result(
                f"[{meta['timestamp']}] 검사 완료 | 공통코인 {meta['checked_count']}개 | 기준 {meta['threshold']}%"
            )
            if not alerts:
                self.log_result("  - 조건(입출금 가능 + 가격차이 기준 이상)에 맞는 코인이 없습니다.")
                return
            self.log_result(f"  - 알림 대상 {len(alerts)}개")
            for item in alerts:
                self.log_result(
                    f"    * {item.symbol}: 업비트 {item.upbit_price:,.0f}원 / "
                    f"빗썸 {item.bithumb_price:,.0f}원 / 차이 {item.diff_percent:.2f}%"
                )
            self._beep()
        except Exception as exc:
            err = f"[오류] {exc}\n{traceback.format_exc()}"
            self.log_error(err)
            self.messagebox.showerror("오류", "검사 중 오류가 발생했습니다. 아래 오류 로그를 복사해 전달해주세요.")

    def _auto_loop(self, interval: int):
        while self.auto_running:
            self.root.after(0, self.run_check)
            time.sleep(interval)

    def start_auto(self):
        try:
            interval = self._load_settings()
        except Exception as exc:
            self.log_error(f"[설정 오류] {exc}")
            self.messagebox.showerror("설정 오류", str(exc))
            return

        if self.auto_running:
            self.messagebox.showinfo("안내", "이미 자동 검사가 실행 중입니다.")
            return

        self.auto_running = True
        self.auto_thread = threading.Thread(target=self._auto_loop, args=(interval,), daemon=True)
        self.auto_thread.start()
        self.log_result("[자동 검사 시작]")

    def stop_auto(self):
        self.auto_running = False
        self.log_result("[자동 검사 중지]")

    def run(self):
        self.root.mainloop()


class WebApp:
    """표준 라이브러리 HTTP 서버 기반 로컬 웹 앱."""

    def __init__(self):
        self.service = PriceMonitorService()

    @staticmethod
    def _html_template() -> str:
        return f"""<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<title>코딩템플릿1 코인 가격차이 알림기 v{APP_VERSION}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
button {{ margin-right: 8px; padding: 8px 12px; }}
input {{ width: 100px; }}
.box {{ border: 1px solid #ddd; padding: 12px; margin-top: 10px; white-space: pre-wrap; }}
.error {{ color: #c00000; }}
</style>
</head>
<body>
<h2>코딩템플릿1 코인 가격차이 알림기 v{APP_VERSION}</h2>
<p>조건: 업비트/빗썸 공통 코인 중 <b>입출금 가능</b> + 가격차이 기준 이상인 경우만 알림</p>

<label>알림 기준(%): <input id='threshold' type='number' min='0.1' step='0.1' value='5.0'></label>
<label>자동 주기(초): <input id='interval' type='number' min='1' step='1' value='30'></label>
<div style='margin-top:10px;'>
  <button onclick='runCheck()'>1회 검사</button>
  <button onclick='startAuto()'>자동 시작</button>
  <button onclick='stopAuto()'>자동 중지</button>
  <button onclick='copyError()'>오류 복사</button>
</div>

<div class='box' id='result'>결과가 여기에 표시됩니다.</div>
<div class='box error' id='error'>오류 로그가 여기에 표시됩니다.</div>

<script>
let timer = null;
function beep() {{
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const osc = ctx.createOscillator();
  osc.type = 'sine'; osc.frequency.value = 1200;
  osc.connect(ctx.destination); osc.start();
  setTimeout(() => {{ osc.stop(); ctx.close(); }}, 300);
}}
async function runCheck() {{
  const threshold = document.getElementById('threshold').value || '5.0';
  const res = await fetch('/api/check?threshold=' + encodeURIComponent(threshold));
  const data = await res.json();
  if (!data.ok) {{
    document.getElementById('error').textContent = `[오류] ${{data.error}}\n${{data.trace}}`;
    return;
  }}
  const m = data.meta;
  let txt = `[${{m.timestamp}}] 검사 완료 | 공통코인 ${{m.checked_count}}개 | 기준 ${{m.threshold}}%\n`;
  if (!data.alerts.length) {{
    txt += '- 조건(입출금 가능 + 가격차이 기준 이상)에 맞는 코인이 없습니다.';
  }} else {{
    txt += `- 알림 대상 ${{data.alerts.length}}개\n`;
    for (const a of data.alerts) {{
      txt += `  * ${{a.symbol}}: 업비트 ${{Math.round(a.upbit_price).toLocaleString()}}원 / ` +
             `빗썸 ${{Math.round(a.bithumb_price).toLocaleString()}}원 / 차이 ${{a.diff_percent.toFixed(2)}}%\n`;
    }}
    beep();
  }}
  document.getElementById('result').textContent = txt;
}}
function startAuto() {{
  stopAuto();
  const sec = Number(document.getElementById('interval').value || '30');
  timer = setInterval(runCheck, Math.max(1000, sec * 1000));
  runCheck();
}}
function stopAuto() {{ if (timer) {{ clearInterval(timer); timer = null; }} }}
function copyError() {{
  navigator.clipboard.writeText(document.getElementById('error').textContent)
    .then(() => alert('오류 로그를 복사했습니다.'));
}}
</script>
</body>
</html>"""

    def _make_handler(self):
        service = self.service
        html = self._html_template().encode("utf-8")

        class Handler(BaseHTTPRequestHandler):
            def _json(self, data: Dict):
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html)
                    return

                if parsed.path == "/api/check":
                    try:
                        q = urllib.parse.parse_qs(parsed.query)
                        threshold = float(q.get("threshold", ["5.0"])[0])
                        service.threshold_percent = threshold
                        alerts, meta = service.find_alerts()
                        self._json(
                            {
                                "ok": True,
                                "meta": meta,
                                "alerts": [
                                    {
                                        "symbol": a.symbol,
                                        "upbit_price": a.upbit_price,
                                        "bithumb_price": a.bithumb_price,
                                        "diff_percent": round(a.diff_percent, 4),
                                    }
                                    for a in alerts
                                ],
                            }
                        )
                    except Exception as exc:
                        self._json({"ok": False, "error": str(exc), "trace": traceback.format_exc()})
                    return

                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):
                return

        return Handler

    def run(self):
        host, port = "0.0.0.0", 5000
        webbrowser.open("http://127.0.0.1:5000")
        server = ThreadingHTTPServer((host, port), self._make_handler())
        print("Web server started: http://127.0.0.1:5000")
        server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="업비트/빗썸 공통코인 가격차이 알림기")
    parser.add_argument("--web", action="store_true", help="웹 서버 모드로 실행")
    args = parser.parse_args()

    if args.web:
        WebApp().run()
    else:
        DesktopApp().run()


if __name__ == "__main__":
    main()
