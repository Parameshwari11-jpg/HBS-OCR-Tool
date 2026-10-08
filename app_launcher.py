import os
import sys
import socket
import time
import webbrowser
import threading
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    paddle_libs = BASE_DIR / "paddle" / "libs"
    if paddle_libs.exists():
        os.environ["PATH"] = str(paddle_libs) + os.path.pathsep + os.environ.get("PATH", "")
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(str(paddle_libs))
            except Exception:
                pass
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(str(BASE_DIR))
        except Exception:
            pass
else:
    BASE_DIR = Path(__file__).resolve().parent

# Add backend directory to sys.path so app modules import cleanly
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import main FastAPI application
try:
    from app.main import app
except ImportError:
    from backend.app.main import app

# Path to built static frontend files
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Mount assets folder if exists
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve index.html on root route
    @app.get("/")
    async def serve_root():
        return FileResponse(FRONTEND_DIST / "index.html")

    # Serve index.html for all non-API fallback routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        target_file = FRONTEND_DIST / full_path
        if full_path and target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(FRONTEND_DIST / "index.html")

def find_free_port(default_port: int = 8000) -> int:
    """Finds an available TCP port starting from default_port."""
    for port in range(default_port, default_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return default_port

def main():
    port = find_free_port(8000)
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("  Starting Universal Document Text Extractor Desktop App")
    print(f"  Access URL: {url}")
    print("=" * 60)

    # Automatically open browser window after short delay
    def open_browser():
        time.sleep(1.5)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"Notice opening browser: {e}")

    threading.Thread(target=open_browser, daemon=True).start()

    # Run Uvicorn server
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
