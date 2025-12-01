from fastapi import APIRouter, Query
from typing import Optional
from app.services.supabase_client import supabase

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.get("/")
def list_cases(
    school: Optional[str] = None,
    major: Optional[str] = None,
    gpa_min: Optional[float] = None,
    gpa_max: Optional[float] = None,
    limit: int = 20,
    offset: int = 0
):
    try:
        # 先获取总数（用于分页）
        count_query = supabase.table("cases").select("*", count="exact")
        
        # ===============================
        # 1. 按目标学校（applied_university）筛选
        # ===============================
        if school:
            count_query = count_query.ilike("applied_university", f"%{school}%")
        
        # ===============================
        # 2. 按申请专业 applied_program 筛选
        # ===============================
        if major:
            count_query = count_query.ilike("applied_program", f"%{major}%")
        
        # ===============================
        # 3. 按学生专业（profile.major）筛选
        # ===============================
        if major:
            count_query = count_query.or_(f"student_profile_json->>major.ilike.%{major}%")
        
        # ===============================
        # 4. 按 GPA 范围筛选
        # ===============================
        if gpa_min is not None:
            count_query = count_query.gte("student_profile_json->>gpa", str(gpa_min))
        
        if gpa_max is not None:
            count_query = count_query.lte("student_profile_json->>gpa", str(gpa_max))
        
        # 获取总数
        count_res = count_query.execute()
        total_count = count_res.count if hasattr(count_res, 'count') and count_res.count is not None else len(count_res.data) if count_res.data else 0
        
        # 获取分页数据
        query = supabase.table("cases").select("*")
        
        # ===============================
        # 1. 按目标学校（applied_university）筛选
        # ===============================
        if school:
            query = query.ilike("applied_university", f"%{school}%")
        
        # ===============================
        # 2. 按申请专业 applied_program 筛选
        # ===============================
        if major:
            query = query.ilike("applied_program", f"%{major}%")
        
        # ===============================
        # 3. 按学生专业（profile.major）筛选
        # ===============================
        if major:
            query = query.or_(f"student_profile_json->>major.ilike.%{major}%")
        
        # ===============================
        # 4. 按 GPA 范围筛选
        # ===============================
        if gpa_min is not None:
            query = query.gte("student_profile_json->>gpa", str(gpa_min))
        
        if gpa_max is not None:
            query = query.lte("student_profile_json->>gpa", str(gpa_max))
        
        # ===============================
        # 5. 分页
        # ===============================
        query = query.range(offset, offset + limit - 1)
        
        res = query.execute()
        
        return {
            "count": total_count,
            "items": res.data or [],
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取案例列表失败: {e}", exc_info=True)
        return {
            "count": 0,
            "items": [],
            "limit": limit,
            "offset": offset
        }


@router.get("/filter-options")
def get_case_filter_options():
    """
    获取案例筛选选项（唯一的学校、专业、结果、年份等）
    """
    try:
        cases = supabase.table("cases").select("*").execute().data
        
        # 提取唯一的学校
        schools = set()
        # 提取唯一的专业
        majors = set()
        # 提取唯一的结果
        results = set()
        # 提取唯一的年份
        years = set()
        # 提取唯一的学校层次
        school_tiers = set()
        
        for case in cases:
            if case.get("applied_university"):
                schools.add(case["applied_university"].strip())
            if case.get("applied_program"):
                majors.add(case["applied_program"].strip())
            if case.get("result"):
                results.add(case["result"].strip())
            if case.get("admission_year"):
                years.add(case["admission_year"].strip())
            
            # 从 student_profile_json 中提取
            profile = case.get("student_profile_json") or {}
            if isinstance(profile, str):
                import json
                try:
                    profile = json.loads(profile)
                except:
                    profile = {}
            
            if profile.get("major"):
                majors.add(str(profile["major"]).strip())
            if profile.get("school_tier"):
                school_tiers.add(str(profile["school_tier"]).strip())
        
        return {
            "schools": sorted(list(schools)),
            "majors": sorted(list(majors)),
            "results": sorted(list(results)),
            "years": sorted(list(years)),
            "school_tiers": sorted(list(school_tiers))
        }
    except Exception as e:
        return {
            "schools": [],
            "majors": [],
            "results": [],
            "years": [],
            "school_tiers": []
        }