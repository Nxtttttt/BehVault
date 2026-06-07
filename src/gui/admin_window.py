import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np

from src.gui.widgets import RiskIndicator
from src.viz.charts import ChartGenerator


class AdminWindow(tk.Toplevel):
    def __init__(self, parent, experiment_service, viz_service=None):
        super().__init__(parent)
        self.experiment_service = experiment_service
        self.viz_service = viz_service or ChartGenerator()
        self.title("BehVault - Admin Panel")
        self.geometry("850x650")
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self, text="Admin Panel — Experiments & Visualization",
                  font=("Arial", 14, "bold")).pack(pady=10)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: Attack Simulation
        attack_tab = ttk.Frame(nb)
        nb.add(attack_tab, text="Attack Simulation")
        self._build_attack_tab(attack_tab)

        # Tab 2: Visualization
        viz_tab = ttk.Frame(nb)
        nb.add(viz_tab, text="Charts")
        self._build_viz_tab(viz_tab)

        # Tab 3: Users
        users_tab = ttk.Frame(nb)
        nb.add(users_tab, text="Users")
        self._build_users_tab(users_tab)

    def _build_attack_tab(self, parent):
        ttk.Label(parent, text="Run attack simulations to evaluate security.",
                  font=("Arial", 10)).pack(pady=5)

        sel_frame = ttk.Frame(parent)
        sel_frame.pack(pady=5)
        ttk.Label(sel_frame, text="User ID:").pack(side="left")
        self.attack_user_id = ttk.Entry(sel_frame, width=10)
        self.attack_user_id.pack(side="left", padx=5)
        ttk.Label(sel_frame, text="Password:").pack(side="left")
        self.attack_password = ttk.Entry(sel_frame, width=20, show="*")
        self.attack_password.pack(side="left", padx=5)
        ttk.Button(sel_frame, text="Run Full Experiment", command=self._run_experiment).pack(side="left", padx=10)

        self.experiment_result_text = tk.Text(parent, height=15, font=("Consolas", 10))
        self.experiment_result_text.pack(fill="both", expand=True, padx=10, pady=5)

    def _build_viz_tab(self, parent):
        ttk.Label(parent, text="Generate behavioral analysis charts.",
                  font=("Arial", 10)).pack(pady=5)

        sel_frame = ttk.Frame(parent)
        sel_frame.pack(pady=5)
        ttk.Label(sel_frame, text="User ID:").pack(side="left")
        self.viz_user_id = ttk.Entry(sel_frame, width=10)
        self.viz_user_id.pack(side="left", padx=5)

        ttk.Button(sel_frame, text="Generate Charts", command=self._generate_charts).pack(side="left", padx=10)

        self.viz_status = ttk.Label(parent, text="", font=("Arial", 9), foreground="gray")
        self.viz_status.pack(pady=2)

        self.viz_canvas = tk.Canvas(parent, bg="white")
        self.viz_canvas.pack(fill="both", expand=True, padx=10, pady=5)

    def _build_users_tab(self, parent):
        ttk.Label(parent, text="Registered Users", font=("Arial", 10)).pack(pady=5)
        ttk.Button(parent, text="Refresh", command=self._refresh_users).pack(pady=5)

        columns = ("id", "username", "created_at")
        self.users_tree = ttk.Treeview(parent, columns=columns, show="headings")
        self.users_tree.heading("id", text="ID")
        self.users_tree.heading("username", text="Username")
        self.users_tree.heading("created_at", text="Created At")
        self.users_tree.column("id", width=60, anchor="center")
        self.users_tree.column("username", width=200)
        self.users_tree.column("created_at", width=200, anchor="center")
        self.users_tree.pack(fill="both", expand=True, padx=10, pady=5)

    def _run_experiment(self):
        try:
            user_id = int(self.attack_user_id.get())
            password = self.attack_password.get()
        except ValueError:
            messagebox.showwarning("Input Error", "Enter valid User ID and Password.")
            return
        self.experiment_result_text.delete("1.0", "end")
        self.experiment_result_text.insert("end", "Running experiment...\n")
        self.update()
        try:
            result = self.experiment_service.run_full_experiment(user_id, password)
            if not result:
                self.experiment_result_text.insert("end", "User not found or no template.\n")
                return
            self.experiment_result_text.delete("1.0", "end")
            self.experiment_result_text.insert("end", "=" * 60 + "\n")
            self.experiment_result_text.insert("end", "Full Attack Experiment Results\n")
            self.experiment_result_text.insert("end", "=" * 60 + "\n\n")
            self.experiment_result_text.insert("end", f"FAR (False Acceptance Rate): {result['far']:.4f}\n")
            self.experiment_result_text.insert("end", f"FRR (False Rejection Rate):  {result['frr']:.4f}\n")
            self.experiment_result_text.insert("end", f"EER (Equal Error Rate):      {result['eer']:.4f}\n")
            self.experiment_result_text.insert("end", f"Best Threshold:              {result['best_threshold']}\n\n")
            self.experiment_result_text.insert("end", "Mean Risk Scores by Attack Type:\n")
            for key in ["password_leak_scores", "imitation_scores", "random_scores"]:
                name = key.replace("_scores", "").replace("_", " ").title()
                vals = result.get(key, [])
                self.experiment_result_text.insert("end", f"  {name:25s}: {np.mean(vals):6.1f} (±{np.std(vals):.1f})\n")
            # FAR/FRR detail
            self.experiment_result_text.insert("end", "\n--- FAR/FRR vs Threshold ---\n")
            self.experiment_result_text.insert("end", f"{'Thr':>6s}  {'FAR':>8s}  {'FRR':>8s}\n")
            for d in result.get("metrics", {}).get("details", []):
                pass  # details not returned in current run_full_experiment
        except Exception as e:
            self.experiment_result_text.insert("end", f"Error: {e}\n")

    def _generate_charts(self):
        try:
            user_id = int(self.viz_user_id.get())
        except ValueError:
            messagebox.showwarning("Input Error", "Enter a valid User ID.")
            return
        try:
            db = self.experiment_service.db
            samples = db.get_samples(user_id)
            if not samples:
                messagebox.showinfo("No Data", "No samples found for this user.")
                return
            from src.auth.feature_extractor import FeatureVector
            fvs = [FeatureVector.from_json(s["features_json"]) for s in samples]
            buf = self.viz_service.hold_time_curve(fvs, f"User {user_id} - Hold Time")
            # Save to screenshots
            import os
            ss_dir = os.path.join(os.path.dirname(__file__), "..", "..", "screenshots")
            os.makedirs(ss_dir, exist_ok=True)
            with open(os.path.join(ss_dir, f"hold_time_u{user_id}.png"), "wb") as f:
                f.write(buf)
            self.viz_status.config(text=f"Charts saved to screenshots/ for user {user_id}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _refresh_users(self):
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        users = self.experiment_service.db.list_users()
        for u in users:
            self.users_tree.insert("", "end", values=(u["id"], u["username"], u["created_at"]))
