@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==================================================
echo   家庭报销管理系统 - Stop Server
echo ==================================================
echo.

echo 正在查找占用端口 3000...
set FOUND=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":3000 " ^| findstr LISTENING') do (
    set FOUND=1
    echo 找到进程 PID %%p
    taskkill /F /PID %%p >nul 2>nul
    if !ERRORLEVEL! equ 0 (
        echo 主进程已终止
    )
)

echo 正在清理残留的 Python 进程
taskkill /F /IM python.exe >nul 2>nul
if !ERRORLEVEL! equ 0 (
    echo 残留进程已清理
) else (
    if !FOUND! equ 0 (
        echo 未找到相关进程，服务可能未启动
    ) else (
        echo 所有进程已终止
    )
)

echo.
echo 操作完成，按任意键退出...
pause >nul
endlocal
