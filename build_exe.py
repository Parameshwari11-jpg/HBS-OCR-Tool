import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = ROOT_DIR / "dist"
EXE_NAME = "OCR_Tool"
SPEC_FILE = ROOT_DIR / "OCR_Tool.spec"

def get_python_exe():
    """Returns virtual environment python if it exists, ensuring all dependencies are found."""
    venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def check_requirements():
    """Ensure required packages like pyinstaller are present in target Python."""
    py_exe = get_python_exe()
    try:
        subprocess.run([py_exe, "-c", "import PyInstaller"], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("[!] PyInstaller is not installed in the Python environment. Installing...")
        subprocess.run([py_exe, "-m", "pip", "install", "pyinstaller"], check=True)

def build_frontend():
    """Build Vite React frontend into frontend/dist."""
    print("=" * 60)
    print("Step 1: Building Frontend (npm run build)...")
    print("=" * 60)

    npm_bin = "npm.cmd" if sys.platform == "win32" else "npm"
    res = subprocess.run([npm_bin, "run", "build"], cwd=FRONTEND_DIR, check=False)
    if res.returncode != 0:
        print("[!] Warning: npm run build returned non-zero code. Retrying build...")
        res = subprocess.run([npm_bin, "run", "build"], cwd=FRONTEND_DIR, check=True)

    dist_path = FRONTEND_DIR / "dist"
    if not dist_path.exists():
        raise FileNotFoundError("Frontend dist folder missing! Build failed.")
    print("Frontend build completed successfully.\n")

def build_single_file_exe():
    """Build PyInstaller single standalone .exe file via spec file."""
    print("=" * 60)
    print(f"Step 2: Packaging into Single Standalone Executable ({EXE_NAME}.exe)...")
    print("=" * 60)

    # Terminate running instances of the executable to avoid PermissionError
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/IM", f"{EXE_NAME}.exe"], capture_output=True, check=False)

    py_exe = get_python_exe()
    print(f"Using Python Environment: {py_exe}")

    cmd = [
        py_exe, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        str(SPEC_FILE)
    ]

    print(f"Running PyInstaller via OCR_Tool.spec...")
    subprocess.run(cmd, check=True, cwd=ROOT_DIR)

    exe_path = DIST_DIR / f"{EXE_NAME}.exe"
    if exe_path.exists():
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"  SUCCESS! Executable built automatically.")
        print(f"  File name     : {EXE_NAME}.exe")
        print(f"  File location : {exe_path}")
        print(f"  File size     : {size_mb:.1f} MB")
        print("=" * 60 + "\n")
    else:
        raise FileNotFoundError("Executable build failed: dist executable not found!")

def main():
    check_requirements()
    build_frontend()
    build_single_file_exe()

if __name__ == "__main__":
    main()
