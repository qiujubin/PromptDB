@echo off
chcp 65001 >nul
title AI Prompt Assistant - First-time Setup

set ROOT=%~dp0

echo ============================================
echo  AI 绘图提示词助手 - 首次配置
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.10+
    pause & exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未检测到 Node.js，请先安装 Node.js 18+
    pause & exit /b 1
)
where psql >nul 2>nul
if errorlevel 1 (
    echo [WARN] 未检测到 psql 命令行，请确认 PostgreSQL 已安装
)

echo.
echo === [1/4] 后端 Python 虚拟环境 ===
cd /d "%ROOT%backend"
if not exist .venv (
    echo 创建 .venv ...
    python -m venv .venv || (echo [ERROR] venv 创建失败 & pause & exit /b 1)
) else (
    echo .venv 已存在，跳过
)
call .venv\Scripts\activate
echo 升级 pip ...
python -m pip install --upgrade pip -q
echo 安装后端依赖 ...
pip install -r requirements.txt || (echo [ERROR] pip install 失败 & pause & exit /b 1)

echo.
echo === [2/4] 准备 .env ===
if not exist .env (
    copy .env.example .env >nul
    echo 已生成 backend\.env，请按以下格式编辑后保存：
    echo.
    echo   DEEPSEEK_API_KEY=sk-你的密钥
    echo   DATABASE_URL=postgresql+asyncpg://postgres:你的密码@localhost:5432/promptdb
    echo.
    echo 完成后按任意键继续 ...
    pause >nul
) else (
    echo .env 已存在，跳过
)

echo.
echo === [3/4] 前端依赖 ===
cd /d "%ROOT%frontend"
if not exist node_modules (
    echo 安装 npm 依赖（首次较慢，请等待）...
    call npm install || (echo [ERROR] npm install 失败 & pause & exit /b 1)
) else (
    echo node_modules 已存在，跳过
)

echo.
echo === [4/4] PostgreSQL 数据库 ===
echo 请手动执行以下命令之一创建 promptdb 库：
echo.
echo   方式 A（命令行）: psql -U postgres -c "CREATE DATABASE promptdb;"
echo   方式 B（pgAdmin）: 在 pgAdmin 里右键 Databases -^> Create -^> Database -^> Name: promptdb
echo.
echo 完成后按任意键结束 ...
pause >nul

echo.
echo ============================================
echo  配置完成！双击 start.bat 启动应用
echo ============================================
pause