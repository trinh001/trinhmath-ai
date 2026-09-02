@echo off
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%.venv\Scripts\python.exe" (
  echo Khong tim thay moi truong chay cua app.
  echo Hay mo README.md de xem cach cai lai moi truong.
  pause
  exit /b 1
)
"%APP_DIR%.venv\Scripts\python.exe" -m streamlit run "%APP_DIR%app.py" --server.port 8501 --server.headless true --global.developmentMode false
pause
