import tkinter as tk
from tkinter import ttk, messagebox

from src.database.db_manager import DatabaseManager
from src.crypto.key_manager import KeyManager
from src.services.auth_service import AuthService
from src.services.vault_service import VaultService
from src.services.experiment_service import ExperimentService
from src.gui.register_window import RegisterWindow
from src.gui.login_window import LoginWindow
from src.gui.vault_window import VaultWindow
from src.gui.admin_window import AdminWindow


class App:
    def __init__(self):
        self.db = DatabaseManager()
        self.key_manager = KeyManager()
        self.auth_service = AuthService(self.db)
        self.vault_service = VaultService(self.db)
        self.experiment_service = ExperimentService(self.db)

        self._current_user_id: int = None
        self._current_username: str = None
        self._vault_key: bytes = None
        self._vault_window: VaultWindow = None

        self.root = tk.Tk()
        self.root.title("BehVault - Behavioral Password + SM4 Encrypted File Vault")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        self._build_main_menu()
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _build_main_menu(self):
        ttk.Label(self.root, text="BehVault", font=("Arial", 24, "bold")).pack(pady=15)
        ttk.Label(self.root, text="基于行为口令与国密SM4的智能保密文件库",
                  font=("Arial", 12)).pack()
        ttk.Label(self.root, text="Behavioral Password + SM4 Encrypted File Vault",
                  font=("Arial", 10), foreground="gray").pack(pady=3)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=40, pady=15)

        ttk.Label(self.root, text="Main Menu", font=("Arial", 14)).pack(pady=10)

        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="1. Register New User", command=self._open_register, width=30).pack(pady=5)
        ttk.Button(btn_frame, text="2. Login", command=self._open_login, width=30).pack(pady=5)
        ttk.Button(btn_frame, text="3. Admin Panel (Experiments)", command=self._open_admin, width=30).pack(pady=5)
        ttk.Button(btn_frame, text="4. Exit", command=self._on_exit, width=30).pack(pady=20)

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=40, pady=10)

        self.status_label = ttk.Label(self.root, text="Welcome to BehVault", font=("Arial", 9), foreground="gray")
        self.status_label.pack(pady=10)

    def _open_register(self):
        RegisterWindow(self.root, self.auth_service, on_complete=self._on_register_complete)

    def _on_register_complete(self, username):
        if username:
            self.status_label.config(text=f"User '{username}' registered successfully.")

    def _open_login(self):
        LoginWindow(self.root, self.auth_service, self.vault_service, self.key_manager,
                    on_success=self._on_login_success)

    def _on_login_success(self, user_id, username, vault_key):
        if user_id is None:
            return
        self._current_user_id = user_id
        self._current_username = username
        self._vault_key = vault_key
        self.status_label.config(text=f"Logged in as '{username}' (ID: {user_id})")
        self._open_vault()

    def _open_vault(self):
        if self._vault_window and self._vault_window.winfo_exists():
            self._vault_window.lift()
            return
        self._vault_window = VaultWindow(self.root, self.vault_service,
                                          self._current_user_id, self._vault_key,
                                          on_lock=self._on_vault_lock)
        # Start continuous auth
        self.auth_service.start_continuous_auth(
            self._current_user_id, self._vault_key,
            on_risk_change=self._on_continuous_auth_event,
            tk_widget=self._vault_window,
        )
        self._vault_window.focus()

    def _on_vault_lock(self):
        self.auth_service.stop_continuous_auth(self._vault_window or self.root)
        self._current_user_id = None
        self._vault_key = None
        self.status_label.config(text="Vault locked.")
        self._vault_window = None

    def _on_continuous_auth_event(self, event_type: str, risk: int, message: str = ""):
        if self._vault_window and self._vault_window.winfo_exists():
            if event_type == "high_risk":
                self._vault_window.update_continuous_auth_status("warning", message)
                self.vault_service.lock(self._current_user_id)
                messagebox.showwarning("Security Alert", message)
                self._vault_window.destroy()
                self._vault_window = None
                self.status_label.config(text="Vault locked due to anomaly!")
            elif event_type == "re_auth":
                self._vault_window.update_continuous_auth_status("monitoring", message)
            else:
                self._vault_window.update_continuous_auth_status("normal")

    def _open_admin(self):
        AdminWindow(self.root, self.experiment_service)

    def _on_exit(self):
        if self._current_user_id:
            self.auth_service.stop_continuous_auth(self._vault_window or self.root)
            self.vault_service.lock(self._current_user_id)
        self.db.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
