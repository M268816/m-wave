@echo off
setlocal EnableExtensions

REM %~dp0 points to:
REM m-wave\security_checks\
REM Resolve the parent directory as the project root.
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"

set "SECURITY_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"

cd /d "%PROJECT_ROOT%" || (
    echo Failed to change to project root:
    echo %PROJECT_ROOT%
    pause
    exit /b 1
)

if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found:
    echo %PROJECT_ROOT%\.venv
    echo.
    echo Run setup\setup.bat first.
    pause
    exit /b 1
)

where gitleaks >nul 2>nul
if errorlevel 1 (
    echo gitleaks was not found on PATH.
    echo Install it separately, for example:
    echo scoop install gitleaks
    pause
    exit /b 1
)

echo Project root:
echo %PROJECT_ROOT%
echo.

REM -----------------------------------------------------------------
REM Bandit
REM -----------------------------------------------------------------

echo Running Bandit...

"%VENV_PYTHON%" -m bandit ^
    -r "%PROJECT_ROOT%\src" ^
    -f json ^
    -o "%SECURITY_DIR%sec-bandit.json" ^
    -v

echo Bandit completed.
pause

REM -----------------------------------------------------------------
REM pip-audit
REM -----------------------------------------------------------------

echo Running pip-audit...

"%VENV_PYTHON%" -m pip_audit ^
    -r "%PROJECT_ROOT%\requirements.txt" ^
    -f json ^
    -o "%SECURITY_DIR%sec-pip-audit.json" ^
    -v

echo pip-audit completed.
pause

REM -----------------------------------------------------------------
REM gitleaks
REM -----------------------------------------------------------------

echo Running gitleaks...

gitleaks detect ^
    --source "%PROJECT_ROOT%" ^
    --report-format json ^
    --report-path "%SECURITY_DIR%sec-gitleaks.json" ^
    --verbose

echo gitleaks completed.
pause

echo.
echo All security checks completed.
echo Reports were written to:
echo %SECURITY_DIR%
pause
