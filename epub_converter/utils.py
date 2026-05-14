"""
通用工具函数和数据类
Common utility functions and data classes
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ContentFile:
    """EPUB内容文件数据类"""
    path: str
    content: str
    title: str
    order: int
    is_cover: bool


@dataclass
class CoverImageInfo:
    """封面图片信息数据类"""
    image_path: str
    image_data: bytes
    file_extension: str
    mime_type: str


@dataclass
class MarkdownFile:
    """Markdown文件数据类"""
    filename: str
    content: str
    title: str
    images: List[str]


@dataclass
class FilenameMapping:
    """文件名映射数据类"""
    original_name: str
    new_name: str
    markdown_name: str


@dataclass
class AnnotationProcessingConfig:
    """注释处理配置数据类"""
    use_inline_mode: bool
    language: str
    annotation_format: str


@dataclass
class ConversionResult:
    """转换结果数据类"""
    output_directory: str
    converted_files: List[str]
    extracted_images: List[str]
    cover_image_path: Optional[str]
    language_detected: str
    annotation_mode_used: str  # 新增：记录使用的注释处理模式
    processing_time: float
    filename_mappings: List[FilenameMapping]  # 新增：记录文件名映射


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，确保符合Windows文件系统规范
    支持多级标题格式（用"-"分隔的层级标题）
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    import re
    import html
    
    # 首先解码HTML实体（如 &#160; -> 空格）
    filename = html.unescape(filename)
    
    # Windows不允许的字符（只包括真正不被文件系统支持的字符）
    # 注意：保留 "-" 作为层级分隔符，但移除冒号
    invalid_chars = '<>:"/\\|?*'
    
    # Windows保留名称
    reserved_names = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # 替换无效字符
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # 替换控制字符 (0-31)
    filename = re.sub(r'[\x00-\x1f]', '_', filename)
    
    # 处理多级标题的特殊清理
    # 将多个空格替换为单个下划线，但保留 "-" 分隔符
    filename = re.sub(r'\s+', '_', filename)  # 将多个空格替换为单个下划线
    
    # 清理 "-" 分隔符周围的多余下划线
    # 例如: "第一篇___-___第二章" -> "第一篇-第二章"
    filename = re.sub(r'_*-_*', '-', filename)
    
    # 将多个下划线合并为单个下划线
    filename = re.sub(r'_+', '_', filename)
    
    # 移除前后的空格、点和下划线，但保留中间的 "-"
    filename = filename.strip(' ._')
    
    # 检查保留名称
    if filename:
        # 对于多级标题，检查每个部分是否为保留名称
        parts = filename.split('-')
        cleaned_parts = []
        for part in parts:
            part = part.strip('_')
            name_without_ext = part.split('.')[0].upper() if part else ''
            if name_without_ext in reserved_names:
                part = f"_{part}"
            cleaned_parts.append(part)
        filename = '-'.join(cleaned_parts)
    
    # 确保不为空
    if not filename:
        filename = "untitled"
    
    # 限制长度（Windows路径限制，考虑扩展名）
    if len(filename) > 200:
        # 对于多级标题，尝试智能截断
        if '-' in filename:
            parts = filename.split('-')
            # 保留扩展名
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_length = 200 - len(ext) - 1
                
                # 尝试平均分配长度给各个部分
                avg_length = max_name_length // len(parts)
                truncated_parts = []
                for part in parts:
                    if len(part) > avg_length:
                        truncated_parts.append(part[:avg_length])
                    else:
                        truncated_parts.append(part)
                
                filename = '-'.join(truncated_parts) + '.' + ext
            else:
                # 没有扩展名的情况
                avg_length = 200 // len(parts)
                truncated_parts = []
                for part in parts:
                    if len(part) > avg_length:
                        truncated_parts.append(part[:avg_length])
                    else:
                        truncated_parts.append(part)
                
                filename = '-'.join(truncated_parts)
        else:
            # 单级标题的截断
            if '.' in filename:
                name, ext = filename.rsplit('.', 1)
                max_name_length = 200 - len(ext) - 1
                filename = name[:max_name_length] + '.' + ext
            else:
                filename = filename[:200]
    
    return filename


def detect_encoding(content: bytes) -> str:
    """
    检测内容编码
    
    Args:
        content: 字节内容
        
    Returns:
        str: 编码名称
    """
    try:
        # 尝试UTF-8
        content.decode('utf-8')
        return 'utf-8'
    except UnicodeDecodeError:
        pass
    
    try:
        # 尝试GBK（中文）
        content.decode('gbk')
        return 'gbk'
    except UnicodeDecodeError:
        pass
    
    try:
        # 尝试Latin-1
        content.decode('latin-1')
        return 'latin-1'
    except UnicodeDecodeError:
        pass
    
    # 默认返回UTF-8
    return 'utf-8'


def is_valid_epub_file(file_path: str) -> bool:
    """
    验证是否为有效的EPUB文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为有效EPUB文件
    """
    import zipfile
    import os
    
    if not os.path.exists(file_path):
        return False
    
    if not file_path.lower().endswith('.epub'):
        return False
    
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_file:
            # 检查必需的EPUB文件
            required_files = ['META-INF/container.xml']
            for required_file in required_files:
                if required_file not in zip_file.namelist():
                    return False
            return True
    except (zipfile.BadZipFile, Exception):
        return False


def extract_text_content(html_content: str) -> str:
    """
    从HTML内容中提取纯文本
    
    Args:
        html_content: HTML内容
        
    Returns:
        str: 纯文本内容
    """
    import re
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', html_content)
    
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def normalize_path(path: str) -> str:
    """
    标准化路径，确保跨平台兼容性
    
    Args:
        path: 原始路径
        
    Returns:
        str: 标准化后的路径
    """
    import os
    import platform
    
    # 标准化路径分隔符
    normalized = os.path.normpath(path)
    
    # 在Windows上处理长路径
    if platform.system() == 'Windows':
        # 处理UNC路径和长路径前缀
        if normalized.startswith('\\\\'):
            # UNC路径，保持原样
            pass
        elif len(normalized) > 260 and not normalized.startswith('\\\\?\\'):
            # 长路径，添加长路径前缀
            if os.path.isabs(normalized):
                normalized = '\\\\?\\' + normalized
            else:
                # 相对路径转为绝对路径后添加前缀
                abs_path = os.path.abspath(normalized)
                if len(abs_path) > 260:
                    normalized = '\\\\?\\' + abs_path
    
    return normalized


def ensure_unicode_path(path: str) -> str:
    """
    确保路径正确处理Unicode字符
    
    Args:
        path: 路径字符串
        
    Returns:
        str: Unicode兼容的路径
    """
    import sys
    
    # 确保路径是Unicode字符串
    if isinstance(path, bytes):
        # 尝试不同编码解码
        for encoding in ['utf-8', 'gbk', 'cp936', sys.getfilesystemencoding()]:
            try:
                path = path.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            # 如果所有编码都失败，使用错误处理
            path = path.decode('utf-8', errors='replace')
    
    return path


def create_safe_directory(directory_path: str) -> str:
    """
    安全创建目录，处理Windows特殊情况
    
    Args:
        directory_path: 目录路径
        
    Returns:
        str: 创建的目录路径
    """
    import os
    from pathlib import Path
    
    # 确保Unicode兼容
    directory_path = ensure_unicode_path(directory_path)
    
    # 标准化路径
    directory_path = normalize_path(directory_path)
    
    # 创建Path对象
    path_obj = Path(directory_path)
    
    try:
        # 创建目录，包括父目录
        path_obj.mkdir(parents=True, exist_ok=True)
        return str(path_obj)
    except OSError as e:
        # 处理Windows特殊错误
        if e.errno == 36:  # 文件名太长
            # 尝试缩短路径
            parent = path_obj.parent
            name = path_obj.name
            if len(name) > 100:
                name = name[:100]
                shortened_path = parent / name
                shortened_path.mkdir(parents=True, exist_ok=True)
                return str(shortened_path)
        raise


def safe_file_write(file_path: str, content: str, encoding: str = 'utf-8') -> None:
    """
    安全写入文件，处理Unicode和Windows兼容性
    
    Args:
        file_path: 文件路径
        content: 文件内容
        encoding: 编码格式
    """
    import os
    from pathlib import Path
    
    # 确保路径Unicode兼容
    file_path = ensure_unicode_path(file_path)
    file_path = normalize_path(file_path)
    
    # 确保目录存在
    directory = os.path.dirname(file_path)
    if directory:
        create_safe_directory(directory)
    
    # 写入文件
    path_obj = Path(file_path)
    
    try:
        with open(path_obj, 'w', encoding=encoding, errors='replace') as f:
            f.write(content)
    except Exception as e:
        # 如果UTF-8失败，尝试系统默认编码
        if encoding == 'utf-8':
            import sys
            system_encoding = sys.getfilesystemencoding() or 'cp1252'
            with open(path_obj, 'w', encoding=system_encoding, errors='replace') as f:
                f.write(content)
        else:
            raise