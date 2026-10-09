@echo off
cd /d "%~dp0"
echo ============================================================
echo   Label Uploaded Car Images and Train on NVIDIA GPU
echo ============================================================
echo.
echo   [1] Auto-Label All Images and Train on GPU (Recommended)
echo   [2] Interactive Visual Labeler (Review / Adjust in UI)
echo.
set /p CHOICE="Enter choice [1 or 2, default is 1]: "
if "%CHOICE%"=="2" (
    py -3.12 python_vision\label_uploaded_images.py
) else (
    py -3.12 python_vision\label_uploaded_images.py --auto
)
pause
