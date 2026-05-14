#!/usr/bin/env python3
"""
创建EPUB转换器便携版
Create portable version of EPUB converter with embedded Python
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
from pathlib import Path
import tempfile

def download_portable_python():
    """下载便携版Python"""
    print("📦 下载便携版Python...")
    
    # Python 3.11 便携版下载链接
    python_url = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip"
    
    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp())
    python_zip = temp_dir / "python-embed.zip"
    
    try:
        print(f"正在下载: {python_url}")
        urllib.request.urlretrieve(python_url, python_zip)
        print("✓ Python下载完成")
        
        # 解压Python
        python_dir = Path("portable_python")
        if python_dir.exists():
            shutil.rmtree(python_dir)
        python_dir.mkdir()
        
        with zipfile.ZipFile(python_zip, 'r') as zip_ref:
            zip_ref.extractall(python_dir)
        print("✓ Python解压完成")
        
        return python_dir
        
    except Exception as e:
        print(f"❌ 下载Python失败: {e}")
        return None
    finally:
        # 清理临时文件
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

def setup_portable_python(python_dir):
    """配置便携版Python"""
    print("🔧 配置便携版Python...")
    
    # 创建pth文件以启用site-packages
    pth_content = """import site
site.main()
"""
    
    pth_file = python_dir / "python311._pth"
    if pth_file.exists():
        # 读取现有内容
        with open(pth_file, 'r') as f:
            content = f.read()
        
        # 如果没有import site，添加它
        if "import site" not in content:
            content = content.replace("#import site", "import site")
            if "import site" not in content:
                content += "\nimport site\n"
            
            with open(pth_file, 'w') as f:
                f.write(content)
    
    # 下载get-pip.py
    get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
    get_pip_path = python_dir / "get-pip.py"
    
    try:
        print("下载pip安装器...")
        urllib.request.urlretrieve(get_pip_url, get_pip_path)
        print("✓ pip安装器下载完成")
    except Exception as e:
        print(f"❌ 下载pip失败: {e}")
        return False
    
    # 安装pip
    python_exe = python_dir / "python.exe"
    try:
        print("安装pip...")
        subprocess.check_call([str(python_exe), str(get_pip_path), "--no-warn-script-location"])
        print("✓ pip安装完成")
        
        # 删除get-pip.py
        get_pip_path.unlink()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ pip安装失败: {e}")
        return False
    
    return True

def install_dependencies(python_dir):
    """安装项目依赖"""
    print("📦 安装项目依赖...")
    
    python_exe = python_dir / "python.exe"
    
    # 安装html2text
    try:
        subprocess.check_call([
            str(python_exe), "-m", "pip", "install", 
            "html2text>=2020.1.16", 
            "--no-warn-script-location"
        ])
        print("✓ html2text安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def create_portable_launcher():
    """创建便携版启动脚本"""
    print("📝 创建启动脚本...")
    
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

:: 设置便携版Python路径
set PYTHON_HOME=%~dp0portable_python
set PYTHON_EXE=%PYTHON_HOME%\\python.exe
set PATH=%PYTHON_HOME%;%PYTHON_HOME%\\Scripts;%PATH%

:: 检查便携版Python是否存在
if not exist "%PYTHON_EXE%" (
    echo ❌ 错误：找不到便携版Python环境
    echo 请确保portable_python目录存在且包含python.exe
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
    
    print("✓ 启动脚本创建完成")

def create_readme():
    """创建使用说明"""
    readme_content = '''# EPUB转换器 便携版

## 📖 简介
这是EPUB转换器的便携版，包含了完整的Python环境和所有依赖包。
无需在目标机器上安装Python，直接运行即可使用。

## 🚀 使用方法

### 方法1：双击运行（推荐）
直接双击 `epub_converter_portable.bat` 启动程序，然后按提示输入EPUB文件路径。

### 方法2：拖拽文件
将EPUB文件直接拖拽到 `epub_converter_portable.bat` 上即可开始转换。

### 方法3：命令行
在命令提示符中运行：
```
epub_converter_portable.bat "C:\\path\\to\\your\\book.epub"
```

## 📁 目录结构
```
epub-converter-portable/
├── epub_converter_portable.bat    # 启动脚本
├── epub_converter/                 # 转换器源代码
├── portable_python/                # 便携版Python环境
├── README.txt                      # 本说明文件
└── 其他项目文件...
```

## 💡 功能特性
- ✅ 完整EPUB解析和转换
- ✅ 智能标题页处理
- ✅ 图片提取和链接更新
- ✅ 中文字符完美支持
- ✅ 交互式用户界面
- ✅ 无需安装Python环境

## 📋 输出说明
转换后的Markdown文件将保存在与EPUB文件相同的目录中，包含：
- 章节Markdown文件
- 提取的图片文件
- 封面图片（如果有）

## 🔧 系统要求
- Windows 7 或更高版本
- 约100MB磁盘空间
- 无其他依赖

## 📞 技术支持
如遇问题，请检查：
1. 确保EPUB文件完整且未损坏
2. 确保有足够的磁盘空间
3. 确保对输出目录有写入权限

## 📄 版本信息
- 版本：v1.0.0 便携版
- Python版本：3.11.7 (embedded)
- 依赖包：html2text >= 2020.1.16

---
EPUB转换器开发团队
'''
    
    with open("README_PORTABLE.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✓ 使用说明创建完成")

def main():
    """主函数"""
    print("========================================")
    print("    EPUB转换器便携版创建工具")
    print("========================================")
    print()
    
    # 检查当前目录
    if not Path("epub_converter").exists():
        print("❌ 错误：找不到epub_converter目录")
        print("请在项目根目录中运行此脚本")
        input("按回车键退出...")
        return False
    
    print("此工具将创建一个包含Python环境的便携版EPUB转换器")
    print("便携版大小约100MB，但可以在没有Python的机器上直接运行")
    print()
    
    response = input("是否继续创建便携版？(y/n): ").strip().lower()
    if response not in ['y', 'yes', '是']:
        print("操作已取消")
        return False
    
    print()
    
    # 下载便携版Python
    python_dir = download_portable_python()
    if not python_dir:
        input("按回车键退出...")
        return False
    
    # 配置Python环境
    if not setup_portable_python(python_dir):
        input("按回车键退出...")
        return False
    
    # 安装依赖
    if not install_dependencies(python_dir):
        input("按回车键退出...")
        return False
    
    # 创建启动脚本
    create_portable_launcher()
    
    # 创建说明文件
    create_readme()
    
    print()
    print("========================================")
    print("✓ 便携版创建完成！")
    print("========================================")
    print()
    print("生成的文件：")
    print("1. epub_converter_portable.bat - 便携版启动脚本")
    print("2. portable_python/ - 便携版Python环境")
    print("3. README_PORTABLE.txt - 使用说明")
    print()
    print("📦 分发说明：")
    print("将整个项目文件夹打包发给别人，对方只需要：")
    print("1. 解压到任意目录")
    print("2. 双击 epub_converter_portable.bat")
    print("3. 按提示使用即可")
    print()
    print("💡 提示：便携版包含完整Python环境，无需目标机器安装Python")
    
    return True

if __name__ == "__main__":
    success = main()
    input("\n按回车键退出...")
    if not success:
        sys.exit(1)