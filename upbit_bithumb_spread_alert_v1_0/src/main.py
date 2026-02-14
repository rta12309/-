import os
import sys
import time
from datetime import datetime

from src.alerts.notifier_desktop import DesktopNotifier
from src.alerts.notifier_telegram import TelegramNotifier
from src.core.compare import calc_diff_percent
from src.core.config import ConfigLoader
from src.core.http import HttpClient
from src.core.logger import setup_logger
from src.core.state import StateStore
from src.exchanges.bithumb import BithumbClient
from src.exchanges.upbit import UpbitClient

APP_NAME = "Spread Alert v1.0"
ALLOW_JUMP_THRESHOLD_PCT = 1.0


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _status_ok(upbit_status, bithumb_status, symbol: str, enable_network_match: bool):
    up = upbit_status.get(symbol)
    bt = bithumb_status.get(symbol)
    if not up or not bt:
        return False, "missing_status"

    base_ok = up.deposit_enabled and up.withdraw_enabled and bt.deposit_enabled and bt.withdraw_enabled
    if not base_ok:
        return False, (
            f"upbit(d={up.deposit_enabled},w={up.withdraw_enabled}) "
            f"bithumb(d={bt.deposit_enabled},w={bt.withdraw_enabled})"
        )

    if enable_network_match:
        # 빗썸 공개 API는 네트워크별 입출금 상태를 충분히 제공하지 않으므로,
        # 업비트에서 사용 가능한 네트워크가 없는 경우에만 차단.
        if not up.networks_enabled:
            return False, "network_match_enabled_but_upbit_network_unknown"

    return True, "ok"


def run() -> None:
    root = _base_dir()
    config_path = os.path.join(root, "config", "config.json")
    log_path = os.path.join(root, "alerts.log")

    config_loader = ConfigLoader(config_path)
    logger = setup_logger(log_path)
    state = StateStore()
    http = HttpClient(timeout=10, retries=3)
    upbit = UpbitClient(http)
    bithumb = BithumbClient(http)
    desktop = DesktopNotifier()
    telegram = TelegramNotifier()

    logger.info("%s starting", APP_NAME)
    logger.info("config=%s", config_loader.mask_sensitive())

    while True:
        cfg = config_loader.load()
        try:
            up_symbols = set(upbit.get_krw_symbols())
            bt_tickers = bithumb.get_tickers()
            bt_symbols = set(bt_tickers.keys())
            symbols = sorted(up_symbols & bt_symbols)

            if cfg.symbols_mode == "LIST" and cfg.symbols_list:
                wanted = set(cfg.symbols_list)
                symbols = [s for s in symbols if s in wanted]

            up_tickers = upbit.get_tickers(symbols)
            up_status = upbit.get_asset_status()
            bt_status = bithumb.get_asset_status()

            for symbol in symbols:
                up_price = up_tickers.get(symbol)
                bt_price = bt_tickers.get(symbol)
                if up_price is None or bt_price is None:
                    continue

                diff = calc_diff_percent(up_price, bt_price)
                eval_diff = abs(diff) if cfg.use_absolute_diff else diff
                meets_threshold = eval_diff >= cfg.threshold_percent

                status_ok, status_reason = _status_ok(up_status, bt_status, symbol, cfg.enable_network_match)

                alerted = False
                if meets_threshold and status_ok:
                    if state.should_alert(symbol, diff, cfg.cooldown_seconds, ALLOW_JUMP_THRESHOLD_PCT):
                        msg = (
                            f"[{APP_NAME}] {symbol} spread {diff:.2f}% | "
                            f"Upbit {up_price:,.0f} KRW / Bithumb {bt_price:,.0f} KRW"
                        )
                        if "desktop" in cfg.notify_channels:
                            err = desktop.notify(APP_NAME, msg)
                            if err:
                                logger.error("desktop notify failed: %s", err)
                        if "telegram" in cfg.notify_channels:
                            err = telegram.notify(cfg.telegram_token, cfg.telegram_chat_id, msg)
                            if err:
                                logger.error("telegram notify failed: %s", err)
                        state.mark_alerted(symbol, diff)
                        alerted = True

                logger.info(
                    "symbol=%s upbit=%.8f bithumb=%.8f diff=%.4f%% threshold=%s status=%s alert=%s",
                    symbol,
                    up_price,
                    bt_price,
                    diff,
                    meets_threshold,
                    status_reason,
                    alerted,
                )

        except Exception as exc:
            logger.error("loop failed but continuing: %s", exc)

        if cfg.relaunch_on_config_change:
            logger.info("relaunch_on_config_change enabled; please restart manually after config edits.")

        time.sleep(max(1, cfg.interval_seconds))


if __name__ == "__main__":
    print(f"{datetime.now().isoformat()} | {APP_NAME} launched")
    run()
