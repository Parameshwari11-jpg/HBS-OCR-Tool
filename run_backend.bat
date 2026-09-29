@echo off
cd /d "%~dp0"
echo Starting Universal Document Text Extractor Backend on http://127.0.0.1:8000...
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
pause
