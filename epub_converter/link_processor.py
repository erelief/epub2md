"""
链接处理器 - 处理文件重命名和链接引用更新
Link Processor - Handles file renaming and link reference updates
"""

import re
from typing import Dict, Optional
from pathlib import Path

from .utils import normalize_path, ensure_unicode_path


class LinkProcessor:
    """
    链接处理器类
    负责处理HTML中文件引用的修正功能，更新所有链接为重命名后的文件名，
    以及实现.html扩展名到.md的转换
    """
    
    def __init__(self, filename_mapping: Dict[str, str]):
        """
        初始化链接处理器
        
        Args:
            filename_mapping: 文件名映射字典，原文件名 -> 新文件名
        """
        self.filename_mapping = filename_mapping
        
        # 创建反向映射以便查找
        self.reverse_mapping = {v: k for k, v in filename_mapping.items()}
    
    def update_file_references(self, html_content: str, current_file: str = "") -> str:
        """
        更新HTML内容中的文件引用
        修正HTML中的文件引用，更新所有链接为重命名后的文件名
        
        Args:
            html_content: HTML内容
            current_file: 当前文件名（用于相对路径解析，可选）
            
        Returns:
            str: 更新后的HTML内容
        """
        if not html_content:
            return html_content
        
        updated_content = html_content
        
        # 更新href属性中的文件引用
        updated_content = self._update_href_references(updated_content)
        
        # 更新src属性中的文件引用（如果有的话）
        updated_content = self._update_src_references(updated_content)
        
        return updated_content
    
    def _update_href_references(self, html_content: str) -> str:
        """
        更新href属性中的文件引用
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 更新后的HTML内容
        """
        def replace_href(match):
            full_match = match.group(0)
            quote_char = match.group(1)  # 引号字符 (" 或 ')
            href_value = match.group(2)
            
            # 处理空链接
            if not href_value:
                return full_match
            
            # 分离文件部分和锚点部分
            if '#' in href_value:
                file_part, anchor_part = href_value.split('#', 1)
                anchor_part = '#' + anchor_part
            else:
                file_part = href_value
                anchor_part = ''
            
            # 跳过外部链接和特殊协议
            if self._is_external_link(file_part):
                return full_match
            
            # 查找映射并更新文件引用
            updated_file_part = self._find_mapped_filename(file_part)
            
            if updated_file_part != file_part:
                new_href = updated_file_part + anchor_part
                return f'href={quote_char}{new_href}{quote_char}'
            
            return full_match
        
        # 匹配href属性，支持单引号和双引号
        href_pattern = r'href\s*=\s*(["\'])([^"\']*?)\1'
        return re.sub(href_pattern, replace_href, html_content, flags=re.IGNORECASE)
    
    def _update_src_references(self, html_content: str) -> str:
        """
        更新src属性中的文件引用
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 更新后的HTML内容
        """
        def replace_src(match):
            full_match = match.group(0)
            quote_char = match.group(1)  # 引号字符 (" 或 ')
            src_value = match.group(2)
            
            # 处理空链接
            if not src_value:
                return full_match
            
            # 跳过外部链接和特殊协议
            if self._is_external_link(src_value):
                return full_match
            
            # 查找映射并更新文件引用
            updated_src = self._find_mapped_filename(src_value)
            
            if updated_src != src_value:
                return f'src={quote_char}{updated_src}{quote_char}'
            
            return full_match
        
        # 匹配src属性，支持单引号和双引号
        src_pattern = r'src\s*=\s*(["\'])([^"\']*?)\1'
        return re.sub(src_pattern, replace_src, html_content, flags=re.IGNORECASE)
    
    def _find_mapped_filename(self, filename: str) -> str:
        """
        查找映射的文件名
        
        Args:
            filename: 原文件名
            
        Returns:
            str: 映射后的文件名，如果未找到映射则返回原文件名
        """
        if not filename:
            return filename
        
        # 标准化文件名
        normalized_filename = filename.replace('\\', '/')
        
        # 直接查找完整匹配
        if normalized_filename in self.filename_mapping:
            return self.filename_mapping[normalized_filename]
        
        # 尝试查找基于路径的匹配
        filename_path = Path(normalized_filename)
        filename_name = filename_path.name
        
        # 查找文件名匹配
        for original, mapped in self.filename_mapping.items():
            original_path = Path(original)
            if original_path.name == filename_name:
                # 保持相对路径结构，只替换文件名
                if filename_path.parent != Path('.'):
                    mapped_path = filename_path.parent / Path(mapped).name
                    return str(mapped_path).replace('\\', '/')
                else:
                    return mapped
        
        return filename
    
    def _is_external_link(self, url: str) -> bool:
        """
        判断是否为外部链接或特殊协议
        
        Args:
            url: URL字符串
            
        Returns:
            bool: 是否为外部链接
        """
        if not url:
            return False
        
        # 外部协议
        external_protocols = ['http://', 'https://', 'ftp://', 'mailto:', 'tel:', 'javascript:']
        url_lower = url.lower()
        
        for protocol in external_protocols:
            if url_lower.startswith(protocol):
                return True
        
        # 绝对路径（以/开头）通常也是外部引用
        if url.startswith('/'):
            return True
        
        return False

    def convert_html_to_md_links(self, markdown_content: str, filename_mapping: Dict[str, str] = None, current_filename: str = None) -> str:
        """
        一次性完成：HTML文件名 → MD文件名
        在Markdown转换完成后调用，替换所有文件引用

        Args:
            markdown_content: Markdown内容
            filename_mapping: 原始HTML名到MD名的完整映射（可选，默认使用self.filename_mapping）
            current_filename: 当前文件的MD文件名（用于判断同页跳转）

        Returns:
            str: 更新后的Markdown内容
        """
        if not markdown_content:
            return markdown_content

        # 使用传入的映射或默认映射
        mapping = filename_mapping if filename_mapping is not None else self.filename_mapping

        def replace_link(match):
            full_match = match.group(0)
            link_text = match.group(1)
            link_url = match.group(2)

            # 跳过外部链接
            if self._is_external_link(link_url):
                return full_match

            # 分离文件部分和锚点部分
            if '#' in link_url:
                file_part, anchor_part = link_url.split('#', 1)
                anchor_part = '#' + anchor_part
            else:
                file_part = link_url
                anchor_part = ''

            # 查找映射并替换
            for original, md_name in mapping.items():
                # 去掉扩展名进行匹配（处理 text00002.xhtml 和 text00002 的情况）
                original_stem = Path(original).stem

                if file_part == original or file_part == original_stem:
                    # 判断是否是同页跳转
                    if current_filename and md_name == current_filename:
                        # 同页跳转：去掉文件名，只保留锚点
                        new_url = anchor_part if anchor_part else ''
                    else:
                        # 跨页跳转：保留完整文件名和锚点
                        new_url = md_name + anchor_part

                    return f'[{link_text}]({new_url})'

            return full_match

        # 匹配Markdown链接格式 [text](url)
        md_link_pattern = r'\[([^\]]*?)\]\(([^)]+?)\)'
        updated_content = re.sub(md_link_pattern, replace_link, markdown_content)

        # 更新引用式链接定义中的文件名
        def replace_ref_link(match):
            full_match = match.group(0)
            ref_id = match.group(1)
            link_url = match.group(2)

            # 跳过外部链接
            if self._is_external_link(link_url):
                return full_match

            # 分离文件部分和锚点部分
            if '#' in link_url:
                file_part, anchor_part = link_url.split('#', 1)
                anchor_part = '#' + anchor_part
            else:
                file_part = link_url
                anchor_part = ''

            # 查找映射并替换
            for original, md_name in mapping.items():
                original_stem = Path(original).stem

                if file_part == original or file_part == original_stem:
                    # 判断是否是同页跳转
                    if current_filename and md_name == current_filename:
                        # 同页跳转：去掉文件名，只保留锚点
                        new_url = anchor_part if anchor_part else ''
                    else:
                        # 跨页跳转：保留完整文件名和锚点
                        new_url = md_name + anchor_part

                    return f'[{ref_id}]: {new_url}'

            return full_match

        # 匹配引用式链接定义 [id]: url
        ref_link_pattern = r'^\s*\[([^\]]+?)\]:\s*(.+?)$'
        updated_content = re.sub(ref_link_pattern, replace_ref_link, updated_content, flags=re.MULTILINE)

        return updated_content

    def get_filename_mapping(self) -> Dict[str, str]:
        """
        获取文件名映射字典
        
        Returns:
            Dict[str, str]: 文件名映射字典的副本
        """
        return self.filename_mapping.copy()
    
    def add_filename_mapping(self, original: str, mapped: str) -> None:
        """
        添加文件名映射
        
        Args:
            original: 原文件名
            mapped: 映射后的文件名
        """
        self.filename_mapping[original] = mapped
        self.reverse_mapping[mapped] = original
    
    def remove_filename_mapping(self, original: str) -> bool:
        """
        移除文件名映射
        
        Args:
            original: 原文件名
            
        Returns:
            bool: 是否成功移除
        """
        if original in self.filename_mapping:
            mapped = self.filename_mapping[original]
            del self.filename_mapping[original]
            if mapped in self.reverse_mapping:
                del self.reverse_mapping[mapped]
            return True
        return False
    
    def clear_mappings(self) -> None:
        """清空所有映射"""
        self.filename_mapping.clear()
        self.reverse_mapping.clear()