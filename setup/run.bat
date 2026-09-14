@echo off
setlocal EnableExtensions

REM Resolve the project root from m-wave\setup\
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"

cd /d "%PROJECT_ROOT%" || (
    echo Failed to change to project root.
    pause
    exit /b 1
)

set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found.
    echo Please run setup\setup.bat first.
    pause
    exit /b 1
)

echo Running M-WAVE...
"%VENV_PYTHON%" -m m_wave

pause
