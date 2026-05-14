#!/usr/bin/env python3
"""
边缘情况和错误处理测试
Edge cases and error handling tests for EPUB to Markdown converter

测试各种边缘情况和错误条件
验证系统的健壮性和错误处理能力
"""

import os
import sys
import tempfile
import shutil
import zipfile
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from epub_converter.main import convert_epub_to_markdown, validate_epub_file
from epub_converter.epub_parser import EPUBParser
from epub_converter.utils import sanitize_filename, is_valid_epub_file


class TestEPUBEdgeCases(unittest.TestCase):
    """EPUB转换器边缘情况测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_empty_epub(self):
        """测试空EPUB文件"""
        epub_path = os.path.join(self.test_dir, "empty.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            # 只包含最基本的EPUB结构，但没有内容
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Empty Book</dc:title>
        <dc:creator>Test</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="uid">empty-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="empty-book"/>
    </head>
    <docTitle>
        <text>Empty Book</text>
    </docTitle>
    <navMap>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 测试转换空EPUB
        with self.assertRaises(RuntimeError) as context:
            convert_epub_to_markdown(epub_path)
        
        self.assertIn("没有找到可转换的内容文件", str(context.exception))
    
    def test_malformed_html_content(self):
        """测试格式错误的HTML内容"""
        epub_path = os.path.join(self.test_dir, "malformed.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Malformed Book</dc:title>
        <dc:creator>Test</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="uid">malformed-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 格式错误的HTML - 未闭合标签、嵌套错误等
            malformed_html = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Malformed Chapter</title>
</head>
<body>
    <h1>Chapter with Malformed HTML
    <p>Paragraph without closing tag
    <div>Nested <span>tags <strong>not properly</div> closed</span></strong>
    <img src="missing.jpg" alt="Missing image"
    <a href="broken-link">Link without closing tag
    &invalid-entity;
    <script>alert('script tag');</script>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', malformed_html)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="malformed-book"/>
    </head>
    <docTitle>
        <text>Malformed Book</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Malformed Chapter</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 应该能够处理格式错误的HTML，不抛出异常
        result = convert_epub_to_markdown(epub_path)
        self.assertIsNotNone(result)
        # 由于HTML格式错误，可能没有成功转换的文件，但不应该崩溃
        self.assertIsInstance(result.converted_files, list)
    
    def test_special_characters_in_filenames(self):
        """测试文件名中的特殊字符"""
        epub_path = os.path.join(self.test_dir, "special_chars.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Book with Special Characters</dc:title>
        <dc:creator>Test Author</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">special-chars-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter with "Special" Characters: <>&|?*</title>
</head>
<body>
    <h1>Chapter with "Special" Characters: &lt;&gt;&amp;|?*</h1>
    <p>This chapter has special characters in the title.</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="special-chars-book"/>
    </head>
    <docTitle>
        <text>Book with Special Characters</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter with Special Characters</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 转换应该成功，特殊字符应该被正确处理
        result = convert_epub_to_markdown(epub_path)
        self.assertIsNotNone(result)
        
        # 验证生成的文件名不包含非法字符
        for file_path in result.converted_files:
            filename = os.path.basename(file_path)
            # Windows非法字符应该被替换
            illegal_chars = '<>:"/\\|?*'
            for char in illegal_chars:
                self.assertNotIn(char, filename)
    
    def test_very_long_content(self):
        """测试非常长的内容"""
        epub_path = os.path.join(self.test_dir, "long_content.epub")
        
        # 生成很长的内容
        long_text = "这是一个很长的段落。" * 1000  # 重复1000次
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Long Content Book</dc:title>
        <dc:creator>Test</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">long-content-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            chapter1 = f'''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Long Chapter</title>
</head>
<body>
    <h1>Long Chapter</h1>
    <p>{long_text}</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="long-content-book"/>
    </head>
    <docTitle>
        <text>Long Content Book</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Long Chapter</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 应该能够处理长内容
        result = convert_epub_to_markdown(epub_path)
        self.assertIsNotNone(result)
        
        # 验证内容被正确转换
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("这是一个很长的段落", content)
    
    def test_missing_metadata(self):
        """测试缺少元数据的EPUB"""
        epub_path = os.path.join(self.test_dir, "missing_metadata.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            # 缺少标题、作者等元数据
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="uid">missing-metadata-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Chapter</title>
</head>
<body>
    <h1>Chapter</h1>
    <p>Content without metadata.</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="missing-metadata-book"/>
    </head>
    <docTitle>
        <text>Unknown</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>Chapter</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 应该能够处理缺少元数据的情况，使用默认值
        result = convert_epub_to_markdown(epub_path)
        self.assertIsNotNone(result)
        self.assertEqual(result.language_detected, 'en')  # 默认语言
    
    def test_filename_sanitization(self):
        """测试文件名清理功能"""
        # 测试各种需要清理的文件名
        test_cases = [
            ('normal_filename', 'normal_filename'),
            ('file with spaces', 'file with spaces'),
            ('file<>:"/\\|?*name', 'file_________name'),
            ('CON', '_CON'),  # Windows保留名称
            ('PRN.txt', '_PRN.txt'),
            ('', 'untitled'),  # 空文件名
            ('   ', 'untitled'),  # 只有空格
            ('file.', 'file'),  # 以点结尾
            ('   file   ', 'file'),  # 前后空格
            ('中文文件名', '中文文件名'),  # 中文字符
            ('file\x00\x01name', 'file__name'),  # 控制字符
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            self.assertEqual(result, expected, f"Input: '{input_name}' -> Expected: '{expected}', Got: '{result}'")
    
    def test_invalid_epub_structures(self):
        """测试无效的EPUB结构"""
        # 测试缺少container.xml的EPUB
        epub_path = os.path.join(self.test_dir, "no_container.epub")
        with zipfile.ZipFile(epub_path, 'w') as epub:
            epub.writestr('mimetype', 'application/epub+zip')
        
        self.assertFalse(is_valid_epub_file(epub_path))
        
        # 测试损坏的ZIP文件
        corrupted_path = os.path.join(self.test_dir, "corrupted.epub")
        with open(corrupted_path, 'wb') as f:
            f.write(b"This is not a ZIP file")
        
        self.assertFalse(is_valid_epub_file(corrupted_path))
    
    def test_encoding_issues(self):
        """测试编码问题"""
        epub_path = os.path.join(self.test_dir, "encoding_test.epub")
        
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as epub:
            epub.writestr('mimetype', 'application/epub+zip')
            
            container_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>'''
            epub.writestr('META-INF/container.xml', container_xml)
            
            content_opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>编码测试书籍</dc:title>
        <dc:creator>测试作者</dc:creator>
        <dc:language>zh</dc:language>
        <dc:identifier id="uid">encoding-test-book</dc:identifier>
    </metadata>
    <manifest>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    </manifest>
    <spine toc="ncx">
        <itemref idref="chapter1"/>
    </spine>
</package>'''
            epub.writestr('OEBPS/content.opf', content_opf)
            
            # 包含各种Unicode字符的内容
            chapter1 = '''<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>编码测试章节</title>
</head>
<body>
    <h1>编码测试章节</h1>
    <p>中文：你好世界！</p>
    <p>日文：こんにちは世界！</p>
    <p>韩文：안녕하세요 세계!</p>
    <p>俄文：Привет мир!</p>
    <p>阿拉伯文：مرحبا بالعالم!</p>
    <p>表情符号：😀😃😄😁😆😅😂🤣</p>
    <p>特殊符号：©®™€£¥§¶†‡•…‰‹›""''</p>
</body>
</html>'''
            epub.writestr('OEBPS/chapter1.xhtml', chapter1)
            
            toc_ncx = '''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="encoding-test-book"/>
    </head>
    <docTitle>
        <text>编码测试书籍</text>
    </docTitle>
    <navMap>
        <navPoint id="chapter1">
            <navLabel><text>编码测试章节</text></navLabel>
            <content src="chapter1.xhtml"/>
        </navPoint>
    </navMap>
</ncx>'''
            epub.writestr('OEBPS/toc.ncx', toc_ncx)
        
        # 应该能够正确处理各种编码
        result = convert_epub_to_markdown(epub_path)
        self.assertIsNotNone(result)
        
        # 验证Unicode字符被正确保存
        for file_path in result.converted_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn('你好世界', content)
                self.assertIn('こんにちは', content)
                self.assertIn('😀', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)