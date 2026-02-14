import json
import os
from dataclasses import dataclass
from typing import List


@dataclass
class AppConfig:
    threshold_percent: float
    interval_seconds: int
    cooldown_seconds: int
    symbols_mode: str
    symbols_list: List[str]
    use_absolute_diff: bool
    notify_channels: List[str]
    telegram_token: str
    telegram_chat_id: str
    enable_network_match: bool
    relaunch_on_config_change: bool


class ConfigLoader:
    def __init__(self, path: str):
        self.path = path
        self._last_mtime = 0.0
        self.current = self.load(force=True)

    def _normalize(self, data: dict) -> AppConfig:
        symbols = [str(s).upper() for s in data.get("symbols_list", [])]
        channels = [str(c).lower() for c in data.get("notify_channels", ["desktop"])]
        return AppConfig(
            threshold_percent=float(data.get("threshold_percent", 5)),
            interval_seconds=int(data.get("interval_seconds", 10)),
            cooldown_seconds=int(data.get("cooldown_seconds", 300)),
            symbols_mode=str(data.get("symbols_mode", "ALL")).upper(),
            symbols_list=symbols,
            use_absolute_diff=bool(data.get("use_absolute_diff", True)),
            notify_channels=channels,
            telegram_token=str(data.get("telegram_token", "")),
            telegram_chat_id=str(data.get("telegram_chat_id", "")),
            enable_network_match=bool(data.get("enable_network_match", False)),
            relaunch_on_config_change=bool(data.get("relaunch_on_config_change", False)),
        )

    def load(self, force: bool = False) -> AppConfig:
        mtime = os.path.getmtime(self.path)
        if not force and mtime <= self._last_mtime:
            return self.current
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._last_mtime = mtime
        self.current = self._normalize(data)
        return self.current

    def mask_sensitive(self) -> dict:
        cfg = self.current
        token = cfg.telegram_token
        chat = cfg.telegram_chat_id
        return {
            "threshold_percent": cfg.threshold_percent,
            "interval_seconds": cfg.interval_seconds,
            "cooldown_seconds": cfg.cooldown_seconds,
            "symbols_mode": cfg.symbols_mode,
            "symbols_list": cfg.symbols_list,
            "use_absolute_diff": cfg.use_absolute_diff,
            "notify_channels": cfg.notify_channels,
            "telegram_token": token[:4] + "***" if token else "",
            "telegram_chat_id": chat[:3] + "***" if chat else "",
            "enable_network_match": cfg.enable_network_match,
            "relaunch_on_config_change": cfg.relaunch_on_config_change,
        }
