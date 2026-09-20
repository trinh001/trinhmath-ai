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
  echo [1/4] Creating isolated launcher environment...
  %PY_CMD% -m venv .dev-fallback-venv
  if errorlevel 1 goto :fail
)

echo [2/4] Installing/updating uv in isolated launcher environment...
".dev-fallback-venv\Scripts\python.exe" -m pip install --upgrade pip uv
if errorlevel 1 goto :fail

set "UV_TOOL_DIR=%CD%\.dev-fallback-tools"
set "UV_TOOL_BIN_DIR=%CD%\.dev-fallback-bin"

echo [3/4] Installing Aider with isolated Python 3.12 via uv...
".dev-fallback-venv\Scripts\python.exe" -m uv tool install --force --python 3.12 aider-chat@latest
if errorlevel 1 goto :fail

if not exist ".dev-fallback-bin\aider.exe" (
  echo [ERROR] Aider installation finished without .dev-fallback-bin\aider.exe
  goto :fail
)

echo [4/4] Checking DeepSeek key...
if "%DEEPSEEK_API_KEY%"=="" (
  echo [WARN] DEEPSEEK_API_KEY is not visible in this shell.
  echo If you used setx before, close this window and open a new terminal/session.
  echo The key is never printed or written by this script.
) else (
  echo [OK] DEEPSEEK_API_KEY is available. Value is hidden.
)

echo.
echo Setup complete.
echo Aider executable: %CD%\.dev-fallback-bin\aider.exe
echo Start long coding tasks with RUN_DEV_TASK_AUTO.bat
exit /b 0

:fail
echo.
echo Setup failed safely. Project source/data were not reset or deleted.
exit /b 1
