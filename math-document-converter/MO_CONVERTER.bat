@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "E:\" (set "MATH_CONVERTER_DATA_DIR=E:\TrinhMath_Data\MathDocumentConverter") else (set "MATH_CONVERTER_DATA_DIR=%CD%\data")
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai Converter. Hay bam CAI_DAT_CONVERTER.bat truoc.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set "APPDATA=%MATH_CONVERTER_DATA_DIR%\runtime\appdata"
set "LOCALAPPDATA=%MATH_CONVERTER_DATA_DIR%\runtime\localappdata"
set "MPLCONFIGDIR=%MATH_CONVERTER_DATA_DIR%\runtime\matplotlib"
set "TORCH_HOME=%MATH_CONVERTER_DATA_DIR%\runtime\torch"
set "YOLO_CONFIG_DIR=%MATH_CONVERTER_DATA_DIR%\runtime\appdata"
set "HF_HOME=%MATH_CONVERTER_DATA_DIR%\runtime\huggingface"
set "HUGGINGFACE_HUB_CACHE=%HF_HOME%\hub"
mkdir "%APPDATA%" "%LOCALAPPDATA%" "%MPLCONFIGDIR%" "%TORCH_HOME%" "%HF_HOME%" >nul 2>nul
streamlit run app.py --server.port 8503
