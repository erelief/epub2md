#!/usr/bin/env python3
"""
文件管理器测试
File Manager tests for EPUB to Markdown converter

测试FileManager类的文件重命名和映射功能
验证文件名生成和映射表创建的正确性
需求: 9.1
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from epub_converter.file_manager import FileManager
from epub_converter.utils import ContentFile, FilenameMapping


class TestFileManager(unittest.TestCase):
    """文件管理器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试用的ContentFile对象
        self.content_files = [
            ContentFile(
                path="chapter1.html",
                content="<html><body><h1>第一章</h1><p>内容</p></body></html>",
                title="第一章 开始",
                order=1,
                is_cover=False
            ),
            ContentFile(
                path="chapter2.html", 
                content="<html><body><h1>第二章</h1><p>内容</p></body></html>",
                title="第二章 发展",
                order=2,
                is_cover=False
            ),
            ContentFile(
                path="cover.html",
                content="<html><body><img src='cover.jpg'/></body></html>",
                title="封面",
                order=0,
                is_cover=True
            )
        ]
        
        self.file_manager = FileManager(self.content_files)
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_generate_markdown_filename(self):
        """测试Markdown文件名生成"""
        # 测试正常情况
        filename1 = self.file_manager.generate_markdown_filename(self.content_files[0])
        self.assertEqual(filename1, "01_第一章_开始.md")
        
        filename2 = self.file_manager.generate_markdown_filename(self.content_files[1])
        self.assertEqual(filename2, "02_第二章_发展.md")
        
        # 测试封面文件
        filename_cover = self.file_manager.generate_markdown_filename(self.content_files[2])
        self.assertEqual(filename_cover, "00_封面.md")
    
    def test_generate_markdown_filename_with_special_characters(self):
        """测试包含特殊字符的标题"""
        special_content = ContentFile(
            path="special.html",
            content="<html><body><h1>特殊</h1></body></html>",
            title="第三章：特殊字符<>|?*测试",
            order=3,
            is_cover=False
        )
        
        filename = self.file_manager.generate_markdown_filename(special_content)
        # 注意：中文冒号：不会被替换，只有ASCII特殊字符<>|?*会被替换为下划线
        self.assertEqual(filename, "03_第三章：特殊字符_测试.md")
    
    def test_generate_markdown_filename_empty_title(self):
        """测试空标题的处理"""
        empty_title_content = ContentFile(
            path="empty.html",
            content="<html><body><p>内容</p></body></html>",
            title="",
            order=4,
            is_cover=False
        )
        
        filename = self.file_manager.generate_markdown_filename(empty_title_content)
        # 空标题应该使用默认的chapter_X格式
        self.assertEqual(filename, "04_chapter_4.md")
    
    def test_create_filename_mapping(self):
        """测试文件名映射创建"""
        mapping_dict = self.file_manager.create_filename_mapping()
        
        # 验证映射字典
        expected_mappings = {
            "chapter1.html": "01_第一章_开始.html",
            "chapter2.html": "02_第二章_发展.html", 
            "cover.html": "00_封面.html"
        }
        
        self.assertEqual(mapping_dict, expected_mappings)
        
        # 验证映射对象列表
        mappings = self.file_manager.get_filename_mappings()
        self.assertEqual(len(mappings), 3)
        
        # 验证第一个映射
        first_mapping = mappings[0]
        self.assertEqual(first_mapping.original_name, "chapter1.html")
        self.assertEqual(first_mapping.new_name, "01_第一章_开始.html")
        self.assertEqual(first_mapping.markdown_name, "01_第一章_开始.md")
    
    def test_find_new_filename(self):
        """测试查找新文件名"""
        self.file_manager.create_filename_mapping()
        
        # 测试存在的文件
        new_name = self.file_manager.find_new_filename("chapter1.html")
        self.assertEqual(new_name, "01_第一章_开始.html")
        
        # 测试不存在的文件
        not_found = self.file_manager.find_new_filename("nonexistent.html")
        self.assertEqual(not_found, "nonexistent.html")
    
    def test_find_markdown_filename(self):
        """测试查找Markdown文件名"""
        self.file_manager.create_filename_mapping()
        
        # 测试存在的文件
        md_name = self.file_manager.find_markdown_filename("chapter1.html")
        self.assertEqual(md_name, "01_第一章_开始.md")
        
        # 测试不存在的文件
        not_found = self.file_manager.find_markdown_filename("nonexistent.html")
        self.assertEqual(not_found, "nonexistent.md")
    
    def test_update_file_references(self):
        """测试更新文件引用"""
        self.file_manager.create_filename_mapping()
        mapping_dict = self.file_manager.get_mapping_dict()
        
        # 测试HTML内容中的链接更新
        html_content = '''
        <html>
        <body>
            <a href="chapter1.html">第一章</a>
            <a href="chapter2.html#section1">第二章第一节</a>
            <img src="image.jpg" alt="图片"/>
        </body>
        </html>
        '''
        
        updated_content = self.file_manager.update_file_references(html_content, mapping_dict)
        
        # 验证链接已更新
        self.assertIn('href="01_第一章_开始.html"', updated_content)
        self.assertIn('href="02_第二章_发展.html#section1"', updated_content)
        # 图片引用不应该被更改（不在映射中）
        self.assertIn('src="image.jpg"', updated_content)
    
    def test_rename_html_files(self):
        """测试HTML文件重命名"""
        # 创建测试文件
        temp_dir = Path(self.test_dir) / "epub_content"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建原始文件
        for content_file in self.content_files:
            file_path = temp_dir / content_file.path
            file_path.write_text(content_file.content, encoding='utf-8')
        
        # 执行重命名
        actual_mappings = self.file_manager.rename_html_files(str(temp_dir))
        
        # 验证重命名结果
        expected_mappings = {
            "chapter1.html": "01_第一章_开始.html",
            "chapter2.html": "02_第二章_发展.html",
            "cover.html": "00_封面.html"
        }
        
        self.assertEqual(actual_mappings, expected_mappings)
        
        # 验证文件确实被重命名
        self.assertTrue((temp_dir / "01_第一章_开始.html").exists())
        self.assertTrue((temp_dir / "02_第二章_发展.html").exists())
        self.assertTrue((temp_dir / "00_封面.html").exists())
        
        # 验证原文件不再存在
        self.assertFalse((temp_dir / "chapter1.html").exists())
        self.assertFalse((temp_dir / "chapter2.html").exists())
        self.assertFalse((temp_dir / "cover.html").exists())


if __name__ == '__main__':
    unittest.main()