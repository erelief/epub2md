"""
文件管理器 - 处理文件重命名和预处理管理
File Manager - Handles file renaming and preprocessing management
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List
import re

from .utils import ContentFile, FilenameMapping, sanitize_filename, normalize_path, ensure_unicode_path


class FileManager:
    """
    文件管理器类
    负责根据Markdown命名规则重命名HTML文件，创建文件名映射表，生成Markdown文件名
    """
    
    def __init__(self, content_files: List[ContentFile]):
        """
        初始化文件管理器
        
        Args:
            content_files: 内容文件列表
        """
        self.content_files = content_files
        self.filename_mappings: List[FilenameMapping] = []
        self._mapping_dict: Dict[str, str] = {}
    
    def create_filename_mapping(self) -> Dict[str, str]:
        """
        创建文件名映射表（原始HTML名 → 最终MD名）
        这是唯一的改名映射源

        Returns:
            Dict[str, str]: 原始HTML文件名到最终MD文件名的映射字典
        """
        self.filename_mappings.clear()
        self._mapping_dict.clear()

        for content_file in self.content_files:
            # 直接生成最终MD文件名
            md_filename = self.generate_markdown_filename(content_file)

            # 生成HTML临时名（用于阶段1-3）
            html_temp_filename = md_filename.replace('.md', '.html')

            # 创建映射对象
            mapping = FilenameMapping(
                original_name=content_file.path,
                new_name=html_temp_filename,  # HTML阶段临时名
                markdown_name=md_filename  # 最终MD名
            )

            self.filename_mappings.append(mapping)
            self._mapping_dict[content_file.path] = md_filename

        return self._mapping_dict.copy()
    
    def generate_markdown_filename(self, content_file: ContentFile) -> str:
        """
        生成Markdown文件名
        根据ContentFile的顺序和标题生成符合规范的Markdown文件名
        
        Args:
            content_file: 内容文件对象
            
        Returns:
            str: 生成的Markdown文件名
        """
        # 格式：序号_标题.md
        # 序号使用两位数字，不足补零
        order_str = f"{content_file.order:02d}"
        
        # 清理标题，确保符合文件名规范
        clean_title = sanitize_filename(content_file.title)
        
        # 如果标题为空或只包含无效字符，使用默认名称
        if not clean_title or clean_title.strip('_') == '' or clean_title == 'untitled':
            clean_title = f"chapter_{content_file.order}"
        
        # 构建文件名
        filename = f"{order_str}_{clean_title}.md"
        
        return filename
    
    def _generate_html_filename(self, content_file: ContentFile) -> str:
        """
        生成HTML文件名（用于预处理阶段的重命名）
        基于Markdown命名规则但保持.html扩展名
        
        Args:
            content_file: 内容文件对象
            
        Returns:
            str: 生成的HTML文件名
        """
        # 格式：序号_标题.html
        order_str = f"{content_file.order:02d}"
        
        # 清理标题
        clean_title = sanitize_filename(content_file.title)
        
        # 如果标题为空，使用默认名称
        if not clean_title or clean_title.strip('_') == '' or clean_title == 'untitled':
            clean_title = f"chapter_{content_file.order}"
        
        # 构建文件名
        filename = f"{order_str}_{clean_title}.html"
        
        return filename
    
    def rename_html_files(self, temp_dir: str) -> Dict[str, str]:
        """
        在临时目录中重命名HTML文件
        根据映射表重命名所有HTML文件，为后续处理做准备
        
        Args:
            temp_dir: 临时目录路径
            
        Returns:
            Dict[str, str]: 实际执行的重命名映射（原路径 -> 新路径）
        """
        # 确保映射表已创建
        if not self.filename_mappings:
            self.create_filename_mapping()
        
        # 标准化临时目录路径
        temp_dir = normalize_path(ensure_unicode_path(temp_dir))
        temp_path = Path(temp_dir)
        
        # 确保临时目录存在
        temp_path.mkdir(parents=True, exist_ok=True)
        
        actual_mappings = {}
        
        for mapping in self.filename_mappings:
            # 构建原文件路径和新文件路径
            original_path = temp_path / mapping.original_name
            new_path = temp_path / mapping.new_name
            
            # 确保新文件的目录存在
            new_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                if original_path.exists():
                    # 如果目标文件已存在且不是同一个文件，先删除
                    if new_path.exists() and original_path.resolve() != new_path.resolve():
                        new_path.unlink()
                    
                    # 重命名文件
                    shutil.move(str(original_path), str(new_path))
                    actual_mappings[mapping.original_name] = mapping.new_name
                    
                    print(f"重命名文件: {mapping.original_name} -> {mapping.new_name}")
                else:
                    print(f"警告: 源文件不存在: {original_path}")
                    
            except Exception as e:
                print(f"重命名文件失败 {mapping.original_name} -> {mapping.new_name}: {e}")
                continue
        
        return actual_mappings
    
    def update_file_references(self, html_content: str, filename_mapping: Dict[str, str]) -> str:
        """
        更新HTML内容中的文件引用
        将HTML内容中的文件引用更新为重命名后的文件名
        
        Args:
            html_content: HTML内容
            filename_mapping: 文件名映射字典
            
        Returns:
            str: 更新后的HTML内容
        """
        updated_content = html_content
        
        # 更新href属性中的文件引用
        def replace_href(match):
            full_match = match.group(0)
            href_value = match.group(1)
            
            # 移除锚点部分进行文件名匹配
            if '#' in href_value:
                file_part, anchor_part = href_value.split('#', 1)
                anchor_part = '#' + anchor_part
            else:
                file_part = href_value
                anchor_part = ''
            
            # 查找映射
            if file_part in filename_mapping:
                new_href = filename_mapping[file_part] + anchor_part
                return full_match.replace(href_value, new_href)
            
            return full_match
        
        # 匹配href属性
        href_pattern = r'href\s*=\s*["\']([^"\']+)["\']'
        updated_content = re.sub(href_pattern, replace_href, updated_content, flags=re.IGNORECASE)
        
        # 更新src属性中的文件引用（如果有的话）
        def replace_src(match):
            full_match = match.group(0)
            src_value = match.group(1)
            
            # 查找映射
            if src_value in filename_mapping:
                new_src = filename_mapping[src_value]
                return full_match.replace(src_value, new_src)
            
            return full_match
        
        # 匹配src属性
        src_pattern = r'src\s*=\s*["\']([^"\']+)["\']'
        updated_content = re.sub(src_pattern, replace_src, updated_content, flags=re.IGNORECASE)
        
        return updated_content
    
    def get_filename_mappings(self) -> List[FilenameMapping]:
        """
        获取文件名映射列表
        
        Returns:
            List[FilenameMapping]: 文件名映射列表
        """
        return self.filename_mappings.copy()
    
    def get_mapping_dict(self) -> Dict[str, str]:
        """
        获取映射字典
        
        Returns:
            Dict[str, str]: 原文件名到新文件名的映射字典
        """
        return self._mapping_dict.copy()
    
    def find_new_filename(self, original_filename: str) -> str:
        """
        根据原文件名查找新文件名
        
        Args:
            original_filename: 原文件名
            
        Returns:
            str: 新文件名，如果未找到则返回原文件名
        """
        return self._mapping_dict.get(original_filename, original_filename)
    
    def find_markdown_filename(self, original_filename: str) -> str:
        """
        根据原文件名查找对应的Markdown文件名

        Args:
            original_filename: 原文件名

        Returns:
            str: Markdown文件名，如果未找到则返回基于原文件名生成的默认名称
        """
        for mapping in self.filename_mappings:
            if mapping.original_name == original_filename:
                return mapping.markdown_name

        # 如果未找到，生成默认的Markdown文件名
        base_name = Path(original_filename).stem
        return f"{sanitize_filename(base_name)}.md"

    def get_html_temp_name(self, original_name: str) -> str:
        """
        根据原始文件名获取HTML临时名（用于阶段1-3）

        Args:
            original_name: 原始HTML文件名

        Returns:
            str: HTML临时文件名，如果未找到则返回原文件名
        """
        md_name = self._mapping_dict.get(original_name)
        if md_name:
            return md_name.replace('.md', '.html')
        return original_name