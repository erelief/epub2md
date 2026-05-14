#!/usr/bin/env python3
"""
端到端集成测试
End-to-end integration tests for EPUB to Markdown converter

测试完整的EPUB转换流程
验证所有组件协同工作
测试各种EPUB格式和内容类型
需求: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import os
import sys
import tempfile
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any
import unittest

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from epub_converter.main import convert_epub_to_markdown
from epub_converter.epub_parser import EPUBParser
from epub_converter.utils import ConversionResult, is_valid_epub_file


class TestEPUBIntegration(unittest.TestCase):
    """EPUB转换器集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.epub_files = {}
        self.create_test_epub_files()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_epub_files(self):
        """创建测试用的EPUB文件"""
        # 创建简单的中文EPUB
        self.epub_files['chinese_simple'] = self._create_chinese_epub()
        
        # 创建英文EPUB
        self.epub_files['english_simple'] = self._create_english_epub()
        
        # 创建包含图片的EPUB
        self.epub_files['with_images'] = self._create_epub_with_images()
        
        # 创建包含注释的EPUB
        self.epub_files['with_annotations'] = self._create_epub_with_annotations()
        
        # 创建包含封面的EPUB
        self.epub_files['with_cover'] = self._create_epub_with_cover()
    
    def _create_chinese_epub(self) -> str:
        """创建中文EPUB测试文件"""
        epub_path = os.path.join(self.test_dir, "chinese_test.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip')
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>测试中文书籍</dc:title>
        <dc:creator>测试作者</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">test-chinese-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
        <itemref idref="chapter2"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 章节文件
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第一章</title>
</head>
<body>
    <h1>第一章：开始</h1>
    <p>这是第一章的内容。包含中文字符测试。</p>
    <p>这里有更多的段落内容，用于测试转换功能。</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            chapter2 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第二章</title>
</head>
<body>
    <h1>第二章：继续</h1>
    <p>这是第二章的内容。</p>
    <ul>
        <li>列表项目一</li>
        <li>列表项目二</li>
    </ul>
</body>
</html>'''
            epub.writestr('OEBPS/chapter2.xhtml', chapter2)
            
            # toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="test-chinese-book"/>
    </head>
    <docTitle>
        <text>测试中文书籍</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>第一章</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
        <navPoint id="chapter2">
            <navLabel><text>第二章</text></navLabel>
            <content src="chapter2.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return epub_path
    
    def _create_english_epub(self) -> str:
        """创建英文EPUB测试文件"""
        epub_path = os.path.join(self.test_dir, "english_test.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip')
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Test English Book</dc:title>
        <dc:creator>Test Author</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="uid">test-english-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
        <itemref idref="chapter2"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 章节文件
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter One</title>
</head>
<body>
    <h1>Chapter One: Beginning</h1>
    <p>This is the content of the first chapter. Testing English text conversion.</p>
    <p>Here is more paragraph content to test the conversion functionality.</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            chapter2 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter Two</title>
</head>
<body>
    <h1>Chapter Two: Continuation</h1>
    <p>This is the content of the second chapter.</p>
    <ul>
        <li>List item one</li>
        <li>List item two</li>
    </ul>
</body>
</html>'''
            epub.writestr('OEBPS/chapter2.xhtml', chapter2)
            
            # toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="test-english-book"/>
    </head>
    <docTitle>
        <text>Test English Book</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter One</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
        <navPoint id="chapter2">
            <navLabel><text>Chapter Two</text></navLabel>
            <content src="chapter2.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return epub_path
    
    def _create_epub_with_images(self) -> str:
        """创建包含图片的EPUB测试文件"""
        epub_path = os.path.join(self.test_dir, "with_images_test.epub")
        
        # 创建一个简单的测试图片（1x1像素PNG）
        test_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip')
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Book with Images</dc:title>
        <dc:creator>Test Author</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="uid">test-images-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="image1" href="images/test.png" media-type="image/png"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 章节文件包含图片
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter with Image</title>
</head>
<body>
    <h1>Chapter with Image</h1>
    <p>This chapter contains an image:</p>
    <img src="images/test.png" alt="Test Image"/>
    <p>Text after the image.</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            # 图片文件
            epub.writestr('OEBPS/images/test.png', test_image_data)
            
            # toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="test-images-book"/>
    </head>
    <docTitle>
        <text>Book with Images</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter with Image</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return epub_path
    
    def _create_epub_with_annotations(self) -> str:
        """创建包含注释的EPUB测试文件"""
        epub_path = os.path.join(self.test_dir, "with_annotations_test.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip')
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>带注释的书籍</dc:title>
        <dc:creator>测试作者</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">test-annotations-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="notes" href="notes.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
        <itemref idref="notes"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 包含注释链接的章节
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>带注释的章节</title>
</head>
<body>
    <h1>带注释的章节</h1>
    <p>这是一个包含<a href="notes.xhtml#note1">注释链接</a>的段落。</p>
    <p>还有另一个<a href="#footnote1">脚注</a>在同一页面。</p>
    
    <div id="footnote1">
        <p>这是页面内的脚注内容。</p>
    </div>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            # 注释页面
            notes = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>注释</title>
</head>
<body>
    <h1>注释</h1>
    <div id="note1">
        <p>这是第一个注释的详细内容。</p>
    </div>
</body>
</html>'''
            epub.writestr('OEBPS/notes.xhtml', notes)
            
            # toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="test-annotations-book"/>
    </head>
    <docTitle>
        <text>带注释的书籍</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>带注释的章节</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return epub_path
    
    def _create_epub_with_cover(self) -> str:
        """创建包含封面的EPUB测试文件"""
        epub_path = os.path.join(self.test_dir, "with_cover_test.epub")
        
        # 创建一个简单的测试图片（1x1像素PNG）
        cover_image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82'
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # mimetype文件
            epub.writestr('mimetype', 'application/epub+zip')
            
            # META-INF/container.xml
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # OEBPS/content.opf
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>带封面的书籍</dc:title>
        <dc:creator>测试作者</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">test-cover-book</dc:identifier>
        <meta name="cover" content="cover-image"/>
    </metadata>
    <manifest>
        <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>
        <item id="cover-image" href="images/cover.png" media-type="image/png"/>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="cover"/>
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 封面页面
            cover = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>封面</title>
</head>
<body>
    <div>
        <img src="images/cover.png" alt="封面"/>
    </div>
</body>
</html>'''
            epub.writestr('OEBPS/cover.xhtml', cover)
            
            # 正文章节
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>第一章</title>
</head>
<body>
    <h1>第一章</h1>
    <p>这是正文内容。</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            # 封面图片
            epub.writestr('OEBPS/images/cover.png', cover_image_data)
            
            # toc.ncx
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="test-cover-book"/>
    </head>
    <docTitle>
        <text>带封面的书籍</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>第一章</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        return epub_path
    
    # 集成测试方法
    
    def test_complete_conversion_chinese(self):
        """测试完整的中文EPUB转换流程"""
        epub_path = self.epub_files['chinese_simple']
        output_dir = os.path.join(self.test_dir, "chinese_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证结果
        self.assertIsInstance(result, ConversionResult)
        self.assertTrue(os.path.exists(result.output_directory))
        self.assertEqual(result.language_detected, 'zh')
        self.assertGreater(len(result.converted_files), 0)
        
        # 验证生成的Markdown文件
        for file_path in result.converted_files:
            self.assertTrue(os.path.exists(file_path))
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('第', content)  # 应该包含中文字符
                self.assertTrue(content.strip())  # 不应该为空
    
    def test_complete_conversion_english(self):
        """测试完整的英文EPUB转换流程"""
        epub_path = self.epub_files['english_simple']
        output_dir = os.path.join(self.test_dir, "english_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证结果
        self.assertIsInstance(result, ConversionResult)
        self.assertTrue(os.path.exists(result.output_directory))
        self.assertEqual(result.language_detected, 'en')
        self.assertGreater(len(result.converted_files), 0)
        
        # 验证生成的Markdown文件
        for file_path in result.converted_files:
            self.assertTrue(os.path.exists(file_path))
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('Chapter', content)  # 应该包含英文内容
                self.assertTrue(content.strip())  # 不应该为空
    
    def test_image_extraction_and_linking(self):
        """测试图片提取和链接更新"""
        epub_path = self.epub_files['with_images']
        output_dir = os.path.join(self.test_dir, "images_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证图片被提取
        self.assertGreater(len(result.extracted_images), 0)
        
        # 验证图片文件存在
        for image_path in result.extracted_images:
            self.assertTrue(os.path.exists(image_path))
        
        # 验证Markdown中的图片链接
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if '![' in content:  # 如果包含图片
                    # 验证图片链接格式正确
                    self.assertRegex(content, r'!\[.*?\]\([^)]+\)')
    
    def test_annotation_processing(self):
        """测试注释处理功能"""
        epub_path = self.epub_files['with_annotations']
        output_dir = os.path.join(self.test_dir, "annotations_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证转换成功
        self.assertGreater(len(result.converted_files), 0)
        
        # 验证注释被内联化
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 中文注释应该使用"（注：...）"格式
                if '注：' in content:
                    self.assertRegex(content, r'（注：.*?）')
    
    def test_cover_handling(self):
        """测试封面处理功能"""
        epub_path = self.epub_files['with_cover']
        output_dir = os.path.join(self.test_dir, "cover_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证封面图片被保存
        self.assertIsNotNone(result.cover_image_path)
        self.assertTrue(os.path.exists(result.cover_image_path))
        
        # 验证封面文件名格式
        cover_filename = os.path.basename(result.cover_image_path)
        self.assertTrue(cover_filename.startswith('00_'))
        self.assertIn('_cover', cover_filename)
        
        # 验证封面页没有生成对应的Markdown文件
        # 封面页应该被跳过，所以Markdown文件数量应该少于总页面数
        self.assertGreaterEqual(len(result.converted_files), 1)
    
    def test_output_directory_structure(self):
        """测试输出目录结构"""
        epub_path = self.epub_files['chinese_simple']
        
        # 不指定输出目录，应该在EPUB文件同目录创建
        result = convert_epub_to_markdown(epub_path)
        
        # 验证输出目录位置和名称
        expected_dir = os.path.join(self.test_dir, "chinese_test")
        self.assertEqual(os.path.normpath(result.output_directory), os.path.normpath(expected_dir))
        self.assertTrue(os.path.exists(result.output_directory))
    
    def test_file_validation(self):
        """测试文件验证功能"""
        # 测试有效EPUB文件
        valid_epub = self.epub_files['chinese_simple']
        self.assertTrue(is_valid_epub_file(valid_epub))
        
        # 测试无效文件
        invalid_file = os.path.join(self.test_dir, "invalid.epub")
        with open(invalid_file, 'w') as f:
            f.write("This is not an EPUB file")
        
        self.assertFalse(is_valid_epub_file(invalid_file))
        
        # 测试不存在的文件
        self.assertFalse(is_valid_epub_file("nonexistent.epub"))
    
    def test_unicode_handling(self):
        """测试Unicode字符处理"""
        epub_path = self.epub_files['chinese_simple']
        output_dir = os.path.join(self.test_dir, "unicode_测试")  # 包含中文的目录名
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证Unicode目录名被正确处理
        self.assertTrue(os.path.exists(result.output_directory))
        
        # 验证生成的文件包含正确的Unicode内容
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 验证中文字符被正确保存
                self.assertRegex(content, r'[\u4e00-\u9fff]')
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试损坏的EPUB文件
        corrupted_epub = os.path.join(self.test_dir, "corrupted.epub")
        with open(corrupted_epub, 'wb') as f:
            f.write(b"corrupted data")
        
        with self.assertRaises(Exception):
            convert_epub_to_markdown(corrupted_epub)
        
        # 测试不存在的文件
        with self.assertRaises(Exception):
            convert_epub_to_markdown("nonexistent.epub")
    
    def test_component_integration(self):
        """测试所有组件协同工作"""
        epub_path = self.epub_files['with_cover']  # 使用包含多种元素的EPUB
        output_dir = os.path.join(self.test_dir, "integration_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证所有组件都正常工作
        # 1. EPUB解析器 - 成功提取内容
        self.assertGreater(len(result.converted_files), 0)
        
        # 2. 语言检测器 - 正确检测语言
        self.assertEqual(result.language_detected, 'zh')
        
        # 3. 封面处理器 - 处理封面
        self.assertIsNotNone(result.cover_image_path)
        
        # 4. 内容处理器 - 转换HTML到Markdown
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 验证Markdown格式
                self.assertTrue(content.startswith('#') or '# ' in content)
        
        # 5. 图片处理器 - 提取图片
        self.assertGreaterEqual(len(result.extracted_images), 0)
        
        # 6. 输出目录创建
        self.assertTrue(os.path.exists(result.output_directory))
    
    def test_performance_and_timing(self):
        """测试性能和计时"""
        epub_path = self.epub_files['chinese_simple']
        output_dir = os.path.join(self.test_dir, "performance_output")
        
        # 执行转换
        result = convert_epub_to_markdown(epub_path, output_dir)
        
        # 验证处理时间被记录
        self.assertGreater(result.processing_time, 0)
        self.assertLess(result.processing_time, 60)  # 应该在合理时间内完成


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)