@echo off
setlocal enabledelayedexpansion

:: 设置窗口标题
title EPUB2Markdown 转换器

:main_loop
:: 显示欢迎信息
echo ========================================
echo    Epub2Markdown 转换器
echo ========================================
echo 功能
echo [+] 把每个 Epub 中的页面转换成单独的 Markdown 文件
echo [+] 同时输出整书的单独 Markdown 文件
echo.
echo 支持单个文件或批量处理
echo [+] 输入单个 Epub 文件路径- 转换单个文件
echo [+] 输入文件夹路径 - 批量转换所有 Epub 文件
echo ========================================
echo.

:: 检查Python环境
echo [1/4] 检查 Python 环境...

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
echo [!] 错误：未找到 Python 环境
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
echo [+] 找到Python版本: %PYTHON_VERSION%

:: 检查Python版本是否满足要求（3.7+）
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% lss 3 (
    echo [!] 错误：Python版本过低，需要3.7或更高版本
    echo 当前版本：%PYTHON_VERSION%
    echo 请升级Python后重试。
    pause
    exit /b 1
)

if %MAJOR% equ 3 if %MINOR% lss 7 (
    echo [!] 错误：Python版本过低，需要3.7或更高版本
    echo 当前版本：%PYTHON_VERSION%
    echo 请升级Python后重试。
    pause
    exit /b 1
)

:: 检查pip是否可用
echo.
echo [2/4] 检查包管理器...
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 错误：pip不可用，无法安装依赖包
    echo 请重新安装Python并确保包含pip。
    pause
    exit /b 1
)
echo [+] pip可用

:: 检查并安装依赖
echo.
echo [3/4] 检查依赖包...

:: 检查html2text
%PYTHON_CMD% -c "import html2text" >nul 2>&1
if %errorlevel% neq 0 (
    echo [>>] 安装html2text依赖包...
    %PYTHON_CMD% -m pip install html2text>=2020.1.16 --no-warn-script-location
    if !errorlevel! neq 0 (
        echo [!] 错误：无法安装html2text依赖包
        echo 请检查网络连接或手动运行：
        echo   %PYTHON_CMD% -m pip install html2text
        pause
        exit /b 1
    )
    echo [+] html2text安装成功
) else (
    echo [+] html2text已安装
)

:: 检查转换器模块是否可用
echo.
echo [4/4] 检查转换器模块...
%PYTHON_CMD% -c "import epub_converter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 错误：找不到epub_converter模块
    echo 请确保在正确的目录中运行此脚本。
    echo 当前目录应包含epub_converter文件夹。
    pause
    exit /b 1
)
echo [+] 转换器模块可用

:run_program
:: 启动程序
echo.
echo ========================================
echo 启动 Epub 转换器...
echo ========================================
echo.

:: 运行主程序，传递所有命令行参数（显示所有debug输出）
%PYTHON_CMD% -m epub_converter %*

:: 检查程序执行结果
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% equ 0 (
    echo ========================================
    echo [+] 转换完成！
    echo ========================================
) else (
    echo ========================================
    echo [!] 程序执行过程中发生错误 (退出代码: %EXIT_CODE%)
    echo ========================================
    echo.
    echo 常见问题解决方案:
    echo 1. 确保 Epub 文件路径正确且文件未损坏
    echo 2. 检查输出目录是否有写入权限
    echo 3. 确保文件名不包含特殊字符
    echo 4. 尝试使用管理员权限运行
    echo.
)

:: 询问用户是否继续转换
:ask_continue
echo.
echo ========================================
echo 是否要继续转换其他 Epub 文件？
echo.

:: 使用choice命令避免stdin问题
choice /c YN /n /m "请按 Y 继续，N 退出: "

if errorlevel 2 (
    echo.
    echo 感谢使用 Epub 转换器！
    echo 按任意键退出...
    pause >nul
    exit /b %EXIT_CODE%
)

echo.
echo 重新启动转换器...
echo.
goto :run_program