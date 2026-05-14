#!/usr/bin/env python3
"""
完整MD文件生成器
在所有独立MD文件生成后，额外生成一个合并的完整版
"""

import re
from pathlib import Path
from typing import List
from dataclasses import dataclass


@dataclass
class MDFile:
    """MD文件信息"""
    path: Path
    content: str
    page_number: int  # 页码（按文件列表顺序）
    original_filename: str


class MergedOutputGenerator:
    """完整MD文件生成器"""

    def __init__(self, md_files: List[str], output_dir: str, epub_name: str):
        """
        Args:
            md_files: 所有独立MD文件的路径列表
            output_dir: 输出目录
            epub_name: EPUB文件名（不含扩展名）
        """
        self.md_files = self._load_md_files(md_files)
        self.output_dir = Path(output_dir)
        self.epub_name = epub_name

    def _load_md_files(self, md_file_paths: List[str]) -> List[MDFile]:
        """加载所有MD文件内容"""
        files = []
        for i, file_path in enumerate(md_file_paths, 1):  # 直接用索引 1, 2, 3...
            path = Path(file_path)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            files.append(MDFile(
                path=path,
                content=content,
                page_number=i,  # 简单的计数器
                original_filename=path.name
            ))
        return files

    def _get_page_number_by_filename(self, filename: str) -> int:
        """根据文件名获取页码（在列表中的位置）"""
        filename_clean = filename.replace('.md', '')
        for md_file in self.md_files:
            if md_file.original_filename.replace('.md', '') == filename_clean:
                return md_file.page_number
        return 0  # 未找到

    def _step1_fix_ids(self, md_file: MDFile) -> str:
        """
        第一步：补正当前文件中的ID
        <a id="xxx"> -> <a id="P页码-xxx">
        """
        page_prefix = f"P{md_file.page_number:05d}-"
        content = md_file.content

        # 替换所有 <a id="xxx"> 为 <a id="P页码-xxx">
        pattern = r'<a id="([^"]+)">'
        replacement = f'<a id="{page_prefix}\\1">'
        content = re.sub(pattern, replacement, content)

        return content

    def _step2_fix_link_targets(self, content: str) -> str:
        """
        第二步：补正链接目标中的锚点ID
        [text](filename.md#xxx) -> [text](filename.md#P目标页码-xxx)
        """
        def replace_anchor(match):
            filename = match.group(1)  # text00026
            anchor = match.group(2)    # d1

            # 找到目标文件的页码
            target_page = self._get_page_number_by_filename(filename)
            if target_page == 0:
                # 未找到目标文件，保持原样
                return match.group(0)

            page_prefix = f"P{target_page:05d}-"
            return f'({filename}.md#{page_prefix}{anchor})'

        # 匹配 [text](filename.md#anchor)
        pattern = r'\(([^)]+\.md)#([^)]+)\)'
        content = re.sub(pattern, replace_anchor, content)

        return content

    def _step3_fix_same_page_links(self, content: str, page_number: int) -> str:
        """
        第三步：补正同页链接（不带文件名的跳转）
        [text](#xxx) -> [text](#P当前页码-xxx)

        这些链接指向同一页面内的锚点，需要添加当前页码前缀
        注意：避免重复处理已带有页码前缀的链接（来自第二步）
        """
        page_prefix = f"P{page_number:05d}-"

        # 匹配 [text](#anchor)，但排除已处理过的格式 (P00000- 前缀)
        pattern = r'\[([^\]]+)\]\((?! *[pP]\d{5}-)#([^)]+)\)'

        def replace_same_page_anchor(match):
            text = match.group(1)
            anchor = match.group(2)
            return f'[{text}](#{page_prefix}{anchor})'

        content = re.sub(pattern, replace_same_page_anchor, content)

        return content

    def _step4_remove_md_filenames(self, content: str) -> str:
        """
        第四步：去掉链接中的.md文件名
        [text](filename.md#xxx) -> [text](#xxx)
        """
        # 匹配 [text](filename.md#anchor) 并替换为 [text](#anchor)
        pattern = r'\[([^\]]+)\]\([^)]+\.md#([^)]+)\)'
        replacement = r'[\1](#\2)'
        content = re.sub(pattern, replacement, content)

        return content

    def _fix_cross_page_links(self, md_file: MDFile) -> str:
        """
        执行完整的跨页链接修正（四步）
        """
        content = md_file.content

        # 第一步：补正当前文件的ID
        content = self._step1_fix_ids(md_file)

        # 第二步：补正链接目标的ID（跨页链接）
        content = self._step2_fix_link_targets(content)

        # 第三步：补正同页链接的ID
        content = self._step3_fix_same_page_links(content, md_file.page_number)

        # 第四步：去掉.md文件名
        content = self._step4_remove_md_filenames(content)

        return content

    def generate_merged_output(self) -> str:
        """
        生成合并的完整MD文件
        """
        print("\n开始生成完整合并版MD文件...")

        merged_sections = []

        for md_file in self.md_files:
            print(f"  处理: {md_file.original_filename}")

            # 修正跨页链接
            fixed_content = self._fix_cross_page_links(md_file)

            # 添加章节分隔符
            section = f"{fixed_content}\n\n---\n\n"
            merged_sections.append(section)

        # 合并所有内容
        merged_content = ''.join(merged_sections)

        # 保存文件
        output_path = self.output_dir / f"{self.epub_name}.md"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(merged_content)

        print(f"✓ 完整版已生成: {output_path.name}")

        return str(output_path)
