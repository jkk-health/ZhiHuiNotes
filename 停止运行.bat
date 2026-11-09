@echo off
chcp 65001 >nul
setlocal
title 智汇笔记 - 停止运行
set "PYTHONHOME="
set "PYTHONPATH="
if not exist "%~dp0python-runtime\python.exe" (
    echo 缺少 Python 运行时，请完整解压交付包。
    pause
    exit /b 1
)
"%~dp0python-runtime\python.exe" -X utf8 -I "%~dp0scripts\launch.py" stop
if errorlevel 1 (
    pause
    exit /b 1
)
exit /b 0
