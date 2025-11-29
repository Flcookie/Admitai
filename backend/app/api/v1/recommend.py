# app/api/v1/recommend.py
"""
选校推荐模块 - 优化版本
重构后的代码具有更好的性能、可维护性和可读性
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import numpy as np
import statistics
import json
import logging

from app.services.supabase_client import supabase
from app.services.llm_client import llm_generate
from openai import OpenAI
from app.config import settings

router = APIRouter(prefix="/recommend", tags=["Recommend"])
client = OpenAI(api_key=settings.OPENAI_API_KEY)
logger = logging.getLogger(__name__)


# ===============================
# 配置参数（可调整的权重）
# ===============================
class ScoringWeights:
    """匹配度计算权重配置"""
    GPA_SCORE_MAX = 30.0
    GPA_SCORE_MIN = 0.0
    GPA_BASE = 70.0
    GPA_MULTIPLIER = 2.0
    
    TIER_SCORE_HIGH = 20.0  # 985/211
    TIER_SCORE_LOW = 8.0    # 其他
    
    LANGUAGE_SCORE_MAX = 15.0
    LANGUAGE_BASE = 5.0
    LANGUAGE_MULTIPLIER = 5.0
    
    EMBEDDING_SCORE_MAX = 40.0
    EMBEDDING_SCORE_DEFAULT = 20.0
    
    ENGINEERING_BOOST = 5.0


class CaseAnalysisConfig:
    """案例分析配置"""
    # 相似度匹配阈值
    SIMILARITY_MIN_SCORE = 4
    
    # GPA匹配范围
    GPA_MATCH_RANGE = 5.0
    
    # 语言成绩匹配范围
    LANGUAGE_MATCH_RANGE = 0.5
    
    # 难度计算配置
    DIFFICULTY_DEFAULT = 55.0
    DIFFICULTY_MIN = 30.0
    DIFFICULTY_MAX = 95.0
    DIFFICULTY_GPA_BASE = 70.0
    DIFFICULTY_GPA_MULTIPLIER = 2.0
    
    # 录取概率配置
    PROBABILITY_MIN = 0.05
    PROBABILITY_MAX = 0.85
    PROBABILITY_ESTIMATE_STRONG = 0.40  # GPA>=85, Lang>=7.0
    PROBABILITY_ESTIMATE_MEDIUM = 0.33  # GPA>=80, Lang>=6.5
    PROBABILITY_ESTIMATE_WEAK = 0.25
    PROBABILITY_ADJUSTMENT_GPA = 0.10
    PROBABILITY_ADJUSTMENT_LANG = 0.05
    PROBABILITY_ADJUSTMENT_985 = 0.10
    PROBABILITY_ADJUSTMENT_211 = 0.05


# ===============================
# 数据模型
# ===============================
class StudentProfile(BaseModel):
    undergrad_school: str
    school_tier: str
    major: str
    gpa: float
    language_score: float
    target_major: str
    target_country: str


class Recommendation(BaseModel):
    university: str
    program: str
    match_score: float
    difficulty: float
    case_matches: int
    tier: str
    admission_probability: float


class CaseMetrics(BaseModel):
    """单个项目的案例统计指标"""
    filtered_cases: List[Dict[str, Any]]
    offer_cases: List[Dict[str, Any]]
    gpa_list: List[float]
    offer_gpa_list: List[float]
    difficulty: float
    case_matches: int
    admission_probability: float


# ===============================
# 工具函数
# ===============================
def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    """
    try:
        a_arr = np.array(a, dtype=float)
        b_arr = np.array(b, dtype=float)
        norm_product = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm_product == 0:
            return 0.0
        return float(np.dot(a_arr, b_arr) / norm_product)
    except Exception as e:
        logger.warning(f"余弦相似度计算失败: {e}")
        return 0.0


def parse_embedding(emb_raw: Any) -> Optional[List[float]]:
    """
    解析embedding数据（可能是字符串或列表）
    """
    if isinstance(emb_raw, list):
        try:
            return [float(x) for x in emb_raw]
        except:
            return None
    
    if isinstance(emb_raw, str):
        try:
            parsed = json.loads(emb_raw)
            if isinstance(parsed, list):
                return [float(x) for x in parsed]
        except:
            pass
    
    return None


# ===============================
# 数据加载
# ===============================
def load_cases_for_country(country: str) -> List[Dict[str, Any]]:
    """
    加载指定国家的所有案例
    """
    try:
        cases = (
            supabase.table("cases")
            .select("*")
            .ilike("applied_university", f"%{country}%")
            .execute()
            .data
        )
        logger.info(f"加载了 {len(cases)} 个 {country} 的案例")
        return cases or []
    except Exception as e:
        logger.error(f"加载案例失败: {e}")
        return []


def load_programs_for_country(country: str) -> List[Dict[str, Any]]:
    """
    加载指定国家的所有项目
    """
    try:
        programs = (
            supabase.table("programs")
            .select("*")
            .ilike("location", f"%{country}%")
            .execute()
            .data
        )
        logger.info(f"加载了 {len(programs)} 个 {country} 的项目")
        return programs or []
    except Exception as e:
        logger.error(f"加载项目失败: {e}")
        return []


# ===============================
# 案例索引构建（性能优化）
# ===============================
def build_case_index(cases: List[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    """
    构建案例索引：按 (program_name, university_name) 分组
    避免重复过滤，大幅提升性能
    """
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    
    for case in cases:
        program_name = case.get("applied_program", "") or ""
        university_name = case.get("applied_university", "") or ""
        if program_name and university_name:
            index[(program_name, university_name)].append(case)
    
    return index


# ===============================
# 一次性计算所有案例指标（核心优化）
# ===============================
def compute_case_metrics(
    profile: StudentProfile,
    program_name: str,
    university_name: str,
    case_index: Dict[Tuple[str, str], List[Dict[str, Any]]]
) -> CaseMetrics:
    """
    一次性计算所有案例相关指标，避免重复遍历
    """
    # 获取匹配的案例（从索引中快速查找）
    key = (program_name, university_name)
    
    # 尝试精确匹配
    filtered_cases = case_index.get(key, [])
    
    # 如果精确匹配失败，尝试模糊匹配
    if not filtered_cases:
        for (p_name, u_name), cases_list in case_index.items():
            if program_name in p_name and university_name in u_name:
                filtered_cases.extend(cases_list)
    
    # 筛选录取案例
    offer_keywords = ["Offer", "Conditional Offer", "录取", "有条件录取"]
    offer_cases = [
        c for c in filtered_cases
        if any(keyword in str(c.get("result", "")).lower() for keyword in [k.lower() for k in offer_keywords])
    ]
    
    # 提取GPA数据
    gpa_list: List[float] = []
    offer_gpa_list: List[float] = []
    
    for case in filtered_cases:
        prof = case.get("student_profile_json") or {}
        gpa = prof.get("gpa")
        if gpa is not None:
            try:
                gpa_value = float(gpa)
                gpa_list.append(gpa_value)
                if case in offer_cases:
                    offer_gpa_list.append(gpa_value)
            except:
                pass
    
    # 计算难度
    difficulty = CaseAnalysisConfig.DIFFICULTY_DEFAULT
    if offer_gpa_list:
        avg_gpa = statistics.mean(offer_gpa_list)
        difficulty = (avg_gpa - CaseAnalysisConfig.DIFFICULTY_GPA_BASE) * CaseAnalysisConfig.DIFFICULTY_GPA_MULTIPLIER
        difficulty = max(CaseAnalysisConfig.DIFFICULTY_MIN, min(CaseAnalysisConfig.DIFFICULTY_MAX, difficulty))
    
    # 计算相似案例数
    match_count = 0
    for case in filtered_cases:
        prof = case.get("student_profile_json") or {}
        score = 0
        
        # GPA匹配
        case_gpa = prof.get("gpa")
        if case_gpa is not None:
            try:
                if abs(float(case_gpa) - profile.gpa) <= CaseAnalysisConfig.GPA_MATCH_RANGE:
                    score += 3
            except:
                pass
        
        # 语言成绩匹配
        case_lang = prof.get("language_score")
        if case_lang is not None:
            try:
                if abs(float(case_lang) - profile.language_score) <= CaseAnalysisConfig.LANGUAGE_MATCH_RANGE:
                    score += 2
            except:
                pass
        
        # 学校档次匹配
        case_tier = prof.get("school_tier", "")
        if case_tier == profile.school_tier:
            score += 2
        
        # 专业大类匹配
        case_major = prof.get("major", "")
        if "工程" in profile.major and "工程" in case_major:
            score += 2
        
        if score >= CaseAnalysisConfig.SIMILARITY_MIN_SCORE:
            match_count += 1
    
    # 计算录取概率
    admission_prob = _calculate_admission_probability(profile, filtered_cases, offer_cases, offer_gpa_list)
    
    return CaseMetrics(
        filtered_cases=filtered_cases,
        offer_cases=offer_cases,
        gpa_list=gpa_list,
        offer_gpa_list=offer_gpa_list,
        difficulty=float(round(difficulty, 1)),
        case_matches=match_count,
        admission_probability=admission_prob
    )


def _calculate_admission_probability(
    profile: StudentProfile,
    filtered_cases: List[Dict[str, Any]],
    offer_cases: List[Dict[str, Any]],
    offer_gpa_list: List[float]
) -> float:
    """计算录取概率"""
    if not filtered_cases:
        # 无案例时基于背景估算
        if profile.gpa >= 85 and profile.language_score >= 7.0:
            return CaseAnalysisConfig.PROBABILITY_ESTIMATE_STRONG
        elif profile.gpa >= 80 and profile.language_score >= 6.5:
            return CaseAnalysisConfig.PROBABILITY_ESTIMATE_MEDIUM
        else:
            return CaseAnalysisConfig.PROBABILITY_ESTIMATE_WEAK
    
    # 基础录取率
    base_rate = len(offer_cases) / len(filtered_cases)
    
    # 调整因子
    adjustment = 0.0
    
    # GPA调整
    if offer_gpa_list:
        avg_offer_gpa = statistics.mean(offer_gpa_list)
        if profile.gpa > avg_offer_gpa:
            adjustment += CaseAnalysisConfig.PROBABILITY_ADJUSTMENT_GPA
    
    # 语言成绩调整
    if profile.language_score >= 7.0:
        adjustment += CaseAnalysisConfig.PROBABILITY_ADJUSTMENT_LANG
    
    # 学校档次调整
    if profile.school_tier == "985":
        adjustment += CaseAnalysisConfig.PROBABILITY_ADJUSTMENT_985
    elif profile.school_tier == "211":
        adjustment += CaseAnalysisConfig.PROBABILITY_ADJUSTMENT_211
    
    # 计算最终概率
    prob = base_rate + adjustment
    prob = max(CaseAnalysisConfig.PROBABILITY_MIN, min(CaseAnalysisConfig.PROBABILITY_MAX, prob))
    
    return round(prob, 2)


# ===============================
# 匹配度计算
# ===============================
def calculate_match_score(
    profile: StudentProfile,
    program: Dict[str, Any],
    student_embedding: List[float]
) -> float:
    """
    计算项目匹配度分数
    """
    weights = ScoringWeights
    
    # 1. GPA分数
    gpa_score = (profile.gpa - weights.GPA_BASE) * weights.GPA_MULTIPLIER
    gpa_score = max(weights.GPA_SCORE_MIN, min(weights.GPA_SCORE_MAX, gpa_score))
    
    # 2. 学校档次分数
    tier_score = weights.TIER_SCORE_HIGH if profile.school_tier in ["985", "211"] else weights.TIER_SCORE_LOW
    
    # 3. 语言成绩分数
    lang_score = (profile.language_score - weights.LANGUAGE_BASE) * weights.LANGUAGE_MULTIPLIER
    lang_score = max(0, min(weights.LANGUAGE_SCORE_MAX, lang_score))
    
    # 4. Embedding相似度分数
    program_embedding = parse_embedding(program.get("program_embedding"))
    if program_embedding:
        similarity = cosine_similarity(student_embedding, program_embedding)
        emb_score = similarity * weights.EMBEDDING_SCORE_MAX
    else:
        emb_score = weights.EMBEDDING_SCORE_DEFAULT
    
    # 5. 专业匹配加分
    eng_boost = 0
    if "工程" in profile.major and "工程" in str(program.get("program_cn_name", "")):
        eng_boost = weights.ENGINEERING_BOOST
    
    # 总分
    total_score = gpa_score + tier_score + lang_score + emb_score + eng_boost
    
    return float(round(total_score, 1))


# ===============================
# Tier计算
# ===============================
def calculate_tier(score: float) -> str:
    """
    根据匹配度分数计算申请档次
    """
    if score >= 80:
        return "稳妥"
    elif score >= 73:
        return "匹配"
    elif score >= 66:
        return "冲刺"
    else:
        return "弱冲刺"


# ===============================
# 结构化分析
# ===============================
def generate_structured_analysis(profile: StudentProfile, top_items: List[Recommendation]) -> Dict[str, List[str]]:
    """
    生成结构化分析（strengths/weaknesses/strategy）
    """
    if not top_items:
        return {
            "strengths": [],
            "weaknesses": [],
            "strategy": []
        }
    
    summary = "\n".join([
        f"- {item.university} • {item.program}（匹配度 {item.match_score:.1f} / 难度 {item.difficulty:.1f}）"
        for item in top_items[:5]
    ])
    
    prompt = f"""
请根据以下信息输出严格 JSON（不得包含解释）。

<学生背景>
- 本科院校：{profile.undergrad_school}（{profile.school_tier}）
- 本科专业：{profile.major}
- GPA：{profile.gpa}
- 语言成绩：{profile.language_score}
- 目标方向：{profile.target_major}

<推荐项目Top5>
{summary}

请输出 JSON：

{{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "strategy": ["...", "..."]
}}

要求：
- 每项 2-4 条
- 必须为 JSON 数组
- 不需要自然语言段落，不要加标题
"""
    
    try:
        text = llm_generate(prompt)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"生成结构化分析失败: {e}")
        return {
            "strengths": [],
            "weaknesses": [],
            "strategy": []
        }


# ===============================
# 主接口
# ===============================
@router.post("/")
def recommend_schools(profile: StudentProfile):
    """
    选校推荐主接口
    优化后的版本具有更好的性能和可维护性
    """
    try:
        # 1. 数据加载
        all_cases = load_cases_for_country(profile.target_country)
        programs = load_programs_for_country(profile.target_country)
        
        if not programs:
            return {"recommendations": [], "overall_reason": ""}
        
        # 2. 构建案例索引（性能优化关键）
        case_index = build_case_index(all_cases)
        logger.info(f"构建了 {len(case_index)} 个案例索引项")
        
        # 3. 生成学生目标专业的embedding
        try:
            embedding_response = client.embeddings.create(
                model="text-embedding-3-small",
                input=profile.target_major
            )
            student_embedding = embedding_response.data[0].embedding
        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            raise HTTPException(status_code=500, detail=f"生成embedding失败: {str(e)}")
        
        # 4. 计算每个项目的推荐指标
        results: List[Recommendation] = []
        
        for program in programs:
            try:
                program_name = program.get("program_cn_name") or ""
                university_name = program.get("chinese_name") or ""
                
                if not program_name or not university_name:
                    continue
                
                # 计算匹配度
                match_score = calculate_match_score(profile, program, student_embedding)
                
                # 一次性计算所有案例指标
                case_metrics = compute_case_metrics(
                    profile,
                    program_name,
                    university_name,
                    case_index
                )
                
                # 计算档次
                tier = calculate_tier(match_score)
                
                # 构建推荐结果
                results.append(
                    Recommendation(
                        university=university_name,
                        program=program_name,
                        match_score=match_score,
                        difficulty=case_metrics.difficulty,
                        case_matches=case_metrics.case_matches,
                        tier=tier,
                        admission_probability=case_metrics.admission_probability
                    )
                )
            except Exception as e:
                logger.warning(f"处理项目失败 {program.get('id')}: {e}")
                continue
        
        # 5. 按匹配度排序
        results.sort(key=lambda x: -x.match_score)
        
        # 6. 生成结构化分析
        top_results = results[:10]
        analysis = generate_structured_analysis(profile, top_results)
        
        # 7. 生成整体分析理由（兼容现有前端）
        overall_reason = _generate_overall_reason(profile, top_results, analysis)
        
        return {
            "recommendations": [r.dict() for r in top_results],
            "overall_reason": overall_reason,
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"推荐失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


def _generate_overall_reason(
    profile: StudentProfile,
    recommendations: List[Recommendation],
    analysis: Dict[str, List[str]]
) -> str:
    """
    生成整体分析理由（兼容现有前端）
    """
    if not recommendations:
        return "暂无推荐项目。"
    
    strengths_text = "\n".join([f"• {s}" for s in analysis.get("strengths", [])])
    weaknesses_text = "\n".join([f"• {w}" for w in analysis.get("weaknesses", [])])
    strategy_text = "\n".join([f"• {s}" for s in analysis.get("strategy", [])])
    
    reason = f"""基于你的背景（{profile.undergrad_school}，{profile.school_tier}，GPA {profile.gpa}，语言 {profile.language_score}），我为你推荐了 {len(recommendations)} 个匹配的项目。

优势：
{strengths_text or "• 需要进一步评估"}

劣势：
{weaknesses_text or "• 需要进一步评估"}

申请策略：
{strategy_text or "• 需要进一步评估"}
"""
    return reason.strip()
