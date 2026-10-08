import os
import sys
from pathlib import Path

# Locate root directory (one directory up from backend)
ROOT_DIR = Path(__file__).resolve().parent.parent
ROOT_BUILD_SCRIPT = ROOT_DIR / "build_exe.py"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

print(f"[Notice] Forwarding build command from backend folder to root project directory: {ROOT_DIR}\n")

# Import and execute main build_exe module from root
import build_exe

if __name__ == "__main__":
    build_exe.main()
