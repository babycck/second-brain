@echo off
chcp 65001 >nul
title 打包 第二大脑_8899.exe
echo 正在安装打包依赖...
python -m pip install pyinstaller fastapi uvicorn httpx pydantic
echo.
echo 正在打包生成独立免环境执行程序...
pyinstaller --noconfirm --onedir --windowed --name "第二大脑_8899" ^
    --add-data "static;static" ^
    --add-data "data;data" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.lifespans" ^
    --hidden-import "uvicorn.lifespans.on" ^
    app.py
echo.
echo 打包成功！程序已生成于 dist\第二大脑_8899 文件夹内。
pause
