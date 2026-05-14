@echo off
echo ==========================================
echo   AtomCode2API - OpenAI 兼容 API 代理
echo ==========================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo [1/2] 创建虚拟环境...
    python -m venv venv
)

echo [2/2] 安装依赖...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo.
echo 启动服务...
echo API 地址: http://localhost:8000/v1/chat/completions
echo 模型列表: http://localhost:8000/v1/models
echo.
python server.py
