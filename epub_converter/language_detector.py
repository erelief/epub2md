"""
语言检测
Language detection functionality
"""

import re
from typing import Dict, Any


class LanguageDetector:
    """语言检测器"""
    
    def detect_language(self, epub_metadata: Dict[str, Any], sample_content: str) -> str:
        """
        检测EPUB的主要语言
        
        Args:
            epub_metadata: EPUB元数据
            sample_content: 内容样本
            
        Returns:
            str: 检测到的语言代码
        """
        # 首先检查元数据中的语言信息
        metadata_language = epub_metadata.get('language', '').lower()
        
        if metadata_language:
            # 标准化语言代码
            normalized_lang = self._normalize_language_code(metadata_language)
            if normalized_lang:
                return normalized_lang
        
        # 基于内容检测语言
        content_language = self._detect_language_from_content(sample_content)
        
        return content_language or 'en'  # 默认返回英文
    
    def _normalize_language_code(self, language_code: str) -> str:
        """
        标准化语言代码
        
        Args:
            language_code: 原始语言代码
            
        Returns:
            str: 标准化后的语言代码
        """
        language_code = language_code.lower().strip()
        
        # 中文语言代码映射
        chinese_codes = {
            'zh', 'zh-cn', 'zh-tw', 'zh-hk', 'zh-sg',
            'chinese', 'china', 'taiwan', 'hongkong'
        }
        
        # 英文语言代码映射
        english_codes = {
            'en', 'en-us', 'en-gb', 'en-au', 'en-ca',
            'english', 'american', 'british'
        }
        
        if any(code in language_code for code in chinese_codes):
            return 'zh'
        elif any(code in language_code for code in english_codes):
            return 'en'
        
        # 其他常见语言
        language_mapping = {
            'ja': 'ja',  # 日文
            'ko': 'ko',  # 韩文
            'fr': 'fr',  # 法文
            'de': 'de',  # 德文
            'es': 'es',  # 西班牙文
            'it': 'it',  # 意大利文
            'ru': 'ru',  # 俄文
        }
        
        for code, normalized in language_mapping.items():
            if code in language_code:
                return normalized
        
        return language_code
    
    def _detect_language_from_content(self, content: str) -> str:
        """
        基于内容检测语言
        
        Args:
            content: 文本内容
            
        Returns:
            str: 检测到的语言代码
        """
        if not content:
            return 'en'
        
        # 移除HTML标签
        clean_content = re.sub(r'<[^>]+>', '', content)
        
        # 计算中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', clean_content))
        total_chars = len(re.sub(r'\s', '', clean_content))
        
        if total_chars == 0:
            return 'en'
        
        chinese_ratio = chinese_chars / total_chars
        
        # 如果中文字符比例超过30%，认为是中文
        if chinese_ratio > 0.3:
            return 'zh'
        
        # 检测其他语言特征
        # 日文假名
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', clean_content))
        if japanese_chars > 0 and japanese_chars / total_chars > 0.1:
            return 'ja'
        
        # 韩文
        korean_chars = len(re.findall(r'[\uac00-\ud7af]', clean_content))
        if korean_chars > 0 and korean_chars / total_chars > 0.1:
            return 'ko'
        
        # 默认返回英文
        return 'en'
    
    def is_chinese(self, language: str) -> bool:
        """
        判断是否为中文
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否为中文
        """
        return language.lower().startswith('zh')
    
    def is_english(self, language: str) -> bool:
        """
        判断是否为英文
        
        Args:
            language: 语言代码
            
        Returns:
            bool: 是否为英文
        """
        return language.lower().startswith('en')