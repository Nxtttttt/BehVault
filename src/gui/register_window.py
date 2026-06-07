import tkinter as tk
from tkinter import ttk, messagebox

from src.gui.widgets import PasswordEntry


class RegisterWindow(tk.Toplevel):
    REQUIRED_SAMPLES = 10

    def __init__(self, parent, auth_service, on_complete: callable = None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.on_complete = on_complete
        self._samples: list[list] = []
        self._current_sample = 0
        self._started = False
        self.title("BehVault - User Registration")
        self.geometry("450x400")
        self.resizable(False, False)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        ttk.Label(self, text="User Registration", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(self, text=f"Enter the same password {self.REQUIRED_SAMPLES} times to build your behavioral template.",
                  wraplength=400).pack(pady=5)

        ttk.Label(self, text="Username:", font=("Arial", 11)).pack(pady=(10, 0))
        self.username_entry = ttk.Entry(self, font=("Consolas", 12), width=30)
        self.username_entry.pack(pady=5)

        self.progress_label = ttk.Label(self, text=f"Sample 0 / {self.REQUIRED_SAMPLES}", font=("Arial", 10))
        self.progress_label.pack(pady=5)
        self.progress_bar = ttk.Progressbar(self, length=300, maximum=self.REQUIRED_SAMPLES)
        self.progress_bar.pack(pady=5)

        ttk.Label(self, text="Password:", font=("Arial", 11)).pack(pady=(10, 0))
        self.pwd_entry = PasswordEntry(self, width=30)
        self.pwd_entry.pack(pady=5)

        self.info_label = ttk.Label(self, text="", font=("Arial", 9), foreground="gray")
        self.info_label.pack(pady=5)

        self.action_btn = ttk.Button(self, text="Start Registration", command=self._on_action)
        self.action_btn.pack(pady=10)

    def _on_action(self):
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showwarning("Input Error", "Please enter a username.")
            return
        if not self._started:
            # Start registration
            self._started = True
            self._samples = []
            self._current_sample = 0
            self.pwd_entry.start_capture()
            self.pwd_entry.clear()
            self.pwd_entry.entry.focus_set()
            self.action_btn.config(text="Submit Sample")
            self.info_label.config(text=f"Sample 1/{self.REQUIRED_SAMPLES}: Type your password and click Submit")
            self.progress_bar["value"] = 0
            self.progress_label.config(text=f"Sample 0 / {self.REQUIRED_SAMPLES}")
        else:
            password = self.pwd_entry.get_password()
            if not password:
                messagebox.showwarning("Input Error", "Please enter the password.")
                return
            events = self.pwd_entry.stop_capture()
            self._samples.append(events)
            self._current_sample += 1
            self.progress_bar["value"] = self._current_sample
            self.progress_label.config(text=f"Sample {self._current_sample} / {self.REQUIRED_SAMPLES}")
            if self._current_sample >= self.REQUIRED_SAMPLES:
                self._finish_registration(username)
            else:
                self.pwd_entry.start_capture()
                self.pwd_entry.clear()
                self.pwd_entry.entry.focus_set()
                self.info_label.config(text=f"Sample {self._current_sample + 1}/{self.REQUIRED_SAMPLES}: Type your password and click Submit")

    def _finish_registration(self, username):
        password = self.pwd_entry.get_password()
        try:
            self.auth_service.register(username, password, self._samples)
            messagebox.showinfo("Success", f"User '{username}' registered successfully!")
            if self.on_complete:
                self.on_complete(username)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Registration Error", str(e))
            self._started = False
            self._current_sample = 0
            self._samples = []
            self.progress_bar["value"] = 0
            self.progress_label.config(text=f"Sample 0 / {self.REQUIRED_SAMPLES}")
            self.action_btn.config(text="Start Registration")

    def _on_close(self):
        if self.on_complete:
            self.on_complete(None)
        self.destroy()
