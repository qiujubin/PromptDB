@echo off
chcp 65001 >nul
title AI Prompt Assistant - Stop

echo ============================================
echo  停止 AI 绘图提示词助手相关进程
echo ============================================
echo.

echo 关闭占用 4165 端口的进程（后端）...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4165" ^| findstr "LISTENING"') do (
    echo 终止 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo 关闭占用 4163 端口的进程（前端）...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4163" ^| findstr "LISTENING"') do (
    echo 终止 PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo 关闭相关 cmd 窗口 ...
taskkill /FI "WINDOWTITLE eq AI Prompt - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq AI Prompt - Frontend*" /F >nul 2>&1

echo 完成。
pause