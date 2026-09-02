@echo off
setlocal
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo.
echo ======================================================
echo      TRINHMATH AI - CAI DAT CHO MAY TINH MOI
echo ======================================================
echo.

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" --version >nul 2>nul
  if not errorlevel 1 goto :ALREADY_READY
)

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m venv ".venv"
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 goto :NO_PYTHON
  python -m venv ".venv"
)

if not exist ".venv\Scripts\python.exe" goto :CREATE_ENV_FAILED

echo Dang cai cac thanh phan can thiet. Lan dau co the mat vai phut...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :PIP_FAILED
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :PIP_FAILED

echo.
echo CAI DAT XONG. Tu lan sau, chi can bam MO_APP_TOAN.bat.
echo.
pause
exit /b 0

:ALREADY_READY
echo App da co moi truong chay tren may nay.
echo Khong can cai dat lai. Hay bam MO_APP_TOAN.bat de mo app.
echo.
pause
exit /b 0

:NO_PYTHON
echo Python chua co tren may nay.
echo Hay cai Python 3.11 hoac moi hon tu https://www.python.org/downloads/
echo Nho tick chon "Add Python to PATH" khi cai, roi bam lai file nay.
echo.
pause
exit /b 1

:CREATE_ENV_FAILED
echo Khong tao duoc moi truong chay cho app.
echo Hay thu cai Python 3.11 va bam lai file nay.
echo.
pause
exit /b 1

:PIP_FAILED
echo Cai dat chua thanh cong. Hay kiem tra ket noi Internet va thu lai.
echo.
pause
exit /b 1
