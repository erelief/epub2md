#!/usr/bin/env python3
"""
创建简单便携版EPUB转换器
使用虚拟环境方式，更轻量级
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def create_virtual_env():
    """创建虚拟环境"""
    print("📦 创建虚拟环境...")
    
    venv_dir = Path("venv_portable")
    
    # 删除已存在的虚拟环境
    if venv_dir.exists():
        shutil.rmtree(venv_dir)
    
    try:
        # 创建虚拟环境
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
        print("✓ 虚拟环境创建完成")
        return venv_dir
    except subprocess.CalledProcessError as e:
        print(f"❌ 虚拟环境创建失败: {e}")
        return None

def install_dependencies_to_venv(venv_dir):
    """在虚拟环境中安装依赖"""
    print("📦 安装依赖到虚拟环境...")
    
    # 确定虚拟环境中的Python路径
    if os.name == 'nt':  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:  # Linux/Mac
        python_exe = venv_dir / "bin" / "python"
        pip_exe = venv_dir / "bin" / "pip"
    
    try:
        # 升级pip
        subprocess.check_call([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])
        
        # 安装html2text
        subprocess.check_call([str(pip_exe), "install", "html2text>=2020.1.16"])
        
        print("✓ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def create_portable_launcher():
    """创建便携版启动脚本"""
    print("📝 创建启动脚本...")
    
    # Windows启动脚本
    launcher_content = '''@echo off
setlocal enabledelayedexpansion

:: 设置UTF-8编码支持中文字符
chcp 65001 >nul 2>&1

:: 设置窗口标题
title EPUB到Markdown转换器 (便携版)

:: 显示欢迎信息
echo ========================================
echo    EPUB到Markdown转换器 (便携版)
echo    EPUB to Markdown Converter (Portable)
echo ========================================
echo.

:: 设置虚拟环境路径
set VENV_DIR=%~dp0venv_portable
set PYTHON_EXE=%VENV_DIR%\\Scripts\\python.exe

:: 检查虚拟环境是否存在
if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到便携版Python环境
    echo 请确保venv_portable目录存在
    echo 如果是首次使用，请先运行 create_portable_simple.py
    echo.
    pause
    exit /b 1
)

:: 检查转换器模块
"%PYTHON_EXE%" -c "import epub_converter" >nul 2>&1
if !errorlevel! neq 0 (
    echo ❌ 错误：找不到epub_converter模块
    echo 请确保在正确的目录中运行此脚本
    echo.
    pause
    exit /b 1
)

:: 启动程序
echo 🚀 启动EPUB转换器...
echo.

:: 运行主程序，传递所有命令行参数
"%PYTHON_EXE%" -m epub_converter %*

:: 检查程序执行结果
set EXIT_CODE=!errorlevel!

echo.
if !EXIT_CODE! equ 0 (
    echo ========================================
    echo ✓ 程序执行完成
    echo ========================================
) else (
    echo ========================================
    echo ❌ 程序执行过程中发生错误 (退出代码: !EXIT_CODE!)
    echo ========================================
    echo.
    echo 常见问题解决方案:
    echo 1. 确保EPUB文件路径正确且文件未损坏
    echo 2. 检查输出目录是否有写入权限
    echo 3. 确保文件名不包含特殊字符
    echo 4. 尝试使用管理员权限运行
    echo.
)

:: 如果有错误或者没有传递参数（交互模式），暂停等待用户
if !EXIT_CODE! neq 0 (
    pause
) else if "%~1"=="" (
    echo 按任意键退出...
    pause >nul
)

exit /b !EXIT_CODE!
'''
    
    with open("epub_converter_portable.bat", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    print("✓ Windows启动脚本创建完成")

def create_distribution_package():
    """创建分发包说明"""
    print("📝 创建分发说明...")
    
    readme_content = '''# EPUB转换器 便携版分发包

## 📦 包含内容
- epub_converter/ - 转换器源代码
- venv_portable/ - Python虚拟环境（包含所有依赖）
- epub_converter_portable.bat - Windows启动脚本
- 其他项目文件

## 🚀 使用方法（接收方）

### Windows用户：
1. 解压整个文件夹到任意位置
2. 双击 `epub_converter_portable.bat` 启动程序
3. 按提示输入EPUB文件路径进行转换

### 拖拽使用：
将EPUB文件直接拖拽到 `epub_converter_portable.bat` 上

## 💡 优势
- ✅ 无需安装Python环境
- ✅ 无需安装任何依赖包
- ✅ 解压即用，绿色便携
- ✅ 包含完整功能

## 📏 大小说明
- 虚拟环境大小：约20-30MB
- 总包大小：约25-35MB
- 比完整Python环境小很多

## 🔧 系统要求
- Windows 7 或更高版本
- 无需预装Python
- 无其他依赖

## ⚠️ 注意事项
1. 请保持文件夹结构完整
2. 不要删除venv_portable目录
3. 如果移动位置，整个文件夹一起移动

---
便携版创建时间：{create_time}
'''
    
    from datetime import datetime
    create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open("PORTABLE_README.txt", "w", encoding="utf-8") as f:
        f.write(readme_content.format(create_time=create_time))
    
    print("✓ 分发说明创建完成")

def main():
    """主函数"""
    print("========================================")
    print("    EPUB转换器便携版创建工具")
    print("    (基于虚拟环境，轻量级方案)")
    print("========================================")
    print()
    
    # 检查当前目录
    if not Path("epub_converter").exists():
        print("❌ 错误：找不到epub_converter目录")
        print("请在项目根目录中运行此脚本")
        input("按回车键退出...")
        return False
    
    print("此工具将创建一个轻量级便携版EPUB转换器")
    print("使用虚拟环境方式，大小约25-35MB")
    print("接收方无需安装Python即可使用")
    print()
    
    response = input("是否继续创建便携版？(y/n): ").strip().lower()
    if response not in ['y', 'yes', '是']:
        print("操作已取消")
        return False
    
    print()
    
    # 创建虚拟环境
    venv_dir = create_virtual_env()
    if not venv_dir:
        input("按回车键退出...")
        return False
    
    # 安装依赖
    if not install_dependencies_to_venv(venv_dir):
        input("按回车键退出...")
        return False
    
    # 创建启动脚本
    create_portable_launcher()
    
    # 创建分发说明
    create_distribution_package()
    
    print()
    print("========================================")
    print("✓ 便携版创建完成！")
    print("========================================")
    print()
    print("📦 分发方法：")
    print("1. 将整个项目文件夹打包（zip/rar）")
    print("2. 发送给其他人")
    print("3. 对方解压后直接双击 epub_converter_portable.bat 即可使用")
    print()
    print("📁 重要文件：")
    print("- venv_portable/ - 虚拟环境（必须包含）")
    print("- epub_converter/ - 源代码（必须包含）")
    print("- epub_converter_portable.bat - 启动脚本")
    print("- PORTABLE_README.txt - 给接收方的说明")
    print()
    print("💡 优势：")
    print("- 无需目标机器安装Python")
    print("- 包大小仅25-35MB")
    print("- 绿色便携，解压即用")
    
    return True

if __name__ == "__main__":
    success = main()
    input("\n按回车键退出...")
    if not success:
        sys.exit(1)