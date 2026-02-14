from typing import Optional


class DesktopNotifier:
    def __init__(self):
        self._toaster = None
        try:
            from win10toast import ToastNotifier

            self._toaster = ToastNotifier()
        except Exception:
            self._toaster = None

    def notify(self, title: str, message: str) -> Optional[str]:
        try:
            if self._toaster:
                self._toaster.show_toast(title, message, threaded=True, duration=7)
            else:
                print(f"[DESKTOP-FALLBACK] {title} | {message}")
            return None
        except Exception as exc:
            return str(exc)
