@echo off
setlocal
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo.
echo ======================================================
echo   TRINHMATH AI - CAI OCR CUC BO (KHONG DUNG GEMINI)
echo ======================================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo App chua duoc cai tren may nay. Dang mo bo cai app truoc...
  call "CAI_DAT_MAY_MOI.bat"
)
if not exist ".venv\Scripts\python.exe" goto :NO_ENV

echo Dang cai Pix2Text va cac thanh phan nhan dien cong thuc.
echo Lan dau co the tai nhieu du lieu va mat kha lau. Can giu ket noi Internet.
".venv\Scripts\python.exe" -m pip install --upgrade "pix2text[multilingual]"
if errorlevel 1 goto :FAILED

echo.
echo Dang kiem tra GPU...
".venv\Scripts\python.exe" -c "import torch; print('PyTorch CUDA san sang:' , torch.cuda.is_available()); print('GPU:' , torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Khong phat hien GPU CUDA')"
echo.
echo CAI DAT OCR XONG.
echo Mo MO_APP_TOAN.bat ^> Goc cung suy nghi AI ^> Quet OCR cuc bo bang may nay.
echo Neu dong CUDA la False, OCR van chay duoc nhung cham hon va may nay khong phai GPU NVIDIA da san sang.
echo.
pause
exit /b 0

:NO_ENV
echo Khong tao duoc moi truong app. Hay cai Python va chay CAI_DAT_MAY_MOI.bat truoc.
pause
exit /b 1

:FAILED
echo Cai OCR chua thanh cong. Hay kiem tra mang, dung luong o dia va thu lai.
pause
exit /b 1
