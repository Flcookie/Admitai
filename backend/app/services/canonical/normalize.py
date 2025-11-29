# app/services/canonical/normalize.py
"""
项目名称规范化模块
清理和标准化项目名称
"""
import re


def normalize_name(name: str) -> str:
    """
    清理和标准化项目名称
    
    Args:
        name: 原始项目名称
        
    Returns:
        规范化后的名称
    """
    if not name:
        return ""
    
    # 转换为小写
    normalized = name.lower()
    
    # 移除学位和项目相关词汇
    normalized = re.sub(r"(msc|ms|ma|meng|beng|phd|mres|programme|program)", "", normalized)
    
    # 移除特殊字符，替换为空格
    normalized = re.sub(r"[\(\)\[\]{}:;/\-]", " ", normalized)
    
    # 清理多余空格
    normalized = re.sub(r"\s+", " ", normalized)
    
    return normalized.strip()

