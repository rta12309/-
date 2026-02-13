"""Simple beginner-friendly counter GUI app.

Run with:
    python app.py
"""

import tkinter as tk
from tkinter import messagebox


class CounterApp:
    """A minimal counter app with increment and reset buttons."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("쉬운 카운터")
        self.root.geometry("360x260")
        self.root.minsize(320, 220)

        # Keep current number in a Tkinter variable so label updates automatically.
        self.count = tk.IntVar(value=0)

        # Main frame for spacing.
        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        # Big number display.
        self.count_label = tk.Label(
            frame,
            textvariable=self.count,
            font=("Arial", 56, "bold"),
            pady=10,
        )
        self.count_label.pack(fill="x")

        # Button row.
        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=(16, 0))

        self.increment_button = tk.Button(
            button_frame,
            text="카운트 +1",
            font=("Arial", 16, "bold"),
            height=2,
            command=self.safe_action(self.increment),
        )
        self.increment_button.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.reset_button = tk.Button(
            button_frame,
            text="리셋",
            font=("Arial", 16, "bold"),
            height=2,
            command=self.safe_action(self.reset),
        )
        self.reset_button.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Optional beginner-friendly keyboard shortcuts.
        self.root.bind("<space>", self.safe_event_action(self.increment))
        self.root.bind("<Return>", self.safe_event_action(self.increment))
        self.root.bind("r", self.safe_event_action(self.reset))
        self.root.bind("R", self.safe_event_action(self.reset))

    def safe_action(self, func):
        """Wrap a button callback and show popup if an error happens."""

        def wrapped():
            try:
                func()
            except Exception as exc:  # broad for beginner-friendly error popup
                messagebox.showerror("오류", f"예기치 않은 오류가 발생했습니다.\n{exc}")

        return wrapped

    def safe_event_action(self, func):
        """Wrap an event callback and show popup if an error happens."""

        def wrapped(_event):
            try:
                func()
            except Exception as exc:  # broad for beginner-friendly error popup
                messagebox.showerror("오류", f"예기치 않은 오류가 발생했습니다.\n{exc}")

        return wrapped

    def increment(self) -> None:
        """Increase counter by 1."""
        self.count.set(self.count.get() + 1)

    def reset(self) -> None:
        """Reset counter to 0."""
        self.count.set(0)


if __name__ == "__main__":
    app_root = tk.Tk()
    CounterApp(app_root)
    app_root.mainloop()
