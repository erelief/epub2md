#!/usr/bin/env python3
"""
MD文件合并器模块
Markdown File Merger Module

将目录中的多个Markdown文件合并为一个完整的文件，自动处理跨页链接。
"""

from .core import MergedOutputGenerator

__version__ = "1.0.0"
__all__ = ['MergedOutputGenerator']
