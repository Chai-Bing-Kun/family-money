@echo off
chcp 65001 >nul
echo Family Expense Manager - Virtual Env Start
echo.

cd /d "D:\桌面文件\GitHub\family-money"
call "D:\桌面文件\GitHub\family-money\.venv\Scripts\activate.bat"

echo [OK] Virtual env activated: .venv
echo.

python "D:\桌面文件\GitHub\family-money\backend\app.py"

pause
