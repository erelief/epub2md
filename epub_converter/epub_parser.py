"""
EPUB文件解析和提取
EPUB file parsing and extraction functionality
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

from .utils import ContentFile, CoverImageInfo, sanitize_filename, detect_encoding, normalize_path, ensure_unicode_path


class EPUBParser:
    """EPUB文件解析器"""
    
    def __init__(self, epub_path: str):
        """
        初始化EPUB解析器
        
        Args:
            epub_path: EPUB文件路径
        """
        # 确保路径Unicode兼容并标准化
        self.epub_path = normalize_path(ensure_unicode_path(epub_path))
        self.zip_file = None
        self._metadata = None
        self._content_files = None
        self._opf_path = None
        self._toc_mapping = None
        
    def __enter__(self):
        """上下文管理器入口"""
        self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if self.zip_file:
            self.zip_file.close()
    
    def _get_opf_path(self) -> str:
        """获取OPF文件路径"""
        if self._opf_path:
            return self._opf_path
            
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        # 读取container.xml获取OPF路径
        container_content = self.zip_file.read('META-INF/container.xml')
        container_root = ET.fromstring(container_content)
        
        # 查找OPF文件路径
        rootfile = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile')
        if rootfile is not None:
            self._opf_path = rootfile.get('full-path')
        else:
            raise ValueError("无法找到OPF文件路径")
        
        return self._opf_path
    
    def extract_metadata(self) -> Dict[str, Any]:
        """
        提取EPUB元数据
        
        Returns:
            Dict[str, Any]: 元数据字典
        """
        if self._metadata:
            return self._metadata
            
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        opf_path = self._get_opf_path()
        opf_content = self.zip_file.read(opf_path)
        opf_root = ET.fromstring(opf_content)
        
        # 定义命名空间
        namespaces = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        metadata = {}
        
        # 提取基本元数据
        title_elem = opf_root.find('.//dc:title', namespaces)
        metadata['title'] = title_elem.text if title_elem is not None else 'Unknown'
        
        creator_elem = opf_root.find('.//dc:creator', namespaces)
        metadata['creator'] = creator_elem.text if creator_elem is not None else 'Unknown'
        
        language_elem = opf_root.find('.//dc:language', namespaces)
        metadata['language'] = language_elem.text if language_elem is not None else 'en'
        
        # 提取封面信息
        cover_meta = opf_root.find('.//opf:meta[@name="cover"]', namespaces)
        if cover_meta is not None:
            metadata['cover_id'] = cover_meta.get('content')
        
        self._metadata = metadata
        return metadata
    
    def get_content_files(self) -> List[ContentFile]:
        """
        获取所有内容文件
        
        Returns:
            List[ContentFile]: 内容文件列表
        """
        if self._content_files:
            return self._content_files
            
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        opf_path = self._get_opf_path()
        opf_content = self.zip_file.read(opf_path)
        opf_root = ET.fromstring(opf_content)
        
        # 定义命名空间
        namespaces = {
            'opf': 'http://www.idpf.org/2007/opf'
        }
        
        # 获取spine中的阅读顺序
        spine_items = opf_root.findall('.//opf:spine/opf:itemref', namespaces)
        
        content_files = []
        opf_dir = str(Path(opf_path).parent)
        
        for order, itemref in enumerate(spine_items):
            idref = itemref.get('idref')
            
            # 在manifest中查找对应的item
            item = opf_root.find(f'.//opf:manifest/opf:item[@id="{idref}"]', namespaces)
            if item is None:
                continue
            
            href = item.get('href')
            media_type = item.get('media-type', '')
            
            # 只处理HTML/XHTML文件
            if not media_type.startswith('application/xhtml+xml') and not media_type.startswith('text/html'):
                continue
            
            # 构建完整路径（用于读取zip文件）
            if opf_dir and opf_dir != '.':
                full_path = f"{opf_dir}/{href}"
            else:
                full_path = href

            # 使用相对路径作为ContentFile.path（便于href匹配）
            file_path = href

            try:
                # 读取文件内容
                file_content = self.zip_file.read(full_path)
                encoding = detect_encoding(file_content)
                content = file_content.decode(encoding, errors='ignore')
                
                # 提取标题（优先使用TOC）
                toc_title = self.get_title_from_toc(file_path)
                if toc_title:
                    title = toc_title
                else:
                    # 从内容中提取标题
                    content_title = self._extract_title_from_content(content)
                    if content_title:
                        title = content_title
                    else:
                        # 使用文件名作为标题
                        filename = Path(file_path).stem
                        # 移除常见的前缀
                        filename = re.sub(r'^(part|chapter|section)0*', '', filename, flags=re.IGNORECASE)
                        title = filename or f"Chapter_{order + 1}"
                
                title = sanitize_filename(title)
                
                # 检查是否为封面页
                is_cover = self.is_cover_page(file_path, order)
                
                content_file = ContentFile(
                    path=file_path,
                    content=content,
                    title=title,
                    order=order + 1,
                    is_cover=is_cover
                )
                
                content_files.append(content_file)
                
            except Exception as e:
                print(f"警告：无法读取文件 {file_path}: {e}")
                continue
        
        self._content_files = content_files
        return content_files
    
    def _extract_title_from_content(self, html_content: str) -> Optional[str]:
        """
        从HTML内容中提取标题
        优先级：h1 > h2 > h3... > h6 > 页面可见内容 > title标签
        注意：TOC标题在调用此方法之前已经被优先处理
        
        Args:
            html_content: HTML内容
            
        Returns:
            Optional[str]: 提取的标题
        """
        import html
        
        # 第一优先级：尝试提取h1-h6标签（读者可见的标题）
        for level in range(1, 7):
            header_match = re.search(f'<h{level}[^>]*>(.*?)</h{level}>', html_content, re.IGNORECASE | re.DOTALL)
            if header_match:
                title = header_match.group(1).strip()
                if title:
                    clean_title = re.sub(r'<[^>]+>', '', title).strip()
                    # 解码HTML实体
                    clean_title = html.unescape(clean_title)
                    # 过滤掉无意义的标题
                    if clean_title and len(clean_title) > 1 and not re.match(r'^(untitled|chapter|section|未知|unknown|\d+)$', clean_title, re.IGNORECASE):
                        return clean_title
        
        # 第二优先级：尝试从body中提取第一行有意义的可见文本
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.IGNORECASE | re.DOTALL)
        if body_match:
            body_content = body_match.group(1)
            # 移除脚本和样式
            body_content = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body_content, flags=re.IGNORECASE | re.DOTALL)
            # 提取第一段文本
            text_content = re.sub(r'<[^>]+>', '', body_content).strip()
            # 解码HTML实体
            text_content = html.unescape(text_content)
            if text_content:
                # 取第一行作为标题，但允许更长的标题
                first_line = text_content.split('\n')[0].strip()
                if first_line and len(first_line) <= 200 and not re.match(r'^(untitled|chapter|section|未知|unknown|\d+)$', first_line, re.IGNORECASE):
                    return first_line
        
        # 最低优先级：尝试提取title标签（读者看不到的元数据）
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            if title:
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                # 解码HTML实体
                clean_title = html.unescape(clean_title)
                # 过滤掉无意义的标题
                if clean_title and not re.match(r'^(untitled|chapter|section|未知|unknown|\d+)$', clean_title, re.IGNORECASE):
                    return clean_title
        
        return None
    
    def extract_images(self, output_dir: str) -> Dict[str, str]:
        """
        提取所有图片文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            Dict[str, str]: 原始路径到新路径的映射
        """
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        image_mapping = {}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'}
        
        for file_path in self.zip_file.namelist():
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in image_extensions:
                try:
                    # 读取图片数据
                    image_data = self.zip_file.read(file_path)
                    
                    # 生成输出文件名
                    filename = Path(file_path).name
                    filename = sanitize_filename(filename)
                    output_path = Path(output_dir) / filename
                    
                    # 确保文件名唯一
                    counter = 1
                    original_stem = output_path.stem
                    while output_path.exists():
                        output_path = output_path.parent / f"{original_stem}_{counter}{output_path.suffix}"
                        counter += 1
                    
                    # 使用安全的文件写入方法
                    try:
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        
                        image_mapping[file_path] = str(output_path)
                    except Exception as write_error:
                        print(f"警告：无法保存图片 {output_path}: {write_error}")
                        continue
                    
                except Exception as e:
                    print(f"警告：无法提取图片 {file_path}: {e}")
        
        return image_mapping
    
    def is_cover_page(self, file_path: str, order: int = None) -> bool:
        """
        判断是否为封面页
        
        Args:
            file_path: 文件路径
            order: 文件在spine中的顺序（可选）
            
        Returns:
            bool: 是否为封面页
        """
        # 基于文件名判断
        filename = Path(file_path).name.lower()
        cover_keywords = ['cover', 'title', 'titlepage', '封面', '标题页']
        
        for keyword in cover_keywords:
            if keyword in filename:
                return True
        
        # 基于在spine中的位置判断（通常封面是第一个文件）
        # 避免递归调用get_content_files，直接使用传入的order参数
        if order is not None and order == 0:  # 第一个文件
            # 检查内容是否主要是图片
            try:
                if not self.zip_file:
                    self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
                
                content = self.zip_file.read(file_path).decode('utf-8', errors='ignore')
                
                # 计算图片标签数量
                img_count = len(re.findall(r'<img[^>]*>', content, re.IGNORECASE))
                
                # 计算文本内容长度
                text_content = re.sub(r'<[^>]+>', '', content)
                text_length = len(text_content.strip())
                
                # 如果主要是图片且文本很少，可能是封面
                if img_count > 0 and text_length < 200:
                    return True
                    
            except Exception:
                pass
        
        return False
    
    def get_cover_image_info(self) -> Optional[CoverImageInfo]:
        """
        获取封面图片信息
        
        Returns:
            Optional[CoverImageInfo]: 封面图片信息
        """
        metadata = self.extract_metadata()
        cover_id = metadata.get('cover_id')
        
        if not cover_id:
            return None
        
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        # 在OPF中查找封面图片
        opf_path = self._get_opf_path()
        opf_content = self.zip_file.read(opf_path)
        opf_root = ET.fromstring(opf_content)
        
        namespaces = {'opf': 'http://www.idpf.org/2007/opf'}
        
        # 查找封面item
        cover_item = opf_root.find(f'.//opf:manifest/opf:item[@id="{cover_id}"]', namespaces)
        if cover_item is None:
            return None
        
        href = cover_item.get('href')
        media_type = cover_item.get('media-type', '')
        
        # 构建完整路径
        opf_dir = str(Path(opf_path).parent)
        if opf_dir and opf_dir != '.':
            image_path = f"{opf_dir}/{href}"
        else:
            image_path = href
        
        try:
            # 读取图片数据
            image_data = self.zip_file.read(image_path)
            file_extension = Path(image_path).suffix
            
            return CoverImageInfo(
                image_path=image_path,
                image_data=image_data,
                file_extension=file_extension,
                mime_type=media_type
            )
            
        except Exception as e:
            print(f"警告：无法读取封面图片 {image_path}: {e}")
            return None
    
    def extract_toc_mapping(self) -> Dict[str, str]:
        """
        提取EPUB目录映射
        
        Returns:
            Dict[str, str]: 文件路径到标题的映射
        """
        if self._toc_mapping:
            return self._toc_mapping
            
        if not self.zip_file:
            self.zip_file = zipfile.ZipFile(self.epub_path, 'r')
        
        toc_mapping = {}
        
        try:
            # 尝试解析NCX文件（EPUB 2.0格式）
            ncx_mapping = self._parse_ncx_toc()
            if ncx_mapping:
                toc_mapping.update(ncx_mapping)
            
            # 尝试解析Navigation Document（EPUB 3.0格式）
            nav_mapping = self._parse_nav_toc()
            if nav_mapping:
                toc_mapping.update(nav_mapping)
            
        except Exception as e:
            print(f"警告：无法解析目录: {e}")
        
        self._toc_mapping = toc_mapping
        return toc_mapping
    
    def _parse_ncx_toc(self) -> Dict[str, str]:
        """
        解析NCX格式的目录文件，支持多级标题结构
        
        Returns:
            Dict[str, str]: 文件路径到标题的映射（包含父级标题）
        """
        try:
            ncx_content = None
            ncx_path = None
            
            # 方法1：直接尝试读取 toc.ncx
            try:
                ncx_content = self.zip_file.read('toc.ncx')
                ncx_path = 'toc.ncx'
            except KeyError:
                pass
            
            # 方法1.5：尝试读取 OEBPS/toc.ncx
            if ncx_content is None:
                try:
                    ncx_content = self.zip_file.read('OEBPS/toc.ncx')
                    ncx_path = 'OEBPS/toc.ncx'
                except KeyError:
                    pass
            
            # 方法2：如果直接读取失败，从OPF中查找NCX文件引用
            if ncx_content is None:
                opf_path = self._get_opf_path()
                opf_content = self.zip_file.read(opf_path)
                opf_root = ET.fromstring(opf_content)
                
                namespaces = {'opf': 'http://www.idpf.org/2007/opf'}
                
                # 通过media-type查找NCX文件引用
                ncx_item = opf_root.find('.//opf:manifest/opf:item[@media-type="application/x-dtbncx+xml"]', namespaces)
                
                # 如果没找到，通过spine的toc属性查找
                if not ncx_item:
                    spine = opf_root.find('.//opf:spine', namespaces)
                    if spine is not None:
                        toc_id = spine.get('toc')
                        if toc_id:
                            ncx_item = opf_root.find(f'.//opf:manifest/opf:item[@id="{toc_id}"]', namespaces)
                
                if ncx_item:
                    ncx_href = ncx_item.get('href')
                    if ncx_href:
                        opf_dir = str(Path(opf_path).parent)
                        
                        if opf_dir and opf_dir != '.':
                            ncx_path = f"{opf_dir}/{ncx_href}"
                        else:
                            ncx_path = ncx_href
                        
                        try:
                            ncx_content = self.zip_file.read(ncx_path)
                        except KeyError:
                            # 如果路径不存在，尝试直接使用href
                            ncx_content = self.zip_file.read(ncx_href)
                            ncx_path = ncx_href
            
            if ncx_content is None:
                return {}
            
            # 解析NCX XML
            ncx_root = ET.fromstring(ncx_content)
            ncx_ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}
            
            toc_mapping = {}
            
            # 递归解析navPoint元素，构建多级标题结构
            def parse_nav_points(nav_points, parent_titles=[]):
                for nav_point in nav_points:
                    # 获取当前标题
                    nav_label = nav_point.find('ncx:navLabel/ncx:text', ncx_ns)
                    if nav_label is None:
                        continue
                    
                    current_title = nav_label.text
                    if not current_title:
                        continue
                    
                    # 解码HTML实体
                    import html
                    current_title = html.unescape(current_title.strip())
                    
                    # 构建完整的标题路径（包含父级标题）
                    full_title_path = parent_titles + [current_title]
                    
                    # 获取内容引用
                    content_elem = nav_point.find('ncx:content', ncx_ns)
                    if content_elem is not None:
                        src = content_elem.get('src')
                        if src:
                            # 移除锚点部分
                            if '#' in src:
                                src = src.split('#')[0]
                            
                            # 构建多级标题字符串
                            if len(full_title_path) > 1:
                                # 多级标题用 "-" 连接
                                hierarchical_title = "-".join(full_title_path)
                            else:
                                # 单级标题直接使用
                                hierarchical_title = current_title
                            
                            # 构建完整的文件路径
                            # 需要考虑NCX文件所在的目录
                            if ncx_path and '/' in ncx_path:
                                ncx_dir = str(Path(ncx_path).parent)
                                if ncx_dir and ncx_dir != '.':
                                    full_src_path = f"{ncx_dir}/{src}"
                                else:
                                    full_src_path = src
                            else:
                                full_src_path = src
                            
                            toc_mapping[full_src_path] = hierarchical_title
                    
                    # 递归处理子级navPoint
                    child_nav_points = nav_point.findall('ncx:navPoint', ncx_ns)
                    if child_nav_points:
                        parse_nav_points(child_nav_points, full_title_path)
            
            # 开始解析顶级navPoint
            top_level_nav_points = ncx_root.findall('.//ncx:navMap/ncx:navPoint', ncx_ns)
            parse_nav_points(top_level_nav_points)
            
            return toc_mapping
            
        except Exception as e:
            print(f"警告：解析NCX目录失败: {e}")
            return {}
    
    def _parse_nav_toc(self) -> Dict[str, str]:
        """
        解析Navigation Document格式的目录文件（EPUB 3.0），支持多级标题结构
        
        Returns:
            Dict[str, str]: 文件路径到标题的映射（包含父级标题）
        """
        try:
            # 在OPF中查找Navigation Document
            opf_path = self._get_opf_path()
            opf_content = self.zip_file.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            namespaces = {'opf': 'http://www.idpf.org/2007/opf'}
            
            # 查找Navigation Document
            nav_item = opf_root.find('.//opf:manifest/opf:item[@properties="nav"]', namespaces)
            if not nav_item:
                return {}
            
            nav_href = nav_item.get('href')
            opf_dir = str(Path(opf_path).parent)
            
            if opf_dir and opf_dir != '.':
                nav_path = f"{opf_dir}/{nav_href}"
            else:
                nav_path = nav_href
            
            # 读取Navigation Document
            nav_content = self.zip_file.read(nav_path)
            nav_root = ET.fromstring(nav_content)
            
            toc_mapping = {}
            
            # 查找TOC导航
            toc_nav = nav_root.find('.//nav[@epub:type="toc"]', {'epub': 'http://www.idpf.org/2007/ops'})
            if toc_nav is None:
                # 尝试不使用命名空间
                toc_nav = nav_root.find('.//nav')
            
            if toc_nav is not None:
                # 递归解析嵌套的列表结构
                def parse_nav_list(element, parent_titles=[]):
                    # 查找所有直接子级的li元素
                    for li in element.findall('./li'):
                        # 查找li中的链接
                        link = li.find('./a')
                        if link is not None:
                            href = link.get('href')
                            title = link.text or ""
                            
                            if href and title:
                                # 移除锚点部分
                                if '#' in href:
                                    href = href.split('#')[0]
                                
                                # 构建完整的标题路径
                                full_title_path = parent_titles + [title.strip()]
                                
                                # 构建多级标题字符串
                                if len(full_title_path) > 1:
                                    hierarchical_title = "-".join(full_title_path)
                                else:
                                    hierarchical_title = title.strip()
                                
                                # 构建完整路径
                                if opf_dir and opf_dir != '.':
                                    full_path = f"{opf_dir}/{href}"
                                else:
                                    full_path = href
                                
                                toc_mapping[full_path] = hierarchical_title
                        
                        # 递归处理嵌套的ol/ul列表
                        nested_lists = li.findall('./ol') + li.findall('./ul')
                        for nested_list in nested_lists:
                            # 如果有链接，使用链接的标题作为父级标题
                            if link is not None and link.text:
                                current_parent_titles = parent_titles + [link.text.strip()]
                            else:
                                current_parent_titles = parent_titles
                            
                            parse_nav_list(nested_list, current_parent_titles)
                
                # 开始解析顶级列表
                top_lists = toc_nav.findall('./ol') + toc_nav.findall('./ul')
                for top_list in top_lists:
                    parse_nav_list(top_list)
            
            return toc_mapping
            
        except Exception as e:
            print(f"警告：解析Navigation Document失败: {e}")
            return {}
    
    def get_title_from_toc(self, file_path: str) -> Optional[str]:
        """
        从目录中获取文件标题
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[str]: 目录中的标题，如果没有则返回None
        """
        toc_mapping = self.extract_toc_mapping()
        
        # 直接匹配
        if file_path in toc_mapping:
            return toc_mapping[file_path]
        
        # 尝试匹配文件名
        filename = Path(file_path).name
        for toc_path, title in toc_mapping.items():
            if Path(toc_path).name == filename:
                return title
        
        return None