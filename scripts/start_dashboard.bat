@echo off
REM Agent OS 快速启动脚本 (Windows)

echo ========================================
echo    Agent OS v0.3.0 - 快速启动
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python未安装
    pause
    exit /b 1
)

REM 切换到项目目录
cd /d "%~dp0\.."

REM 启动服务
echo [1/2] 启动API服务...
start "Agent OS API" python src\api\main_complete.py

timeout /t 3 /nobreak >nul

echo [2/2] 启动Dashboard...
start "Agent OS Dashboard" python -m http.server 8080 -d dashboard

timeout /t 2 /nobreak >nul

REM 打开浏览器
echo [完成] 打开浏览器...
start http://localhost:8080

echo.
echo ========================================
echo   服务已启动！
echo ========================================
echo.
echo 服务地址:
echo   - API: http://localhost:8000
echo   - Dashboard: http://localhost:8080
echo   - API文档: http://localhost:8000/docs
echo.
echo 测试用户:
echo   - User ID: test_user_001
echo   - Role: admin
echo   - 请求头: X-User-ID: test_user_001
echo.
echo 按任意键退出（服务将继续运行）...
pause >nul
