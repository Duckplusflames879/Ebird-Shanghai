@echo off
setlocal
cd /d "%~dp0"
python start_app.py
if errorlevel 1 (
  echo.
  echo 启动失败，请确认 Python 3 已安装，并已安装 requirements.txt 中的依赖。
  pause
)
endlocal
