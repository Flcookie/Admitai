# app/api/v1/canonical.py
"""
规范化管道API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from app.services.canonical.run_pipeline import (
    run_pipeline,
    pause_pipeline,
    resume_pipeline,
    stop_pipeline,
    get_pipeline_status,
    reset_pipeline_state
)

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


@router.get("/canonical-pipeline-status")
def get_status() -> Dict[str, Any]:
    """获取管道当前状态"""
    status = get_pipeline_status()
    return {"status": "ok", "data": status}


@router.get("/canonical-pipeline-checkpoint")
def get_checkpoint() -> Dict[str, Any]:
    """
    查找应该从哪里继续处理（断点检查）
    返回每个表中最后处理的记录ID，以及第一个未处理的记录ID
    """
    try:
        from app.services.supabase_client import supabase
        
        checkpoint = {}
        
        # 检查 programs 表
        try:
            # 找到最后一个已处理的记录（有canonical_program_id的最大ID）
            last_processed = supabase.table("programs").select("id").not_.is_("canonical_program_id", "null").order("id", desc=True).limit(1).execute()
            last_id = last_processed.data[0]["id"] if last_processed.data else None
            
            # 找到第一个未处理的记录（canonical_program_id为null的最小ID）
            first_unmatched = supabase.table("programs").select("id").is_("canonical_program_id", "null").order("id").limit(1).execute()
            first_unmatched_id = first_unmatched.data[0]["id"] if first_unmatched.data else None
            
            # 统计未处理的数量
            unmatched_count = supabase.table("programs").select("id", count="exact").is_("canonical_program_id", "null").execute()
            
            checkpoint["programs"] = {
                "last_processed_id": last_id,
                "first_unmatched_id": first_unmatched_id,
                "unmatched_count": unmatched_count.count if hasattr(unmatched_count, 'count') else len(unmatched_count.data)
            }
        except Exception as e:
            logger.warning(f"检查programs表失败: {e}")
            checkpoint["programs"] = {"error": str(e)}
        
        # 检查 ic_program_stats 表
        try:
            last_processed = supabase.table("ic_program_stats").select("id").not_.is_("canonical_program_id", "null").order("id", desc=True).limit(1).execute()
            last_id = last_processed.data[0]["id"] if last_processed.data else None
            
            first_unmatched = supabase.table("ic_program_stats").select("id").is_("canonical_program_id", "null").order("id").limit(1).execute()
            first_unmatched_id = first_unmatched.data[0]["id"] if first_unmatched.data else None
            
            unmatched_count = supabase.table("ic_program_stats").select("id", count="exact").is_("canonical_program_id", "null").execute()
            
            checkpoint["ic_program_stats"] = {
                "last_processed_id": last_id,
                "first_unmatched_id": first_unmatched_id,
                "unmatched_count": unmatched_count.count if hasattr(unmatched_count, 'count') else len(unmatched_count.data)
            }
        except Exception as e:
            logger.warning(f"检查ic_program_stats表失败: {e}")
            checkpoint["ic_program_stats"] = {"error": str(e)}
        
        # 检查 cases 表
        try:
            last_processed = supabase.table("cases").select("id").not_.is_("canonical_program_id", "null").order("id", desc=True).limit(1).execute()
            last_id = last_processed.data[0]["id"] if last_processed.data else None
            
            first_unmatched = supabase.table("cases").select("id").is_("canonical_program_id", "null").order("id").limit(1).execute()
            first_unmatched_id = first_unmatched.data[0]["id"] if first_unmatched.data else None
            
            unmatched_count = supabase.table("cases").select("id", count="exact").is_("canonical_program_id", "null").execute()
            
            checkpoint["cases"] = {
                "last_processed_id": last_id,
                "first_unmatched_id": first_unmatched_id,
                "unmatched_count": unmatched_count.count if hasattr(unmatched_count, 'count') else len(unmatched_count.data)
            }
        except Exception as e:
            logger.warning(f"检查cases表失败: {e}")
            checkpoint["cases"] = {"error": str(e)}
        
        return {
            "status": "ok",
            "checkpoint": checkpoint,
            "recommendation": {
                "resume_from_table": checkpoint.get("programs", {}).get("first_unmatched_id") and "programs" or 
                                    (checkpoint.get("ic_program_stats", {}).get("first_unmatched_id") and "ic_program_stats" or 
                                     (checkpoint.get("cases", {}).get("first_unmatched_id") and "cases" or None)),
                "resume_from_id": checkpoint.get("programs", {}).get("last_processed_id") or 
                                 checkpoint.get("ic_program_stats", {}).get("last_processed_id") or 
                                 checkpoint.get("cases", {}).get("last_processed_id")
            }
        }
    except Exception as e:
        logger.error(f"检查断点失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查断点失败: {str(e)}")


@router.post("/canonical-pipeline-pause")
def pause() -> Dict[str, Any]:
    """暂停管道处理"""
    result = pause_pipeline()
    return result


@router.post("/canonical-pipeline-resume")
def resume() -> Dict[str, Any]:
    """恢复管道处理"""
    result = resume_pipeline()
    return result


@router.post("/canonical-pipeline-stop")
def stop() -> Dict[str, Any]:
    """停止管道处理"""
    result = stop_pipeline()
    status = get_pipeline_status()
    return {
        **result,
        "last_processed_id": status.get("last_processed_id"),
        "last_processed_table": status.get("current_table")
    }


@router.post("/canonical-pipeline-reset")
def reset() -> Dict[str, Any]:
    """重置管道状态（用于重新开始）"""
    reset_pipeline_state()
    return {"status": "ok", "message": "管道状态已重置"}


@router.post("/run-canonical-pipeline")
def run_canonical(
    clear_existing: bool = Query(False, description="是否先清除所有现有的canonical_program_id匹配"),
    resume_from_id: Optional[int] = Query(None, description="从指定ID继续处理（断点续传）"),
    resume_from_table: Optional[str] = Query(None, description="从指定表继续处理（programs/ic_program_stats/cases）"),
    only_unmatched: bool = Query(True, description="只处理未匹配的记录（canonical_program_id为空）")
) -> Dict[str, Any]:
    """
    运行规范化管道
    
    处理以下表：
    - programs: 更新canonical_program_id和category
    - ic_program_stats: 更新canonical_program_id
    - cases: 更新canonical_program_id
    
    Args:
        clear_existing: 如果为True，先清除所有现有的canonical_program_id，然后重新匹配
    
    Returns:
        处理结果
    """
    try:
        logger.info("收到规范化管道运行请求")
        
        # 如果设置了clear_existing，先清除所有现有的匹配
        if clear_existing:
            logger.info("正在清除所有现有的canonical_program_id匹配...")
            from app.services.supabase_client import supabase
            
            # 清除programs表的匹配
            try:
                supabase.table("programs").update({"canonical_program_id": None}).execute()
                logger.info("已清除programs表的canonical_program_id")
            except Exception as e:
                logger.warning(f"清除programs表失败: {e}")
            
            # 清除ic_program_stats表的匹配
            try:
                supabase.table("ic_program_stats").update({"canonical_program_id": None}).execute()
                logger.info("已清除ic_program_stats表的canonical_program_id")
            except Exception as e:
                logger.warning(f"清除ic_program_stats表失败: {e}")
            
            # 清除cases表的匹配
            try:
                supabase.table("cases").update({"canonical_program_id": None}).execute()
                logger.info("已清除cases表的canonical_program_id")
            except Exception as e:
                logger.warning(f"清除cases表失败: {e}")
        
        result = run_pipeline(
            resume_from_id=resume_from_id,
            resume_from_table=resume_from_table,
            only_unmatched=only_unmatched
        )
        return {"message": "Canonical mapping completed", "details": result}
    except Exception as e:
        logger.error(f"运行规范化管道失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"运行规范化管道失败: {str(e)}"
        )

