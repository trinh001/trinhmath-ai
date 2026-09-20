@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo ===============================================
echo TrinhMath Auto Dev - detached launcher
echo ===============================================

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] git was not found in PATH.
  pause
  exit /b 1
)

set "DIRTY="
for /f "delims=" %%I in ('git status --porcelain 2^>nul') do set "DIRTY=1"
if defined DIRTY (
  echo [STOP] Working tree has local changes.
  echo This launcher will not switch branches or overwrite work.
  echo Finish/review the current local changes first.
  pause
  exit /b 2
)

echo [1/4] Fetching latest main...
git fetch origin main
if errorlevel 1 goto :gitfail

echo [2/4] Switching to main...
git switch main
if errorlevel 1 goto :gitfail

echo [3/4] Fast-forwarding main...
git pull --ff-only origin main
if errorlevel 1 goto :gitfail

if exist ".dev-fallback\running.lock" (
  set "LOCK_PID="
  for /f "tokens=2 delims==" %%P in ('findstr /b "pid=" ".dev-fallback\running.lock" 2^>nul') do set "LOCK_PID=%%P"

  if defined LOCK_PID (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-Process -Id !LOCK_PID! -ErrorAction SilentlyContinue; if ($null -ne $p) { exit 0 } else { exit 1 }"
    if not errorlevel 1 (
      echo [STOP] Another dev task is still running with PID !LOCK_PID!.
      echo No second task was started.
      pause
      exit /b 3
    )
  )

  echo [INFO] Removing stale dev lock from an interrupted run.
  del /q ".dev-fallback\running.lock" >nul 2>&1
)

echo [4/4] Starting auto task in a separate window...
start "TrinhMath Auto Dev" cmd /k call "%CD%\RUN_DEV_TASK_AUTO.bat"

echo.
echo Started in a separate window.
echo This launcher can now close; the task continues independently.
timeout /t 2 /nobreak >nul
exit /b 0

:gitfail
echo.
echo [STOP] Git sync failed. Nothing was reset or deleted.
pause
exit /b 4
