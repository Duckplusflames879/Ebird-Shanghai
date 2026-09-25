@echo off
setlocal
cd /d "%~dp0"
REM 现在默认启动完整应用并在打开前自动更新最近7日观鸟数据。
python start_app.py
if errorlevel 1 (
  echo.
  echo 启动失败，请确认 Python 3 已安装，并已安装 requirements.txt 中的依赖。
  pause
)
endlocal
