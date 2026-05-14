"""
注释和超链接处理
Annotation and hyperlink processing
"""

import re
from typing import Dict, Optional, List, Set, Tuple
from urllib.parse import urlparse, unquote

from .utils import extract_text_content


class AnnotationProcessor:
    """注释处理器"""
    
    def __init__(self, language: str, content_files: Dict[str, str]):
        """
        初始化注释处理器
        
        Args:
            language: 检测到的语言
            content_files: 内容文件映射 {文件路径: 内容}
        """
        self.language = language
        self.content_files = content_files
        self._annotations_cache = {}
        self._used_annotations = set()  # 跟踪已使用的注释ID
        self._annotation_files = set()  # 跟踪注释文件，这些文件不应生成独立的Markdown
        self._use_inline_mode = True  # 默认使用内联模式
        self._processing_mode_set = False  # 标记是否已设置处理模式
    
    def set_processing_mode(self, use_inline_mode: bool) -> None:
        """
        设置注释处理模式
        
        Args:
            use_inline_mode: True为内联注释模式，False为页内跳转模式
        """
        self._use_inline_mode = use_inline_mode
        self._processing_mode_set = True
    
    def get_processing_mode(self) -> bool:
        """
        获取当前注释处理模式
        
        Returns:
            bool: True为内联注释模式，False为页内跳转模式
        """
        return self._use_inline_mode
    
    def is_processing_mode_set(self) -> bool:
        """
        检查是否已设置处理模式
        
        Returns:
            bool: 是否已设置处理模式
        """
        return self._processing_mode_set
    
    def convert_annotation_images_to_numbers(self, html_content: str) -> str:
        """
        将注释载体图片转换为文本标记

        将图片形式的注释标记（如注、注释编号图标）转换为文本标记。
        例如：<a href="#note1"><img src="note-icon.png"></a> → <a href="#note1">[1]</a>

        Args:
            html_content: HTML内容

        Returns:
            str: 处理后的HTML内容
        """
        annotation_counter = 0

        def replace_annotation_image(match):
            nonlocal annotation_counter
            full_tag = match.group(0)
            href = match.group(1)
            link_content = match.group(2)

            # 检查链接内容是否包含载体图片
            # 注意：这里不需要判断是否为注释链接，后续的AB配对算法会自动处理
            if self._contains_carrier_image(link_content):
                annotation_counter += 1
                # 创建文本标记
                anchor_id = f"note-{annotation_counter}"
                return f'<a href="#{anchor_id}">[{annotation_counter}]</a>'

            return full_tag

        # 替换包含载体图片的链接
        updated_content = re.sub(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            replace_annotation_image,
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )

        return updated_content

    def extract_annotations(self, html_content: str) -> Dict[str, str]:
        """
        从HTML内容中提取注释（调用统一的范围查找方法）

        【重构】使用与页内跳转模式完全相同的查找算法

        Args:
            html_content: HTML内容

        Returns:
            Dict[str, str]: 注释ID到注释内容的映射
        """
        annotations = {}

        # 【重构】收集当前文件的所有锚点
        all_anchors = {}
        pattern = r'<a[^>]*\s+id=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(pattern, html_content, re.IGNORECASE):
            anchor_id = match.group(1)
            full_tag = match.group(0)
            position = match.start()

            # 检查是否有href
            href_match = re.search(r'href=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
            has_href = href_match is not None
            href = href_match.group(1) if has_href else None

            all_anchors[anchor_id] = {
                'tag': full_tag,
                'pos': position,
                'has_href': has_href,
                'href': href
            }

        # 【重构】对每个注释ID，使用统一的 _find_annotation_range 方法提取内容
        for anchor_id in all_anchors.keys():
            # 只处理注释ID（排除导航链接）
            if not self._is_annotation_id(anchor_id):
                continue

            # 调用统一的范围查找方法
            range_result = self._find_annotation_range(
                anchor_id, html_content, all_anchors
            )

            if range_result:
                start_pos, end_pos, annotation_content = range_result

                # 提取文本内容
                if annotation_content:
                    clean_content = extract_text_content(annotation_content)
                    if clean_content and clean_content.strip():
                        annotations[anchor_id] = clean_content.strip()

        return annotations
    
    def process_all_annotations_globally(self):
        """
        第一阶段：全局处理所有注释
        根据设置的模式选择内联注释或页内跳转处理
        """
        if not self._processing_mode_set:
            raise ValueError("注释处理模式未设置，请先调用set_processing_mode()方法")

        # 步骤0：预处理 - 将图片形式的注释A转换为文本标记
        for file_path in list(self.content_files.keys()):
            self.content_files[file_path] = self.convert_annotation_images_to_numbers(
                self.content_files[file_path]
            )

        # 步骤1：根据模式处理注释
        if self._use_inline_mode:
            self._process_inline_annotations()
        else:
            self._process_page_jump_annotations()
    
    def _remove_annotation_number(self, b_content: str) -> str:
        """
        从注释内容中移除序号

        通过检测第一个<a>标签：
        1. 内容是否很短（≤10字符）
        2. </a>后是否有其他内容
        两个条件都满足，确认是序号，删除该<a>标签

        Args:
            b_content: 注释的完整HTML内容

        Returns:
            str: 删除序号后的HTML内容
        """
        import re

        # 找到第一个<a>标签
        a_pattern = r'<a[^>]*>(.*?)</a>'
        match = re.search(a_pattern, b_content, re.DOTALL)

        if not match:
            return b_content

        # 提取<a>标签内容
        a_content = match.group(1).strip()
        a_content_text = extract_text_content(a_content).strip()

        # 检查条件1：内容很短
        is_short = len(a_content_text) <= 10

        # 检查条件2：</a>后有内容
        after_a = b_content[match.end():]
        text_after = extract_text_content(after_a).strip()
        has_content_after = len(text_after) > 0

        # 两个条件都满足，确认是序号，删除
        if is_short and has_content_after:
            return b_content[:match.start()] + b_content[match.end():]

        return b_content

    def _process_inline_annotations(self):
        """
        内联注释模式：把B的内容移动到A的位置，然后根据ID删除所有B

        逻辑：
        1. 找到所有A-B注释对
        2. 用格式化后的B内容替换A标签（不分同页/跨页）
        3. 根据ID删除所有B（最后统一删除）
        """
        # 步骤1: 通过关键词识别可能包含注释的文件
        files_with_annotations = self._identify_files_with_annotations()

        # 步骤2: 通过href-id配对验证，确定所有真正的A-B注释对
        annotation_pairs = self._find_annotation_pairs_generic(files_with_annotations)

        if not annotation_pairs:
            return

        # 步骤3: 替换所有A（不分同页/跨页，统一处理）
        from collections import defaultdict

        # 按a_file分组
        by_file = defaultdict(list)
        for pair in annotation_pairs:
            a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content = pair
            by_file[a_file].append(pair)

        # 每个文件内按a_start倒序排序（从后往前替换）
        for file_path in by_file:
            by_file[file_path].sort(key=lambda x: x[3], reverse=True)  # x[3]是a_start

        # 替换所有A
        for pair in [p for pairs in by_file.values() for p in pairs]:
            a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content = pair
            # 从b_content中删除序号
            b_content_clean = self._remove_annotation_number(b_content)
            # 提取纯文本
            text = extract_text_content(b_content_clean)
            if not text:
                continue
            # 按格式化处理
            note_format = self.get_annotation_format()
            b_text = note_format.format(text)
            # 替换A
            a_file_content = self.content_files[a_file]
            a_file_content = a_file_content[:a_start] + b_text + a_file_content[a_end:]
            self.content_files[a_file] = a_file_content

        # 步骤4: 根据ID删除所有B
        self._remove_all_annotations_by_id(annotation_pairs)

        # 步骤5: 处理所有剩余链接
        for file_path, file_content in self.content_files.items():
            updated_content = self.convert_remaining_links(file_content, current_file_path=file_path)
            self.content_files[file_path] = updated_content

    def _remove_all_annotations_by_id(self, annotation_pairs):
        """
        根据ID删除所有B标签（不依赖之前保存的位置）

        Args:
            annotation_pairs: 注释对列表
        """
        import re
        from collections import defaultdict

        # 按文件分组需要删除的B
        files_to_clean = defaultdict(list)

        # 收集所有需要删除的B的ID
        for pair in annotation_pairs:
            a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content = pair

            # 从a_href中提取B的ID（如 "text00026.html#footnote-1960-1" -> "footnote-1960-1"）
            from urllib.parse import urlparse
            from urllib.parse import unquote
            parsed = urlparse(unquote(a_href))
            b_id = parsed.fragment  # 提取fragment部分

            if b_id:
                files_to_clean[b_file].append(b_id)

        # 对每个文件，根据ID查找并删除B
        for file_path, b_ids in files_to_clean.items():
            if file_path not in self.content_files:
                continue

            html_content = self.content_files[file_path]

            # 按B在文件中的位置倒序删除（从后往前）
            b_positions = []
            for b_id in b_ids:
                # 查找id="b_id"或id='b_id'的位置
                pattern_double = f'id="{b_id}"'
                pattern_single = f"id='{b_id}'"

                pos_double = html_content.find(pattern_double)
                pos_single = html_content.find(pattern_single)

                # 取找到的位置
                if pos_double != -1 and pos_single != -1:
                    pos = min(pos_double, pos_single)
                elif pos_double != -1:
                    pos = pos_double
                elif pos_single != -1:
                    pos = pos_single
                else:
                    continue  # 没找到，跳过

                b_positions.append((pos, b_id))

            # 按位置倒序排序
            b_positions.sort(key=lambda x: x[0], reverse=True)

            # 从后往前删除
            for pos, b_id in b_positions:
                # 找到B的完整标签（从id位置往前找到标签开始）
                # 查找pos之前的最后一个'<'
                tag_start = html_content.rfind('<', 0, pos)
                if tag_start == -1:
                    continue

                # 查找标签结束（找到匹配的>）
                tag_end = html_content.find('>', pos)
                if tag_end == -1:
                    continue

                # 现在需要找到整个B内容的结束位置
                # 找到B标签的闭合标签（通常是</a>或</div>）
                # 使用_find_annotation_range的逻辑来找到完整的B范围

                # 简化方案：找到<div class="footnote">...</div>的范围
                # 从tag_start往前找，看是否有<div>
                search_start = tag_start
                div_start = html_content.rfind('<div', 0, search_start)

                # 如果找到了<div>，找对应的</div>
                if div_start != -1:
                    # 从div_start开始找第一个</div>
                    div_end = html_content.find('</div>', div_start)
                    if div_end != -1:
                        # 删除整个div
                        html_content = html_content[:div_start] + html_content[div_end + 6:]
                        print(f"  已删除B (ID={b_id}): 位置 {div_start}-{div_end + 6}")
                        continue

                # 如果找不到<div>，就只删除<a>标签
                # 找到</a>
                a_end = html_content.find('</a>', pos)
                if a_end != -1:
                    html_content = html_content[:tag_start] + html_content[a_end + 4:]
                    print(f"  已删除B (ID={b_id}): 位置 {tag_start}-{a_end + 4}")

            # 清理多余的空行
            html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)

            self.content_files[file_path] = html_content
    
    def _process_page_jump_annotations(self):
        """
        页内跳转注释模式：将跨页的B（注释内容）移动到A（注释标记）所在页面的底部

        新方案：
        1. 区分同页/跨页注释（看A的href是否指向当前页面）
        2. 跨页注释：完整复制B到A所在页面底部，删除原B
        3. 同页注释：不挪动
        4. 修改所有A和B的href，去掉文件名，变成单纯页内跳转
        5. 不创建任何新ID，保留原始ID
        """
        # 步骤1: 通过关键词识别可能包含注释的文件
        files_with_annotations = self._identify_files_with_annotations()

        # 步骤2: 通过href-id配对验证，确定所有真正的A-B注释对
        annotation_pairs = self._find_annotation_pairs_generic(files_with_annotations)

        if not annotation_pairs:
            return

        # 按页面分组：需要添加B的页面（跨页注释）
        pages_to_add_b = {}

        for a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content in annotation_pairs:
            # 判断是同页还是跨页
            is_cross_page = (a_file != b_file)

            # 对于跨页注释，将B添加到A所在页面底部
            if is_cross_page:
                if a_file not in pages_to_add_b:
                    pages_to_add_b[a_file] = []
                # 完整保留B的内容（包括原始<a>标签，不修改href）
                pages_to_add_b[a_file].append(b_content)

        # 3. 将跨页注释的B添加到A所在页面底部
        for file_path, b_contents in pages_to_add_b.items():
            if file_path in self.content_files:
                content = self.content_files[file_path]

                # 直接添加B内容到页面底部（不修改href）
                footer_html = "\n\n<hr>\n\n"
                for b_content in b_contents:
                    # 保持原始B内容，不修改href
                    footer_html += b_content + "\n\n"

                # 添加到</body>之前
                body_end_pattern = r'</body>'
                body_end_match = re.search(body_end_pattern, content, re.IGNORECASE)
                if body_end_match:
                    insert_pos = body_end_match.start()
                    content = content[:insert_pos] + footer_html + content[insert_pos:]
                else:
                    content = content + footer_html

                self.content_files[file_path] = content

        # 4. 只删除跨页注释的原B（同页注释保留在原位置）
        # 过滤出跨页注释对
        cross_page_pairs = [
            (a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content)
            for a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content in annotation_pairs
            if a_file != b_file  # 只删除跨页注释的原B
        ]
        print(f"[DEBUG] 总注释对数: {len(annotation_pairs)}, 跨页注释对数: {len(cross_page_pairs)}")
        self._remove_moved_annotations(cross_page_pairs)

        # 7. 【统一处理】让 convert_remaining_links 处理所有页内跳转链接
        for file_path, file_content in self.content_files.items():
            updated_content = self.convert_remaining_links(file_content, current_file_path=file_path)
            self.content_files[file_path] = updated_content

    def _identify_files_with_annotations(self):
        """
        步骤1: 通过关键词在HTML全文中搜索，识别可能包含注释的文件
        在HTML的任意文本中搜索关键词（不限于标签属性）

        Returns:
            Set[str]: 可能包含注释的文件路径集合
        """
        # 定义注释关键词
        annotation_keywords = ['note', 'footnote', '注释', '注']

        files_with_annotations = set()

        for file_path, file_content in self.content_files.items():
            # 在HTML全文中搜索关键词（大小写不敏感）
            content_lower = file_content.lower()

            # 检查是否包含任何关键词
            for keyword in annotation_keywords:
                if keyword.lower() in content_lower:
                    files_with_annotations.add(file_path)
                    break

        return files_with_annotations

    def _find_annotation_pairs_generic(self, candidate_files):
        """
        步骤2: 通过href-id对应关系验证，确定所有真正的A-B注释对
        处理同页注释和跨页注释

        核心逻辑：
        1. 全文搜索关键词，找到所有包含关键词的位置
        2. 从关键词位置附近收集可能相关的<a>标签
        3. 从收集的标签中识别相互指向的AB对
        4. 判断A/B并记录完整范围

        Args:
            candidate_files: 可能包含注释的文件路径集合

        Returns:
            List[Tuple]: (a_file, a_href, a_full_tag, a_start, a_end,
                          b_file, b_content, b_start, b_end, raw_content) 的列表
        """
        annotation_pairs = []

        # 步骤1: 全文搜索关键词，收集相关位置
        keywords = ['note', 'footnote', '注释', '注']
        keyword_positions = []  # (file_path, position, keyword, context)

        for file_path in candidate_files:
            file_content = self.content_files[file_path]

            # 搜索每个关键词
            for keyword in keywords:
                # 不区分大小写搜索
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                for match in pattern.finditer(file_content):
                    # 记录关键词位置和前后各50个字符的上下文
                    start = match.start()
                    context_start = max(0, start - 50)
                    context_end = min(len(file_content), start + len(keyword) + 50)
                    context = file_content[context_start:context_end]

                    keyword_positions.append({
                        'file': file_path,
                        'pos': start,
                        'keyword': keyword,
                        'context': context
                    })

        if not keyword_positions:
            print("[DEBUG] 未找到任何关键词")
            return []

        print(f"[DEBUG] 找到 {len(keyword_positions)} 个关键词位置")

        # 步骤2: 从关键词位置收集相关<a>标签
        candidate_links = []  # {file, href, id, full_tag, position}
        seen_links = set()  # 避免重复

        for kw_pos in keyword_positions:
            file_path = kw_pos['file']
            file_content = self.content_files[file_path]
            pos = kw_pos['pos']

            # 查找关键词附近的<a>标签（前后200个字符内）
            search_start = max(0, pos - 200)
            search_end = min(len(file_content), pos + 200)
            search_area = file_content[search_start:search_end]

            # 在搜索区域内查找所有<a>标签
            link_pattern = re.compile(r'<a[^>]*>', re.IGNORECASE)
            for match in link_pattern.finditer(search_area):
                full_tag = match.group(0)
                abs_pos = search_start + match.start()

                # 生成唯一标识
                link_id = f"{file_path}:{abs_pos}:{full_tag[:50]}"
                if link_id in seen_links:
                    continue
                seen_links.add(link_id)

                # 提取href和id
                href_match = re.search(r'href=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
                id_match = re.search(r'id=["\']([^"\']+)["\']', full_tag, re.IGNORECASE)

                href = href_match.group(1) if href_match else None
                anchor_id = id_match.group(1) if id_match else None

                # 只保留有href或id的标签
                if href or anchor_id:
                    candidate_links.append({
                        'file': file_path,
                        'href': href,
                        'id': anchor_id,
                        'tag': full_tag,
                        'pos': abs_pos
                    })

        print(f"[DEBUG] 从关键词位置收集到 {len(candidate_links)} 个候选链接")

        # 步骤3: 从候选链接中找出AB对
        # 只保留同时有href和id的链接
        valid_links = [link for link in candidate_links if link['href'] and link['id']]
        print(f"[DEBUG] 其中同时有href和id的链接: {len(valid_links)} 个")

        # 找相互指向的链接对
        pairs = []
        matched = set()

        print(f"[DEBUG] 开始配对检查，有效链接数: {len(valid_links)}")

        for i, link_a in enumerate(valid_links):
            if i in matched:
                continue

            # 解析link_a的href
            parsed = urlparse(unquote(link_a['href']))
            if not parsed.fragment:
                continue

            print(f"[DEBUG] [{i}] link_a: href={link_a['href']}, id={link_a['id']}, file={link_a['file'][:50]}")

            # 在valid_links中找目标锚点
            for j, link_b in enumerate(valid_links):
                if j in matched:
                    continue

                print(f"[DEBUG]   [{j}] link_b: href={link_b['href']}, id={link_b['id']}")

                # 检查link_b的id是否匹配link_a的href的fragment
                if link_b['id'] != parsed.fragment:
                    continue

                print(f"[DEBUG]   [OK] ID匹配: {link_b['id']} == {parsed.fragment}")

                # 检查link_b的href是否指回link_a的id
                if not link_b['href']:
                    print(f"[DEBUG]   [X] link_b没有href")
                    continue

                parsed_b = urlparse(unquote(link_b['href']))
                if not parsed_b.fragment:
                    print(f"[DEBUG]   [X] link_b的href没有fragment")
                    continue

                if parsed_b.fragment != link_a['id']:
                    print(f"[DEBUG]   [X] fragment不匹配: {parsed_b.fragment} != {link_a['id']}")
                    continue

                print(f"[DEBUG]   [FOUND] 找到一对！")
                # 找到一对！
                matched.add(i)
                matched.add(j)
                pairs.append((link_a, link_b))
                break

        print(f"[DEBUG] 找到 {len(pairs)} 对相互指向的链接")

        # 步骤4: 判断A和B并收集信息
        b_info_collected = []  # 收集所有B的初步信息
        for link_a, link_b in pairs:
            # 提取文本内容（<a>和</a>之间的内容）
            a_text_match = re.search(r'>([^<]+)</a>', link_a['tag'], re.IGNORECASE)
            b_text_match = re.search(r'>([^<]+)</a>', link_b['tag'], re.IGNORECASE)

            a_text = a_text_match.group(1) if a_text_match else ""
            b_text = b_text_match.group(1) if b_text_match else ""

            # 判断标准：出现位置和文本长度
            if link_a['pos'] < link_b['pos'] and len(a_text) <= len(b_text):
                # link_a是A，link_b是B
                a_info = link_a
                b_info = link_b
            elif link_b['pos'] < link_a['pos'] and len(b_text) <= len(a_text):
                # link_b是A，link_a是B
                a_info = link_b
                b_info = link_a
            else:
                # 无法判断，跳过
                print(f"[WARNING] 无法判断AB对: {link_a['href']} vs {link_b['href']}")
                continue

            # 收集B的初步信息（后面统一处理）
            b_info_collected.append({
                'a_info': a_info,
                'b_info': b_info
            })

        # === 第二轮：计算所有B的完整范围 ===
        # 按文件分组，便于处理同一个文件中的多个注释
        by_file = {}
        for item in b_info_collected:
            b_file = item['b_info']['file']
            if b_file not in by_file:
                by_file[b_file] = []
            by_file[b_file].append(item)

        # 对每个文件的注释进行处理
        for b_file, items in by_file.items():
            b_file_content = self.content_files[b_file]

            # 收集该文件的所有锚点
            all_anchors = self._collect_anchors_from_files({b_file})
            if b_file not in all_anchors:
                continue

            # 逐个处理注释
            for item in items:
                b_id = item['b_info']['id']
                range_result = self._find_annotation_range(
                    b_id, b_file_content, all_anchors[b_file]
                )
                if range_result:
                    b_start, b_end, b_content = range_result

                    # 计算raw_content（从b的id到下一个注释id）
                    # 获取该文件所有注释ID的位置
                    annotation_ids = [
                        aid for aid in all_anchors[b_file].keys()
                        if self._is_annotation_id(aid) and '-backlink' not in aid
                    ]
                    annotation_positions = []
                    for aid in annotation_ids:
                        if aid in all_anchors[b_file]:
                            annotation_positions.append((aid, all_anchors[b_file][aid]['pos']))
                    annotation_positions.sort(key=lambda x: x[1])

                    # 找到当前B的ID位置和下一个ID位置
                    b_id = item['b_info']['id']
                    current_index = -1
                    for i, (aid, pos) in enumerate(annotation_positions):
                        if aid == b_id:
                            current_index = i
                            break

                    # 确定raw_content的范围
                    if current_index >= 0 and current_index + 1 < len(annotation_positions):
                        next_pos = annotation_positions[current_index + 1][1]
                    else:
                        next_pos = len(b_file_content)

                    # 提取raw_content
                    raw_content = b_file_content[b_info['pos']:next_pos]

                    # 记录完整信息
                    a_info = item['a_info']
                    b_info = item['b_info']

                    # 计算完整的<a>标签结束位置（包括文本内容和</a>）
                    a_start = a_info['pos']
                    a_file_content_for_a = self.content_files[a_info['file']]
                    # 从a_start开始查找完整的</a>标签
                    closing_tag_pattern = re.compile(r'</a>', re.IGNORECASE)
                    closing_match = closing_tag_pattern.search(a_file_content_for_a[a_start:])
                    if closing_match:
                        a_end = a_start + closing_match.end()
                    else:
                        # 如果找不到</a>，使用tag长度作为fallback
                        a_end = a_start + len(a_info['tag'])

                    annotation_pairs.append((
                        a_info['file'],              # a_file
                        a_info['href'],              # a_href
                        a_info['tag'],               # a_full_tag
                        a_start,                     # a_start
                        a_end,                       # a_end
                        b_info['file'],              # b_file
                        b_content,                   # b_content
                        b_start,                     # b_start
                        b_end,                       # b_end
                        raw_content                  # raw_content
                    ))

        return annotation_pairs

    def _collect_anchors_from_files(self, file_paths):
        """
        从指定文件中收集所有锚点信息

        Args:
            file_paths: 文件路径集合

        Returns:
            Dict[file_path, Dict[anchor_id, anchor_info]]: 锚点信息
        """
        all_anchors = {}

        for file_path in file_paths:
            file_content = self.content_files[file_path]
            file_anchors = {}

            # 查找所有带id的<a>标签
            pattern = r'<a[^>]*\s+id=["\']([^"\']+)["\'][^>]*>'
            for match in re.finditer(pattern, file_content, re.IGNORECASE):
                anchor_id = match.group(1)
                full_tag = match.group(0)
                position = match.start()

                # 检查是否有href
                href_match = re.search(r'href=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
                has_href = href_match is not None
                href = href_match.group(1) if has_href else None

                file_anchors[anchor_id] = {
                    'tag': full_tag,
                    'pos': position,
                    'has_href': has_href,
                    'href': href
                }

            if file_anchors:
                all_anchors[file_path] = file_anchors

        return all_anchors

    def _extract_original_filename(self, file_path):
        """
        从文件路径中提取原始的EPUB文件名

        例如：
        - "C:/.../27_附录二_四种层次阅读的练习与测验.html" -> "text00026.html"
        - "C:/.../05_第一篇_阅读的层次-第一章_阅读的活力与艺术.html" -> "text00004.html"
        - "OEBPS/text00026.html" -> "text00026.html"

        Args:
            file_path: 文件路径（可能是重命名后的路径或原始路径）

        Returns:
            str: 原始文件名（如 "text00026.html"），如果不是重命名文件则返回None
        """
        # 标准化路径分隔符
        normalized_path = file_path.replace('\\', '/')

        # 提取文件名（包含路径的最后一部分）
        file_name = normalized_path.split('/')[-1]

        # 情况1：如果已经是原始格式 textXXXX.html，直接返回
        if re.match(r'^text\d+\.html$', file_name):
            return file_name

        # 情况2：如果路径中包含textXXXX.html（如OEBPS/text00026.html），提取并返回
        match = re.search(r'text\d+\.html', normalized_path)
        if match:
            return match.group(0)

        # 情况3：如果是重命名格式 XX_标题.html 或 XX_标题.md
        # 提取开头的数字部分
        match = re.match(r'^(\d+)_', file_name)
        if match:
            try:
                # 提取数字部分（如 27 或 05）
                number = int(match.group(1))

                # 转换为原始文件名：数字减1，然后格式化为text000XX.html
                # 例如：27 -> text00026.html, 05 -> text00004.html
                original_number = number - 1
                original_filename = f"text{original_number:05d}.html"

                return original_filename
            except (ValueError, IndexError):
                pass

        return None

    def _find_annotation_range(self, annotation_id, html_content, all_anchors):
        """
        通过锚点位置确定注释的完整范围（包含外层容器）

        Args:
            annotation_id: 注释ID（如footnote-1960-1）
            html_content: HTML内容
            all_anchors: 该文件中所有锚点的信息

        Returns:
            Optional[Tuple[int, int, str]]: (start_pos, end_pos, b_content) 或 None
        """
        if annotation_id not in all_anchors:
            return None

        current_anchor = all_anchors[annotation_id]
        id1_pos = current_anchor['pos']

        # === 步骤1: 找到 id1 和 id2 的位置，提取 raw_content ===
        # 只考虑注释ID（排除backlink和其他导航ID）
        annotation_ids = [
            aid for aid in all_anchors.keys()
            if self._is_annotation_id(aid) and '-backlink' not in aid
        ]

        # 按位置排序所有注释锚点
        annotation_positions = sorted(
            [(aid, all_anchors[aid]['pos']) for aid in annotation_ids],
            key=lambda x: x[1]
        )

        # 找到当前注释锚点的索引
        current_index = -1
        for i, (aid, pos) in enumerate(annotation_positions):
            if aid == annotation_id:
                current_index = i
                break

        # 确定 id2 位置
        if current_index >= 0 and current_index + 1 < len(annotation_positions):
            id2_pos = annotation_positions[current_index + 1][1]
        else:
            # 最后一个注释，id2_pos 到文件末尾
            id2_pos = len(html_content)

        # 提取 raw_content（id1 到 id2）
        raw_content = html_content[id1_pos:id2_pos]

        # === 步骤2: 从后往前找停止符，通过HTML语法逆推起始符 ===
        # 找到 raw_content 中所有停止符（</tag>）的位置
        # 过滤掉文件级标签（html, body, head等），只保留内容结构标签
        excluded_tags = {'html', 'body', 'head', 'meta', 'title', 'link', 'style', 'script'}
        closing_tags = []
        for match in re.finditer(r'</(\w+)>', raw_content):
            tag_name = match.group(1)
            if tag_name.lower() in excluded_tags:
                continue  # 跳过文件级标签
            tag_end_pos = match.end()  # 停止符的结束位置
            closing_tags.append({
                'tag': tag_name,
                'pos': tag_end_pos
            })

        # 只处理最后一个停止符（raw_content 中最后的停止符）
        if closing_tags:
            # 获取最后一个停止符
            last_closing_tag = closing_tags[-1]
            tag_name = last_closing_tag['tag']
            stop_pos = last_closing_tag['pos']  # 停止符在 raw_content 中的结束位置

            # 计算停止符的绝对位置
            stop_absolute_pos = id1_pos + stop_pos

            # === 阶段1: 在 raw_content 中从 stop_pos 向后退，用计数法找起始符 ===
            tag_count = 1
            found_start_offset = -1
            pos = stop_pos - 1  # 从停止符之前开始，在 raw_content 内向后退

            while pos >= 0:
                # 检查是否有结束标签
                if raw_content[pos:pos+len(f'</{tag_name}>')] == f'</{tag_name}>':
                    tag_count += 1
                    pos -= 1
                    continue

                # 检查是否有开始标签（需要匹配完整标签，如 <div class="footnote">）
                # 先检查是否有开始标签的起始标记 '<tag_name'
                start_marker = f'<{tag_name}'
                if raw_content[pos:pos+len(start_marker)] == start_marker:
                    # 检查这个位置后面是否有 '>', 确认是完整标签
                    gt_pos = raw_content.find('>', pos)
                    if gt_pos != -1:
                        tag_count -= 1
                        if tag_count == 0:
                            found_start_offset = pos
                            break
                        pos -= 1
                        continue

                pos -= 1

            # 如果在 raw_content 中找到了起始符
            if found_start_offset != -1:
                start_pos = id1_pos + found_start_offset
                end_pos = stop_absolute_pos
                b_content = html_content[start_pos:end_pos]

                print(f"[DEBUG] 注释 {annotation_id}:")
                print(f"[DEBUG]   停止符: </{tag_name}> at {stop_pos}")
                print(f"[DEBUG]   在raw_content中找到起始符，位置: {found_start_offset}")
                print(f"[DEBUG]   start_pos: {start_pos}, end_pos: {end_pos}")

                return start_pos, end_pos, b_content

            # === 阶段2: 在 raw_content 中没找到，说明起始符在 id1 之前 ===
            # 从 id1 位置开始向后退，用计数法找起始符
            tag_count = 1
            found_start_absolute = -1
            pos = id1_pos - 1  # 从 id1 之前开始

            while pos >= 0:
                # 检查是否有结束标签
                if html_content[pos:pos+len(f'</{tag_name}>')] == f'</{tag_name}>':
                    tag_count += 1
                    pos -= 1
                    continue

                # 检查是否有开始标签
                start_marker = f'<{tag_name}'
                if html_content[pos:pos+len(start_marker)] == start_marker:
                    gt_pos = html_content.find('>', pos)
                    if gt_pos != -1:
                        tag_count -= 1
                        if tag_count == 0:
                            found_start_absolute = pos
                            break
                        pos -= 1
                        continue

                pos -= 1

            if found_start_absolute != -1:
                start_pos = found_start_absolute
                end_pos = stop_absolute_pos
                b_content = html_content[start_pos:end_pos]

                print(f"[DEBUG] 注释 {annotation_id}:")
                print(f"[DEBUG]   停止符: </{tag_name}> at {stop_pos}")
                print(f"[DEBUG]   在id1之前找到起始符，位置: {found_start_absolute}")
                print(f"[DEBUG]   start_pos: {start_pos}, end_pos: {end_pos}")

                return start_pos, end_pos, b_content


        # 如果没找到，使用 id1-id2 的原始范围
        print(f"[WARNING] 注释 {annotation_id} 未找到完整结构，使用 id1-id2 范围")
        return id1_pos, id2_pos, raw_content

    def _collect_related_annotation_ids(self, html_content: str, current_id: str) -> list:
        """
        从HTML内容中收集与指定ID相关的注释ID（按文档顺序）
        通过分析当前ID的命名模式，推断并收集所有同系列的注释ID

        Args:
            html_content: HTML内容
            current_id: 当前注释ID（如 footnote-1960-1）

        Returns:
            list: 相关注释ID列表（按在文档中出现的顺序）
        """
        # 从当前ID提取模式
        # 例如：footnote-1960-1 -> prefix='footnote-1960-', current_num=1
        # 或者：note1 -> prefix='note', current_num=1

        # 尝试匹配带数字后缀的模式（如 footnote-1960-1, note2 等）
        match = re.match(r'^(.*?)(\d+)$', current_id)
        if match:
            prefix = match.group(1)
            current_num = match.group(2)

            # 查找所有符合该模式的ID
            pattern = rf'<a[^>]*\s+id=["\']({re.escape(prefix)}\d+)["\'][^>]*>'
            matches = re.findall(pattern, html_content, re.IGNORECASE)

            # 过滤掉backlink
            annotation_ids = [m for m in matches if '-backlink' not in m.lower()]

            return annotation_ids
        else:
            # 如果没有数字模式，返回空列表（fallback到使用容器结束标签）
            return []

    def _resolve_file_path(self, path):
        """
        解析文件路径，找到对应的实际文件
        
        Args:
            path: 相对路径
            
        Returns:
            str: 实际文件路径或None
        """
        # 清理路径
        clean_path = path.replace('../', '').replace('./', '')
        
        # 在content_files中查找匹配的文件
        for file_path in self.content_files.keys():
            if file_path.endswith(clean_path) or clean_path in file_path:
                return file_path
        
        return None

    def _remove_moved_annotations(self, annotation_pairs):
        """
        从原来的页面中删除已移动的注释内容（调用统一的范围查找方法）

        Args:
            annotation_pairs: 注释对列表
        """
        # 按文件分组需要删除的注释ID
        files_to_clean = {}

        # 按文件分组需要删除的注释位置（直接使用保存的位置，不重新搜索）
        files_to_delete_from = {}

        for a_file, a_href, a_full_tag, a_start, a_end, b_file, b_content, b_start, b_end, raw_content in annotation_pairs:
            # 判断是否为跨页注释（传入的annotation_pairs已经过滤过，都是跨页注释）
            # 但这里需要再次检查，避免意外删除
            print(f"[DEBUG] a_file={a_file}, b_file={b_file}, a_href={a_href[:50]}")

            # 直接删除B文件中的B内容（不再判断，因为传入的都是跨页注释）
            if b_file not in files_to_delete_from:
                files_to_delete_from[b_file] = []
            files_to_delete_from[b_file].append((b_start, b_end, 'B'))

        # 从对应文件中删除注释元素（直接使用保存的位置）
        for file_path, delete_ranges in files_to_delete_from.items():
            if file_path not in self.content_files:
                continue

            html_content = self.content_files[file_path]

            # 按位置从后往前删除，避免位置偏移
            delete_ranges.sort(key=lambda x: x[0], reverse=True)

            for start_pos, end_pos, tag_type in delete_ranges:
                # 使用字符串切片删除
                html_content = html_content[:start_pos] + html_content[end_pos:]
                print(f"  已删除{tag_type}: 位置 {start_pos}-{end_pos}")

            # 清理多余的空行
            html_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', html_content)

            self.content_files[file_path] = html_content
    
    def convert_remaining_links(self, content: str, is_toc_page: bool = False, current_file_path: str = "") -> str:
        """
        处理注释后的所有剩余链接

        注释处理完成后，所有注释都已经是页内跳转格式（back-N ↔ note-N）
        此方法统一处理剩余的所有链接类型

        Args:
            content: 原始HTML内容
            is_toc_page: 是否为目录页面（已废弃，保留参数以兼容现有调用）
            current_file_path: 当前文件路径

        Returns:
            str: 转换后的HTML内容
        """
        # 步骤1：收集所有href中的锚点ID
        href_pattern = re.compile(r'href=["\']#([^"\']+)["\']', re.IGNORECASE)
        anchor_ids = set(href_pattern.findall(content))

        if anchor_ids:
            print(f"[DEBUG] convert_remaining_links: 收集到 {len(anchor_ids)} 个锚点ID: {anchor_ids}")

        # 步骤2：保护所有被链接指向的锚点标签（任何标签，不限于<a>）
        for anchor_id in anchor_ids:
            # 匹配 id="xxx" 或 id='xxx'，在任何标签中
            # 使用正则匹配整个标签，并在标签前插入KIRO保护标记
            id_pattern = re.compile(
                r'(<\w+[^>]*?)\s+(id=["\']' + re.escape(anchor_id) + r'["\'])([^>]*>)',
                re.IGNORECASE
            )

            def protect_anchor_tag(match):
                tag_start = match.group(1)  # 标签开始部分（如 <li class="xxx"）
                id_attr = match.group(2)    # id属性（如 id="df-1"）
                tag_end = match.group(3)    # 标签结束部分（如 >）
                # 在整个标签前插入KIRO保护标记
                return f'KIRO_ANCHOR_START_{anchor_id}_KIRO_ANCHOR_END{tag_start} {id_attr}{tag_end}'

            content = id_pattern.sub(protect_anchor_tag, content)

        # 步骤3：处理<a>标签
        def replace_link(match):
            full_tag = match.group(0)
            href = match.group(1)
            link_text = match.group(2)

            # 解析URL
            parsed = urlparse(href)

            # 检查是否有id属性（需要保留锚点）
            id_match = re.search(r'\s+id=["\']([^"\']+)["\']', full_tag, re.IGNORECASE)

            # === 情况1: 有锚点ID - 需要保留 ===
            if id_match:
                element_id = id_match.group(1)

                # 生成KIRO标记来保留锚点，html2text会保留纯文本
                anchor_target = f'KIRO_ANCHOR_START_{element_id}_KIRO_ANCHOR_END'
                link_part = f'KIRO_LINK_START[{link_text}]({href})KIRO_LINK_END'
                return f'{anchor_target}{link_part}'

            # === 情况2: 没有锚点ID ===
            # 外部链接：直接转Markdown
            if parsed.scheme in ['http', 'https', 'ftp', 'mailto']:
                return f'[{link_text}]({href})'

            # 跨文件链接：保持HTML格式（后续LinkProcessor会更新文件名）
            if parsed.path:
                return f'<a href="{href}">{link_text}</a>'

            # 单文件锚点链接：也保持HTML格式（页内跳转需要保留锚点）
            if parsed.fragment:
                return f'<a href="{href}">{link_text}</a>'

            # 其他情况：保持原样
            return full_tag

        # 匹配所有<a>标签
        content = re.sub(
            r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            replace_link,
            content,
            flags=re.IGNORECASE | re.DOTALL
        )

        return content

    def _mark_annotation_as_used(self, href: str):
        """
        标记注释为已使用
        只标记真正的注释ID，不标记导航锚点ID
        
        Args:
            href: 注释链接
        """
        # 解析链接获取锚点ID
        parsed = urlparse(unquote(href))
        if parsed.fragment and self._is_annotation_id(parsed.fragment):
            self._used_annotations.add(parsed.fragment)
    
    def _remove_all_used_annotations(self):
        """
        删除所有已使用的注释原文B（调用统一的范围查找方法）
        只删除真正的注释锚点，保留导航锚点
        """
        if not self._used_annotations:
            return

        # 收集所有需要处理的文件的锚点信息
        files_with_anchors = self._collect_anchors_from_files(set(self.content_files.keys()))

        # 遍历所有文件，删除已使用的注释
        for file_path, file_content in self.content_files.items():
            updated_content = file_content

            # 获取该文件的所有锚点信息
            file_anchors = files_with_anchors.get(file_path, {})

            # 收集所有要删除的范围
            ranges_to_remove = []

            for annotation_id in self._used_annotations:
                # 检查这个ID是否真的是注释ID（包含注释关键词）
                if not self._is_annotation_id(annotation_id):
                    continue  # 跳过非注释ID，保留导航锚点

                # 【重构】调用统一的范围查找方法（包含容器）
                range_result = self._find_annotation_range(
                    annotation_id, updated_content, file_anchors,
                    include_container=True  # 包含容器，删除整个<div>
                )

                if range_result:
                    start_pos, end_pos = range_result
                    ranges_to_remove.append((start_pos, end_pos))

            # 按位置从后往前删除，避免位置偏移
            ranges_to_remove.sort(key=lambda x: x[0], reverse=True)

            for start_pos, end_pos in ranges_to_remove:
                # 使用字符串切片删除
                updated_content = updated_content[:start_pos] + updated_content[end_pos:]

            # 清理多余的空行和空白
            updated_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', updated_content)
            updated_content = re.sub(r'^\s*\n', '', updated_content)  # 移除开头的空行
            updated_content = re.sub(r'\n\s*$', '', updated_content)  # 移除结尾的空行

            # 更新文件内容
            self.content_files[file_path] = updated_content
    
    def _is_annotation_id(self, element_id: str) -> bool:
        """
        检查ID是否为注释ID（而不是导航锚点ID）

        只识别原始EPUB中的注释ID（如footnote-1960-1）
        不识别我们自己生成的back-N和note-N

        Args:
            element_id: 元素ID

        Returns:
            bool: 是否为注释ID
        """
        if not element_id:
            return False

        # 不把我们自己生成的页内跳转锚点识别为注释ID
        # back-N, note-N 是我们生成的，应该像c1/d1一样被当作导航锚点处理
        if re.match(r'^(back|note)-\d+$', element_id):
            return False

        # 检查ID是否包含注释关键词
        id_lower = element_id.lower()
        annotation_keywords = ['footnote', 'annotation', 'ref', 'reference']

        # 如果ID包含注释关键词（但排除note-N格式），认为是注释ID
        if any(keyword in id_lower and keyword != 'note' for keyword in annotation_keywords):
            return True

        # 检查ID是否为纯数字（可能是简单的导航锚点）
        if element_id.isdigit() or (element_id.startswith('d') and element_id[1:].isdigit()):
            # 这种格式通常是导航锚点，不是注释
            return False

        return False
    
    def get_excluded_annotation_files(self) -> set:
        """
        获取应该排除的注释文件列表
        
        Returns:
            set: 应该排除生成Markdown的文件路径集合
        """
        return self._annotation_files
    
    def _clean_annotation_content(self, content: str) -> str:
        """
        清理注释内容中的超链接和其他格式
        
        Args:
            content: 原始注释内容
            
        Returns:
            str: 清理后的纯文本注释内容
        """
        if not content:
            return ""
        
        # 移除所有HTML标签，包括超链接
        # 先移除<a>标签但保留其文本内容
        content = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', content, flags=re.IGNORECASE | re.DOTALL)
        
        # 移除其他HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def _find_element_by_id(self, html_content: str, element_id: str,
                            known_annotation_ids: list = None) -> Optional[str]:
        """
        在HTML内容中查找指定ID的元素内容（调用统一的范围查找方法）

        Args:
            html_content: HTML内容
            element_id: 元素ID
            known_annotation_ids: 【已废弃】保留参数以兼容现有调用

        Returns:
            Optional[str]: 元素的文本内容
        """
        # DEBUG: 添加调试输出
        debug = 'footnote-1960-1' in element_id or 'footnote-1960-10' in element_id

        if debug:
            print(f'DEBUG _find_element_by_id(element_id="{element_id}")')
            if known_annotation_ids:
                print(f'  known_annotation_ids: {known_annotation_ids[:5]}...' if len(known_annotation_ids) > 5 else f'  known_annotation_ids: {known_annotation_ids}')

        # 【重构】使用统一的 _find_annotation_range 方法
        # 收集当前文件的所有锚点
        all_anchors = {}
        pattern = r'<a[^>]*\s+id=["\']([^"\']+)["\'][^>]*>'
        for match in re.finditer(pattern, html_content, re.IGNORECASE):
            anchor_id = match.group(1)
            full_tag = match.group(0)
            position = match.start()

            # 检查是否有href
            href_match = re.search(r'href=["\']([^"\']*)["\']', full_tag, re.IGNORECASE)
            has_href = href_match is not None
            href = href_match.group(1) if has_href else None

            all_anchors[anchor_id] = {
                'tag': full_tag,
                'pos': position,
                'has_href': has_href,
                'href': href
            }

        # 调用统一的范围查找方法
        range_result = self._find_annotation_range(
            element_id, html_content, all_anchors,
            include_container=False  # 不包含容器，只要内容
        )

        if not range_result:
            if debug:
                print(f'  ERROR: _find_annotation_range returned None for id="{element_id}"!')
            return None

        start_pos, end_pos = range_result
        annotation_content = html_content[start_pos:end_pos]

        if debug:
            print(f'  extraction range: {start_pos} to {end_pos} (length={end_pos-start_pos})')
            print(f'  extracted content preview: {annotation_content[:100]}...')

        # 提取文本内容
        if annotation_content:
            clean_content = extract_text_content(annotation_content)
            if clean_content and clean_content.strip():
                if debug:
                    print(f'  final content length: {len(clean_content.strip())}')
                return clean_content.strip()

        return None
    
    def get_annotation_format(self) -> str:
        """
        根据语言获取注释格式
        
        Returns:
            str: 注释格式字符串，包含占位符 {}
        """
        if self._is_chinese_language():
            return "（注：{}）"
        else:
            return " (Note: {})"
    
    def _is_chinese_language(self) -> bool:
        """
        判断是否为中文语言
        
        Returns:
            bool: 是否为中文
        """
        chinese_codes = ['zh', 'zh-cn', 'zh-tw', 'zh-hk', 'chinese']
        return any(code in self.language.lower() for code in chinese_codes)
    
    def get_carrier_image_paths(self) -> set:
        """
        获取所有注释载体图片的路径
        
        Returns:
            set: 载体图片路径集合
        """
        carrier_images = set()
        
        # 遍历所有内容文件，查找注释载体图片
        for file_path, content in self.content_files.items():
            carrier_images.update(self._find_carrier_images_in_content(content))
        
        return carrier_images
    
    def _find_carrier_images_in_content(self, html_content: str) -> set:
        """
        在HTML内容中查找注释载体图片
        
        Args:
            html_content: HTML内容
            
        Returns:
            set: 载体图片路径集合
        """
        carrier_images = set()
        
        # 查找包含图片的链接，这些图片可能是载体图片
        # 模式：<a href="注释链接"><img src="图片路径" /></a>
        link_img_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>.*?<img[^>]*src=["\']([^"\']+)["\'][^>]*>.*?</a>'
        
        matches = re.findall(link_img_pattern, html_content, re.IGNORECASE | re.DOTALL)
        
        for link_href, img_src in matches:
            # 检查链接是否指向EPUB内部内容
            if self._is_internal_link(link_href):
                # 这是一个载体图片（用于链接到内部内容）
                normalized_img_path = self._normalize_image_path(img_src)
                if normalized_img_path:
                    carrier_images.add(normalized_img_path)
        
        return carrier_images
    
    def _is_internal_link(self, href: str) -> bool:
        """
        判断链接是否为EPUB内部链接
        
        Args:
            href: 链接地址
            
        Returns:
            bool: 是否为内部链接
        """
        # 解码URL
        decoded_href = unquote(href)
        
        # 解析URL
        parsed = urlparse(decoded_href)
        
        # 跳过外部链接
        if parsed.scheme and parsed.scheme not in ['', 'file']:
            return False
        
        # 检查是否有锚点（注释通常使用锚点）
        if parsed.fragment:
            return True
        
        # 检查文件路径是否指向EPUB内部文件
        if parsed.path:
            # 相对路径通常是内部链接
            if not parsed.path.startswith('http'):
                return True
        
        return False
    
    def _contains_carrier_image(self, link_content: str) -> bool:
        """
        检查链接内容是否包含载体图片
        
        Args:
            link_content: 链接内的HTML内容
            
        Returns:
            bool: 是否包含载体图片
        """
        # 检查是否包含img标签
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        img_matches = re.findall(img_pattern, link_content, re.IGNORECASE)
        
        if img_matches:
            # 检查图片是否为注释载体图片
            for img_src in img_matches:
                # 载体图片通常有特定的命名模式
                img_name = img_src.lower()
                carrier_indicators = [
                    'note', 'annotation', 'footnote', 'ref', 'reference',
                    '注', '注释', '脚注', '参考'
                ]
                
                # 如果图片名包含载体指示词，认为是载体图片
                if any(indicator in img_name for indicator in carrier_indicators):
                    return True
                    
                # 检查图片是否很小（通常载体图片都很小）
                # 这里通过文件名模式来判断
                if re.search(r'(small|tiny|icon|bullet)', img_name):
                    return True
        
        return False

    def _normalize_image_path(self, img_src: str) -> Optional[str]:
        """
        标准化图片路径
        
        Args:
            img_src: 原始图片路径
            
        Returns:
            Optional[str]: 标准化后的路径
        """
        if not img_src:
            return None
        
        # 解码URL编码
        decoded_src = unquote(img_src)
        
        # 移除查询参数和锚点
        parsed = urlparse(decoded_src)
        clean_path = parsed.path

        # 如果是相对路径，需要根据当前文件路径进行解析
        # 这里简化处理，直接返回路径
        return clean_path if clean_path else None