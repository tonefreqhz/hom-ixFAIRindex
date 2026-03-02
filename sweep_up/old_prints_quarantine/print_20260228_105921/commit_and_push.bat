@echo off
setlocal
cd /d "%~dp0"

echo === Homeix: commit + push ===
git rev-parse --is-inside-work-tree >nul 2>&1 || (echo Not a git repo here.& pause & exit /b 1)

set /p msg=Commit message: 
if "%msg%"=="" set msg=Update

git add -A
git commit -m "%msg%"
if errorlevel 1 (
  echo.
  echo (Nothing committed. Maybe nothing changed?)
  pause
  exit /b 0
)

git push
pause
