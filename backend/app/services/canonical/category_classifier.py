# app/services/canonical/category_classifier.py
"""
类别分类器模块
根据专业关键词匹配最佳类别
"""
from .keyword_match import MAJOR_KEYWORDS, keyword_overlap_score


def classify_category(program_name: str, requirements: str = "") -> str:
    """
    分类项目到最佳类别
    
    Args:
        program_name: 项目名称
        requirements: 项目要求（可选）
        
    Returns:
        最佳类别，如果没有匹配则返回"other"
    """
    # 组合项目名称和要求文本
    text = (program_name + " " + (requirements or "")).lower()
    
    if not text.strip():
        return "other"
    
    best_category = None
    best_score = 0.0
    
    # 遍历所有类别，找到最佳匹配
    for cat, kw_list in MAJOR_KEYWORDS.items():
        score = keyword_overlap_score(text, kw_list)
        if score > best_score:
            best_score = score
            best_category = cat
    
    # 如果没有匹配，返回"other"
    if best_category is None:
        return "other"
    
    return best_category

