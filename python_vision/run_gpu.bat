@echo off
cd /d "%~dp0"
echo ============================================================
echo   Smart Traffic Vision AI - Running on NVIDIA RTX 3050 GPU
echo ============================================================
py -3.12 main_vision.py
pause
