import json
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Tuple
from urllib.parse import urlencode
from urllib.request import urlopen

UPBIT_MARKETS_URL = "https://api.upbit.com/v1/market/all"
UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"
UPBIT_WALLET_STATUS_URL = "https://api.upbit.com/v1/status/wallet"

BITHUMB_TICKER_ALL_URL = "https://api.bithumb.com/public/ticker/ALL_KRW"
BITHUMB_ASSET_STATUS_URL = "https://api.bithumb.com/public/assetsstatus/ALL"

THRESHOLD_PERCENT = 5.0
POLL_INTERVAL_SEC = 20
ALERT_COOLDOWN_SEC = 120
REQUEST_TIMEOUT_SEC = 10


def http_get_json(url: str, params: Dict[str, str] | None = None):
    if params:
        url = f"{url}?{urlencode(params)}"
    with urlopen(url, timeout=REQUEST_TIMEOUT_SEC) as response:
        return json.loads(response.read().decode("utf-8"))


class PriceGapMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("업비트-빗썸 가격차이 알림기")
        self.root.geometry("980x620")

        self.running = False
        self.worker_thread = None
        self.disable_unavailable_alert = tk.BooleanVar(value=True)
        self.status_text = tk.StringVar(value="대기 중")

        self.last_alert_times: Dict[str, float] = {}
        self.shared_symbols: List[str] = []

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="가격차이 기준(%)").pack(side=tk.LEFT)
        self.threshold_entry = ttk.Entry(top, width=8)
        self.threshold_entry.insert(0, str(THRESHOLD_PERCENT))
        self.threshold_entry.pack(side=tk.LEFT, padx=(6, 18))

        ttk.Label(top, text="조회 간격(초)").pack(side=tk.LEFT)
        self.interval_entry = ttk.Entry(top, width=8)
        self.interval_entry.insert(0, str(POLL_INTERVAL_SEC))
        self.interval_entry.pack(side=tk.LEFT, padx=(6, 18))

        self.start_button = ttk.Button(top, text="모니터링 시작", command=self.start_monitor)
        self.start_button.pack(side=tk.LEFT, padx=(0, 6))

        self.stop_button = ttk.Button(top, text="모니터링 중지", command=self.stop_monitor, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)

        options = ttk.Frame(self.root, padding=(12, 0))
        options.pack(fill=tk.X)
        ttk.Checkbutton(
            options,
            text="입출금 불가능한 코인은 알림 끄기",
            variable=self.disable_unavailable_alert,
        ).pack(side=tk.LEFT)

        status_row = ttk.Frame(self.root, padding=(12, 10))
        status_row.pack(fill=tk.X)
        ttk.Label(status_row, text="상태:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(status_row, textvariable=self.status_text).pack(side=tk.LEFT, padx=(6, 0))

        columns = (
            "symbol",
            "upbit",
            "bithumb",
            "gap",
            "upbit_wallet",
            "bithumb_deposit",
            "bithumb_withdraw",
            "alert",
        )
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=24)
        headers = {
            "symbol": "코인",
            "upbit": "업비트(KRW)",
            "bithumb": "빗썸(KRW)",
            "gap": "차이(%)",
            "upbit_wallet": "업비트 입출금",
            "bithumb_deposit": "빗썸 입금",
            "bithumb_withdraw": "빗썸 출금",
            "alert": "알림여부",
        }
        widths = {
            "symbol": 100,
            "upbit": 140,
            "bithumb": 140,
            "gap": 90,
            "upbit_wallet": 130,
            "bithumb_deposit": 110,
            "bithumb_withdraw": 110,
            "alert": 110,
        }
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor=tk.CENTER)

        yscroll = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0), pady=(0, 12))
        yscroll.pack(side=tk.RIGHT, fill=tk.Y, pady=(0, 12), padx=(0, 12))

    def start_monitor(self):
        if self.running:
            return
        try:
            float(self.threshold_entry.get())
            int(self.interval_entry.get())
        except ValueError:
            messagebox.showerror("입력 오류", "기준값과 조회 간격은 숫자로 입력해주세요.")
            return

        self.running = True
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)
        self.status_text.set("마켓 동기화 중...")

        self.worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.worker_thread.start()

    def stop_monitor(self):
        self.running = False
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)
        self.status_text.set("중지됨")

    def _monitor_loop(self):
        try:
            self.shared_symbols = self.get_shared_symbols()
            if not self.shared_symbols:
                self._on_error("공통 거래 코인을 찾지 못했습니다.")
                return
            self._set_status(f"모니터링 시작: 공통 코인 {len(self.shared_symbols)}개")
        except Exception as exc:
            self._on_error(f"초기 데이터 수집 실패: {exc}")
            return

        while self.running:
            try:
                threshold = float(self.threshold_entry.get())
                interval = max(5, int(self.interval_entry.get()))
                snapshot = self.collect_snapshot(threshold)
                self.root.after(0, self.render_snapshot, snapshot)
            except Exception as exc:
                self._set_status(f"에러: {exc}")

            for _ in range(interval):
                if not self.running:
                    break
                time.sleep(1)

    def get_shared_symbols(self) -> List[str]:
        upbit_markets = http_get_json(UPBIT_MARKETS_URL, {"isDetails": "false"})
        upbit_symbols = {
            m["market"].split("-")[1]
            for m in upbit_markets
            if m.get("market", "").startswith("KRW-")
        }

        bithumb_tickers = http_get_json(BITHUMB_TICKER_ALL_URL)
        data = bithumb_tickers.get("data", {})
        bithumb_symbols = {k for k in data.keys() if k != "date"}

        return sorted(upbit_symbols & bithumb_symbols)

    def collect_snapshot(self, threshold: float) -> List[Tuple]:
        upbit_pairs = [f"KRW-{sym}" for sym in self.shared_symbols]
        upbit_prices = self.fetch_upbit_prices(upbit_pairs)
        bithumb_prices = self.fetch_bithumb_prices()

        upbit_wallet = self.fetch_upbit_wallet_status()
        bithumb_asset = self.fetch_bithumb_asset_status()

        rows = []
        for sym in self.shared_symbols:
            up = upbit_prices.get(sym)
            bt = bithumb_prices.get(sym)
            if not up or not bt:
                continue

            gap = abs(up - bt) / min(up, bt) * 100

            upbit_ok = upbit_wallet.get(sym, False)
            binfo = bithumb_asset.get(sym, {})
            deposit_ok = binfo.get("deposit", False)
            withdraw_ok = binfo.get("withdraw", False)
            transferable = upbit_ok and deposit_ok and withdraw_ok

            alert_enabled = not (self.disable_unavailable_alert.get() and not transferable)
            alert_text = "ON" if alert_enabled else "OFF(입출금불가)"

            if gap >= threshold and alert_enabled:
                self.maybe_alert(sym, gap, up, bt, upbit_ok, deposit_ok, withdraw_ok)

            rows.append(
                (
                    sym,
                    f"{up:,.0f}",
                    f"{bt:,.0f}",
                    f"{gap:.2f}",
                    "가능" if upbit_ok else "불가",
                    "가능" if deposit_ok else "불가",
                    "가능" if withdraw_ok else "불가",
                    alert_text,
                )
            )

        rows.sort(key=lambda x: float(x[3]), reverse=True)
        self._set_status(f"업데이트 완료: {time.strftime('%H:%M:%S')}")
        return rows

    def fetch_upbit_prices(self, upbit_pairs: List[str]) -> Dict[str, float]:
        prices = {}
        chunk = 80
        for i in range(0, len(upbit_pairs), chunk):
            markets = ",".join(upbit_pairs[i:i + chunk])
            data = http_get_json(UPBIT_TICKER_URL, {"markets": markets})
            for item in data:
                symbol = item["market"].split("-")[1]
                prices[symbol] = float(item["trade_price"])
        return prices

    def fetch_bithumb_prices(self) -> Dict[str, float]:
        payload = http_get_json(BITHUMB_TICKER_ALL_URL).get("data", {})
        prices = {}
        for symbol, item in payload.items():
            if symbol == "date":
                continue
            try:
                prices[symbol] = float(item["closing_price"])
            except (TypeError, ValueError, KeyError):
                continue
        return prices

    def fetch_upbit_wallet_status(self) -> Dict[str, bool]:
        data = http_get_json(UPBIT_WALLET_STATUS_URL)
        status = {}
        for item in data:
            symbol = item.get("currency")
            wallet_state = item.get("wallet_state", "")
            block_state = item.get("block_state", "")
            status[symbol] = wallet_state.lower() == "working" and block_state.lower() == "normal"
        return status

    def fetch_bithumb_asset_status(self) -> Dict[str, Dict[str, bool]]:
        data = http_get_json(BITHUMB_ASSET_STATUS_URL).get("data", {})
        parsed = {}
        for symbol, item in data.items():
            parsed[symbol] = {
                "deposit": self._is_enabled(item.get("deposit_status")),
                "withdraw": self._is_enabled(item.get("withdrawal_status")),
            }
        return parsed

    @staticmethod
    def _is_enabled(value) -> bool:
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "working", "normal"}

    def maybe_alert(self, symbol, gap, up, bt, upbit_ok, deposit_ok, withdraw_ok):
        now = time.time()
        last = self.last_alert_times.get(symbol, 0)
        if now - last < ALERT_COOLDOWN_SEC:
            return
        self.last_alert_times[symbol] = now

        msg = (
            f"[{symbol}] 가격 차이 {gap:.2f}%\n"
            f"업비트: {up:,.0f}원\n"
            f"빗썸: {bt:,.0f}원\n"
            f"업비트 입출금: {'가능' if upbit_ok else '불가'}\n"
            f"빗썸 입금: {'가능' if deposit_ok else '불가'} / 출금: {'가능' if withdraw_ok else '불가'}"
        )

        self.root.after(0, lambda: self._show_alert(msg))

    def _show_alert(self, msg):
        self.root.bell()
        messagebox.showinfo("가격 차이 알림", msg)

    def render_snapshot(self, rows: List[Tuple]):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def _set_status(self, text: str):
        self.root.after(0, lambda: self.status_text.set(text))

    def _on_error(self, text: str):
        self.running = False
        self.root.after(0, lambda: self.start_button.configure(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_button.configure(state=tk.DISABLED))
        self._set_status(text)


def main():
    root = tk.Tk()
    app = PriceGapMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop_monitor(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    main()
