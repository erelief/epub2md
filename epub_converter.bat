@echo off
setlocal enabledelayedexpansion

chcp 65001 >nul 2>&1
title EPUB2Markdown 转换器

:main_loop
echo ========================================
echo    Epub2Markdown 转换器
echo ========================================
echo 功能
echo [+] 将单个 Epub 中的页面转换为多个的 Markdown 文件
echo [+] 同时生成一个合并的 Markdown 文件
echo.
echo 支持的输入文件或文件夹
echo [+] 输入单个 Epub 文件路径 - 转换单个文件
echo [+] 输入文件夹路径 - 批量转换其中所有 Epub 文件
echo ========================================
echo.

:: 查找 Python：优先内置 portable Python，再找系统 Python
echo [1/4] 检查 Python 环境...

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

:: 系统Python需要检查依赖
echo.
echo [2/4] 检查依赖管理器...
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] pip不可用
    pause
    exit /b 1
)
echo [+] pip可用

echo.
echo [3/4] 检查依赖包...
%PYTHON_CMD% -c "import html2text" >nul 2>&1
if %errorlevel% neq 0 (
    echo [>>] 安装html2text依赖包...
    %PYTHON_CMD% -m pip install html2text>=2020.1.16 --no-warn-script-location
    if !errorlevel! neq 0 (
        echo [!] 无法安装html2text
        pause
        exit /b 1
    )
    echo [+] html2text安装成功
) else (
    echo [+] html2text已安装
)

echo.
echo [4/4] 检查转换器模块...
%PYTHON_CMD% -c "import epub_converter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到epub_converter模块
    pause
    exit /b 1
)
echo [+] 转换器模块可用
goto :run_program

:skip_dep_check
echo.
echo [2/4] 跳过 - 便携版已预装依赖
echo [3/4] 跳过 - 便携版已预装依赖
echo.
echo [4/4] 检查转换器模块...
%PYTHON_CMD% -c "import epub_converter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 找不到epub_converter模块
    pause
    exit /b 1
)
echo [+] 转换器模块可用

:run_program
echo.
echo ========================================
echo 启动 Epub 转换器...
echo ========================================
echo.

%PYTHON_CMD% -m epub_converter %*

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

:ask_continue
echo.
echo ========================================
echo 是否要继续转换其他 Epub 文件？
echo.

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
