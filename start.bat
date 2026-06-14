@echo off
chcp 65001 >nul
title AI Prompt Assistant - Launcher

set ROOT=%~dp0

echo ============================================
echo  启动 AI 绘图提示词助手
echo ============================================
echo.

if not exist "%ROOT%backend\.venv\Scripts\python.exe" (
    echo [ERROR] 未检测到后端虚拟环境，请先双击 setup.bat 完成首次配置
    pause & exit /b 1
)
if not exist "%ROOT%frontend\node_modules" (
    echo [ERROR] 未检测到前端依赖，请先双击 setup.bat 完成首次配置
    pause & exit /b 1
)
if not exist "%ROOT%backend\.env" (
    echo [ERROR] 未检测到 backend\.env，请先双击 setup.bat 完成首次配置
    pause & exit /b 1
)

echo [1/3] 启动后端 http://localhost:4165
start "AI Prompt - Backend (4165)" cmd /k "cd /d %ROOT%backend && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 4165"

echo [2/3] 启动前端 http://localhost:4163
start "AI Prompt - Frontend (4163)" cmd /k "cd /d %ROOT%frontend && npm run dev"

echo [3/3] 等待服务就绪，5 秒后自动打开浏览器 ...
timeout /t 5 /nobreak >nul
start http://localhost:4163

echo.
echo 两个服务已在独立窗口运行，关闭对应窗口即可停止。
echo 按任意键关闭启动器（不会停止已启动的服务）...
pause >nul