import json
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from flask import Flask, jsonify, render_template

CONFIG_PATH = Path("config.json")

DEFAULT_CONFIG = {
    "symbol": "BTC",
    "threshold_percent": 5.0,
    "check_interval_seconds": 10,
    "host": "127.0.0.1",
    "port": 5000,
}


@dataclass
class MonitorState:
    symbol: str = "BTC"
    upbit_price: float | None = None
    bithumb_price: float | None = None
    difference_percent: float | None = None
    threshold_percent: float = 5.0
    is_alert: bool = False
    checked_at: str | None = None
    status: str = "starting"
    last_error: str | None = None
    alert_count: int = 0


class PriceMonitor:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.state = MonitorState(
            symbol=config["symbol"],
            threshold_percent=float(config["threshold_percent"]),
        )
        self._lock = threading.Lock()

    def fetch_upbit_price(self) -> float:
        market = f"KRW-{self.config['symbol']}"
        url = "https://api.upbit.com/v1/ticker"
        response = requests.get(url, params={"markets": market}, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data[0]["trade_price"])

    def fetch_bithumb_price(self) -> float:
        symbol = self.config["symbol"]
        url = f"https://api.bithumb.com/public/ticker/{symbol}_KRW"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "0000":
            raise RuntimeError(f"Bithumb API error: {data}")
        return float(data["data"]["closing_price"])

    def check_once(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            upbit = self.fetch_upbit_price()
            bithumb = self.fetch_bithumb_price()
            diff_percent = ((upbit - bithumb) / bithumb) * 100
            is_alert = abs(diff_percent) >= self.state.threshold_percent

            with self._lock:
                previous_alert = self.state.is_alert
                self.state.upbit_price = upbit
                self.state.bithumb_price = bithumb
                self.state.difference_percent = diff_percent
                self.state.is_alert = is_alert
                self.state.checked_at = now
                self.state.status = "ok"
                self.state.last_error = None
                if is_alert and not previous_alert:
                    self.state.alert_count += 1
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self.state.status = "error"
                self.state.last_error = str(exc)
                self.state.checked_at = now

    def loop(self) -> None:
        interval = int(self.config["check_interval_seconds"])
        while True:
            self.check_once()
            time.sleep(interval)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self.state)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return DEFAULT_CONFIG

    loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = {**DEFAULT_CONFIG, **loaded}
    return config


config = load_config()
monitor = PriceMonitor(config)
app = Flask(__name__)


@app.route("/")
def home() -> str:
    return render_template("index.html", config=config)


@app.route("/api/status")
def api_status() -> Any:
    return jsonify(monitor.snapshot())


def main() -> None:
    worker = threading.Thread(target=monitor.loop, daemon=True)
    worker.start()
    app.run(host=config["host"], port=int(config["port"]))


if __name__ == "__main__":
    main()
