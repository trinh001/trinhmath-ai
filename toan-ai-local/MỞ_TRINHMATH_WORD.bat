@echo off
setlocal
cd /d "%~dp0"
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
if not exist ".venv\Scripts\python.exe" (
  echo Khong tim thay moi truong Python cua TrinhMath AI.
  echo Hay mo app bang launcher da cai dat truoc do, sau do thu lai.
  pause
  exit /b 1
)
echo Mo TrinhMath AI trong phien Windows hien tai...
echo Word/MathType se co quyen render PDF trong cua so nay.
if not exist "tmp" mkdir "tmp"
start "TrinhMath AI - Word" /b ".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8505 --server.headless false --browser.gatherUsageStats false > "tmp\trinhmath_word_8505.log" 2>&1
echo Dang cho app khoi dong...
timeout /t 8 /nobreak > nul
start "" http://127.0.0.1:8505
echo Da mo TrinhMath AI tai http://127.0.0.1:8505
echo Khong dong cua so nay trong khi dang dung app.
pause
