# app/api/v1/applications.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import re
from app.services.supabase_client import supabase
from app.schemas.application import ApplicationPlan, ApplicationPlanCreate, ApplicationPlanUpdate

router = APIRouter(prefix="/applications", tags=["Applications"])


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    将各种日期格式转换为 YYYY-MM-DD 格式
    如果无法解析，返回 None
    """
    if not date_str:
        return None
    
    # 如果已经是 YYYY-MM-DD 格式，直接返回
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # 尝试解析 ISO 格式
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime('%Y-%m-%d')
    except:
        pass
    
    # 处理中文日期格式，如 "7月24日"、"2024年7月24日" 等
    chinese_match = re.match(r'(\d{4})?年?(\d{1,2})月(\d{1,2})日?', date_str)
    if chinese_match:
        year = chinese_match.group(1) or str(datetime.now().year)
        month = chinese_match.group(2).zfill(2)
        day = chinese_match.group(3).zfill(2)
        return f"{year}-{month}-{day}"
    
    # 如果无法解析，返回 None（不传递日期字段）
    return None


@router.post("/", response_model=ApplicationPlan)
def create_application(application: ApplicationPlanCreate):
    """
    添加项目到申请列表
    """
    try:
        # 检查是否已存在
        existing = supabase.table("applications").select("*").eq(
            "student_id", application.student_id
        ).eq("program_id", application.program_id).execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="该项目已在申请列表中")
        
        # 规范化日期格式
        normalized_deadline = normalize_date(application.application_deadline)
        
        # 插入新申请
        data = {
            "student_id": application.student_id,
            "program_id": application.program_id,
            "program_name": application.program_name,
            "university": application.university,
            "status": "planned",
            "priority": application.priority,
            "application_deadline": normalized_deadline,
            "notes": application.notes,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        result = supabase.table("applications").insert(data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="创建申请失败")
        
        return ApplicationPlan(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建申请失败: {str(e)}")


@router.get("/")
def list_applications(
    student_id: str = Query(..., description="学生ID"),
    status: Optional[str] = Query(None, description="筛选状态"),
    limit: int = Query(100, description="每页数量"),
    offset: int = Query(0, description="分页偏移量")
):
    """
    获取学生的申请列表
    """
    try:
        query = supabase.table("applications").select("*").eq(
            "student_id", student_id
        )
        
        if status:
            query = query.eq("status", status)
        
        query = query.order("priority", desc=True).order("created_at", desc=True)
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # 如果表不存在或为空，返回空列表
        if not result.data:
            return {
                "count": 0,
                "items": [],
                "limit": limit,
                "offset": offset
            }
        
        return {
            "count": len(result.data),
            "items": [ApplicationPlan(**item) for item in result.data],
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        error_msg = str(e)
        # 检查是否是表不存在的错误
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="数据库表applications不存在，请先在Supabase中执行create_applications_table.sql脚本创建表"
            )
        raise HTTPException(status_code=500, detail=f"获取申请列表失败: {error_msg}")


@router.get("/{application_id}", response_model=ApplicationPlan)
def get_application(application_id: int, student_id: str = Query(..., description="学生ID")):
    """
    获取单个申请详情
    """
    try:
        result = supabase.table("applications").select("*").eq(
            "id", application_id
        ).eq("student_id", student_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="申请不存在")
        
        return ApplicationPlan(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取申请详情失败: {str(e)}")


@router.put("/{application_id}", response_model=ApplicationPlan)
def update_application(
    application_id: int,
    update: ApplicationPlanUpdate,
    student_id: str = Query(..., description="学生ID")
):
    """
    更新申请信息（状态、优先级、截止日期、备注等）
    """
    try:
        # 检查申请是否存在且属于该学生
        existing = supabase.table("applications").select("*").eq(
            "id", application_id
        ).eq("student_id", student_id).execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="申请不存在")
        
        # 构建更新数据
        update_data = {"updated_at": datetime.now().isoformat()}
        
        if update.status is not None:
            update_data["status"] = update.status
        if update.priority is not None:
            update_data["priority"] = update.priority
        if update.application_deadline is not None:
            # 规范化日期格式
            normalized_deadline = normalize_date(update.application_deadline)
            update_data["application_deadline"] = normalized_deadline
        if update.notes is not None:
            update_data["notes"] = update.notes
        
        # 更新
        result = supabase.table("applications").update(update_data).eq(
            "id", application_id
        ).eq("student_id", student_id).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="更新申请失败")
        
        return ApplicationPlan(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新申请失败: {str(e)}")


@router.delete("/{application_id}")
def delete_application(
    application_id: int,
    student_id: str = Query(..., description="学生ID")
):
    """
    从申请列表中删除项目
    """
    try:
        # 检查申请是否存在且属于该学生
        existing = supabase.table("applications").select("*").eq(
            "id", application_id
        ).eq("student_id", student_id).execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(status_code=404, detail="申请不存在")
        
        # 删除
        supabase.table("applications").delete().eq(
            "id", application_id
        ).eq("student_id", student_id).execute()
        
        return {"success": True, "message": "申请已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除申请失败: {str(e)}")


@router.get("/stats/summary")
def get_application_stats(student_id: str = Query(..., description="学生ID")):
    """
    获取申请统计信息
    """
    try:
        result = supabase.table("applications").select("status").eq(
            "student_id", student_id
        ).execute()
        
        if not result.data:
            return {
                "total": 0,
                "by_status": {}
            }
        
        stats = {
            "total": len(result.data),
            "by_status": {}
        }
        
        for item in result.data:
            status = item.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        return stats
        
    except Exception as e:
        error_msg = str(e)
        # 检查是否是表不存在的错误
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="数据库表applications不存在，请先在Supabase中执行create_applications_table.sql脚本创建表"
            )
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {error_msg}")

