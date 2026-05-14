#!/usr/bin/env python3
"""
主入口点和CLI界面
Main entry point and CLI interface for EPUB to Markdown converter
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Optional

from .epub_parser import EPUBParser
from .content_processor import ContentProcessor
from .cover_handler import CoverHandler
from .image_handler import ImageHandler
from .annotation_processor import AnnotationProcessor
from .language_detector import LanguageDetector
from .file_manager import FileManager
from .link_processor import LinkProcessor
from .utils import ConversionResult, is_valid_epub_file, normalize_path, ensure_unicode_path, create_safe_directory, safe_file_write


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="EPUB到Markdown转换器 - 将EPUB电子书转换为Markdown格式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python -m epub_converter                    # 交互式模式
  python -m epub_converter book.epub         # 直接转换指定文件
  python -m epub_converter /path/to/folder   # 批量转换文件夹中的所有EPUB
  python -m epub_converter -o /path book.epub # 指定输出目录
        """
    )
    
    parser.add_argument(
        'epub_file',
        nargs='?',
        help='要转换的EPUB文件路径或包含EPUB文件的文件夹路径'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='输出目录路径（默认为EPUB文件同目录下的同名文件夹）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细处理信息'
    )

    parser.add_argument(
        '-a', '--annotation-mode',
        choices=['inline', 'jump'],
        help='注释处理模式: inline=内联注释, jump=页内跳转 (不指定则交互式选择)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='EPUB转换器 v1.0.0'
    )

    return parser.parse_args()


def get_epub_path_interactive() -> str:
    """交互式获取EPUB文件或文件夹路径"""
    print("EPUB到Markdown转换器")
    print("=" * 30)
    print("支持单个文件或批量处理：")
    print("- 输入EPUB文件路径：转换单个文件")
    print("- 输入文件夹路径：批量转换文件夹中的所有EPUB文件")
    print()
    
    while True:
        epub_path = input("请输入EPUB文件或文件夹路径（或拖拽到此处）: ").strip()
        
        # 处理拖拽文件时可能包含的引号
        if epub_path.startswith('"') and epub_path.endswith('"'):
            epub_path = epub_path[1:-1]
        elif epub_path.startswith("'") and epub_path.endswith("'"):
            epub_path = epub_path[1:-1]
        
        # 确保Unicode兼容性
        epub_path = ensure_unicode_path(epub_path)
        
        # 标准化路径
        epub_path = normalize_path(epub_path)
        
        if not epub_path:
            print("错误：请提供EPUB文件或文件夹路径")
            continue
        
        # 验证路径
        validation_result = validate_epub_path(epub_path)
        if validation_result is True:
            return epub_path
        else:
            print(f"错误：{validation_result}")
            print("请重新输入正确的EPUB文件或文件夹路径。")
            print()


def validate_epub_path(epub_path: str) -> str | bool:
    """
    验证EPUB文件或文件夹路径
    
    Args:
        epub_path: EPUB文件或文件夹路径
        
    Returns:
        bool | str: True表示验证通过，字符串表示错误信息
    """
    if not epub_path:
        return "请提供EPUB文件或文件夹路径"
    
    # 确保Unicode兼容性
    epub_path = ensure_unicode_path(epub_path)
    epub_path = normalize_path(epub_path)
    
    if not os.path.exists(epub_path):
        return f"路径不存在: {epub_path}"
    
    if os.path.isfile(epub_path):
        # 单个文件验证
        return validate_epub_file(epub_path)
    elif os.path.isdir(epub_path):
        # 文件夹验证：检查是否包含EPUB文件
        epub_files = find_epub_files(epub_path)
        if not epub_files:
            return f"文件夹中没有找到EPUB文件: {epub_path}"
        return True
    else:
        return f"路径既不是文件也不是文件夹: {epub_path}"


def find_epub_files(directory: str) -> list[str]:
    """
    在指定目录中查找所有EPUB文件
    
    Args:
        directory: 目录路径
        
    Returns:
        list[str]: EPUB文件路径列表
    """
    epub_files = []
    directory = Path(directory)
    
    # 递归查找所有.epub文件
    for epub_file in directory.rglob("*.epub"):
        if epub_file.is_file() and is_valid_epub_file(str(epub_file)):
            epub_files.append(str(epub_file))
    
    return sorted(epub_files)  # 排序以确保处理顺序一致


def validate_epub_file(epub_path: str) -> str | bool:
    """
    验证EPUB文件
    
    Args:
        epub_path: EPUB文件路径
        
    Returns:
        bool | str: True表示验证通过，字符串表示错误信息
    """
    if not epub_path:
        return "请提供EPUB文件路径"
    
    # 确保Unicode兼容性
    epub_path = ensure_unicode_path(epub_path)
    epub_path = normalize_path(epub_path)
    
    if not os.path.exists(epub_path):
        return f"文件不存在: {epub_path}"
    
    if not os.path.isfile(epub_path):
        return f"路径不是文件: {epub_path}"
    
    if not epub_path.lower().endswith('.epub'):
        return "文件扩展名不正确，请提供.epub文件"
    
    if not is_valid_epub_file(epub_path):
        return "文件不是有效的EPUB格式"
    
    return True


def print_progress(message: str, verbose: bool = False):
    """打印进度信息"""
    if verbose:
        print(f"[进度] {message}")


def batch_convert_epub_files(epub_files: list[str], output_base_dir: str = None, verbose: bool = False) -> dict:
    """
    批量转换EPUB文件
    
    Args:
        epub_files: EPUB文件路径列表
        output_base_dir: 输出基础目录（可选）
        verbose: 是否显示详细信息
        
    Returns:
        dict: 批处理结果统计
    """
    total_files = len(epub_files)
    successful_conversions = []
    failed_conversions = []
    
    print(f"\n开始批量转换 {total_files} 个EPUB文件...")
    print("=" * 50)
    
    for i, epub_file in enumerate(epub_files, 1):
        print(f"\n[{i}/{total_files}] 处理: {Path(epub_file).name}")
        
        try:
            # 确定输出目录
            if output_base_dir:
                epub_name = Path(epub_file).stem
                output_dir = Path(output_base_dir) / epub_name
            else:
                epub_path = Path(epub_file)
                output_dir = epub_path.parent / epub_path.stem
            
            # 转换文件
            result = convert_epub_to_markdown(epub_file, str(output_dir), verbose)
            successful_conversions.append({
                'file': epub_file,
                'output': result.output_directory,
                'converted_files': len(result.converted_files),
                'processing_time': result.processing_time
            })
            
            print(f"✓ 转换成功: {len(result.converted_files)} 个文件, {result.processing_time:.2f}秒")
            
        except Exception as e:
            failed_conversions.append({
                'file': epub_file,
                'error': str(e)
            })
            print(f"✗ 转换失败: {str(e)}")
    
    # 显示批处理结果
    print("\n" + "=" * 50)
    print("批处理完成！")
    print(f"成功转换: {len(successful_conversions)} 个文件")
    print(f"转换失败: {len(failed_conversions)} 个文件")
    
    if failed_conversions:
        print("\n失败的文件:")
        for failed in failed_conversions:
            print(f"  - {Path(failed['file']).name}: {failed['error']}")
    
    total_converted_files = sum(conv['converted_files'] for conv in successful_conversions)
    total_time = sum(conv['processing_time'] for conv in successful_conversions)
    
    if successful_conversions:
        print(f"\n总计转换了 {total_converted_files} 个Markdown文件")
        print(f"总处理时间: {total_time:.2f}秒")
        print(f"平均每个EPUB: {total_time/len(successful_conversions):.2f}秒")
    
    return {
        'total': total_files,
        'successful': len(successful_conversions),
        'failed': len(failed_conversions),
        'successful_conversions': successful_conversions,
        'failed_conversions': failed_conversions
    }


def main():
    """主程序入口点"""
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 获取EPUB文件或文件夹路径
        if args.epub_file:
            # 命令行模式
            epub_path = ensure_unicode_path(args.epub_file)
            epub_path = normalize_path(epub_path)
            validation_result = validate_epub_path(epub_path)
            if validation_result is not True:
                print(f"错误：{validation_result}")
                sys.exit(1)
        else:
            # 交互式模式
            epub_path = get_epub_path_interactive()
        
        # 判断是单个文件还是文件夹
        if os.path.isfile(epub_path):
            # 单个文件处理
            # 确定输出目录
            if args.output:
                output_dir = ensure_unicode_path(args.output)
                output_dir = normalize_path(output_dir)
                output_dir = Path(output_dir)
            else:
                epub_file = Path(epub_path)
                output_dir = epub_file.parent / epub_file.stem
            
            print(f"\n开始处理: {epub_path}")
            if args.verbose:
                print(f"输出目录: {output_dir}")
            
            # 开始转换过程
            annotation_mode = args.annotation_mode if hasattr(args, 'annotation_mode') else None
            result = convert_epub_to_markdown(epub_path, str(output_dir), args.verbose, annotation_mode)
            
            # 显示成功消息
            print(f"\n[OK] 转换完成！")
            print(f"输出目录: {result.output_directory}")
            print(f"转换文件数: {len(result.converted_files)}")
            if result.extracted_images:
                print(f"提取图片数: {len(result.extracted_images)}")
            if result.cover_image_path:
                print(f"封面图片: {Path(result.cover_image_path).name}")
            print(f"检测语言: {result.language_detected}")
            print(f"处理时间: {result.processing_time:.2f}秒")
            
            print(f"\n转换成功！您可以在以下目录查看结果：")
            print(f"{result.output_directory}")
            
        elif os.path.isdir(epub_path):
            # 批量处理
            epub_files = find_epub_files(epub_path)
            
            if not epub_files:
                print(f"错误：在文件夹 {epub_path} 中没有找到EPUB文件")
                sys.exit(1)
            
            print(f"\n在文件夹中找到 {len(epub_files)} 个EPUB文件:")
            for epub_file in epub_files:
                print(f"  - {Path(epub_file).name}")
            
            # 确认是否继续
            if not args.epub_file:  # 只在交互模式下询问确认
                response = input(f"\n是否继续批量转换这 {len(epub_files)} 个文件？(y/n): ").strip().lower()
                if response not in ['y', 'yes', '是', '确认']:
                    print("用户取消操作")
                    sys.exit(0)
            
            # 确定输出基础目录
            output_base_dir = None
            if args.output:
                output_base_dir = ensure_unicode_path(args.output)
                output_base_dir = normalize_path(output_base_dir)
            
            # 开始批量转换
            batch_result = batch_convert_epub_files(epub_files, output_base_dir, args.verbose)

            # 根据结果设置退出码
            if batch_result['failed'] > 0:
                sys.exit(1)  # 有失败的转换
        
    except KeyboardInterrupt:
        print("\n\n用户取消操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n转换过程中发生错误: {str(e)}")
        if args.verbose if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def convert_epub_to_markdown(epub_path: str, output_dir: str = None, verbose: bool = False, annotation_mode: str = None) -> ConversionResult:
    """
    将EPUB文件转换为Markdown格式
    使用四阶段处理流程：预处理→注释处理→链接修正→格式转换

    Args:
        epub_path: EPUB文件路径
        output_dir: 输出目录路径（可选）
        verbose: 是否显示详细信息
        annotation_mode: 注释处理模式 ('inline', 'jump', None=交互式选择)

    Returns:
        ConversionResult: 转换结果信息
    """
    import time
    import tempfile
    import shutil
    start_time = time.time()
    
    try:
        # 创建输出目录
        if output_dir is None:
            epub_file = Path(epub_path)
            output_dir = epub_file.parent / epub_file.stem
        
        # 使用安全的目录创建方法
        output_path_str = create_safe_directory(str(output_dir))
        output_path = Path(output_path_str)
        print_progress("创建输出目录", verbose)
        
        # 初始化解析器
        print_progress("初始化EPUB解析器", verbose)
        with EPUBParser(epub_path) as parser:
            
            # 提取元数据和内容文件
            print_progress("提取EPUB元数据", verbose)
            metadata = parser.extract_metadata()
            
            print_progress("获取内容文件列表", verbose)
            content_files = parser.get_content_files()
            
            if not content_files:
                raise ValueError("EPUB文件中没有找到可转换的内容文件")
            
            print_progress(f"找到 {len(content_files)} 个内容文件", verbose)
            
            # 检测语言
            print_progress("检测内容语言", verbose)
            detector = LanguageDetector()
            sample_content = content_files[0].content if content_files else ""
            language = detector.detect_language(metadata, sample_content)
            print_progress(f"检测到语言: {language}", verbose)
            
            # 处理封面
            print_progress("处理封面图片", verbose)
            book_title = metadata.get('title', 'Unknown')
            cover_handler = CoverHandler(parser, book_title)
            cover_image_path = cover_handler.extract_and_save_cover(str(output_path))
            
            if cover_image_path:
                print_progress(f"封面已保存: {Path(cover_image_path).name}", verbose)
            
            # 确定注释处理模式
            print_progress("确定注释处理模式", verbose)

            # 检测是否在测试环境中（通过检查是否有pytest在运行）
            import sys
            is_testing = 'pytest' in sys.modules or 'unittest' in sys.modules

            content_processor = ContentProcessor(language)

            # 如果通过命令行指定了模式，则直接使用；否则交互式询问
            if annotation_mode:
                # 命令行指定了模式
                use_inline_mode = (annotation_mode == 'inline')
                print_progress(f"使用命令行指定的注释处理模式: {'内联模式' if use_inline_mode else '页内跳转模式'}", verbose)
            else:
                # 未指定，交互式询问（除非在测试环境）
                use_inline_mode = content_processor.ask_annotation_mode_preference(interactive=not is_testing)

            print_progress(f"注释处理模式: {'内联模式' if use_inline_mode else '页内跳转模式'}", verbose)

            # ========== 阶段1：预处理阶段 (FileManager) ==========
            print_progress("阶段1：文件预处理 - 创建文件名映射", verbose)
            file_manager = FileManager(content_files)
            filename_mapping = file_manager.create_filename_mapping()
            print_progress(f"创建了 {len(filename_mapping)} 个文件名映射", verbose)

            # 创建临时目录用于文件重命名
            with tempfile.TemporaryDirectory() as temp_dir:
                print_progress("创建临时目录进行文件预处理", verbose)

                # 将内容文件写入临时目录
                temp_path = Path(temp_dir)
                for content_file in content_files:
                    file_path = temp_path / content_file.path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content_file.content)

                # 重命名HTML文件
                print_progress("重命名HTML文件", verbose)
                actual_mappings = file_manager.rename_html_files(temp_dir)
                print_progress(f"成功重命名 {len(actual_mappings)} 个文件", verbose)

                # 更新content_files中的路径和内容
                for content_file in content_files:
                    if content_file.path in actual_mappings:
                        new_path = actual_mappings[content_file.path]
                        # 读取重命名后的文件内容
                        renamed_file_path = temp_path / new_path
                        if renamed_file_path.exists():
                            with open(renamed_file_path, 'r', encoding='utf-8') as f:
                                content_file.content = f.read()
                            content_file.path = new_path

                # ========== 阶段2：注释处理阶段 (AnnotationProcessor) ==========
                print_progress("阶段2：注释处理", verbose)

                # 创建注释处理器的内容映射
                content_map = {cf.path: cf.content for cf in content_files}
                annotation_processor = AnnotationProcessor(language, content_map)

                # 设置注释处理模式
                annotation_processor.set_processing_mode(use_inline_mode)

                # 全局处理所有注释
                print_progress("全局处理注释链接", verbose)
                annotation_processor.process_all_annotations_globally()

                # 更新content_files中的内容（注释已被处理）
                for cf in content_files:
                    if cf.path in annotation_processor.content_files:
                        cf.content = annotation_processor.content_files[cf.path]
                        # 同时更新临时目录中的文件
                        temp_file_path = temp_path / cf.path
                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            f.write(cf.content)

                # ========== 阶段3：链接修正阶段 (LinkProcessor) ==========
                print_progress("阶段3：链接修正", verbose)

                # 创建HTML临时名映射（用于阶段3）
                html_temp_mapping = {k: v.replace('.md', '.html') for k, v in filename_mapping.items()}
                link_processor = LinkProcessor(html_temp_mapping)

                # 修正所有HTML内容中的文件引用（使用HTML临时名）
                for content_file in content_files:
                    print_progress(f"修正文件引用: {content_file.path}", verbose)
                    updated_content = link_processor.update_file_references(
                        content_file.content,
                        content_file.path
                    )
                    content_file.content = updated_content

                    # 更新临时目录中的文件
                    temp_file_path = temp_path / content_file.path
                    with open(temp_file_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)

                print_progress("链接修正完成", verbose)
                
                # ========== 阶段4：格式转换阶段 (ContentProcessor) ==========
                print_progress("阶段4：格式转换 - HTML到Markdown", verbose)
                
                # 处理图片（传入注释处理器以排除载体图片）
                print_progress("提取图片文件", verbose)
                image_handler = ImageHandler(parser, str(output_path), cover_handler, annotation_processor)
                extracted_images = image_handler.extract_all_images()
                
                if extracted_images:
                    print_progress(f"提取了 {len(extracted_images)} 个图片文件", verbose)
                
                # 使用内容处理器处理所有文件（包括标题页合并和HTML到Markdown转换）
                print_progress("开始转换内容文件", verbose)
                markdown_files = content_processor.process_content_files(
                    content_files,
                    annotation_processor,
                    interactive=not is_testing,
                    md_filename_mapping=filename_mapping,  # 传入完整映射
                    output_mode='multi'  # 默认多文件模式
                )

                converted_files = []
                skipped_cover_files = 0

                for markdown_file in markdown_files:
                    print_progress(f"保存文件: {markdown_file.filename}", verbose)

                    try:
                        # 更新图片链接
                        markdown_content = image_handler.update_image_links(markdown_file.content)

                        # 一次性完成HTML文件名到MD文件名的替换，并判断同页跳转
                        markdown_content = link_processor.convert_html_to_md_links(
                            markdown_content,
                            filename_mapping,  # 传入完整映射
                            current_filename=markdown_file.filename  # 传入当前文件名
                        )

                        # 保存文件
                        output_file = output_path / markdown_file.filename

                        # 使用安全的文件写入方法
                        safe_file_write(str(output_file), markdown_content)

                        converted_files.append(str(output_file))
                        print_progress(f"已保存: {output_file.name}", verbose)

                    except Exception as e:
                        print(f"警告：处理文件 '{markdown_file.title}' 时出错: {str(e)}")
                        if verbose:
                            import traceback
                            traceback.print_exc()
                        continue
                
                # 计算跳过的封面文件数
                total_content_files = len([cf for cf in content_files if not cf.is_cover])
                skipped_cover_files = len(content_files) - total_content_files
                
                if skipped_cover_files > 0:
                    print_progress(f"跳过了 {skipped_cover_files} 个封面页文件", verbose)

                processing_time = time.time() - start_time

                print_progress("转换完成", verbose)

                # ========== 生成完整合并版MD文件（独立模块）==========
                try:
                    from .merged_output_generator import MergedOutputGenerator

                    # 获取EPUB文件名
                    epub_name = Path(epub_path).stem

                    # 创建合并文件生成器
                    merged_generator = MergedOutputGenerator(
                        md_files=converted_files,
                        output_dir=str(output_path),
                        epub_name=epub_name
                    )

                    # 生成合并文件
                    merged_file_path = merged_generator.generate_merged_output()

                    # 将合并文件也添加到结果中
                    converted_files.append(merged_file_path)

                except Exception as e:
                    # 如果生成合并文件失败，不影响主流程
                    if verbose:
                        print(f"警告：生成完整合并版时出错: {str(e)}")
                        import traceback
                        traceback.print_exc()

                return ConversionResult(
                    output_directory=str(output_path),
                    converted_files=converted_files,
                    extracted_images=list(extracted_images.values()) if extracted_images else [],
                    cover_image_path=cover_image_path,
                    language_detected=language,
                    annotation_mode_used="内联注释模式" if use_inline_mode else "页内跳转模式",
                    processing_time=processing_time,
                    filename_mappings=file_manager.get_filename_mappings()
                )
            
    except Exception as e:
        # 提供更详细的错误信息
        error_msg = f"转换过程中发生错误: {str(e)}"
        
        if "zipfile.BadZipFile" in str(type(e)):
            error_msg = "EPUB文件损坏或格式不正确"
        elif "FileNotFoundError" in str(type(e)):
            error_msg = f"找不到文件: {str(e)}"
        elif "PermissionError" in str(type(e)):
            error_msg = f"权限错误，无法访问文件: {str(e)}"
        elif "UnicodeDecodeError" in str(type(e)):
            error_msg = "文件编码错误，无法正确读取内容"
        
        raise RuntimeError(error_msg) from e


if __name__ == "__main__":
    main()