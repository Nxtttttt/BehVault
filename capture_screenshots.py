"""Capture BehVault GUI screenshots using Tkinter + PIL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
root = tk.Tk()
root.withdraw()  # Hide the root window

# Create screenshots directory
OUTDIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUTDIR, exist_ok=True)

# We'll use a simple approach: create windows, render them, and use postscript/winfo
# On Windows we'll try PIL ImageGrab, as backup use canvas postscript

def capture_window(window, name, delay_ms=300):
    """Capture a Tkinter window as PNG."""
    window.update_idletasks()
    window.update()
    window.deiconify()
    window.lift()
    window.focus_force()
    # Schedule the actual capture
    path = os.path.join(OUTDIR, name)
    window.after(delay_ms, lambda w=window, p=path: _do_capture(w, p))
    return path

def _do_capture(window, path):
    try:
        import pyautogui
        x = window.winfo_rootx()
        y = window.winfo_rooty()
        w = window.winfo_width()
        h = window.winfo_height()
        img = pyautogui.screenshot(region=(x, y, w, h))
        img.save(path)
        print(f"  Captured: {os.path.basename(path)}")
    except ImportError:
        try:
            from PIL import ImageGrab
            x = window.winfo_rootx()
            y = window.winfo_rooty()
            w = window.winfo_width()
            h = window.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            img.save(path)
            print(f"  Captured: {os.path.basename(path)}")
        except Exception as e:
            print(f"  PIL fallback failed: {e}")
            try:
                eps_path = path.replace('.png', '.eps')
                window.postscript(file=eps_path, colormode='color')
                print(f"  Saved EPS: {os.path.basename(eps_path)}")
            except Exception as e2:
                print(f"  PostScript also failed: {e2}")

# Create the app but don't run mainloop - we'll drive it manually
print("Creating GUI windows for screenshots...")

# Import app modules
from src.database.db_manager import DatabaseManager
from src.services.auth_service import AuthService
from src.services.vault_service import VaultService
from src.crypto.key_manager import KeyManager

# Setup database
db_path = os.path.join(os.path.dirname(__file__), "data", "behvault_screenshot.db")
if os.path.exists(db_path):
    try: os.remove(db_path)
    except: pass

db = DatabaseManager(db_path)
auth = AuthService(db)
vault_svc = VaultService(db)
key_mgr = KeyManager()

# Import GUI
from src.gui.app import App

app = App(root, auth, vault_svc, key_mgr)
root.deiconify()

# Capture main window after a delay
print("Waiting for GUI to render...")
root.after(500, lambda: _do_capture(root, os.path.join(OUTDIR, "08_main_window.png")))

# Open login window
root.after(1000, lambda: app._show_login_window())
root.after(1500, lambda: _do_capture(
    app._current_window if hasattr(app, '_current_window') else root,
    os.path.join(OUTDIR, "09_login_window.png")))

# Open register window
root.after(2000, lambda: app._show_register_window())
root.after(2500, lambda w=None: _do_capture(
    app._current_window if hasattr(app, '_current_window') and app._current_window else root,
    os.path.join(OUTDIR, "10_register_window.png")))

# Close after capturesss
root.after(3500, lambda: root.destroy())

print("Starting GUI (will auto-close after screenshots)...")
root.mainloop()
print("Done.")
