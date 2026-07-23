@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==================================================
echo   🏠 家庭报销管理系统 - 启动后端服务
echo ==================================================
echo.

cd /d "%~dp0..\backend"

REM 检查 Python 是否存在
set "PYTHON=python"
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ 未找到 python 命令，尝试 D 盘 Python...
    if exist "D:\python-file\python.exe" (
        set "PYTHON=D:\python-file\python.exe"
    ) else (
        echo ❌ 未找到 Python，请确认 Python 已安装
        pause
        exit /b 1
    )
)

echo 🔄 正在后台启动后端服务...
echo.

REM 在后台静默启动 Flask 服务（独立于本窗口，关闭窗口不影响服务）
start "" /MIN "%COMSPEC%" /c "title flask-server && cd /d "%~dp0..\backend" && "%PYTHON%" app.py"

REM 等待 2 秒确认端口是否已监听
timeout /t 2 /nobreak >nul
netstat -ano 2>nul | findstr ":3000 " | findstr LISTENING >nul
if !ERRORLEVEL! equ 0 (
    echo ✅ 后端服务已启动！
) else (
    echo ⚠️ 服务启动中，请稍后访问网页检查...
)

echo.
echo   前端地址: http://localhost:3000
echo   账号管理: http://localhost:3000/admin/accounts
echo   管理员账号: chaibingkun
echo.
echo   ✅ 关闭此窗口不影响服务运行
echo   🛑 停止服务请双击: close.bat
echo ==================================================
echo.
pause
