@echo off
setlocal
cd /d "%~dp0"

set "CONVERTER_DIR=%CD%\math-document-converter"
set "TOAN_DIR=%CD%\toan-ai-local"
set "PROVENANCE_FILE=%TOAN_DIR%\question_provenance.json"

if exist "%CONVERTER_DIR%\.venv\Scripts\python.exe" (
  set "CONVERTER_PY=%CONVERTER_DIR%\.venv\Scripts\python.exe"
) else (
  set "CONVERTER_PY=python"
)

if exist "%TOAN_DIR%\.venv\Scripts\python.exe" (
  set "TOAN_PY=%TOAN_DIR%\.venv\Scripts\python.exe"
) else (
  set "TOAN_PY=python"
)

echo [1/3] Exporting trusted question-level provenance...
"%CONVERTER_PY%" "%CONVERTER_DIR%\export_question_provenance.py" --output "%PROVENANCE_FILE%"
if errorlevel 1 goto :fail

echo.
echo [2/3] Running full local M2 measurement...
pushd "%TOAN_DIR%"
"%TOAN_PY%" run_local_m2_measurement.py --candidates question_candidates.json --sources source_catalog.json --question-provenance question_provenance.json
if errorlevel 1 (
  popd
  goto :fail
)
popd

echo.
echo [3/3] Done.
echo Derived provenance: %PROVENANCE_FILE%
echo No source/OCR/student data was sent to an external API.
echo Open TrinhMath and go to "Phan tich kho de" to see the updated M2 queue.
exit /b 0

:fail
echo.
echo M2 provenance cycle FAILED. No approval/release state was changed.
exit /b 1
