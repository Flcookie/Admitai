# app/api/v1/recommendations.py
"""
推荐记录管理模块
用于保存、查询和获取选校推荐记录
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import logging

from app.services.supabase_client import supabase

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


# ===============================
# 数据模型
# ===============================
class RecommendationRecordCreate(BaseModel):
    """创建推荐记录请求"""
    student_id: Optional[str] = None  # 学生ID，从localStorage获取
    input_form: Dict[str, Any]  # 输入的背景信息表单
    recommendations: List[Dict[str, Any]]  # 推荐结果列表
    overall_reason: str  # 整体分析理由
    analysis: Optional[Dict[str, Any]] = None  # 结构化分析


class RecommendationRecord(BaseModel):
    """推荐记录响应"""
    id: int
    student_id: Optional[str]
    input_form: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    overall_reason: str
    analysis: Optional[Dict[str, Any]]
    created_at: str


# ===============================
# API 端点
# ===============================
@router.post("/")
def create_recommendation_record(record: RecommendationRecordCreate):
    """保存推荐记录"""
    try:
        # 如果没有student_id，使用默认值（暂时用"guest"）
        student_id = record.student_id or "guest"
        
        # 准备插入的数据
        data = {
            "student_id": student_id,
            "input_form": json.dumps(record.input_form, ensure_ascii=False),
            "recommendations": json.dumps(record.recommendations, ensure_ascii=False),
            "overall_reason": record.overall_reason,
            "analysis": json.dumps(record.analysis or {}, ensure_ascii=False) if record.analysis else None,
        }
        
        # 插入Supabase
        result = supabase.table("recommendation_records").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="保存推荐记录失败")
        
        return {"id": result.data[0]["id"], "message": "推荐记录保存成功"}
        
    except Exception as e:
        logger.error(f"保存推荐记录失败: {e}", exc_info=True)
        error_str = str(e)
        # 检查是否是表不存在的错误
        if "recommendation_records" in error_str or "PGRST205" in error_str:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "数据库表 'recommendation_records' 不存在",
                    "code": "TABLE_NOT_FOUND",
                    "hint": "请在 Supabase 中创建该表。SQL语句请查看API文档或联系管理员。"
                }
            )
        raise HTTPException(status_code=500, detail=f"保存推荐记录失败: {error_str}")


@router.get("/")
def list_recommendation_records(
    student_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """获取推荐记录列表"""
    try:
        query = supabase.table("recommendation_records").select("*", count="exact")
        
        # 如果提供了student_id，进行过滤
        if student_id:
            query = query.eq("student_id", student_id)
        else:
            # 默认使用"guest"
            query = query.eq("student_id", "guest")
        
        # 按创建时间降序排序
        query = query.order("created_at", desc=True)
        
        # 分页
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # 解析JSON字段
        records = []
        for item in result.data:
            try:
                records.append({
                    "id": item["id"],
                    "student_id": item.get("student_id"),
                    "input_form": json.loads(item["input_form"]) if isinstance(item.get("input_form"), str) else item.get("input_form", {}),
                    "recommendations": json.loads(item["recommendations"]) if isinstance(item.get("recommendations"), str) else item.get("recommendations", []),
                    "overall_reason": item.get("overall_reason", ""),
                    "analysis": json.loads(item["analysis"]) if isinstance(item.get("analysis"), str) and item.get("analysis") else item.get("analysis"),
                    "created_at": item.get("created_at", ""),
                })
            except json.JSONDecodeError as e:
                logger.warning(f"解析记录JSON失败: {e}, 记录ID: {item.get('id')}")
                continue
        
        return {
            "count": result.count if hasattr(result, 'count') else len(records),
            "items": records,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"获取推荐记录列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐记录列表失败: {str(e)}")


@router.get("/{record_id}")
def get_recommendation_record(record_id: int):
    """获取单个推荐记录详情"""
    try:
        result = supabase.table("recommendation_records").select("*").eq("id", record_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="推荐记录不存在")
        
        item = result.data[0]
        
        # 解析JSON字段
        record = {
            "id": item["id"],
            "student_id": item.get("student_id"),
            "input_form": json.loads(item["input_form"]) if isinstance(item.get("input_form"), str) else item.get("input_form", {}),
            "recommendations": json.loads(item["recommendations"]) if isinstance(item.get("recommendations"), str) else item.get("recommendations", []),
            "overall_reason": item.get("overall_reason", ""),
            "analysis": json.loads(item["analysis"]) if isinstance(item.get("analysis"), str) and item.get("analysis") else item.get("analysis"),
            "created_at": item.get("created_at", ""),
        }
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐记录详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐记录详情失败: {str(e)}")


@router.get("/count/by-student")
def count_recommendation_records(student_id: Optional[str] = None):
    """统计学生的推荐记录数量"""
    try:
        query = supabase.table("recommendation_records").select("*", count="exact")
        
        # 如果提供了student_id，进行过滤
        if student_id:
            query = query.eq("student_id", student_id)
        else:
            # 默认使用"guest"
            query = query.eq("student_id", "guest")
        
        result = query.execute()
        count = result.count if hasattr(result, 'count') else len(result.data) if result.data else 0
        
        return {"count": count}
        
    except Exception as e:
        logger.error(f"统计推荐记录数量失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"统计推荐记录数量失败: {str(e)}")


@router.delete("/{record_id}")
def delete_recommendation_record(record_id: int):
    """删除推荐记录"""
    try:
        # 先检查记录是否存在
        result = supabase.table("recommendation_records").select("*").eq("id", record_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="推荐记录不存在")
        
        # 删除记录
        delete_result = supabase.table("recommendation_records").delete().eq("id", record_id).execute()
        
        return {"message": "推荐记录删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除推荐记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除推荐记录失败: {str(e)}")

