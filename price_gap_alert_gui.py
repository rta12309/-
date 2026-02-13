#!/usr/bin/env python3
"""업비트-빗썸 가격 차이 알림 GUI (버튼형)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext

import price_gap_alert as core


class PriceGapAlertGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("업비트-빗썸 가격 차이 알림")
        self.root.geometry("900x600")

        self.threshold_var = tk.StringVar(value=str(core.DEFAULT_THRESHOLD))
        self.interval_var = tk.StringVar(value=str(core.DEFAULT_INTERVAL))

        self.is_running = False
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()

        self._build_ui()
        self.root.after(150, self._drain_log_queue)

    def _build_ui(self) -> None:
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="알림 기준(%)").grid(row=0, column=0, sticky="w")
        tk.Entry(top, textvariable=self.threshold_var, width=10).grid(row=0, column=1, padx=6)

        tk.Label(top, text="조회 간격(초)").grid(row=0, column=2, sticky="w")
        tk.Entry(top, textvariable=self.interval_var, width=10).grid(row=0, column=3, padx=6)

        self.start_btn = tk.Button(top, text="시작", command=self.start_monitoring, width=12, bg="#4CAF50", fg="white")
        self.start_btn.grid(row=0, column=4, padx=6)

        self.stop_btn = tk.Button(top, text="중지", command=self.stop_monitoring, width=12, state="disabled")
        self.stop_btn.grid(row=0, column=5, padx=6)

        self.once_btn = tk.Button(top, text="한번만 조회", command=self.run_once, width=12)
        self.once_btn.grid(row=0, column=6, padx=6)

        self.status_label = tk.Label(self.root, text="대기 중", anchor="w")
        self.status_label.pack(fill="x", padx=10)

        self.log_text = scrolledtext.ScrolledText(self.root, wrap="word", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.log_text.insert("end", "앱 준비 완료. [시작] 또는 [한번만 조회] 버튼을 누르세요.\n")
        self.log_text.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                kind, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(payload)
            elif kind == "status":
                self.status_label.config(text=payload)
            elif kind == "error":
                self._append_log(payload)
                messagebox.showerror("오류", payload)
            elif kind == "alert":
                self._append_log(payload)
                self.root.bell()

        self.root.after(150, self._drain_log_queue)

    def _validate_inputs(self) -> tuple[float, int] | None:
        try:
            threshold = float(self.threshold_var.get())
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("입력 오류", "숫자만 입력해 주세요.")
            return None

        if threshold <= 0 or interval <= 0:
            messagebox.showerror("입력 오류", "기준값/간격은 0보다 커야 합니다.")
            return None

        return threshold, interval

    def _fetch_and_render(self, symbols: list[str], threshold: float) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        upbit_prices = core.fetch_upbit_prices(symbols)
        bithumb_prices = core.fetch_bithumb_prices()
        alerts = core.find_gap_alerts(upbit_prices, bithumb_prices, threshold)

        if alerts:
            rendered = f"\n[{now}]\n" + core.render_alerts(alerts, threshold)
            self.log_queue.put(("alert", rendered))
        else:
            self.log_queue.put(("log", f"[{now}] 이상 없음 (기준 {threshold:.2f}%)"))

    def run_once(self) -> None:
        validated = self._validate_inputs()
        if not validated:
            return
        threshold, _ = validated

        def task() -> None:
            self.log_queue.put(("status", "1회 조회 중..."))
            try:
                symbols = core.fetch_upbit_markets()
                if not symbols:
                    self.log_queue.put(("error", "업비트 KRW 마켓을 찾지 못했습니다."))
                    return
                self._fetch_and_render(symbols, threshold)
                self.log_queue.put(("status", "대기 중"))
            except Exception as err:  # noqa: BLE001
                self.log_queue.put(("error", f"조회 실패: {err}"))
                self.log_queue.put(("status", "대기 중"))

        threading.Thread(target=task, daemon=True).start()

    def start_monitoring(self) -> None:
        if self.is_running:
            return

        validated = self._validate_inputs()
        if not validated:
            return
        threshold, interval = validated

        self.is_running = True
        self.stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.once_btn.configure(state="disabled")

        def task() -> None:
            self.log_queue.put(("status", "마켓 목록 초기화 중..."))
            try:
                symbols = core.fetch_upbit_markets()
                if not symbols:
                    self.log_queue.put(("error", "업비트 KRW 마켓을 찾지 못했습니다."))
                    return

                self.log_queue.put(("log", f"모니터링 시작: 업비트 KRW 마켓 {len(symbols)}개"))
                self.log_queue.put(("status", "모니터링 중"))

                while not self.stop_event.is_set():
                    try:
                        self._fetch_and_render(symbols, threshold)
                    except Exception as err:  # noqa: BLE001
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.log_queue.put(("log", f"[{now}] 조회 오류: {err}"))

                    if self.stop_event.wait(interval):
                        break
            finally:
                self.is_running = False
                self.log_queue.put(("status", "대기 중"))
                self.root.after(0, self._reset_buttons)

        self.worker = threading.Thread(target=task, daemon=True)
        self.worker.start()

    def stop_monitoring(self) -> None:
        if not self.is_running:
            return
        self.stop_event.set()
        self.log_queue.put(("log", "중지 요청됨..."))

    def _reset_buttons(self) -> None:
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.once_btn.configure(state="normal")


def main() -> None:
    root = tk.Tk()
    PriceGapAlertGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
