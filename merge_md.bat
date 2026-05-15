@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1
title Markdown 文件合并工具

:main_loop
echo ========================================
echo    Markdown 文件合并工具
echo ========================================
echo 功能
echo [+] 将目录中的所有 MD 文件合并为一个完整文件
echo [+] 自动处理跨页链接和锚点
echo [+] 支持拖拽目录或手动输入路径
echo ========================================
echo.

:: 查找 Python：优先内置 portable Python，再找系统 Python
echo [1/2] 检查 Python 环境...

:: 1) 内置 portable Python
set "PORTABLE_PY=%~dp0python\python.exe"
if exist "%PORTABLE_PY%" (
    set PYTHON_CMD="%PORTABLE_PY%"
    echo [+] 使用内置 Python 环境
    goto :skip_dep_check
)

:: 2) 系统 Python
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :check_version
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :check_version
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :check_version
)

echo [!] 错误：未找到 Python 环境
echo.
echo 便携版：请确保 python 文件夹存在
echo 手动安装：https://www.python.org/downloads/
echo.
pause
exit /b 1

:check_version
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [+] 找到Python版本: %PYTHON_VERSION%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)
if %MAJOR% lss 3 (
    echo [!] Python版本过低，需要3.7或更高版本
    pause
    exit /b 1
)
if %MAJOR% equ 3 if %MINOR% lss 7 (
    echo [!] Python版本过低，需要3.7或更高版本
    pause
    exit /b 1
)

echo.
echo [2/2] 检查合并器模块...
%PYTHON_CMD% -c "import md_merger" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到md_merger模块
    pause
    exit /b 1
)
echo [+] 合并器模块可用
goto :run_program

:skip_dep_check
echo.
echo [2/2] 检查合并器模块...
%PYTHON_CMD% -c "import md_merger" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到md_merger模块
    pause
    exit /b 1
)
echo [+] 合并器模块可用

:run_program
echo.
echo ========================================
echo 启动 MD 合并器...
echo ========================================
echo.

%PYTHON_CMD% -m md_merger %*

set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% equ 0 (
    echo ========================================
    echo [+] 合并完成！
    echo ========================================
) else (
    echo ========================================
    echo [!] 程序执行过程中发生错误 (退出代码: %EXIT_CODE%)
    echo ========================================
    echo.
    echo 常见问题解决方案:
    echo 1. 确保目录路径正确且包含MD文件
    echo 2. 检查目录是否有写入权限
    echo 3. 确保文件名不包含特殊字符
    echo 4. 尝试使用管理员权限运行
    echo.
)

:ask_continue
echo.
echo ========================================
echo 是否要继续合并其他目录？
echo.

choice /c YN /n /m "请按 Y 继续，N 退出: "

if errorlevel 2 (
    echo.
    echo 感谢使用 MD 合并工具！
    echo 按任意键退出...
    pause >nul
    exit /b %EXIT_CODE%
)

echo.
echo 重新启动合并器...
echo.
goto :run_program
