@echo off
setlocal enabledelayedexpansion

:: 设置UTF-8编码支持中文字符
chcp 65001 >nul 2>&1

:: 设置窗口标题
title Markdown 文件合并工具

:main_loop
:: 显示欢迎信息
echo ========================================
echo    Markdown 文件合并工具
echo ========================================
echo 功能
echo ✓ 将目录中的所有 MD 文件合并为一个完整文件
echo ✓ 自动处理跨页链接和锚点
echo ✓ 支持拖拽目录或手动输入路径
echo.
echo 使用方式
echo ✓ 拖拽包含MD文件的目录到此处
echo ✓ 双击运行后手动输入目录路径
echo ========================================
echo.

:: 检查Python环境
echo [1/2] 检查 Python 环境...

:: 首先尝试python命令
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :check_version
)

:: 如果python不可用，尝试python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :check_version
)

:: 如果都不可用，尝试py启动器
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :check_version
)

:: 都没找到Python
echo ❌ 错误：未找到 Python 环境
echo.
echo 请先安装 Python 3.7 或更高版本：
echo   - 官方下载：https://www.python.org/downloads/
echo   - 或者从 Microsoft Store 安装 Python
echo.
echo 安装完成后请重新运行此脚本。
echo.
pause
exit /b 1

:check_version
:: 获取Python版本信息
for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ 找到Python版本: %PYTHON_VERSION%

:: 检查Python版本是否满足要求（3.7+）
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% lss 3 (
    echo ❌ 错误：Python版本过低，需要3.7或更高版本
    echo 当前版本：%PYTHON_VERSION%
    echo 请升级Python后重试。
    pause
    exit /b 1
)

if %MAJOR% equ 3 if %MINOR% lss 7 (
    echo ❌ 错误：Python版本过低，需要3.7或更高版本
    echo 当前版本：%PYTHON_VERSION%
    echo 请升级Python后重试。
    pause
    exit /b 1
)

:: 检查合并器模块是否可用
echo.
echo [2/2] 检查合并器模块...
%PYTHON_CMD% -c "import md_merger" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：找不到md_merger模块
    echo 请确保在正确的目录中运行此脚本。
    echo 当前目录应包含md_merger文件夹。
    pause
    exit /b 1
)
echo ✓ 合并器模块可用

:run_program
:: 启动程序
echo.
echo ========================================
echo 启动 MD 合并器...
echo ========================================
echo.

:: 运行主程序，传递所有命令行参数
%PYTHON_CMD% -m md_merger %*

:: 检查程序执行结果
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% equ 0 (
    echo ========================================
    echo ✓ 合并完成！
    echo ========================================
) else (
    echo ========================================
    echo ❌ 程序执行过程中发生错误 (退出代码: %EXIT_CODE%)
    echo ========================================
    echo.
    echo 常见问题解决方案:
    echo 1. 确保目录路径正确且包含MD文件
    echo 2. 检查目录是否有写入权限
    echo 3. 确保文件名不包含特殊字符
    echo 4. 尝试使用管理员权限运行
    echo.
)

:: 询问用户是否继续合并
:ask_continue
echo.
echo ========================================
echo 是否要继续合并其他目录？
echo.

:: 使用choice命令避免stdin问题
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
