import tkinter as tk
from tkinter import ttk, messagebox

from src.gui.widgets import PasswordEntry, RiskIndicator


class LoginWindow(tk.Toplevel):
    def __init__(self, parent, auth_service, vault_service, key_manager,
                 on_success: callable = None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.vault_service = vault_service
        self.key_manager = key_manager
        self.on_success = on_success
        self._login_events = []
        self.title("BehVault - Login")
        self.geometry("480x420")
        self.resizable(False, False)
        self._build_ui()
        self.pwd_entry.start_capture()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        ttk.Label(self, text="BehVault Login", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(self, text="Enter your username and password for behavioral authentication.",
                  wraplength=400).pack(pady=5)

        ttk.Label(self, text="Username:", font=("Arial", 11)).pack(pady=(10, 0))
        self.username_entry = ttk.Entry(self, font=("Consolas", 12), width=30)
        self.username_entry.pack(pady=5)

        ttk.Label(self, text="Password:", font=("Arial", 11)).pack(pady=(10, 0))
        self.pwd_entry = PasswordEntry(self, width=30)
        self.pwd_entry.pack(pady=5)

        self.risk_indicator = RiskIndicator(self)
        self.risk_indicator.pack(pady=15)

        self.result_label = ttk.Label(self, text="", font=("Arial", 10, "bold"))
        self.result_label.pack(pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Login", command=self._do_login).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self._clear).pack(side="left", padx=5)

        # Bind Enter key to login
        self.username_entry.bind("<Return>", lambda e: self.pwd_entry.entry.focus_set())
        self.pwd_entry.entry.bind("<Return>", lambda e: self._do_login())
        self.bind("<Return>", lambda e: self._do_login())

    def _do_login(self):
        username = self.username_entry.get().strip()
        password = self.pwd_entry.get_password()
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter username and password.")
            return
        events = self.pwd_entry.get_events()
        risk, category = self.auth_service.login(username, password, events)
        self.risk_indicator.set_risk(risk)
        risk_cn = {
            "safe": "安全 (Safe)", "suspicious": "可疑 (Suspicious)",
            "high_risk": "高风险 (High Risk)", "wrong_password": "密码错误",
            "user_not_found": "用户不存在", "no_events": "无击键数据",
        }
        color = {30: "green", 70: "orange", 100: "red"}
        threshold_levels = [30, 70, 100]
        rcolor = "green"
        for t in threshold_levels:
            if risk <= t:
                rcolor = color[t]
                break
        self.result_label.config(text=f"Risk: {risk}/100 — {risk_cn.get(category, category)}",
                                 foreground=rcolor)

        if category == "user_not_found":
            messagebox.showerror("Login Failed", "User does not exist. Please register first.")
        elif category == "wrong_password":
            messagebox.showerror("Login Failed", "Incorrect password!")
        elif category == "no_events":
            messagebox.showerror("Login Failed",
                "No keystroke data captured. Make sure to type in the password field (not paste).")
        elif category == "high_risk":
            messagebox.showerror("Login Failed",
                f"Behavioral pattern mismatch! (Risk: {risk}/100)\n"
                "Your typing pattern differs significantly from the registered template. "
                "Try typing at your usual speed and rhythm.")
        elif category == "safe":
            user = self.auth_service.db.get_user_by_username(username)
            vault_key, _ = self.key_manager.derive_key(password)
            self.vault_service.unlock(user["id"], vault_key)
            self._login_events = events
            if self.on_success:
                self.on_success(user["id"], username, vault_key)
            self.destroy()
        elif category == "suspicious":
            messagebox.showinfo("Suspicious",
                f"Your typing pattern is slightly unusual (Risk: {risk}/100). "
                "Access granted with continuous monitoring.")
            user = self.auth_service.db.get_user_by_username(username)
            vault_key, _ = self.key_manager.derive_key(password)
            self.vault_service.unlock(user["id"], vault_key)
            self._login_events = events
            if self.on_success:
                self.on_success(user["id"], username, vault_key)
            self.destroy()

    def _clear(self):
        self.pwd_entry.clear()
        self.username_entry.delete(0, "end")
        self.risk_indicator.set_risk(0)
        self.result_label.config(text="")

    def _on_close(self):
        if self.on_success:
            self.on_success(None)
        self.destroy()
