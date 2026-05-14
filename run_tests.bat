@echo off
setlocal enabledelayedexpansion

:: 设置UTF-8编码支持中文字符
chcp 65001 >nul 2>&1

:: 设置窗口标题
title EPUB转换器测试套件

echo ========================================
echo    EPUB转换器测试套件
echo    EPUB Converter Test Suite
echo ========================================
echo.

:: 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未找到Python环境
    echo 请先安装Python 3.7或更高版本
    pause
    exit /b 1
)

:: 检查项目结构
if not exist "epub_converter" (
    echo ❌ 错误：找不到epub_converter目录
    echo 请在项目根目录中运行此脚本
    pause
    exit /b 1
)

if not exist "tests" (
    echo ❌ 错误：找不到tests目录
    pause
    exit /b 1
)

:: 运行测试
echo 🚀 运行测试套件...
echo.

python tests/run_all_tests.py

:: 检查测试结果
set EXIT_CODE=%errorlevel%

echo.
if %EXIT_CODE% equ 0 (
    echo ========================================
    echo ✅ 所有测试通过
    echo ========================================
) else (
    echo ========================================
    echo ⚠️  部分测试失败或有错误
    echo ========================================
)

echo.
echo 按任意键退出...
pause >nul

exit /b %EXIT_CODE%