@echo off
setlocal EnableExtensions

REM Resolve the project root:
REM %~dp0 = m-wave\setup\
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"

cd /d "%PROJECT_ROOT%" || (
    echo Failed to change to project root.
    pause
    exit /b 1
)

set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found on PATH.
    echo Install it first:
    echo https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo Project root:
echo %PROJECT_ROOT%
echo.

echo Checking for virtual environment...

if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found.
    echo Creating it with Python 3.11...

    uv venv ^
        --python 3.11 ^
        --prompt m-wave ^
        "%PROJECT_ROOT%\.venv"

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

echo Installing requirements...

if exist "%PROJECT_ROOT%\requirements.txt" (
    uv pip install ^
        -r "%PROJECT_ROOT%\requirements.txt" ^
        --python "%VENV_PYTHON%"

    if errorlevel 1 (
        echo Failed to install requirements.
        pause
        exit /b 1
    )
) else (
    echo requirements.txt not found.
    echo Skipping requirements installation.
)

echo DONE
echo.

echo Installing m_wave package in editable mode...

uv pip install ^
    -e "%PROJECT_ROOT%" ^
    --python "%VENV_PYTHON%"

if errorlevel 1 (
    echo Failed to install m_wave.
    pause
    exit /b 1
)

echo DONE
echo.

echo Virtual environment ready at:
echo %PROJECT_ROOT%\.venv
echo.

echo To activate the environment from the project root, run:
echo .venv\Scripts\activate
echo.

echo To activate it while staying in the setup folder, run:
echo ..\.venv\Scripts\activate
echo.

echo To run the application as a python package, run:
echo python -m m_wave
echo.

echo To run the installed package, run:
echo m-wave
echo.

pause
