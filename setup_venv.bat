@echo off
REM change to directory
cd /d %~dp0

REM create venv if missing
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

REM install and upgrade pip, install dependencies
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo Virtual environment ready at %cd%\.venv
pause
