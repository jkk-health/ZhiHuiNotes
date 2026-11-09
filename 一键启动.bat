@echo off
chcp 65001 >nul
setlocal
title 智汇笔记 - 一键启动
set "PYTHONHOME="
set "PYTHONPATH="
if not exist "%~dp0python-runtime\python.exe" (
    echo 缺少 Python 运行时，请先完整解压交付包，再双击一键启动.bat。
    pause
    exit /b 1
)
"%~dp0python-runtime\python.exe" -X utf8 -I "%~dp0scripts\launch.py" start %*
if errorlevel 1 (
    echo.
    echo 启动失败，请查看上方提示和日志。
    pause
    exit /b 1
)
exit /b 0
