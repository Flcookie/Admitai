# app/api/v1/recommend_v2.py
"""
选校推荐模块 - V2 优化版本
基于新的评分模型：45%官方录取率 + 35%案例因子 + 20%用户匹配度
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import statistics
import logging
import re

from app.services.supabase_client import supabase
from app.services.llm_client import llm_generate

router = APIRouter(prefix="/recommend-v2", tags=["Recommend V2"])
logger = logging.getLogger(__name__)


# ===============================
# 数据模型
# ===============================
class RecommendationRequest(BaseModel):
    """新的推荐请求模型"""
    gpa: float
    major: str
    lang: float
    preferred_direction: Optional[str] = None  # Finance / Management / Other
    max_programs: Optional[int] = 3
    force_business_school: Optional[bool] = False
    target_country: Optional[str] = "英国"


class RecommendedProgram(BaseModel):
    """推荐项目模型"""
    name: str
    score: float
    official_offer_rate: float
    case_offer_rate: float
    user_fit: float
    reason: str
    school: Optional[str] = None
    category: Optional[str] = None
    difficulty: Optional[float] = None
    match_score: Optional[float] = None


class RecommendationResponse(BaseModel):
    """推荐响应模型"""
    recommended_programs: List[RecommendedProgram]
    selected_plan: List[str]
    rule_validation: str


# ===============================
# IC 商学院分类定义
# ===============================
BUSINESS_FINANCE = {
    "Finance",
    "Finance & Accounting",
    "Financial Technology",
    "Investment & Wealth Management",
    "Risk Management & Financial Engineering",
}

BUSINESS_MANAGEMENT = {
    "Management",
    "Economics & Strategy for Business",
    "Strategic Marketing",
}

BUSINESS_OTHER = {
    "Business Analytics",
    "Climate Change, Management & Finance",
    "Innovation, Entrepreneurship & Management",
    "Global Health Management",
}


# ===============================
# 专业关键词映射
# ===============================
MAJOR_KEYWORDS = {
    "computer": ["computer", "computing", "software", "cs", "it", "informatics", "计算机", "软件", "软件工程", "计算机科学", "计算机科学与技术", "信息", "数据科学", "人工智能", "ai", "machine learning", "机器学习"],
    "mechanical": ["mechanical", "mechanics", "机械", "机械工程", "机械设计"],
    "civil": ["civil", "construction", "土木", "建筑工程", "土木工程"],
    "materials": ["materials", "material", "composite", "材料", "复合材料", "材料科学", "材料工程"],
    "biomedical": ["biomedical", "bioengineering", "biotechnology", "生物医学", "生物工程", "生物技术"],
    "finance": ["finance", "financial", "fintech", "金融", "金融工程", "金融学"],
    "management": ["management", "business", "mba", "管理", "工商管理", "企业管理"],
    "electrical": ["electrical", "electronics", "ee", "电气", "电子", "电气工程", "电子工程"],
    "chemical": ["chemical", "chemistry", "化工", "化学", "化学工程"],
    "aerospace": ["aerospace", "aviation", "航空", "航天", "航空航天"],
}


# ===============================
# 数据加载
# ===============================
def load_ic_programs() -> List[Dict[str, Any]]:
    """加载所有IC项目（从programs表）"""
    try:
        # 先尝试用chinese_name筛选
        programs1 = (
            supabase.table("programs")
            .select("*")
            .ilike("chinese_name", "%帝国理工%")
            .execute()
            .data
        ) or []
        
        # 再尝试用english_name筛选
        programs2 = (
            supabase.table("programs")
            .select("*")
            .ilike("english_name", "%Imperial%")
            .execute()
            .data
        ) or []
        
        # 合并并去重
        program_ids = set()
        all_programs = []
        for p in programs1 + programs2:
            if p.get("id") not in program_ids:
                program_ids.add(p.get("id"))
                all_programs.append(p)
        
        logger.info(f"加载了 {len(all_programs)} 个IC项目")
        
        # 记录一些项目名称用于调试
        if all_programs:
            sample_names = [p.get("program_cn_name") or p.get("program_en_name", "") for p in all_programs[:10]]
            logger.info(f"示例项目: {sample_names}")
        
        return all_programs
    except Exception as e:
        logger.error(f"加载IC项目失败: {e}")
        return []


def load_ic_stats() -> Dict[str, List[Dict[str, Any]]]:
    """加载IC项目统计数据，按program_name（英文名）分组"""
    try:
        stats = (
            supabase.table("ic_program_stats")
            .select("*")
            .execute()
            .data
        )
        
        # 按program_name（英文名）分组
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for stat in stats or []:
            program_name = stat.get("program_name", "")
            if program_name:
                grouped[program_name].append(stat)
        
        logger.info(f"加载了 {len(grouped)} 个项目的统计数据")
        return dict(grouped)
    except Exception as e:
        logger.error(f"加载IC统计数据失败: {e}")
        return {}


def load_all_cases() -> List[Dict[str, Any]]:
    """加载所有案例（用于计算学院级和全局级统计）"""
    try:
        cases = (
            supabase.table("cases")
            .select("*")
            .execute()
            .data
        )
        return cases or []
    except Exception as e:
        logger.error(f"加载所有案例失败: {e}")
        return []


def load_cases_for_program(program_en_name: str) -> List[Dict[str, Any]]:
    """加载指定项目的案例"""
    try:
        cases = (
            supabase.table("cases")
            .select("*")
            .ilike("applied_program", f"%{program_en_name}%")
            .execute()
            .data
        )
        return cases or []
    except Exception as e:
        logger.error(f"加载案例失败: {e}")
        return []


def load_cases_for_faculty(school: str) -> List[Dict[str, Any]]:
    """加载指定学院的案例"""
    try:
        cases = (
            supabase.table("cases")
            .select("*")
            .ilike("applied_university", "%Imperial%")
            .execute()
            .data
        )
        # 过滤出属于该学院的案例（通过applied_program匹配）
        # 这里简化处理，实际可能需要更复杂的匹配逻辑
        return cases or []
    except Exception as e:
        logger.error(f"加载学院案例失败: {e}")
        return []


# ===============================
# 评分模型
# ===============================
def calculate_official_offer_factor(
    program_en_name: str,
    stats_by_program: Dict[str, List[Dict[str, Any]]]
) -> Tuple[float, float]:
    """
    计算官方录取率因子（45%权重）
    使用program_en_name匹配ic_program_stats的program_name
    返回: (normalized_factor, avg_offer_rate)
    """
    # 尝试精确匹配
    program_stats = stats_by_program.get(program_en_name, [])
    
    # 如果精确匹配失败，尝试模糊匹配
    if not program_stats:
        for key in stats_by_program.keys():
            if program_en_name.lower() in key.lower() or key.lower() in program_en_name.lower():
                program_stats = stats_by_program[key]
                logger.info(f"使用模糊匹配: {program_en_name} -> {key}")
                break
    
    if not program_stats:
        return (50.0, 0.0)  # 默认值
    
    # 提取最近3年的数据，按academic_year排序
    sorted_stats = sorted(program_stats, key=lambda x: x.get("academic_year", ""), reverse=True)
    
    offer_rates = []
    for stat in sorted_stats[:3]:  # 只取最近3年
        applications = stat.get("applications_received", 0)
        # 尝试不同的字段名
        offers = 0
        for key in stat.keys():
            if "offer" in key.lower() and "made" in key.lower():
                offers = stat.get(key, 0)
                break
            elif key.lower().startswith("offers_ma"):
                offers = stat.get(key, 0)
                break
        
        if applications > 0 and offers > 0:
            offer_rate = offers / applications
            offer_rates.append(offer_rate)
    
    if not offer_rates:
        return (50.0, 0.0)
    
    # 计算3年平均
    avg_offer_rate = statistics.mean(offer_rates)
    
    # 归一化到0~100（min=0.05, max=0.40）
    min_rate = 0.05
    max_rate = 0.40
    
    if avg_offer_rate <= min_rate:
        normalized = 0.0
    elif avg_offer_rate >= max_rate:
        normalized = 100.0
    else:
        normalized = ((avg_offer_rate - min_rate) / (max_rate - min_rate)) * 100.0
    
    return (round(normalized, 2), round(avg_offer_rate, 3))


def calculate_case_factor_hierarchical(
    program_en_name: str,
    program_school: Optional[str],
    all_cases: List[Dict[str, Any]],
    official_offer_rate: float
) -> float:
    """
    分层计算案例因子
    1. 如果项目有>=5个案例：使用项目offer rate
    2. 否则如果学院有>=10个案例：使用学院级平均offer rate
    3. 否则如果平台有>=30个案例：使用全局平均offer rate
    4. 否则：fallback到official_offer_rate
    """
    # 1. 项目级案例
    project_cases = [
        c for c in all_cases
        if program_en_name.lower() in (c.get("applied_program", "") or "").lower()
    ]
    
    if len(project_cases) >= 5:
        offer_cases = [
            c for c in project_cases
            if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
        ]
        if len(project_cases) > 0:
            return len(offer_cases) / len(project_cases)
    
    # 2. 学院级案例
    if program_school:
        faculty_cases = [
            c for c in all_cases
            if ("imperial" in (c.get("applied_university", "") or "").lower() or "帝国" in (c.get("applied_university", "") or ""))
            and program_school.lower() in (c.get("applied_program", "") or "").lower()
        ]
        
        if len(faculty_cases) >= 10:
            offer_cases = [
                c for c in faculty_cases
                if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
            ]
            if len(faculty_cases) > 0:
                return len(offer_cases) / len(faculty_cases)
    
    # 3. 全局案例（中国学生）
    chinese_cases = [
        c for c in all_cases
        if ("imperial" in (c.get("applied_university", "") or "").lower() or "帝国" in (c.get("applied_university", "") or ""))
    ]
    
    if len(chinese_cases) >= 30:
        offer_cases = [
            c for c in chinese_cases
            if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
        ]
        if len(chinese_cases) > 0:
            return len(offer_cases) / len(chinese_cases)
    
    # 4. Fallback到官方录取率
    return official_offer_rate


def calculate_similar_rate_hierarchical(
    program_en_name: str,
    program_school: Optional[str],
    user_major: str,
    all_cases: List[Dict[str, Any]],
    project_case_offer_rate: float
) -> float:
    """
    计算相似专业案例的offer rate（分层）
    如果similar_cases=0，使用faculty_average_offer_rate
    """
    # 1. 项目级相似案例
    project_cases = [
        c for c in all_cases
        if program_en_name.lower() in (c.get("applied_program", "") or "").lower()
    ]
    
    similar_cases = []
    for case in project_cases:
        profile = case.get("student_profile_json", {})
        case_major = profile.get("major", "")
        if _is_major_similar(user_major, case_major):
            similar_cases.append(case)
    
    if len(similar_cases) > 0:
        similar_offers = [
            c for c in similar_cases
            if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
        ]
        return len(similar_offers) / len(similar_cases) if similar_cases else project_case_offer_rate
    
    # 2. 如果similar_cases=0，使用学院级平均offer rate
    if program_school:
        faculty_cases = [
            c for c in all_cases
            if ("imperial" in (c.get("applied_university", "") or "").lower() or "帝国" in (c.get("applied_university", "") or ""))
            and program_school.lower() in (c.get("applied_program", "") or "").lower()
        ]
        
        if len(faculty_cases) >= 10:
            offer_cases = [
                c for c in faculty_cases
                if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
            ]
            if len(faculty_cases) > 0:
                return len(offer_cases) / len(faculty_cases)
    
    # Fallback到项目级offer rate
    return project_case_offer_rate


def calculate_mean_offer_gpa_hierarchical(
    program_en_name: str,
    program_school: Optional[str],
    all_cases: List[Dict[str, Any]]
) -> float:
    """
    分层计算mean_offer_gpa
    1. 如果项目有>=3个offer案例：使用项目平均offer GPA
    2. 否则如果学院有>=10个offer案例：使用学院offer GPA平均
    3. 否则如果全局offer案例>=30：使用全局offer GPA平均
    4. 否则：使用默认baseline = 85
    """
    # 1. 项目级offer GPA
    project_cases = [
        c for c in all_cases
        if program_en_name.lower() in (c.get("applied_program", "") or "").lower()
    ]
    
    project_offer_cases = [
        c for c in project_cases
        if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
    ]
    
    project_offer_gpas = []
    for case in project_offer_cases:
        profile = case.get("student_profile_json", {})
        gpa = profile.get("gpa")
        if gpa:
            try:
                project_offer_gpas.append(float(gpa))
            except:
                pass
    
    if len(project_offer_gpas) >= 3:
        return statistics.mean(project_offer_gpas)
    
    # 2. 学院级offer GPA
    if program_school:
        faculty_cases = [
            c for c in all_cases
            if ("imperial" in (c.get("applied_university", "") or "").lower() or "帝国" in (c.get("applied_university", "") or ""))
            and program_school.lower() in (c.get("applied_program", "") or "").lower()
        ]
        
        faculty_offer_cases = [
            c for c in faculty_cases
            if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
        ]
        
        faculty_offer_gpas = []
        for case in faculty_offer_cases:
            profile = case.get("student_profile_json", {})
            gpa = profile.get("gpa")
            if gpa:
                try:
                    faculty_offer_gpas.append(float(gpa))
                except:
                    pass
        
        if len(faculty_offer_gpas) >= 10:
            return statistics.mean(faculty_offer_gpas)
    
    # 3. 全局offer GPA
    chinese_cases = [
        c for c in all_cases
        if ("imperial" in (c.get("applied_university", "") or "").lower() or "帝国" in (c.get("applied_university", "") or ""))
    ]
    
    global_offer_cases = [
        c for c in chinese_cases
        if c.get("result") and ("offer" in str(c.get("result", "")).lower() or "录取" in str(c.get("result", "")))
    ]
    
    global_offer_gpas = []
    for case in global_offer_cases:
        profile = case.get("student_profile_json", {})
        gpa = profile.get("gpa")
        if gpa:
            try:
                global_offer_gpas.append(float(gpa))
            except:
                pass
    
    if len(global_offer_gpas) >= 30:
        return statistics.mean(global_offer_gpas)
    
    # 4. 默认baseline
    return 85.0


def _is_major_similar(major1: str, major2: str) -> bool:
    """判断两个专业是否相似"""
    if not major1 or not major2:
        return False
    
    major1_lower = major1.lower()
    major2_lower = major2.lower()
    
    # 完全匹配
    if major1_lower == major2_lower:
        return True
    
    # 包含关系
    if major1_lower in major2_lower or major2_lower in major1_lower:
        return True
    
    # 关键词匹配
    keywords = ["工程", "engineering", "金融", "finance", "管理", "management", "经济", "economics"]
    for keyword in keywords:
        if keyword in major1_lower and keyword in major2_lower:
            return True
    
    return False


def calculate_major_relevance_score(
    user_major: str,
    program_en_name: str,
    program_cn_name: Optional[str],
    program_objectives: Optional[str],
    program_requirements: Optional[str],
    program_school: Optional[str]
) -> float:
    """
    计算专业相关性分数（改进版）
    1. 关键词匹配（主要方法）
    2. 学院级fallback
    3. LLM语义fallback（仅在keyword_score < 0.5时）
    """
    user_major_lower = user_major.lower()
    program_en_name_lower = (program_en_name or "").lower()
    program_cn_name_lower = (program_cn_name or "").lower()
    objectives_lower = (program_objectives or "").lower()
    requirements_lower = (program_requirements or "").lower()
    
    # ===============================
    # 1. 关键词匹配（主要方法）
    # ===============================
    keyword_score = 0.2  # 默认值
    
    # 提取用户专业的关键词
    user_keywords = []
    for category, keywords in MAJOR_KEYWORDS.items():
        # 检查用户专业是否包含任何关键词
        if any(kw in user_major_lower for kw in keywords):
            user_keywords.extend(keywords)
            logger.info(f"用户专业 '{user_major}' 匹配到关键词类别 '{category}': {keywords}")
    
    # 如果没有找到关键词，尝试直接使用专业名称中的关键词
    if not user_keywords:
        # 提取专业名称中的关键词（中文和英文）
        major_words = user_major_lower.split()
        # 添加完整专业名称作为关键词
        user_keywords = [user_major_lower] + [w for w in major_words if len(w) > 1]
        logger.info(f"未找到预定义关键词，使用专业名称关键词: {user_keywords}")
    
    # 检查关键词是否出现在项目名称、目标或要求中
    search_text = f"{program_en_name_lower} {program_cn_name_lower} {objectives_lower} {requirements_lower}"
    
    if user_keywords:
        # 检查强匹配（完整关键词出现）
        strong_matches = sum(1 for kw in user_keywords if kw in search_text)
        if strong_matches > 0:
            keyword_score = 1.0  # 强匹配
            logger.info(f"强匹配: 关键词 '{user_keywords}' 在项目文本中找到 {strong_matches} 次")
        else:
            # 检查部分匹配（关键词的部分出现在搜索文本中）
            partial_matches = sum(1 for kw in user_keywords if len(kw) > 3 and any(kw[:i] in search_text for i in range(3, len(kw)+1)))
            if partial_matches > 0:
                keyword_score = 0.7  # 部分匹配
                logger.info(f"部分匹配: 关键词部分出现在项目文本中")
            else:
                keyword_score = 0.2  # 无匹配
                logger.info(f"无匹配: 关键词 '{user_keywords[:3]}...' 未在项目文本中找到")
    
    # ===============================
    # 2. 学院级fallback
    # ===============================
    faculty_score = 0.1  # 默认值
    
    if program_school:
        # 检查用户专业是否与学院相关
        school_lower = program_school.lower()
        
        # 简单的学院匹配逻辑
        if "business" in school_lower and any(kw in user_major_lower for kw in ["finance", "management", "business", "金融", "管理", "商"]):
            faculty_score = 0.4
        elif "engineering" in school_lower and any(kw in user_major_lower for kw in ["engineering", "工程", "mechanical", "electrical", "机械", "电气"]):
            faculty_score = 0.4
        elif "computing" in school_lower and any(kw in user_major_lower for kw in ["computer", "computing", "cs", "计算机", "软件"]):
            faculty_score = 0.4
        elif "science" in school_lower and any(kw in user_major_lower for kw in ["science", "数学", "物理", "化学", "math", "physics", "chemistry"]):
            faculty_score = 0.4
    
    # ===============================
    # 3. LLM语义fallback（仅在keyword_score < 0.5时）
    # ===============================
    relevance_score = keyword_score
    
    if keyword_score < 0.5:
        try:
            # 构建项目描述
            program_description = f"""
Program Name (English): {program_en_name}
Program Name (Chinese): {program_cn_name or "N/A"}
Objectives: {program_objectives or "N/A"}
Requirements: {program_requirements or "N/A"}
School: {program_school or "N/A"}
"""
            
            llm_prompt = f"""用户专业："{user_major}"，项目信息如下：

{program_description}

请评估用户专业与此项目的相关性。请仅返回一个0到1之间的数字（例如：0.85），表示相关性分数。
- 1.0 表示完美匹配
- 0.7-0.9 表示良好匹配
- 0.4-0.6 表示中等匹配
- 0.0-0.3 表示弱匹配

仅返回数字，不要解释。"""
            
            # LLM调用可能较慢，添加超时处理
            try:
                llm_response = llm_generate(llm_prompt)
            except Exception as llm_error:
                logger.warning(f"LLM调用失败，使用keyword_score: {llm_error}")
                llm_response = None
            
            if llm_response:
                # 尝试从响应中提取数字
                import re
                numbers = re.findall(r'\d+\.?\d*', llm_response)
                if numbers:
                    llm_score = float(numbers[0])
                    # 确保在0-1范围内
                    llm_score = max(0.0, min(1.0, llm_score))
                    relevance_score = max(keyword_score, llm_score)
                    logger.info(f"LLM relevance score for {user_major} -> {program_en_name}: {llm_score}")
                else:
                    # 如果无法解析，使用keyword_score
                    relevance_score = max(keyword_score, faculty_score)
            else:
                relevance_score = max(keyword_score, faculty_score)
        except Exception as e:
            logger.warning(f"LLM relevance calculation failed: {e}, using keyword_score")
            relevance_score = max(keyword_score, faculty_score)
    else:
        # 如果keyword_score >= 0.5，直接使用，但考虑faculty_score作为补充
        relevance_score = max(keyword_score, faculty_score)
    
    # ===============================
    # 4. 最终major_fit分数
    # ===============================
    major_fit = relevance_score * 100
    
    return round(major_fit, 2)


def calculate_user_fit_factor(
    user_gpa: float,
    user_major: str,
    user_lang: float,
    program_en_name: str,
    program_cn_name: Optional[str],
    program_objectives: Optional[str],
    program_requirements: Optional[str],
    program_school: Optional[str],
    program_lang_requirement: Optional[str],
    mean_offer_gpa: float
) -> float:
    """
    计算用户匹配度因子（20%权重）
    """
    # Step C1: GPA匹配
    if mean_offer_gpa > 0:
        gpa_score = min(user_gpa / mean_offer_gpa, 1.0)
    else:
        gpa_score = 0.7  # 默认值
    
    # Step C2: 专业匹配（使用新的相关性评分系统）
    major_fit = calculate_major_relevance_score(
        user_major,
        program_en_name,
        program_cn_name,
        program_objectives,
        program_requirements,
        program_school
    )
    major_score = major_fit / 100.0
    
    # Step C3: 语言匹配
    lang_score = _calculate_lang_score(user_lang, program_lang_requirement)
    
    # Step C4: 综合
    user_fit_factor = (0.5 * gpa_score + 0.3 * major_score + 0.2 * lang_score) * 100
    
    return round(user_fit_factor, 2)


def _calculate_lang_score(user_lang: float, lang_requirement: Optional[str]) -> float:
    """计算语言匹配分数"""
    if not lang_requirement:
        return 0.85
    
    # 尝试从requirement中提取分数（例如 "IELTS 7.0"）
    try:
        # 简单的提取逻辑
        if "7.0" in lang_requirement or "7" in lang_requirement:
            required = 7.0
        elif "6.5" in lang_requirement:
            required = 6.5
        elif "6.0" in lang_requirement:
            required = 6.0
        else:
            return 0.85
        
        if user_lang >= required:
            return 0.95
        elif user_lang >= required - 0.5:
            return 0.7
        else:
            return 0.5
    except:
        return 0.85


# ===============================
# IC规则验证
# ===============================
def validate_ic_rules(selected_programs: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    验证IC申请规则
    """
    if not selected_programs:
        return True, "选择有效"
    
    # 提取所有学院
    faculties = set()
    ic_programs = []
    
    for prog in selected_programs:
        school = prog.get("school", "")
        program_name = prog.get("program_en_name", "")
        category = prog.get("category", "")
        
        # 判断是否属于商学院
        is_business = False
        if school and "business" in school.lower():
            is_business = True
        elif _is_program_in_category(program_name, BUSINESS_FINANCE):
            is_business = True
            category = "Finance"
        elif _is_program_in_category(program_name, BUSINESS_MANAGEMENT):
            is_business = True
            category = "Management"
        elif _is_program_in_category(program_name, BUSINESS_OTHER):
            is_business = True
            category = "Other"
        
        if is_business:
            faculties.add("Business School")
            ic_programs.append({"name": program_name, "category": category})
        else:
            faculty_name = school or "Other Faculty"
            faculties.add(faculty_name)
    
    # Rule 1 & 2: Business School cannot be mixed with other faculties
    if "Business School" in faculties and len(faculties) > 1:
        return False, "商学院不能与其他学院混合申请"
    
    # 商学院内部数量统计
    finance_count = sum(1 for p in ic_programs if p.get("category") == "Finance")
    mgmt_count = sum(1 for p in ic_programs if p.get("category") == "Management")
    other_count = sum(1 for p in ic_programs if p.get("category") == "Other")
    
    # Rule 3: Finance programmes max = 2
    if finance_count > 2:
        return False, "金融类项目最多选择2个"
    
    # Rule 4: Management/Strategy programmes max = 1
    if mgmt_count > 1:
        return False, "管理/战略类项目最多选择1个"
    
    # Rule 5: Other business programmes max = 1
    if other_count > 1:
        return False, "其他商业类项目最多选择1个"
    
    # Rule 6: Non-Business faculties allow max 2 programmes
    if "Business School" not in faculties and len(selected_programs) > 2:
        return False, "非商学院最多选择2个项目"
    
    return True, "选择有效"


def _is_program_in_category(program_name: str, category_set: set) -> bool:
    """检查专业名称是否属于某个类别"""
    if not program_name:
        return False
    
    program_lower = program_name.lower()
    for category_name in category_set:
        if category_name.lower() in program_lower:
            return True
    
    return False


# ===============================
# 推荐组合生成
# ===============================
def generate_recommended_plan(
    scored_programs: List[Dict[str, Any]],
    max_programs: int = 3
) -> List[Dict[str, Any]]:
    """
    从高分项目中找出合法组合
    """
    # 按分数降序排序
    sorted_programs = sorted(scored_programs, key=lambda x: x.get("score", 0), reverse=True)
    
    candidate = []
    
    for program in sorted_programs:
        candidate.append(program)
        
        # 验证规则
        is_valid, reason = validate_ic_rules(candidate)
        
        if not is_valid:
            candidate.pop()  # 移除不符合规则的项目
            continue
        
        # 检查是否达到上限
        if len(candidate) >= max_programs:
            break
    
    return candidate


# ===============================
# 主接口
# ===============================
@router.post("/", response_model=RecommendationResponse)
def recommend_programs(request: RecommendationRequest):
    """
    新的推荐接口
    """
    try:
        # 1. 加载数据
        ic_programs = load_ic_programs()
        ic_stats = load_ic_stats()
        all_cases = load_all_cases()  # 一次性加载所有案例
        
        if not ic_programs:
            return RecommendationResponse(
                recommended_programs=[],
                selected_plan=[],
                rule_validation="未找到IC项目"
            )
        
        # 2. 过滤项目（如果指定了preferred_direction）
        if request.preferred_direction:
            filtered_programs = [
                p for p in ic_programs
                if p.get("category", "").lower() == request.preferred_direction.lower()
            ]
            if filtered_programs:
                ic_programs = filtered_programs
        
        # 3. 对每个项目计算综合分数
        scored_programs = []
        
        for program in ic_programs:
            program_en_name = program.get("program_en_name", "")
            program_cn_name = program.get("program_cn_name", "")
            
            if not program_en_name:
                continue  # 必须要有英文名
            
            program_school = program.get("school", "")
            
            logger.info(f"计算项目: {program_cn_name or program_en_name}")
            
            # 匹配ic_program_stats（使用program_en_name）
            official_factor, official_offer_rate = calculate_official_offer_factor(program_en_name, ic_stats)
            logger.info(f"  - 官方因子: {official_factor}, 录取率: {official_offer_rate}")
            
            # 计算case_factor（分层）
            case_offer_rate = calculate_case_factor_hierarchical(
                program_en_name,
                program_school,
                all_cases,
                official_offer_rate
            )
            logger.info(f"  - 案例录取率: {case_offer_rate}")
            
            # 计算similar_rate（分层）
            similar_rate = calculate_similar_rate_hierarchical(
                program_en_name,
                program_school,
                request.major,
                all_cases,
                case_offer_rate
            )
            logger.info(f"  - 相似案例录取率: {similar_rate}")
            
            case_factor = (0.7 * case_offer_rate + 0.3 * similar_rate) * 100
            
            # 计算mean_offer_gpa（分层）
            mean_offer_gpa = calculate_mean_offer_gpa_hierarchical(
                program_en_name,
                program_school,
                all_cases
            )
            logger.info(f"  - 平均录取GPA: {mean_offer_gpa}")
            
            # 计算user_fit_factor（包含专业相关性）
            user_fit_factor = calculate_user_fit_factor(
                request.gpa,
                request.major,
                request.lang,
                program_en_name,
                program_cn_name,
                program.get("objectives"),
                program.get("requirements"),
                program_school,
                program.get("language_requirement"),
                mean_offer_gpa
            )
            
            # 单独计算专业相关性分数（用于过滤和排序）
            major_relevance = calculate_major_relevance_score(
                request.major,
                program_en_name,
                program_cn_name,
                program.get("objectives"),
                program.get("requirements"),
                program_school
            )
            
            logger.info(f"  - 用户匹配度: {user_fit_factor}, 专业相关性: {major_relevance}")
            
            # 计算最终分数（增加专业相关性权重）
            # 如果专业相关性高，给予额外加分
            relevance_bonus = 0
            if major_relevance >= 80:
                relevance_bonus = 10  # 高相关性项目额外加分
            elif major_relevance >= 60:
                relevance_bonus = 5  # 中等相关性项目少量加分
            
            final_score = 0.40 * official_factor + 0.30 * case_factor + 0.30 * user_fit_factor + relevance_bonus
            
            # 计算Difficulty
            difficulty = (1 - official_offer_rate) * 100 if official_offer_rate > 0 else 50.0
            
            # 生成推荐理由（中文）
            reason = _generate_reason(
                request.gpa,
                official_factor,
                case_factor,
                user_fit_factor,
                mean_offer_gpa,
                program_en_name,
                program_cn_name
            )
            
            # 优先使用中文名，如果没有则使用英文名
            display_name = program_cn_name or program_en_name
            
            scored_programs.append({
                "name": display_name,
                "score": round(final_score, 2),
                "official_offer_rate": official_offer_rate,
                "case_offer_rate": round(case_offer_rate, 3),
                "user_fit": round(user_fit_factor / 100, 2),
                "reason": reason,
                "school": program_school,
                "category": program.get("category"),
                "program_en_name": program_en_name,
                "program_cn_name": program_cn_name,
                "difficulty": round(difficulty, 1),
                "match_score": round(final_score, 2),
                "_official_factor": official_factor,
                "_case_factor": case_factor,
                "_user_fit_factor": user_fit_factor,
                "_major_relevance": major_relevance,  # 保存专业相关性用于排序
            })
        
        # 过滤掉专业相关性太低的项目（<30分）
        filtered_scored_programs = [
            p for p in scored_programs 
            if p.get("_major_relevance", 0) >= 30
        ]
        
        if not filtered_scored_programs:
            # 如果没有相关性>=30的项目，保留所有项目但降低相关性要求
            logger.warning("没有找到专业相关性>=30的项目，保留所有项目")
            filtered_scored_programs = scored_programs
        
        # 按专业相关性优先排序，然后按总分排序
        filtered_scored_programs.sort(
            key=lambda x: (x.get("_major_relevance", 0), x["score"]), 
            reverse=True
        )
        
        logger.info(f"推荐项目数量: {len(filtered_scored_programs)}")
        for i, p in enumerate(filtered_scored_programs[:5], 1):
            logger.info(f"  {i}. {p['name']} - 专业相关性: {p.get('_major_relevance', 0):.1f}, 总分: {p['score']:.1f}")
        
        scored_programs = filtered_scored_programs
        
        # 4. 生成推荐组合
        selected_plan = generate_recommended_plan(
            scored_programs,
            max_programs=request.max_programs or 3
        )
        
        # 5. 验证最终组合
        is_valid, validation_msg = validate_ic_rules(selected_plan)
        
        # 6. 转换为响应格式
        recommended_programs = [
            RecommendedProgram(
                name=p["name"],
                score=p["score"],
                official_offer_rate=p.get("official_offer_rate", 0.0),
                case_offer_rate=p["case_offer_rate"],
                user_fit=p["user_fit"],
                reason=p["reason"],
                school=p.get("school"),
                category=p.get("category"),
                difficulty=p.get("difficulty"),
                match_score=p.get("match_score"),
            )
            for p in scored_programs[:10]  # 返回Top 10
        ]
        
        selected_plan_names = [p["name"] for p in selected_plan]
        
        # 将验证消息翻译为中文
        validation_msg_cn = validation_msg
        if not is_valid:
            if "Business School cannot be mixed" in validation_msg:
                validation_msg_cn = "商学院不能与其他学院混合申请"
            elif "Finance programmes max = 2" in validation_msg:
                validation_msg_cn = "金融类项目最多选择2个"
            elif "Management/Strategy programmes max = 1" in validation_msg:
                validation_msg_cn = "管理/战略类项目最多选择1个"
            elif "Other business programmes max = 1" in validation_msg:
                validation_msg_cn = "其他商业类项目最多选择1个"
            elif "Non-Business faculties allow max 2 programmes" in validation_msg:
                validation_msg_cn = "非商学院最多选择2个项目"
            else:
                validation_msg_cn = f"不符合规则: {validation_msg}"
        else:
            validation_msg_cn = "选择有效"
        
        return RecommendationResponse(
            recommended_programs=recommended_programs,
            selected_plan=selected_plan_names,
            rule_validation=validation_msg_cn
        )
        
    except Exception as e:
        logger.error(f"推荐失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")


def _generate_reason(
    user_gpa: float,
    official_factor: float,
    case_factor: float,
    user_fit_factor: float,
    mean_offer_gpa: float,
    program_en_name: Optional[str] = None,
    program_cn_name: Optional[str] = None
) -> str:
    """生成推荐理由（中文）"""
    reasons = []
    
    if mean_offer_gpa > 0 and user_gpa >= mean_offer_gpa:
        reasons.append(f"GPA高于历史平均录取水平（{mean_offer_gpa:.1f}分）")
    
    if user_fit_factor >= 80:
        reasons.append("与项目要求高度匹配")
    elif user_fit_factor >= 60:
        reasons.append("与项目要求较为匹配")
    
    if official_factor >= 70:
        reasons.append("官方录取率较为理想")
    
    if case_factor >= 70:
        reasons.append("历史案例成功率较高")
    
    if not reasons:
        # 使用LLM生成更详细的推荐理由
        try:
            program_name = program_cn_name or program_en_name or "该项目"
            llm_prompt = f"""请为以下情况生成一段简短的中文推荐理由（50字以内）：

学生GPA: {user_gpa}
项目名称: {program_name}
匹配度分数: {user_fit_factor:.1f}/100
官方录取率因子: {official_factor:.1f}/100
案例成功率因子: {case_factor:.1f}/100

请用简洁、专业的中文说明为什么推荐这个项目，重点突出学生的优势。"""
            
            llm_reason = llm_generate(llm_prompt)
            return llm_reason.strip()
        except Exception as e:
            logger.warning(f"LLM生成推荐理由失败: {e}")
            return "基于综合评估，该项目与您的背景较为匹配"
    
    return "；".join(reasons)
