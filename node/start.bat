@echo off
echo ==========================================
echo   AtomCode2API (Node.js) - 启动
echo ==========================================
cd /d "%~dp0"
if not exist "node_modules" (
    echo 安装依赖...
    npm install
)
echo.
echo 启动服务 (端口 8001)...
node server.js
