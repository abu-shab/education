@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the Python 3.12 environment first. See README.md.
  pause
  exit /b 1
)
echo ACADEMIA AI - open http://127.0.0.1:8000 after startup. Ctrl+C stops the server.
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000 --no-access-log
pause
