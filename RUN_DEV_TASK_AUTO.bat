@echo off
setlocal
cd /d "%~dp0"

if not exist "ai\DEV_TASK.md" (
  echo Missing ai\DEV_TASK.md
  echo Put the full coding task in that file once, then run this launcher.
  exit /b 1
)

if not exist ".dev-fallback-venv\Scripts\python.exe" (
  echo Fallback environment is not installed yet.
  echo Run SETUP_DEV_FALLBACK.bat once first.
  exit /b 1
)

if not exist ".dev-fallback-venv\Scripts\aider.exe" (
  echo Aider fallback is not installed yet.
  echo Run SETUP_DEV_FALLBACK.bat once first.
  exit /b 1
)

".dev-fallback-venv\Scripts\python.exe" "dev-tools\dev_fallback.py" --repo "%CD%" --task-file "ai\DEV_TASK.md"
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
  echo Dev task completed. See .dev-fallback\state.json for worker/status details.
) else (
  echo Dev task stopped safely with exit code %EXIT_CODE%.
  echo See .dev-fallback\state.json for the exact reason.
)
exit /b %EXIT_CODE%
