"""
Setup script for EPUB to Markdown Converter
"""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="epub-to-markdown-converter",
    version="1.0.0",
    description="A Python tool for converting EPUB files to structured Markdown format",
    author="EPUB Converter",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "epub-converter=epub_converter.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)