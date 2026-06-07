import tkinter as tk
from tkinter import ttk

from src.auth.keystroke_capture import KeystrokeCapture


class PasswordEntry(tk.Frame):
    def __init__(self, parent, show: str = "*", width: int = 30, **kwargs):
        super().__init__(parent, **kwargs)
        self.password_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.password_var, show=show,
                              width=width, font=("Consolas", 12))
        self.entry.pack(fill="x", expand=True)
        self.capture = KeystrokeCapture(self.entry)
        self.capture.bind_events()

    def start_capture(self):
        self.capture.start_capture()

    def stop_capture(self):
        return self.capture.stop_capture()

    def get_events(self):
        return self.capture.get_current_events()

    def get_password(self) -> str:
        return self.password_var.get()

    def set_password(self, value: str):
        self.password_var.set(value)

    def clear(self):
        self.password_var.set("")
        self.capture.clear_buffer()


class RiskIndicator(tk.Canvas):
    WIDTH = 400
    HEIGHT = 40

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=self.WIDTH, height=self.HEIGHT,
                         bg="white", highlightthickness=1, **kwargs)
        self._risk = 0
        self._draw()

    def set_risk(self, score: int):
        self._risk = max(0, min(100, score))
        self._draw()

    def _draw(self):
        self.delete("all")
        # Background zones
        green_w = int(self.WIDTH * 0.3)
        yellow_w = int(self.WIDTH * 0.4)
        red_w = self.WIDTH - green_w - yellow_w
        self.create_rectangle(0, 0, green_w, self.HEIGHT, fill="#d4edda", outline="")
        self.create_rectangle(green_w, 0, green_w + yellow_w, self.HEIGHT, fill="#fff3cd", outline="")
        self.create_rectangle(green_w + yellow_w, 0, self.WIDTH, self.HEIGHT, fill="#f8d7da", outline="")
        # Labels
        self.create_text(green_w // 2, self.HEIGHT // 2, text="Safe", font=("Arial", 9), fill="#155724")
        self.create_text(green_w + yellow_w // 2, self.HEIGHT // 2, text="Suspicious", font=("Arial", 9), fill="#856404")
        self.create_text(green_w + yellow_w + red_w // 2, self.HEIGHT // 2, text="High Risk", font=("Arial", 9), fill="#721c24")
        # Needle
        x = int(self.WIDTH * self._risk / 100)
        self.create_line(x, 0, x, self.HEIGHT, fill="black", width=3)
        # Score text
        color = "#155724" if self._risk <= 30 else ("#856404" if self._risk <= 70 else "#721c24")
        self.create_text(self.WIDTH // 2, self.HEIGHT - 10,
                         text=f"Risk: {self._risk}/100", font=("Arial", 10, "bold"), fill=color)


class ContinuousAuthStatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.dot = tk.Canvas(self, width=16, height=16, bg="SystemButtonFace", highlightthickness=0)
        self.dot.pack(side="left", padx=(5, 5))
        self.label = tk.Label(self, text="Continuous Auth: Inactive", font=("Arial", 9))
        self.label.pack(side="left")
        self._draw_dot("#999999")

    def set_status(self, status: str, message: str = ""):
        colors = {"normal": "#28a745", "monitoring": "#ffc107", "warning": "#dc3545", "inactive": "#999999"}
        texts = {"normal": "Continuous Auth: Normal", "monitoring": "Continuous Auth: Monitoring",
                 "warning": message or "Continuous Auth: Warning", "inactive": "Continuous Auth: Inactive"}
        self._draw_dot(colors.get(status, "#999999"))
        self.label.config(text=texts.get(status, message))

    def _draw_dot(self, color: str):
        self.dot.delete("all")
        self.dot.create_oval(2, 2, 14, 14, fill=color, outline="")
