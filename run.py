import os
import sys
import subprocess
import time
import webbrowser
import signal

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")
PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

def kill_process_tree(proc):
    if proc is None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, check=False)
        else:
            proc.terminate()
    except Exception:
        pass

def main():
    print("=" * 60)
    print("  Starting Universal Document Text Extractor")
    print("=" * 60)
    print(f"Backend  : http://127.0.0.1:8000")
    print(f"Frontend : http://localhost:3000")
    print("-" * 60)
    print("Press Ctrl+C at any time to stop both servers.\n")

    # Start Backend (FastAPI / Uvicorn)
    backend_cmd = [
        PYTHON_EXE, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "8000",
        "--reload", "--app-dir", "backend"
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=ROOT_DIR)

    # Start Frontend (Vite)
    frontend_proc = subprocess.Popen(["npm.cmd", "run", "dev"], cwd=FRONTEND_DIR)

    # Open browser after a brief delay
    def open_browser():
        time.sleep(2.5)
        try:
            webbrowser.open("http://localhost:3000")
        except Exception:
            pass

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    try:
        while True:
            # Check if any process terminated unexpectedly
            if backend_proc.poll() is not None:
                print("\n[Notice] Backend process exited.")
                break
            if frontend_proc.poll() is not None:
                print("\n[Notice] Frontend process exited.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping all servers...")
    finally:
        kill_process_tree(backend_proc)
        kill_process_tree(frontend_proc)
        print("Universal Document Text Extractor stopped cleanly.")

if __name__ == "__main__":
    main()
