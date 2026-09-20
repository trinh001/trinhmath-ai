@echo off
setlocal
cd /d "%~dp0"

if not exist "ai\DEV_TASK.md" (
  echo Missing ai\DEV_TASK.md
  exit /b 1
)

if not exist ".dev-fallback-venv\Scripts\python.exe" (
  echo Fallback launcher environment is not installed.
  echo Run SETUP_DEV_FALLBACK.bat first.
  exit /b 1
)

if not exist ".dev-fallback-bin\aider.exe" (
  echo Aider fallback is not installed.
  echo Run SETUP_DEV_FALLBACK.bat first.
  exit /b 1
)

set "TRINHMATH_AIDER_CMD=%CD%\.dev-fallback-bin\aider.exe"

".dev-fallback-venv\Scripts\python.exe" "dev-tools\dev_fallback.py" --repo "%CD%" --task-file "ai\DEV_TASK.md"
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
  echo Dev task completed. See .dev-fallback\state.json for status details.
) else (
  echo Dev task stopped safely with exit code %EXIT_CODE%.
  echo See .dev-fallback\state.json for the exact reason.
)
exit /b %EXIT_CODE%
