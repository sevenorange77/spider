@echo off
echo 正在安装NGA论坛监控工具所需的依赖库...
echo.

echo 检测Python版本...
python --version 2>nul
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python
    pause
    exit /b 1
)

python -c "import sys; print('Python版本:', sys.version)" 2>nul
echo.
echo 注意：如果使用Python 2.7，某些功能可能受限，建议升级到Python 3.7+
echo.

echo 升级pip...
python -m pip install --upgrade pip

echo.
echo 安装项目依赖库...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo 安装失败！可能的原因：
    echo 1. Python版本过低（建议使用Python 3.7+）
    echo 2. 网络连接问题
    echo 3. 权限不足
    echo.
    echo 请尝试手动运行：pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo 安装完成！
echo 现在可以运行以下命令启动GUI：
echo python nga_monitor_gui.py
echo.
echo 或者双击运行：运行可视化窗口.bat
echo.
pause 