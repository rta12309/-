import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class AlertState:
    last_alert_ts: float = 0.0
    last_alert_percent: float = 0.0


class StateStore:
    def __init__(self):
        self._state: Dict[str, AlertState] = {}

    def should_alert(self, symbol: str, diff_percent: float, cooldown_seconds: int, allow_jump_threshold: float) -> bool:
        now = time.time()
        st = self._state.get(symbol)
        if not st:
            return True
        cooldown_passed = now - st.last_alert_ts >= cooldown_seconds
        jumped = abs(diff_percent) >= abs(st.last_alert_percent) + allow_jump_threshold
        return cooldown_passed or jumped

    def mark_alerted(self, symbol: str, diff_percent: float) -> None:
        self._state[symbol] = AlertState(last_alert_ts=time.time(), last_alert_percent=diff_percent)
