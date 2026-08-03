@echo off
setlocal

REM Change to script directory / project root
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Running the app...
".venv\Scripts\python.exe" -m m_wave

if errorlevel 1 (
    echo.
    echo App exited with an error.
    pause
    exit /b 1
)

endlocal