@echo off
setlocal

REM Change to script directory / project root
cd /d "%~dp0"

echo Checking for virtual environment...

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo Virtual environment found.
)

echo DONE
echo.

echo Installing requirements and upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

if exist "requirements.txt" (
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install requirements.
        pause
        exit /b 1
    )
) else (
    echo requirements.txt not found. Skipping requirements installation.
)

echo DONE
echo.

echo Installing m_wave package in editable mode...
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
    echo Failed to install m_wave package.
    pause
    exit /b 1
)

echo DONE
echo.
echo Virtual environment ready at:
echo %cd%\.venv
echo.
echo To activate the environment in Windows, run:
echo .venv\Scripts\activate
echo.
echo To run the app, run:
echo python -m m_wave
echo.
pause