# app/services/canonical/canonical_mapper.py
"""
规范化映射器模块
主函数：normalize → fuzzy match → keyword match → llm fallback
"""
from typing import Optional, List, Dict, Any
import logging

from .normalize import normalize_name
from .fuzzy_match import is_fuzzy_match
from .keyword_match import keyword_overlap_score
from .llm_match import llm_semantic_match

logger = logging.getLogger(__name__)


def map_to_canonical(program_name: str, canonical_list: List[Dict[str, Any]]) -> Optional[int]:
    """
    映射项目名称到规范化项目ID
    
    匹配流程：
    1. exact match（规范化后精确匹配）
    2. fuzzy match（模糊匹配，阈值85）
    3. keyword-based match（关键词匹配，阈值0.3）
    4. LLM semantic fallback（LLM语义匹配）
    
    Args:
        program_name: 项目名称
        canonical_list: 规范化项目列表
        
    Returns:
        规范化项目ID，如果未找到则返回None
    """
    if not program_name or not canonical_list:
        return None
    
    # 规范化输入名称
    norm = normalize_name(program_name)
    
    # Step 1: exact match（规范化后精确匹配）
    for c in canonical_list:
        canonical_name = c.get("canonical_program_name_en") or ""
        if normalize_name(canonical_name) == norm:
            logger.info(f"精确匹配: {program_name} -> {canonical_name}")
            return c.get("id")
    
    # Step 2: fuzzy match（模糊匹配）
    for c in canonical_list:
        canonical_name = c.get("canonical_program_name_en") or ""
        if is_fuzzy_match(norm, normalize_name(canonical_name)):
            logger.info(f"模糊匹配: {program_name} -> {canonical_name}")
            return c.get("id")
    
    # Step 3: keyword-based match（关键词匹配）
    for c in canonical_list:
        canonical_name = c.get("canonical_program_name_en") or ""
        keywords = c.get("keywords", [])
        
        if keywords:
            score = keyword_overlap_score(norm, keywords)
            if score >= 0.3:
                logger.info(f"关键词匹配 ({score:.2f}): {program_name} -> {canonical_name}")
                return c.get("id")
    
    # Step 4: LLM semantic fallback（LLM语义匹配）
    for c in canonical_list:
        canonical_name = c.get("canonical_program_name_en") or ""
        if llm_semantic_match(program_name, canonical_name):
            logger.info(f"LLM语义匹配: {program_name} -> {canonical_name}")
            return c.get("id")
    
    # Step 5: no match
    logger.warning(f"未找到匹配: {program_name}")
    return None

