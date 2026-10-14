@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set /p "LAB_PYTHON="<"%~dp0python-path.txt"
if not exist "%LAB_PYTHON%" (
  echo Interpreteur absent. Modifiez python-path.txt avec le chemin de Python 3.12 ou plus.
  pause
  exit /b 1
)
"%LAB_PYTHON%" "%~dp0run.py" --open
pause
