import os
import sys
import zipfile
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False

APP_NAME = "Universal Document Text Extractor"
DEFAULT_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "OCR-Tool")

def create_shortcut(target_exe, shortcut_path, working_dir, icon_path):
    """Robust Windows shortcut creator with COM & VBScript fallbacks."""
    if HAS_WIN32COM:
        try:
            pythoncom.CoInitialize()
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = target_exe
            shortcut.WorkingDirectory = working_dir
            shortcut.IconLocation = icon_path
            shortcut.save()
            return
        except Exception as e:
            print(f"Win32COM shortcut notice: {e}")

    # Fallback to VBScript launcher
    try:
        vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.WorkingDirectory = "{working_dir}"
oLink.IconLocation = "{icon_path}"
oLink.Save
"""
        vbs_path = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "make_lnk.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        subprocess.run(["cscript", "//Nologo", vbs_path], check=False)
        if os.path.exists(vbs_path):
            os.remove(vbs_path)
    except Exception as e:
        print(f"VBScript shortcut notice: {e}")

class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - Setup Wizard")
        self.geometry("560x380")
        self.resizable(False, False)
        self.install_dir = tk.StringVar(value=DEFAULT_DIR)
        self.create_desktop_icon = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)
        self.launch_after = tk.BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self):
        # Header Banner
        header_frame = tk.Frame(self, bg="#1e293b", height=70)
        header_frame.pack(fill="x", side="top")
        
        title_label = tk.Label(header_frame, text=APP_NAME, font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#1e293b")
        title_label.pack(anchor="w", padx=20, pady=(15, 2))
        
        subtitle = tk.Label(header_frame, text="Setup Wizard & Package Installer", font=("Segoe UI", 9), fg="#94a3b8", bg="#1e293b")
        subtitle.pack(anchor="w", padx=20)

        # Content Frame
        content = tk.Frame(self, padx=25, pady=20)
        content.pack(fill="both", expand=True)

        # Installation Directory Selector
        lbl_dir = tk.Label(content, text="Select Installation Folder:", font=("Segoe UI", 9, "bold"))
        lbl_dir.pack(anchor="w", pady=(0, 5))

        dir_frame = tk.Frame(content)
        dir_frame.pack(fill="x", pady=(0, 15))

        ent_dir = tk.Entry(dir_frame, textvariable=self.install_dir, font=("Segoe UI", 9))
        ent_dir.pack(side="left", fill="x", expand=True, padx=(0, 8))

        btn_browse = tk.Button(dir_frame, text="Browse...", command=self.browse_dir, font=("Segoe UI", 9), width=10)
        btn_browse.pack(side="right")

        # Shortcuts Options
        lbl_opts = tk.Label(content, text="Shortcuts & Options:", font=("Segoe UI", 9, "bold"))
        lbl_opts.pack(anchor="w", pady=(0, 5))

        chk_desk = tk.Checkbutton(content, text="Create Desktop Shortcut", variable=self.create_desktop_icon, font=("Segoe UI", 9))
        chk_desk.pack(anchor="w")

        chk_start = tk.Checkbutton(content, text="Create Start Menu Program Group", variable=self.create_start_menu, font=("Segoe UI", 9))
        chk_start.pack(anchor="w")

        chk_launch = tk.Checkbutton(content, text="Launch application after installation completes", variable=self.launch_after, font=("Segoe UI", 9))
        chk_launch.pack(anchor="w", pady=(0, 15))

        # Progress Bar & Status
        self.lbl_status = tk.Label(content, text="Ready to install.", font=("Segoe UI", 9), fg="#64748b")
        self.lbl_status.pack(anchor="w", pady=(0, 4))

        self.progress = ttk.Progressbar(content, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 15))

        # Bottom Button Frame
        btn_frame = tk.Frame(self, pady=10, padx=20, bg="#f8fafc")
        btn_frame.pack(fill="x", side="bottom")

        self.btn_cancel = tk.Button(btn_frame, text="Cancel", command=self.destroy, width=10, font=("Segoe UI", 9))
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_install = tk.Button(btn_frame, text="Install", command=self.start_install, width=12, font=("Segoe UI", 9, "bold"), bg="#2563eb", fg="#ffffff", relief="flat")
        self.btn_install.pack(side="right")

    def browse_dir(self):
        chosen = filedialog.askdirectory(initialdir=self.install_dir.get())
        if chosen:
            self.install_dir.set(os.path.normpath(chosen))

    def start_install(self):
        self.btn_install.config(state="disabled")
        self.btn_cancel.config(state="disabled")
        threading.Thread(target=self._run_installation, daemon=True).start()

    def _run_installation(self):
        try:
            target_path = self.install_dir.get()
            os.makedirs(target_path, exist_ok=True)
            self.lbl_status.config(text="Extracting application files...")

            # Locate payload zip attached or in temp
            base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            zip_payload = os.path.join(base_dir, "app_payload.zip")

            if not os.path.exists(zip_payload):
                raise FileNotFoundError("Installation payload missing!")

            with zipfile.ZipFile(zip_payload, 'r') as zf:
                members = zf.infolist()
                total = len(members)
                for idx, member in enumerate(members):
                    zf.extract(member, target_path)
                    pct = int(((idx + 1) / total) * 100)
                    self.progress['value'] = pct
                    self.lbl_status.config(text=f"Installing: {os.path.basename(member.filename)}")
                    self.update_idletasks()

            exe_main = os.path.join(target_path, "OCR-Tool.exe")

            # Create Desktop Shortcut
            if self.create_desktop_icon.get() and os.path.exists(exe_main):
                desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
                shortcut_file = os.path.join(desktop, f"{APP_NAME}.lnk")
                create_shortcut(exe_main, shortcut_file, target_path, exe_main)

            # Create Start Menu Shortcut
            if self.create_start_menu.get() and os.path.exists(exe_main):
                start_menu = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", APP_NAME)
                os.makedirs(start_menu, exist_ok=True)
                shortcut_file = os.path.join(start_menu, f"{APP_NAME}.lnk")
                create_shortcut(exe_main, shortcut_file, target_path, exe_main)

            self.lbl_status.config(text="Installation finished successfully!")
            self.progress['value'] = 100

            if self.launch_after.get() and os.path.exists(exe_main):
                subprocess.Popen([exe_main], cwd=target_path)

            messagebox.showinfo("Installation Complete", f"{APP_NAME} was installed successfully!")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Installation Error", f"Failed to install: {e}")
            self.btn_install.config(state="normal")
            self.btn_cancel.config(state="normal")

if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
