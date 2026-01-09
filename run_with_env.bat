@echo off
cd /d %~dp0

REM activate venv
call .venv\Scripts\activate

REM run the app
python -m src.main
