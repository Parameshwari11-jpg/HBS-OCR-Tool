# Run Commands (Universal Document Text Extractor)

### Easiest Way (Double click or run the .bat files):
- **Backend:** Double click `run_backend.bat` (or run `.\run_backend.bat` in terminal)
- **Frontend:** Double click `run_frontend.bat` (or run `.\run_frontend.bat` in terminal)

---

### Terminal 1: Backend (FastAPI)
From `C:\Users\HBS\Desktop\OCR`:
```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
```

---

### Terminal 2: Frontend (React)
From `C:\Users\HBS\Desktop\OCR\frontend`:
> **Note:** Use `npm.cmd` in PowerShell to bypass the script execution restriction:
```powershell
npm.cmd run dev
```

*(Or enable script execution for PowerShell once with: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`)*
