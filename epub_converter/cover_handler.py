"""
封面处理器
Cover image handling functionality
"""

from pathlib import Path
from typing import Optional
import os

from .epub_parser import EPUBParser
from .utils import sanitize_filename, CoverImageInfo, create_safe_directory


class CoverHandler:
    """封面处理器类"""
    
    def __init__(self, epub_parser: EPUBParser, book_title: str):
        """
        初始化封面处理器
        
        Args:
            epub_parser: EPUB解析器实例
            book_title: 书籍标题
        """
        self.epub_parser = epub_parser
        self.book_title = sanitize_filename(book_title)
        self._saved_cover_path = None
        self._cover_image_info = None
    
    def extract_and_save_cover(self, output_dir: str) -> Optional[str]:
        """
        提取并保存封面图片
        
        Args:
            output_dir: 输出目录路径
            
        Returns:
            Optional[str]: 保存的封面图片路径，如果没有封面则返回None
        """
        # 如果已经保存过，直接返回路径
        if self._saved_cover_path:
            return self._saved_cover_path
        
        # 获取封面图片信息
        cover_info = self.epub_parser.get_cover_image_info()
        
        if not cover_info:
            return None
        
        # 记录封面图片信息
        self._cover_image_info = cover_info
        
        # 生成封面文件名
        cover_filename = self.generate_cover_filename(cover_info.file_extension)
        cover_path = Path(output_dir) / cover_filename
        
        try:
            # 确保输出目录存在（使用安全的目录创建方法）
            create_safe_directory(output_dir)
            
            # 保存封面图片
            with open(cover_path, 'wb') as f:
                f.write(cover_info.image_data)
            
            print(f"封面图片已保存: {cover_path}")
            self._saved_cover_path = str(cover_path)
            return self._saved_cover_path
            
        except Exception as e:
            print(f"警告：无法保存封面图片: {e}")
            return None
    
    def get_cover_image_path(self) -> Optional[str]:
        """
        获取封面图片在EPUB中的原始路径
        
        Returns:
            Optional[str]: 封面图片的原始路径
        """
        if not self._cover_image_info:
            cover_info = self.epub_parser.get_cover_image_info()
            if cover_info:
                self._cover_image_info = cover_info
        
        return self._cover_image_info.image_path if self._cover_image_info else None
    
    def generate_cover_filename(self, original_extension: str) -> str:
        """
        生成封面文件名，格式为"00_书名_cover.扩展名"
        
        Args:
            original_extension: 原始文件扩展名
            
        Returns:
            str: 生成的封面文件名
        """
        # 确保扩展名以点开头
        if not original_extension.startswith('.'):
            original_extension = '.' + original_extension
        
        # 清理书名，确保符合文件名规范
        clean_title = sanitize_filename(self.book_title)
        
        # 生成文件名：00_书名_cover.扩展名
        filename = f"00_{clean_title}_cover{original_extension}"
        
        return filename
    
    def should_skip_cover_markdown(self, file_path: str) -> bool:
        """
        判断是否应该跳过为封面页生成Markdown文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 如果是封面页则返回True，应该跳过生成Markdown
        """
        return self.epub_parser.is_cover_page(file_path)