# backend/app/api/v1/ic_stats.py

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from collections import defaultdict
import logging

from app.services.supabase_client import supabase

router = APIRouter(prefix="/ic-stats", tags=["IC Stats"])
logger = logging.getLogger(__name__)


@router.get("/programs")
def list_ic_programs(
    program_name: Optional[str] = Query(None, description="项目名称（模糊搜索）"),
    complete_only: bool = Query(True, description="只返回有完整3年数据的项目")
):
    """
    获取IC项目列表（只返回有完整3年数据的项目）
    """
    try:
        query = supabase.table("ic_program_stats").select("*")
        
        if program_name:
            query = query.ilike("program_name", f"%{program_name}%")
        
        result = query.execute()
        all_data = result.data or []
        
        # 按项目名称分组
        programs_dict: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in all_data:
            program_name_key = item.get("program_name") or ""
            if program_name_key:
                programs_dict[program_name_key].append(item)
        
        # 筛选有完整3年数据的项目
        complete_programs = []
        for program_name_key, stats_list in programs_dict.items():
            # 统计不同年份的数据
            years = set()
            for stat in stats_list:
                academic_year = stat.get("academic_year")
                if academic_year:
                    # 提取年份（假设格式是 "2024-2025" 或 "2024"）
                    year_str = str(academic_year)
                    if "-" in year_str:
                        year = year_str.split("-")[0]
                    else:
                        year = year_str[:4] if len(year_str) >= 4 else year_str
                    if year.isdigit():
                        years.add(int(year))
            
            # 如果有3年或以上的数据，认为是完整的
            if len(years) >= 3:
                # 计算最新一年的数据
                latest_stat = max(stats_list, key=lambda x: x.get("academic_year", ""))
                
                applications = latest_stat.get("applications_received") or 0
                offers = latest_stat.get("offers_made") or 0
                accepted = latest_stat.get("places_confirmed") or 0
                
                # 计算录取率
                admission_rate = (offers / applications * 100) if applications > 0 else 0
                
                complete_programs.append({
                    "program_name": program_name_key,
                    "latest_year": latest_stat.get("academic_year", ""),
                    "applications": applications,
                    "offers": offers,
                    "accepted": accepted,
                    "admission_rate": round(admission_rate, 2),
                    "years_count": len(years),
                })
        
        # 按项目名称排序
        complete_programs.sort(key=lambda x: x["program_name"])
        
        return {
            "count": len(complete_programs),
            "items": complete_programs
        }
        
    except Exception as e:
        logger.error(f"获取IC项目列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取IC项目列表失败: {str(e)}")


@router.get("/program/{program_name}")
def get_program_stats(program_name: str):
    """
    获取指定项目的详细统计数据（3年数据）
    """
    try:
        result = supabase.table("ic_program_stats").select("*").ilike(
            "program_name", f"%{program_name}%"
        ).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        # 按项目名称精确匹配
        program_stats = [item for item in result.data if item.get("program_name") == program_name]
        
        if not program_stats:
            # 如果没有精确匹配，使用第一个模糊匹配的结果
            program_stats = result.data[:1]
            program_name = program_stats[0].get("program_name", "")
        
        # 按年份排序
        program_stats.sort(key=lambda x: x.get("academic_year", ""))
        
        # 构建3年数据
        stats_by_year = []
        for stat in program_stats:
            academic_year = stat.get("academic_year", "")
            # 提取年份
            if "-" in str(academic_year):
                year = str(academic_year).split("-")[0]
            else:
                year = str(academic_year)[:4] if len(str(academic_year)) >= 4 else str(academic_year)
            
            applications = stat.get("applications_received") or 0
            offers = stat.get("offers_made") or 0
            accepted = stat.get("places_confirmed") or 0
            
            # 计算录取率
            admission_rate = (offers / applications * 100) if applications > 0 else 0
            
            stats_by_year.append({
                "year": year,
                "academic_year": academic_year,
                "applications": applications,
                "offers": offers,
                "accepted": accepted,
                "admission_rate": round(admission_rate, 2),
            })
        
        # 只返回有3年数据的项目
        if len(stats_by_year) < 3:
            raise HTTPException(status_code=404, detail="该项目数据不完整（少于3年）")
        
        # 获取最新一年的数据
        latest = stats_by_year[-1] if stats_by_year else {}
        
        return {
            "program_name": program_name,
            "latest_year": latest.get("year", ""),
            "latest_data": {
                "applications": latest.get("applications", 0),
                "offers": latest.get("offers", 0),
                "accepted": latest.get("accepted", 0),
                "admission_rate": latest.get("admission_rate", 0),
            },
            "yearly_stats": stats_by_year[-3:] if len(stats_by_year) >= 3 else stats_by_year
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目统计数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目统计数据失败: {str(e)}")

