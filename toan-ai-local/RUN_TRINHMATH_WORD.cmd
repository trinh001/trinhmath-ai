@echo off
setlocal
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist ".venv\Scripts\python.exe" (
  echo Khong tim thay moi truong Python cua TrinhMath AI.
  pause
  exit /b 1
)
if not exist "tmp" mkdir "tmp"
start "TrinhMath AI - Word" /b ".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8505 --server.headless false --browser.gatherUsageStats false > "tmp\trinhmath_word_8505.log" 2>&1
echo Dang cho app khoi dong...
timeout /t 8 /nobreak > nul
start "" http://127.0.0.1:8505
echo Da mo TrinhMath AI tai http://127.0.0.1:8505
pause
