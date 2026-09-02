@echo off
chcp 65001 >nul
title Math Document Converter - Cai dat
cd /d "%~dp0"
if exist "E:\" (set "MATH_CONVERTER_DATA_DIR=E:\TrinhMath_Data\MathDocumentConverter") else (set "MATH_CONVERTER_DATA_DIR=%CD%\data")
echo ============================================================
echo   MATH DOCUMENT CONVERTER - CAI DAT CUC BO
echo ============================================================
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON if exist "..\toan-ai-local\.venv\Scripts\python.exe" set "PYTHON=..\toan-ai-local\.venv\Scripts\python.exe"
if not defined PYTHON (
  echo Khong tim thay Python 3.11+. Hay cai Python va tick Add Python to PATH.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" %PYTHON% -m venv .venv
call .venv\Scripts\activate.bat
set "PIP_CACHE_DIR=%CD%\.pip-cache"
set "APPDATA=%MATH_CONVERTER_DATA_DIR%\runtime\appdata"
set "LOCALAPPDATA=%MATH_CONVERTER_DATA_DIR%\runtime\localappdata"
set "MPLCONFIGDIR=%MATH_CONVERTER_DATA_DIR%\runtime\matplotlib"
set "YOLO_CONFIG_DIR=%MATH_CONVERTER_DATA_DIR%\runtime\appdata"
set "HF_HOME=%MATH_CONVERTER_DATA_DIR%\runtime\huggingface"
set "HUGGINGFACE_HUB_CACHE=%HF_HOME%\hub"
mkdir "%PIP_CACHE_DIR%" "%APPDATA%" "%LOCALAPPDATA%" "%MPLCONFIGDIR%" "%HF_HOME%" >nul 2>nul
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Cai PyTorch CPU va Pix2Text. Lan dau mo app, Pix2Text co the tai model ve may.
echo Ban CPU on dinh hon tren laptop 4GB VRAM; app tu dung GPU neu sau nay cai CUDA phu hop.
python -m pip install torch torchvision
python -m pip install "pix2text[multilingual]"
python -c "import torch, importlib.util; print('CUDA:', torch.cuda.is_available()); print('Pix2Text:', bool(importlib.util.find_spec('pix2text')))"
echo.
echo Cai dat xong. Bam MO_CONVERTER.bat de mo app.
pause
