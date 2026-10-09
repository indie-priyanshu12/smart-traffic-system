@echo off
cd /d "%~dp0"
echo ============================================================
echo   Running YOLO Training on NVIDIA GPU (Python 3.12)
echo ============================================================
py -3.12 train_custom.py
pause
