#!/usr/bin/env python3
"""
MD文件合并器主入口
Main entry point for Markdown file merger

将目录中的多个Markdown文件合并为一个完整的文件
"""

import sys
import os
import argparse
from pathlib import Path


def get_md_files(directory: str) -> list:
    """
    在指定目录中查找所有MD文件

    Args:
        directory: 目录路径

    Returns:
        list: MD文件路径列表（按文件名排序）
    """
    dir_path = Path(directory)

    if not dir_path.is_dir():
        raise ValueError(f"不是有效的目录: {directory}")

    # 查找所有.md文件（不包括子目录）
    md_files = sorted(dir_path.glob("*.md"), key=lambda x: x.name)

    # 过滤掉已经存在的合并文件（避免重复合并）
    filtered_files = [f for f in md_files if f.name != f"{dir_path.name}.md"]

    return [str(f) for f in filtered_files]


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Markdown文件合并器 - 将目录中的多个MD文件合并为一个完整的文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m md_merger                    # 交互式模式
  python -m md_merger /path/to/folder   # 合并指定目录中的所有MD文件
        """
    )

    parser.add_argument(
        'directory',
        nargs='?',
        help='包含MD文件的目录路径'
    )

    parser.add_argument(
        '-o', '--output',
        help='输出文件名（不含扩展名，默认为目录名）'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='MD文件合并器 v1.0.0'
    )

    return parser.parse_args()


def get_directory_interactive() -> str:
    """交互式获取目录路径"""
    print("Markdown 文件合并工具")
    print("=" * 30)
    print()

    while True:
        directory = input("请输入包含MD文件的目录路径（或拖拽到此处）: ").strip()

        # 处理拖拽文件时可能包含的引号
        if directory.startswith('"') and directory.endswith('"'):
            directory = directory[1:-1]
        elif directory.startswith("'") and directory.endswith("'"):
            directory = directory[1:-1]

        if not directory:
            print("错误：请提供目录路径")
            continue

        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"错误：目录不存在: {directory}")
            continue

        if not dir_path.is_dir():
            print(f"错误：不是有效的目录: {directory}")
            continue

        # 检查目录中是否有MD文件
        md_files = list(dir_path.glob("*.md"))
        if not md_files:
            print(f"错误：目录中没有找到MD文件: {directory}")
            continue

        return str(dir_path)


def merge_markdown_files(directory: str, output_name: str = None):
    """
    合并目录中的所有MD文件

    Args:
        directory: 目录路径
        output_name: 输出文件名（不含扩展名，默认为目录名）
    """
    dir_path = Path(directory)

    # 获取所有MD文件
    print(f"\n正在扫描目录: {dir_path.name}")
    md_files = get_md_files(directory)

    if not md_files:
        print("错误：目录中没有找到可合并的MD文件")
        sys.exit(1)

    print(f"找到 {len(md_files)} 个MD文件:")
    for md_file in md_files:
        print(f"  - {Path(md_file).name}")

    # 确定输出文件名
    if output_name is None:
        output_name = dir_path.name

    # 检查输出文件是否已存在
    output_file = dir_path / f"{output_name}.md"
    if output_file.exists():
        response = input(f"\n警告：文件 {output_file.name} 已存在，是否覆盖？(y/n): ").strip().lower()
        if response not in ['y', 'yes', '是', '确认']:
            print("操作已取消")
            sys.exit(0)

    # 导入核心模块
    from .core import MergedOutputGenerator

    # 创建合并器
    merger = MergedOutputGenerator(
        md_files=md_files,
        output_dir=str(dir_path),
        output_name=output_name
    )

    # 生成合并文件
    try:
        merged_file = merger.generate_merged_output()
        print(f"\n[OK] 合并完成！")
        print(f"输出文件: {merged_file}")
        print(f"共合并 {len(md_files)} 个文件")
    except Exception as e:
        print(f"\n[ERROR] 合并失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """主程序入口点"""
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 获取目录路径
        if args.directory:
            # 命令行模式
            directory = args.directory
            dir_path = Path(directory)

            if not dir_path.exists():
                print(f"错误：目录不存在: {directory}")
                sys.exit(1)

            if not dir_path.is_dir():
                print(f"错误：不是有效的目录: {directory}")
                sys.exit(1)
        else:
            # 交互式模式
            directory = get_directory_interactive()

        # 开始合并
        merge_markdown_files(directory, args.output)

    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n合并过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
