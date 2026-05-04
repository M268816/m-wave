@echo off
REM change to directory
cd /d %~dp0

REM runs three security checks.
REM pauses after every check.
bandit -r ./src/ -f json -o sec-bandit.json -v
echo Bandit completed
pause
pip-audit -r requirements.txt -f json -o sec-pip-audit.json -v
echo pip-audit completed
pause
gitleaks detect -s . -r sec-gitleak.json -v
echo gitleaks completed
pause
