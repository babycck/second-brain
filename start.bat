@echo off
chcp 65001 >nul
title 第二大脑 (Port 8899)
echo ========================================================
echo   启动 第二大脑 故事资产与认知工坊 (Port 8899)
echo   默认模型: deepseek-flash
echo ========================================================
python -m pip install -r requirements.txt
echo.
echo 正在启动本地服务器并自动唤起浏览器 (单窗口模式)...
python app.py
pause
