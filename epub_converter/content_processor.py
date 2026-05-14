"""
HTML到Markdown转换和内容处理
HTML to Markdown conversion and content processing
"""

import re
from typing import List, Optional, Dict
import html2text

from .utils import ContentFile, MarkdownFile


class ContentProcessor:
    """内容处理器"""
    
    def __init__(self, language: str):
        """
        初始化内容处理器
        
        Args:
            language: 检测到的语言
        """
        self.language = language
        self.html2text_converter = html2text.HTML2Text()
        
        # 配置html2text转换器
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_anchors = False
        self.html2text_converter.skip_internal_links = False  # 转换内部链接
        self.html2text_converter.ignore_images = False
        self.html2text_converter.body_width = 0  # 不限制行宽
        self.html2text_converter.unicode_snob = True
        self.html2text_converter.escape_snob = True
        # 确保段落之间有换行
        self.html2text_converter.single_line_break = False  # 使用双换行分隔段落
    
    def convert_html_to_markdown(self, html_content: str, annotation_processor=None, title: str = "", file_path: str = "") -> str:
        """
        将HTML内容转换为Markdown

        Args:
            html_content: HTML内容
            annotation_processor: 注释处理器（可选）
            title: 页面标题（用于TOC检测）
            file_path: 当前文件路径

        Returns:
            str: Markdown内容
        """
        try:
            # HTML阶段已完成所有格式处理，这里只做语法转换
            processed_html = self._preprocess_html(html_content)

            # html2text只做语法转换
            markdown = self.html2text_converter.handle(processed_html)

            # 转换KIRO标记为HTML锚点格式
            markdown = self._convert_kiro_markers(markdown)

            return markdown

        except Exception as e:
            print(f"警告：HTML转换失败: {e}")
            # 如果转换失败，返回清理后的文本
            return self._extract_text_fallback(html_content)

    def _convert_kiro_markers(self, markdown: str) -> str:
        """
        将KIRO标记转换为HTML锚点格式

        html2text会把下划线转义成\_
        所以需要匹配 KIRO\_XXX\_START\_xxx\_KIRO\_XXX\_END

        Args:
            markdown: Markdown内容

        Returns:
            str: 转换后的Markdown内容
        """
        # 1. 转换导航锚点
        # KIRO\_ANCHOR\_START\_c1\_KIRO\_ANCHOR\_END -> <a id="c1"></a>
        markdown = re.sub(
            r'KIRO\\_ANCHOR\\_START\\_([^_\\]+)\\_KIRO\\_ANCHOR\\_END',
            r'<a id="\1"></a>',
            markdown
        )

        # 2. 转换注释回跳锚点
        # KIRO\_ANNOTATION\_BACK\_START\_back-1\_KIRO\_ANNOTATION\_BACK\_END -> <a id="back-1"></a>
        markdown = re.sub(
            r'KIRO\\_ANNOTATION\\_BACK\\_START\\_(\S+)\\_KIRO\\_ANNOTATION\\_BACK\\_END',
            r'<a id="\1"></a>',
            markdown
        )

        # 3. 转换注释内容锚点
        # KIRO\_ANNOTATION\_ANCHOR\_START\_note-1\_KIRO\_ANNOTATION\_ANCHOR\_END -> <a id="note-1"></a>
        markdown = re.sub(
            r'KIRO\\_ANNOTATION\\_ANCHOR\\_START\\_(\S+)\\_KIRO\\_ANNOTATION\_ANCHOR\\_END',
            r'<a id="\1"></a>',
            markdown
        )

        # 4. 转换链接标记
        # KIRO\_LINK\_START\[text\](url)KIRO\_LINK\_END -> [text](url)
        # 使用非贪婪匹配，匹配任何字符（包括中文）
        markdown = re.sub(
            r'KIRO\\_LINK\\_START\\?\[(.+?)\\?\]\\?\((.+?)\\?\)KIRO\\_LINK\\_END',
            r'[\1](\2)',
            markdown
        )

        # 5. 清理markdown链接中不必要的转义（html2text会转义特殊字符）
        # 只清理markdown链接语法中的转义：\# \[ \] \( \)
        def clean_link_escapes(match):
            text = match.group(1).replace('\\#', '#').replace('\\[', '[').replace('\\]', ']')
            url = match.group(2).replace('\\#', '#').replace('\\(', '(').replace('\\)', ')')
            return f'[{text}]({url})'

        markdown = re.sub(r'\[(.+?)\]\((.+?)\)', clean_link_escapes, markdown)

        return markdown
    

    def _preprocess_html(self, html_content: str) -> str:
        """
        预处理HTML内容（所有格式处理都在此阶段完成）

        Args:
            html_content: 原始HTML内容

        Returns:
            str: 预处理后的HTML内容
        """
        import html

        # 解码HTML实体
        html_content = html.unescape(html_content)

        # 移除XML声明和DOCTYPE
        html_content = re.sub(r'<\?xml[^>]*\?>', '', html_content)
        html_content = re.sub(r'<!DOCTYPE[^>]*>', '', html_content)

        # 确保段落之间有分隔
        html_content = re.sub(r'</p>\s*', '</p>\n\n', html_content, flags=re.IGNORECASE)

        # 处理CSS样式（HTML阶段的格式清理）
        html_content = self._process_css_styles(html_content)

        # 处理自闭合标签
        html_content = re.sub(r'<br\s*/?>', '<br/>', html_content)
        html_content = re.sub(r'<hr\s*/?>', '<hr/>', html_content)
        html_content = re.sub(r'<img([^>]*?)/?>', r'<img\1/>', html_content)

        return html_content
    
    def _process_css_styles(self, html_content: str) -> str:
        """
        智能处理CSS样式，合并重复的格式标记
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            str: 处理后的HTML内容
        """
        # 1. 合并连续的相同格式标签
        html_content = self._merge_consecutive_tags(html_content)
        
        # 2. 移除纯装饰性的span标签
        html_content = self._remove_decorative_spans(html_content)
        
        # 3. 简化嵌套的格式标签
        html_content = self._simplify_nested_formatting(html_content)
        
        return html_content
    
    def _merge_consecutive_tags(self, html_content: str) -> str:
        """
        合并连续的相同格式标签
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 处理后的HTML内容
        """
        # 处理连续的<b>标签，但只在同一段落内合并
        # 例如: <b>短</b><b>剧</b> -> <b>短剧</b>
        def merge_bold_tags_in_paragraph(match):
            full_match = match.group(0)
            # 检查是否跨越了段落边界
            if '</p>' in full_match or '<p' in full_match:
                return full_match  # 不合并跨段落的标签
            
            # 提取所有<b>标签中的文本
            texts = re.findall(r'<b[^>]*>(.*?)</b>', full_match, re.IGNORECASE | re.DOTALL)
            if texts:
                merged_text = ''.join(texts)
                return f'<b>{merged_text}</b>'
            return full_match
        
        # 匹配连续的<b>标签，但不跨越段落
        html_content = re.sub(
            r'(?:<b[^>]*>[^<]*?</b>\s*){2,}',
            merge_bold_tags_in_paragraph,
            html_content,
            flags=re.IGNORECASE
        )
        
        # 处理连续的<i>标签
        def merge_italic_tags_in_paragraph(match):
            full_match = match.group(0)
            if '</p>' in full_match or '<p' in full_match:
                return full_match
            
            texts = re.findall(r'<i[^>]*>(.*?)</i>', full_match, re.IGNORECASE | re.DOTALL)
            if texts:
                merged_text = ''.join(texts)
                return f'<i>{merged_text}</i>'
            return full_match
        
        html_content = re.sub(
            r'(?:<i[^>]*>[^<]*?</i>\s*){2,}',
            merge_italic_tags_in_paragraph,
            html_content,
            flags=re.IGNORECASE
        )
        
        # 处理连续的<em>标签
        def merge_em_tags_in_paragraph(match):
            full_match = match.group(0)
            if '</p>' in full_match or '<p' in full_match:
                return full_match
            
            texts = re.findall(r'<em[^>]*>(.*?)</em>', full_match, re.IGNORECASE | re.DOTALL)
            if texts:
                merged_text = ''.join(texts)
                return f'<em>{merged_text}</em>'
            return full_match
        
        html_content = re.sub(
            r'(?:<em[^>]*>[^<]*?</em>\s*){2,}',
            merge_em_tags_in_paragraph,
            html_content,
            flags=re.IGNORECASE
        )
        
        # 处理连续的<strong>标签
        def merge_strong_tags_in_paragraph(match):
            full_match = match.group(0)
            if '</p>' in full_match or '<p' in full_match:
                return full_match
            
            texts = re.findall(r'<strong[^>]*>(.*?)</strong>', full_match, re.IGNORECASE | re.DOTALL)
            if texts:
                merged_text = ''.join(texts)
                return f'<strong>{merged_text}</strong>'
            return full_match
        
        html_content = re.sub(
            r'(?:<strong[^>]*>[^<]*?</strong>\s*){2,}',
            merge_strong_tags_in_paragraph,
            html_content,
            flags=re.IGNORECASE
        )
        
        return html_content
    
    def _remove_decorative_spans(self, html_content: str) -> str:
        """
        移除纯装饰性的span标签
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 处理后的HTML内容
        """
        # 移除只有class属性的span标签，保留内容
        html_content = re.sub(
            r'<span[^>]*class=["\'][^"\']*["\'][^>]*>(.*?)</span>',
            r'\1',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # 移除空的span标签
        html_content = re.sub(
            r'<span[^>]*></span>',
            '',
            html_content,
            flags=re.IGNORECASE
        )
        
        return html_content
    
    def _simplify_nested_formatting(self, html_content: str) -> str:
        """
        简化嵌套的格式标签
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 处理后的HTML内容
        """
        # 处理嵌套的粗体标签 <b><strong>text</strong></b> -> <b>text</b>
        html_content = re.sub(
            r'<b[^>]*>\s*<strong[^>]*>(.*?)</strong>\s*</b>',
            r'<b>\1</b>',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # 处理嵌套的斜体标签 <i><em>text</em></i> -> <i>text</i>
        html_content = re.sub(
            r'<i[^>]*>\s*<em[^>]*>(.*?)</em>\s*</i>',
            r'<i>\1</i>',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # 移除重复的格式标签 <b><b>text</b></b> -> <b>text</b>
        html_content = re.sub(
            r'<(b|i|em|strong)([^>]*)>\s*<\1[^>]*>(.*?)</\1>\s*</\1>',
            r'<\1\2>\3</\1>',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        return html_content
    
    def _extract_text_fallback(self, html_content: str) -> str:
        """
        备用文本提取方法
        
        Args:
            html_content: HTML内容
            
        Returns:
            str: 提取的文本
        """
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # 解码HTML实体
        import html
        text = html.unescape(text)
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def is_potential_title_page(self, content: str, title: str = "") -> bool:
        """
        判断是否为疑似标题页
        
        Args:
            content: 页面内容
            title: 页面标题
            
        Returns:
            bool: 是否为疑似标题页
        """
        # 排除版权信息页和出版信息页
        if self._is_copyright_or_publication_page(content, title):
            return False
        
        # 条件1：明显的短标题页（最确定的情况）
        if self._is_obvious_title_page(content):
            return True
        
        # 条件2：章节标题页模式（需要模式匹配的情况）
        if self._is_chapter_title_page(content, title):
            return True
            
        return False
    
    def _is_copyright_or_publication_page(self, content: str, title: str) -> bool:
        """
        判断是否为版权信息页或出版信息页
        
        Args:
            content: 页面内容
            title: 页面标题
            
        Returns:
            bool: 是否为版权或出版信息页
        """
        # 移除HTML标签获取纯文本
        text_content = re.sub(r'<[^>]+>', '', content).strip()
        combined_text = f"{title} {text_content}".lower()
        
        # 版权和出版信息关键词
        copyright_keywords = [
            '版权', '出版', '印刷', '发行', 'isbn', 'copyright', 'publisher', 
            '出版社', '印刷厂', '版次', '印次', '定价', '书号', 
            'all rights reserved', '保留所有权利', '未经许可', 
            '作者简介', '编辑', '责任编辑', '装帧设计'
        ]
        
        # 如果包含多个版权关键词，很可能是版权页
        keyword_count = sum(1 for keyword in copyright_keywords if keyword in combined_text)
        if keyword_count >= 2:
            return True
        
        # 检查是否包含典型的版权页格式（如ISBN、出版日期等）
        copyright_patterns = [
            r'isbn[:\s]*[\d\-x]+',  # ISBN号
            r'\d{4}年\d{1,2}月.*?版',  # 中文出版日期格式
            r'copyright\s*©?\s*\d{4}',  # 版权年份
            r'第\d+版.*?第\d+次印刷',  # 版次印次
        ]
        
        for pattern in copyright_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_obvious_title_page(self, content: str) -> bool:
        """
        判断是否为明显的标题页
        
        Args:
            content: 页面内容
            
        Returns:
            bool: 是否为明显标题页
        """
        # 移除HTML标签获取纯文本
        text_content = re.sub(r'<[^>]+>', '', content).strip()
        
        # 如果内容为空，认为是标题页
        if not text_content:
            return True
        
        # 内容很短且只包含标题标签的情况
        if len(text_content) < 50:
            has_heading = re.search(r'<h[1-6][^>]*>', content, re.IGNORECASE)
            if has_heading:
                # 移除标题内容后检查剩余内容
                content_without_headings = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', content, flags=re.IGNORECASE | re.DOTALL)
                remaining_text = re.sub(r'<[^>]+>', '', content_without_headings).strip()
                
                # 如果移除标题后剩余内容很少或没有，认为是标题页
                if len(remaining_text) < 10:
                    return True
        
        return False
    
    def _is_chapter_title_page(self, content: str, title: str) -> bool:
        """
        判断是否为章节标题页
        
        Args:
            content: 页面内容
            title: 页面标题
            
        Returns:
            bool: 是否为章节标题页
        """
        # 移除HTML标签获取纯文本
        text_content = re.sub(r'<[^>]+>', '', content).strip()
        
        # 检查标题和内容中是否包含章节标识符
        chapter_patterns = [
            r'第\s*[一二三四五六七八九十\d]+\s*章',  # 中文章节
            r'Chapter\s+\d+',  # 英文章节
            r'第\s*[一二三四五六七八九十\d]+\s*节',  # 中文节
            r'Section\s+\d+',  # 英文节
            r'Part\s+\d+',  # 部分
            r'第\s*[一二三四五六七八九十\d]+\s*部分',  # 中文部分
            r'charpter\s*\d+',  # 常见的chapter拼写错误
        ]
        
        combined_text = f"{title} {text_content}"
        
        # 必须包含章节标识符
        has_chapter_marker = False
        for pattern in chapter_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                has_chapter_marker = True
                break
        
        if not has_chapter_marker:
            return False
        
        # 内容必须相对简短（标题页特征）
        if len(text_content) > 200:
            return False
        
        # 内容行数不能太多（标题页通常只有几行）
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        if len(lines) > 5:
            return False
        
        return True
    
    
    def show_page_preview(self, content: str, title: str) -> str:
        """
        显示页面预览
        
        Args:
            content: 页面内容
            title: 页面标题
            
        Returns:
            str: 格式化的预览文本
        """
        # 移除HTML标签获取纯文本
        text_content = re.sub(r'<[^>]+>', '', content).strip()
        
        # 限制预览长度
        preview_lines = text_content.split('\n')[:3]  # 最多显示3行
        preview_text = '\n'.join(line.strip() for line in preview_lines if line.strip())
        
        # 限制每行长度
        if len(preview_text) > 100:
            preview_text = preview_text[:100] + "..."
        
        return f"{title} ({len(text_content)}字符)"
    
    def collect_potential_title_pages(self, files: List[ContentFile]) -> List[int]:
        """
        收集所有疑似标题页的索引
        
        Args:
            files: 内容文件列表
            
        Returns:
            List[int]: 疑似标题页的索引列表
        """
        potential_title_pages = []
        
        for i, file in enumerate(files):
            if file.is_cover:
                continue
            
            if self.is_potential_title_page(file.content, file.title):
                potential_title_pages.append(i)
        
        return potential_title_pages
    
    def ask_user_batch_merge_confirmation(self, files: List[ContentFile], potential_indices: List[int], interactive: bool = True) -> List[int]:
        """
        批量询问用户哪些标题页需要合并
        
        Args:
            files: 内容文件列表
            potential_indices: 疑似标题页的索引列表
            interactive: 是否使用交互模式，False时默认不合并任何页面
            
        Returns:
            List[int]: 用户选择要合并的页面索引列表
        """
        if not potential_indices:
            return []
        
        if not interactive:
            # 非交互模式，默认不合并任何页面
            return []
        
        print(f"\n检测到 {len(potential_indices)} 个疑似标题页（只包含标题和少量解释，可能不需要作为单独的页面）：")
        print("=" * 50)
        
        for i, idx in enumerate(potential_indices):
            file = files[idx]
            preview = self.show_page_preview(file.content, file.title)
            print(f"{i+1}. {preview}")
        
        print("=" * 50)
        print("你想合并到后面的文章吗？请先确认原来的 EPUB 文件后，谨慎选择处理方式：")
        print("1) 不合并任何页面")
        print("2) 全部合并")
        print("3) 选择不合并的页面（其余全部合并）")
        
        while True:
            response = input("选择 (1/2/3): ").strip()
            
            if response == '1':
                return []
            elif response == '2':
                return potential_indices
            elif response == '3':
                return self._ask_selective_keep(files, potential_indices)
            else:
                print("请输入 1、2 或 3")
    
    def _ask_selective_keep(self, files: List[ContentFile], potential_indices: List[int]) -> List[int]:
        """
        选择性保留的详细选择（选择不合并的页面）
        
        Args:
            files: 内容文件列表
            potential_indices: 疑似标题页的索引列表
            
        Returns:
            List[int]: 用户选择要合并的页面索引列表（排除了不合并的页面）
        """
        print("\n1) 请选择要保留为独立页面的标题页（输入数字，用空格分隔，如：1 3 5）：")
        print("2) 直接按回车表示全部合并：")
        print("3) 输入 'b' 或 'back' 返回上一步：")
        
        while True:
            response = input("选择: ").strip()
            
            if not response:
                # 全部合并
                return potential_indices
            
            if response.lower() in ['b', 'back', '返回']:
                # 返回上一步，重新调用主选择方法
                return self.ask_user_batch_merge_confirmation(files, potential_indices)
            
            try:
                selected_numbers = [int(x) for x in response.split()]
                keep_indices = []  # 要保留为独立页面的索引
                
                for num in selected_numbers:
                    if 1 <= num <= len(potential_indices):
                        keep_indices.append(potential_indices[num - 1])
                    else:
                        print(f"错误：数字 {num} 超出范围 (1-{len(potential_indices)})")
                        break
                else:
                    # 返回要合并的页面索引（排除要保留的）
                    merge_indices = [idx for idx in potential_indices if idx not in keep_indices]
                    return merge_indices
                    
            except ValueError:
                print("错误：请输入有效的数字，用空格分隔")
    
    def ask_user_title_page_confirmation(self, preview: str) -> bool:
        """
        询问用户是否为标题页（保留用于向后兼容）
        
        Args:
            preview: 页面预览文本
            
        Returns:
            bool: 用户确认结果
        """
        print(preview)
        print()
        
        while True:
            response = input("这是标题页吗？(y/n): ").strip().lower()
            if response in ['y', 'yes', '是', '确认']:
                return True
            elif response in ['n', 'no', '否', '不是']:
                return False
            else:
                print("请输入 y(是) 或 n(否)")
    
    def ask_user_merge_confirmation(self, title_page_title: str, next_page_title: str) -> bool:
        """
        询问用户是否合并页面（保留用于向后兼容）
        
        Args:
            title_page_title: 标题页标题
            next_page_title: 下一页标题
            
        Returns:
            bool: 用户确认结果
        """
        while True:
            response = input(f'是否与下一页"{next_page_title}"合并？(y/n): ').strip().lower()
            if response in ['y', 'yes', '是', '确认']:
                print("正在合并页面...")
                return True
            elif response in ['n', 'no', '否', '不合并']:
                return False
            else:
                print("请输入 y(是) 或 n(否)")
    
    def merge_title_with_content(self, title: str, content: str) -> str:
        """
        将标题与内容合并
        
        Args:
            title: 标题内容（可能是HTML或Markdown）
            content: 后续内容（Markdown格式）
            
        Returns:
            str: 合并后的内容
        """
        # 提取标题文本
        if '<' in title and '>' in title:
            # HTML格式标题
            title_text = re.sub(r'<[^>]+>', '', title).strip()
        elif title.startswith('#'):
            # Markdown格式标题，提取文本部分
            title_text = re.sub(r'^#+\s*', '', title).strip()
        else:
            # 纯文本标题
            title_text = title.strip()
        
        # 确保标题格式正确，并添加分页符分隔两页内容
        if title_text:
            merged_content = f"# {title_text}\n\n---\n\n{content}"
        else:
            merged_content = f"---\n\n{content}"
        
        return merged_content
    
    def ask_annotation_mode_preference(self, interactive: bool = True) -> bool:
        """
        询问用户注释处理模式偏好
        
        Args:
            interactive: 是否使用交互模式，False时默认使用内联模式
        
        Returns:
            bool: True为内联注释模式，False为页内跳转模式
        """
        if not interactive:
            # 非交互模式，默认使用内联注释模式
            return True
        
        print("\n注释处理模式选择：")
        print("=" * 30)
        print("1. 内联注释模式：将注释内容直接插入到正文中")
        print("   - 优点：阅读时无需跳转，注释内容直接可见")
        print("   - 缺点：可能打断阅读流畅性")
        print()
        print("2. 页内跳转模式：保持注释的跳转功能，注释移动到页面底部")
        print("   - 优点：保持原有的阅读体验和导航功能")
        print("   - 缺点：需要跳转查看注释内容")
        print()
        
        while True:
            response = input("请选择注释处理模式 (1=内联注释, 2=页内跳转): ").strip()
            
            if response == '1':
                print("已选择：内联注释模式")
                return True  # 内联模式
            elif response == '2':
                print("已选择：页内跳转模式")
                return False  # 页内跳转模式
            else:
                print("请输入 1 或 2")

    def process_content_files(self, files: List[ContentFile], annotation_processor=None, interactive: bool = True, md_filename_mapping: Dict[str, str] = None, output_mode: str = 'multi') -> List[MarkdownFile]:
        """
        处理所有内容文件

        Args:
            files: 内容文件列表
            annotation_processor: 注释处理器（可选）
            interactive: 是否使用交互模式
            md_filename_mapping: MD文件名映射（原始HTML名 → MD名）
            output_mode: 输出模式（'multi' 或 'single'）

        Returns:
            List[MarkdownFile]: 处理后的Markdown文件列表
        """
        from .utils import sanitize_filename

        # 收集所有疑似标题页
        potential_title_pages = self.collect_potential_title_pages(files)

        # 批量询问用户要合并哪些标题页
        if output_mode == 'single':
            # 单文件模式：跳过标题页合并询问
            pages_to_merge = set()
        else:
            # 多文件模式：原有逻辑
            pages_to_merge = set(self.ask_user_batch_merge_confirmation(files, potential_title_pages, interactive))

        markdown_files = []
        i = 0

        while i < len(files):
            current_file = files[i]

            # 跳过封面页
            if current_file.is_cover:
                i += 1
                continue

            # 转换当前文件
            markdown_content = self.convert_html_to_markdown(current_file.content, annotation_processor, current_file.title, current_file.path)

            # 获取文件名（使用传入的映射或回退逻辑）
            if md_filename_mapping and current_file.path in md_filename_mapping:
                filename = md_filename_mapping[current_file.path]
            else:
                # 回退逻辑（不应该执行到这里）
                safe_title = sanitize_filename(current_file.title)
                filename = f"{current_file.order:02d}_{safe_title}.md"

            # 检查是否需要合并
            if i in pages_to_merge and i + 1 < len(files):
                next_file = files[i + 1]
                if not next_file.is_cover:
                    print(f"正在合并: {current_file.title} → {next_file.title}")
                    next_markdown = self.convert_html_to_markdown(next_file.content, annotation_processor, next_file.title, next_file.path)
                    markdown_content = self.merge_title_with_content(markdown_content, next_markdown)

                    # 使用当前文件的标题（文件名已在上面获取）
                    title = current_file.title

                    # 跳过下一个文件
                    i += 2
                else:
                    # 下一个是封面页，不合并
                    title = current_file.title
                    i += 1
            else:
                # 不合并，按正常页面处理
                title = current_file.title
                i += 1

            # 提取图片引用
            images = self._extract_image_references(markdown_content)

            markdown_file = MarkdownFile(
                filename=filename,
                content=markdown_content,
                title=title,
                images=images
            )
            
            markdown_files.append(markdown_file)
        
        return markdown_files
    
    def _extract_image_references(self, markdown_content: str) -> List[str]:
        """
        从Markdown内容中提取图片引用
        
        Args:
            markdown_content: Markdown内容
            
        Returns:
            List[str]: 图片路径列表
        """
        # 匹配Markdown图片语法
        image_pattern = r'!\[.*?\]\(([^)]+)\)'
        matches = re.findall(image_pattern, markdown_content)
        
        return matches