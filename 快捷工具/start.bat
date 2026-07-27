@echo off
chcp 65001 >nul

echo ==================================================
echo   家庭报销管理系统 - Start Server
echo ==================================================
echo.

REM 调用 VBS 静默启动（无窗口运行 Flask）
start "" /B wscript.exe "%~dp0start_backend.vbs"

echo 启动指令已发送，窗口即将自动关闭...
echo.
echo   前端地址: http://localhost:3000
echo   账号管理: http://localhost:3000/admin/accounts
echo.
echo   停止服务：运行 tools\close.bat 或按 Ctrl+C
echo ==================================================
timeout /t 3 /nobreak >nul
