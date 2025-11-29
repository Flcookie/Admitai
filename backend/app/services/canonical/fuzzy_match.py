# app/services/canonical/fuzzy_match.py
"""
模糊匹配模块
使用 rapidfuzz 进行字符串相似度匹配
"""
from rapidfuzz import fuzz


def fuzzy_similarity(a: str, b: str) -> int:
    """
    计算两个文本的模糊相似度
    
    Args:
        a: 第一个文本
        b: 第二个文本
        
    Returns:
        相似度分数 (0-100)
    """
    if not a or not b:
        return 0
    
    return fuzz.partial_ratio(a.lower(), b.lower())


def is_fuzzy_match(a: str, b: str, threshold: int = 85) -> bool:
    """
    判断两个文本是否模糊匹配（超过阈值）
    
    Args:
        a: 第一个文本
        b: 第二个文本
        threshold: 相似度阈值，默认85
        
    Returns:
        是否匹配
    """
    return fuzzy_similarity(a, b) >= threshold

