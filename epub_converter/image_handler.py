"""
图片提取和链接处理
Image extraction and link processing
"""

import re
import zipfile
from pathlib import Path
from typing import Dict
from urllib.parse import unquote

from .epub_parser import EPUBParser
from .utils import normalize_path, ensure_unicode_path, sanitize_filename


class ImageHandler:
    """图片处理器"""
    
    def __init__(self, epub_parser: EPUBParser, output_dir: str, cover_handler=None, annotation_processor=None):
        """
        初始化图片处理器
        
        Args:
            epub_parser: EPUB解析器实例
            output_dir: 输出目录
            cover_handler: 封面处理器实例（可选）
            annotation_processor: 注释处理器实例（可选）
        """
        self.epub_parser = epub_parser
        # 确保输出目录Unicode兼容
        self.output_dir = normalize_path(ensure_unicode_path(output_dir))
        self.cover_handler = cover_handler
        self.annotation_processor = annotation_processor
        self._image_mapping = None
        self.images_subdir = "images"  # 图片子文件夹名称
    
    def extract_all_images(self) -> Dict[str, str]:
        """
        提取所有图片文件（除了封面图片）
        
        Returns:
            Dict[str, str]: 原始路径到新路径的映射
        """
        if self._image_mapping is None:
            self._image_mapping = self._extract_images_excluding_cover()
        
        return self._image_mapping
    
    def _extract_images_excluding_cover(self) -> Dict[str, str]:
        """
        提取图片文件，但排除封面图片和注释载体图片
        
        Returns:
            Dict[str, str]: 原始路径到新路径的映射
        """
        if not self.epub_parser.zip_file:
            self.epub_parser.zip_file = zipfile.ZipFile(self.epub_parser.epub_path, 'r')
        
        # 获取封面图片路径（如果有的话）
        cover_image_path = None
        if self.cover_handler:
            cover_image_path = self.cover_handler.get_cover_image_path()
        
        # 获取注释载体图片路径列表
        carrier_image_paths = set()
        if self.annotation_processor:
            carrier_image_paths = self.annotation_processor.get_carrier_image_paths()
        
        image_mapping = {}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
        
        # 创建图片子文件夹
        images_dir = Path(self.output_dir) / self.images_subdir
        images_dir.mkdir(exist_ok=True)
        
        # 用于跟踪已保存的文件，避免重复保存
        saved_files = set()
        
        for file_path in self.epub_parser.zip_file.namelist():
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in image_extensions:
                # 跳过封面图片
                if cover_image_path and file_path == cover_image_path:
                    continue
                
                # 跳过注释载体图片（基于注释处理器识别）
                normalized_file_path = self._normalize_image_path_for_comparison(file_path)
                is_carrier_image = False
                
                for carrier_path in carrier_image_paths:
                    normalized_carrier_path = self._normalize_image_path_for_comparison(carrier_path)
                    if normalized_file_path == normalized_carrier_path:
                        is_carrier_image = True
                        break
                
                if is_carrier_image:
                    continue
                
                try:
                    # 读取图片数据
                    image_data = self.epub_parser.zip_file.read(file_path)
                    
                    # 生成输出文件名
                    filename = Path(file_path).name
                    filename = sanitize_filename(filename)
                    
                    # 避免重复保存相同的文件
                    if filename in saved_files:
                        continue
                    
                    output_path = images_dir / filename
                    
                    # 确保文件名唯一（只有在文件确实存在时才重命名）
                    counter = 1
                    original_stem = output_path.stem
                    while output_path.exists():
                        output_path = output_path.parent / f"{original_stem}_{counter}{output_path.suffix}"
                        counter += 1
                    
                    # 使用安全的文件写入方法
                    try:
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        
                        # 记录已保存的文件
                        saved_files.add(filename)
                        image_mapping[file_path] = str(output_path)
                        
                    except Exception as write_error:
                        print(f"警告：无法保存图片 {output_path}: {write_error}")
                        continue
                    
                except Exception as e:
                    print(f"警告：无法提取图片 {file_path}: {e}")
        
        return image_mapping
    
    def _normalize_image_path_for_comparison(self, path: str) -> str:
        """
        标准化图片路径用于比较
        
        Args:
            path: 原始路径
            
        Returns:
            str: 标准化后的路径
        """
        if not path:
            return ""
        
        # 移除URL编码
        decoded_path = unquote(path)
        
        # 标准化路径分隔符
        normalized = decoded_path.replace('\\', '/')
        
        # 移除开头的相对路径标记
        if normalized.startswith('../'):
            normalized = normalized[3:]
        if normalized.startswith('./'):
            normalized = normalized[2:]
        
        return normalized
        
        return image_mapping
    
    def update_image_links(self, markdown_content: str) -> str:
        """
        更新Markdown中的图片链接
        
        Args:
            markdown_content: 原始Markdown内容
            
        Returns:
            str: 更新后的Markdown内容
        """
        image_mapping = self.extract_all_images()
        
        if not image_mapping:
            return markdown_content
        
        # 匹配Markdown图片语法: ![alt](src)
        def replace_image_link(match):
            alt_text = match.group(1)
            original_src = match.group(2)
            
            # 解码URL编码并确保Unicode兼容
            decoded_src = ensure_unicode_path(unquote(original_src))
            
            # 查找匹配的图片路径
            new_path = self._find_matching_image_path(decoded_src, image_mapping)
            
            if new_path:
                # 生成相对路径（图片现在在子文件夹中）
                relative_path = Path(new_path).relative_to(self.output_dir)
                return f"![{alt_text}]({relative_path})"
            else:
                # 如果找不到匹配的图片，保持原样
                return match.group(0)
        
        # 替换图片链接
        updated_content = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            replace_image_link,
            markdown_content
        )
        
        return updated_content
    
    def _find_matching_image_path(self, src_path: str, image_mapping: Dict[str, str]) -> str:
        """
        查找匹配的图片路径
        
        Args:
            src_path: 源图片路径
            image_mapping: 图片路径映射
            
        Returns:
            str: 匹配的新路径，如果没找到则返回空字符串
        """
        # 标准化路径
        normalized_src = normalize_path(src_path)
        
        # 直接匹配
        if normalized_src in image_mapping:
            return image_mapping[normalized_src]
        
        # 尝试匹配文件名
        src_filename = Path(normalized_src).name
        
        for original_path, new_path in image_mapping.items():
            if Path(original_path).name == src_filename:
                return new_path
        
        # 尝试部分路径匹配
        for original_path, new_path in image_mapping.items():
            if normalized_src.endswith(Path(original_path).name):
                return new_path
            
            # 反向匹配
            if original_path.endswith(Path(normalized_src).name):
                return new_path
        
        return ""