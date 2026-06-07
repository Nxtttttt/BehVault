"""Quick GUI screenshot capture."""
import sys, os, tkinter as tk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OUTDIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(OUTDIR, exist_ok=True)

def _capture(r):
    try:
        from PIL import ImageGrab
        x, y = r.winfo_rootx(), r.winfo_rooty()
        w, h = r.winfo_width(), r.winfo_height()
        if w > 10 and h > 10:
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            path = os.path.join(OUTDIR, "08_main_window.png")
            img.save(path)
            print(f"  Saved: 08_main_window.png ({w}x{h})")
        else:
            print(f"  Window not visible ({w}x{h})")
    except Exception as e:
        print(f"  Screenshot failed: {e}")
    r.destroy()

root = tk.Tk()
root.title("BehVault - Behavioral Authentication + SM4 Encrypted Vault")
root.geometry("700x500")
root.configure(bg="#f0f0f0")

tk.Label(root, text="BehVault", font=("Arial", 20, "bold"),
         bg="#f0f0f0", fg="#1a5276").pack(pady=(20, 5))
tk.Label(root, text="Behavioral Authentication + SM4 Encrypted File Vault",
         font=("Arial", 10), bg="#f0f0f0", fg="#666").pack(pady=(0, 20))

main = tk.Frame(root, bg="white", relief="groove", bd=1)
main.pack(fill="both", expand=True, padx=20, pady=10)
tk.Label(main, text="MAIN DASHBOARD", font=("Arial", 12, "bold"), bg="white").pack(pady=10)

btn = tk.Frame(main, bg="white")
btn.pack(pady=10)
tk.Button(btn, text="Register", font=("Arial", 10), width=16, height=2,
          bg="#2e86c1", fg="white").pack(side="left", padx=10)
tk.Button(btn, text="Login", font=("Arial", 10), width=16, height=2,
          bg="#27ae60", fg="white").pack(side="left", padx=10)
tk.Button(btn, text="Admin Panel", font=("Arial", 10), width=16, height=2,
          bg="#e67e22", fg="white").pack(side="left", padx=10)

bottom = tk.Frame(root, bg="#e8f8f5", height=30)
bottom.pack(fill="x", side="bottom", padx=20, pady=10)
tk.Label(bottom, text="Continuous Auth: Inactive", font=("Arial", 9),
         bg="#e8f8f5", fg="#666").pack(side="left", padx=10)

tk.Label(main, text="Welcome to BehVault. Login or register to access the encrypted file vault.",
         font=("Arial", 9), bg="white", fg="#888", wraplength=600).pack(pady=20)

root.update_idletasks()
root.update()
root.after(500, lambda: _capture(root))
root.mainloop()
