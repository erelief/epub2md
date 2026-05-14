"""
EPUB to Markdown Converter

A Python tool for converting EPUB files to structured Markdown format.
"""

__version__ = "1.0.0"
__author__ = "EPUB Converter"

from .main import main, convert_epub_to_markdown
from .link_processor import LinkProcessor

__all__ = ['main', 'convert_epub_to_markdown', 'LinkProcessor']