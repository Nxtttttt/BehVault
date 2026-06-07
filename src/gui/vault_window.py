import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from src.gui.widgets import ContinuousAuthStatusBar


class VaultWindow(tk.Toplevel):
    def __init__(self, parent, vault_service, user_id: int, vault_key: bytes,
                 on_lock: callable = None):
        super().__init__(parent)
        self.vault_service = vault_service
        self.user_id = user_id
        self.vault_key = vault_key
        self.on_lock = on_lock
        self.title("BehVault - Encrypted File Vault")
        self.geometry("700x500")
        self._build_ui()
        self._refresh_file_list()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Top bar
        top_bar = ttk.Frame(self)
        top_bar.pack(fill="x", padx=10, pady=5)
        ttk.Label(top_bar, text="Encrypted File Vault", font=("Arial", 14, "bold")).pack(side="left")
        self.lock_btn = ttk.Button(top_bar, text="Lock Vault", command=self._lock)
        self.lock_btn.pack(side="right")

        # Status bar
        self.status_bar = ContinuousAuthStatusBar(self)
        self.status_bar.pack(fill="x", padx=10, pady=2)

        # Action buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(action_frame, text="Import File", command=self._import_file).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Decrypt Selected", command=self._decrypt_file).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Delete Selected", command=self._delete_file).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Refresh", command=self._refresh_file_list).pack(side="left", padx=3)

        # File list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("id", "enc_filename", "created_at")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("enc_filename", text="Encrypted Filename")
        self.tree.heading("created_at", text="Created At")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("enc_filename", width=400)
        self.tree.column("created_at", width=180, anchor="center")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _refresh_file_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            files = self.vault_service.list_files(self.user_id)
            for f in files:
                self.tree.insert("", "end", values=(f["id"], f["enc_filename"], f["created_at"]))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _import_file(self):
        filepath = filedialog.askopenfilename(title="Select file to encrypt and import")
        if not filepath:
            return
        try:
            file_id = self.vault_service.import_file(self.user_id, filepath)
            messagebox.showinfo("Success", f"File imported (ID: {file_id}). Original encrypted and stored.")
            self._refresh_file_list()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def _decrypt_file(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a file to decrypt.")
            return
        file_id = self.tree.item(sel[0], "values")[0]
        output_dir = filedialog.askdirectory(title="Select output directory")
        if not output_dir:
            return
        try:
            output_path = self.vault_service.decrypt_file(self.user_id, int(file_id), output_dir)
            messagebox.showinfo("Success", f"File decrypted to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Decrypt Error", str(e))

    def _delete_file(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a file to delete.")
            return
        file_id = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Confirm", f"Delete file {file_id}? This cannot be undone."):
            try:
                self.vault_service.delete_file(self.user_id, int(file_id))
                self._refresh_file_list()
            except Exception as e:
                messagebox.showerror("Delete Error", str(e))

    def _lock(self):
        self.vault_service.lock(self.user_id)
        if self.on_lock:
            self.on_lock()
        self.destroy()

    def _on_close(self):
        self.vault_service.lock(self.user_id)
        if self.on_lock:
            self.on_lock()
        self.destroy()

    def update_continuous_auth_status(self, status: str, message: str = ""):
        self.status_bar.set_status(status, message)
