import os
import sys
import subprocess
import time
import webbrowser
import socket
import signal

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
VENV_PYTHON = os.path.join(ROOT_DIR, "venv", "Scripts", "python.exe")
PYTHON_EXE = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

def free_port(port: int):
    """Automatically frees the port if it is occupied by an orphaned process."""
    if os.name != "nt":
        return
    try:
        proc = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, check=False)
        pids = set()
        my_pid = str(os.getpid())
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 4 and parts[1].endswith(f":{port}"):
                pid = parts[-1]
                if pid.isdigit() and pid != "0" and pid != my_pid:
                    pids.add(pid)
        for pid in pids:
            print(f"Releasing port {port} (terminating stale process {pid})...")
            subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True, check=False)

        # Wait up to 3 seconds for the port to become fully bindable
        start = time.time()
        while time.time() - start < 3.0:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                break
            except OSError:
                time.sleep(0.3)
    except Exception as e:
        print(f"Notice during port cleanup for {port}: {e}")

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

    # Ensure ports 8000 and 3000 are clean
    free_port(8000)
    free_port(3000)

    print(f"Backend  : http://127.0.0.1:8000")
    print(f"Frontend : http://localhost:3000")
    print("-" * 60)
    print("Press Ctrl+C at any time to stop both servers.\n")

    # Start Backend (FastAPI / Uvicorn)
    backend_cmd = [
        PYTHON_EXE, "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1", "--port", "8000",
        "--reload", "--reload-dir", "backend/app",
        "--app-dir", "backend"
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=ROOT_DIR)

    # Start Frontend (Vite)
    npm_bin = "npm.cmd" if sys.platform == "win32" else "npm"
    frontend_proc = subprocess.Popen([npm_bin, "run", "dev"], cwd=FRONTEND_DIR)

    # Open browser after a brief startup delay
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
            b_code = backend_proc.poll()
            if b_code is not None:
                print(f"\n[Notice] Backend process exited (code {b_code}).")
                break
            f_code = frontend_proc.poll()
            if f_code is not None:
                print(f"\n[Notice] Frontend process exited (code {f_code}).")
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
