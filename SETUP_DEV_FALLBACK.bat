@echo off
setlocal
cd /d "%~dp0"

echo ===============================================
echo TrinhMath Dev Fallback Setup
echo Codex primary - DeepSeek/Aider fallback
echo ===============================================

where codex >nul 2>&1
if errorlevel 1 (
  echo [WARN] Codex CLI was not found in PATH.
  echo Install/authenticate Codex CLI first if you want Codex as primary.
) else (
  echo [OK] Codex CLI found.
)

set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PY_CMD=py"

if "%PY_CMD%"=="" (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_CMD=python"
)

if "%PY_CMD%"=="" (
  where python3 >nul 2>&1
  if not errorlevel 1 set "PY_CMD=python3"
)

if "%PY_CMD%"=="" (
  echo [ERROR] Python was not found in PATH.
  echo Install Python 3 or add python.exe to PATH, then run this file again.
  goto :fail
)

echo [OK] Python launcher: %PY_CMD%

if not exist ".dev-fallback-venv\Scripts\python.exe" (
  echo [1/3] Creating isolated Aider environment...
  %PY_CMD% -m venv .dev-fallback-venv
  if errorlevel 1 goto :fail
)

echo [2/3] Installing/updating Aider in isolated environment...
".dev-fallback-venv\Scripts\python.exe" -m pip install --upgrade pip aider-chat
if errorlevel 1 goto :fail

echo [3/3] Checking DeepSeek key...
if "%DEEPSEEK_API_KEY%"=="" (
  echo [WARN] DEEPSEEK_API_KEY is not visible in this shell.
  echo If you used setx before, close this window and open a new terminal/session.
  echo The key is never printed or written by this script.
) else (
  echo [OK] DEEPSEEK_API_KEY is available. Value is hidden.
)

echo.
echo Setup complete.
echo From now on start long coding tasks with RUN_DEV_TASK_AUTO.bat
exit /b 0

:fail
echo.
echo Setup failed. No project data was changed.
exit /b 1
