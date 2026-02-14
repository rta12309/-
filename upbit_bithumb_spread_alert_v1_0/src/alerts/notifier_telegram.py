from typing import Optional

import requests


class TelegramNotifier:
    def notify(self, token: str, chat_id: str, message: str) -> Optional[str]:
        if not token or not chat_id:
            return "telegram_token/chat_id not configured"
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
            resp.raise_for_status()
            return None
        except Exception as exc:
            return str(exc)
