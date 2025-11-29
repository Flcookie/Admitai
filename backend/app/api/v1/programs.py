# backend/app/api/v1/programs.py

from fastapi import APIRouter, Query
from typing import List, Optional

from app.services.supabase_client import supabase

router = APIRouter(prefix="/programs", tags=["Programs"])


@router.get("/")
def list_programs(
    country: Optional[str] = Query(None, description="国家，例如：英国/美国/加拿大"),
    school: Optional[str] = Query(None, description="学校名称（模糊搜索，中英均可）"),
    keyword: Optional[str] = Query(None, description="专业关键词，例如：engineering / 机械 / AI"),
    limit: int = Query(20, description="每页数量"),
    offset: int = Query(0, description="分页偏移量")
):

    query = supabase.table("programs").select("*")

    # 🇬🇧 国家筛选
    if country:
        query = query.ilike("location", f"%{country}%")

    # 🏫 学校筛选
    if school:
        query = query.or_(
            f"chinese_name.ilike.%{school}%,english_name.ilike.%{school}%"
        )

    # 🔍 专业关键词筛选
    if keyword:
        query = query.or_(
            f"program_cn_name.ilike.%{keyword}%,program_en_name.ilike.%{keyword}%"
        )

    # 分页
    query = query.range(offset, offset + limit - 1)

    res = query.execute()
    return {
        "count": len(res.data),
        "items": res.data,
        "limit": limit,
        "offset": offset
    }


@router.get("/faculties")
def list_faculties():
    """
    获取所有唯一的学院列表（用于目标系选择）
    """
    try:
        programs = supabase.table("programs").select("school").execute().data
        
        # 提取唯一的学院名称
        faculties = set()
        for program in programs:
            school = program.get("school")
            if school and school.strip():
                faculties.add(school.strip())
        
        # 排序并转换为列表
        faculty_list = sorted(list(faculties))
        
        return {
            "faculties": faculty_list
        }
    except Exception as e:
        return {
            "faculties": []
        }


@router.get("/filter-options")
def get_filter_options():
    """
    获取筛选选项（唯一的国家、学校等）
    """
    try:
        programs = supabase.table("programs").select("location,chinese_name,english_name,school").execute().data
        
        # 提取唯一的国家/地区
        countries = set()
        for program in programs:
            location = program.get("location")
            if location and location.strip():
                countries.add(location.strip())
        
        # 提取唯一的学校
        schools = set()
        for program in programs:
            chinese_name = program.get("chinese_name")
            english_name = program.get("english_name")
            if chinese_name and chinese_name.strip():
                schools.add(chinese_name.strip())
            if english_name and english_name.strip():
                schools.add(english_name.strip())
        
        # 提取唯一的学院
        faculties = set()
        for program in programs:
            school = program.get("school")
            if school and school.strip():
                faculties.add(school.strip())
        
        return {
            "countries": sorted(list(countries)),
            "schools": sorted(list(schools)),
            "faculties": sorted(list(faculties))
        }
    except Exception as e:
        return {
            "countries": [],
            "schools": [],
            "faculties": []
        }