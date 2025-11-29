# app/api/v1/essay_sessions.py
"""
文书写作会话管理模块
用于保存、查询和获取文书写作会话
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import logging

from app.services.supabase_client import supabase

router = APIRouter(prefix="/essay-sessions", tags=["EssaySessions"])
logger = logging.getLogger(__name__)


# ===============================
# 数据模型
# ===============================
class EssaySessionCreate(BaseModel):
    """创建文书会话请求"""
    student_id: Optional[str] = None  # 学生ID
    session_name: Optional[str] = None  # 会话名称
    essay_type: str  # 文书类型
    setup: Dict[str, Any]  # 初始设置（包含student_background, target_university, target_program, language）
    messages: List[Dict[str, Any]]  # 对话消息历史
    current_essay: Optional[str] = None  # 当前文书内容
    setup_complete: bool = False  # 是否已完成设置


class EssaySessionUpdate(BaseModel):
    """更新文书会话请求"""
    session_name: Optional[str] = None  # 会话名称
    messages: Optional[List[Dict[str, Any]]] = None  # 对话消息历史
    current_essay: Optional[str] = None  # 当前文书内容
    setup_complete: Optional[bool] = None  # 是否已完成设置


class EssaySession(BaseModel):
    """文书会话响应"""
    id: int
    student_id: Optional[str]
    session_name: Optional[str] = None  # 会话名称
    essay_type: str
    setup: Dict[str, Any]
    messages: List[Dict[str, Any]]
    current_essay: Optional[str]
    setup_complete: bool
    created_at: str
    updated_at: str


# ===============================
# API 端点
# ===============================
@router.post("/")
def create_essay_session(session: EssaySessionCreate):
    """保存文书会话"""
    try:
        # 如果没有student_id，使用默认值（暂时用"guest"）
        student_id = session.student_id or "guest"
        
        # 准备插入的数据
        data = {
            "student_id": student_id,
            "session_name": session.session_name or None,
            "essay_type": session.essay_type,
            "setup": json.dumps(session.setup, ensure_ascii=False),
            "messages": json.dumps(session.messages, ensure_ascii=False),
            "current_essay": session.current_essay,
            "setup_complete": session.setup_complete,
        }
        
        # 插入Supabase
        result = supabase.table("essay_sessions").insert(data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="保存文书会话失败")
        
        return {"id": result.data[0]["id"], "message": "文书会话保存成功"}
        
    except Exception as e:
        logger.error(f"保存文书会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"保存文书会话失败: {str(e)}")


@router.put("/{session_id}")
def update_essay_session(session_id: int, session: EssaySessionUpdate):
    """更新文书会话"""
    try:
        update_data = {}
        
        if session.session_name is not None:
            update_data["session_name"] = session.session_name
        if session.messages is not None:
            update_data["messages"] = json.dumps(session.messages, ensure_ascii=False)
        if session.current_essay is not None:
            update_data["current_essay"] = session.current_essay
        if session.setup_complete is not None:
            update_data["setup_complete"] = session.setup_complete
        
        if not update_data:
            return {"message": "没有需要更新的数据"}
        
        # 更新Supabase
        result = supabase.table("essay_sessions").update(update_data).eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="文书会话不存在")
        
        return {"message": "文书会话更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文书会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新文书会话失败: {str(e)}")


@router.get("/")
def list_essay_sessions(
    student_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """获取文书会话列表"""
    try:
        query = supabase.table("essay_sessions").select("*", count="exact")
        
        # 如果提供了student_id，进行过滤
        if student_id:
            query = query.eq("student_id", student_id)
        else:
            # 默认使用"guest"
            query = query.eq("student_id", "guest")
        
        # 按更新时间降序排序（最近修改的在前）
        query = query.order("updated_at", desc=True)
        
        # 分页
        query = query.range(offset, offset + limit - 1)
        
        result = query.execute()
        
        # 解析JSON字段
        sessions = []
        for item in result.data:
            try:
                sessions.append({
                    "id": item["id"],
                    "student_id": item.get("student_id"),
                    "session_name": item.get("session_name"),
                    "essay_type": item.get("essay_type", ""),
                    "setup": json.loads(item["setup"]) if isinstance(item.get("setup"), str) else item.get("setup", {}),
                    "messages": json.loads(item["messages"]) if isinstance(item.get("messages"), str) else item.get("messages", []),
                    "current_essay": item.get("current_essay"),
                    "setup_complete": item.get("setup_complete", False),
                    "created_at": item.get("created_at", ""),
                    "updated_at": item.get("updated_at", ""),
                })
            except json.JSONDecodeError as e:
                logger.warning(f"解析会话JSON失败: {e}, 会话ID: {item.get('id')}")
                continue
        
        return {
            "count": result.count if hasattr(result, 'count') else len(sessions),
            "items": sessions,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"获取文书会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文书会话列表失败: {str(e)}")


@router.get("/{session_id}")
def get_essay_session(session_id: int):
    """获取单个文书会话详情"""
    try:
        result = supabase.table("essay_sessions").select("*").eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="文书会话不存在")
        
        item = result.data[0]
        
        # 解析JSON字段
        session = {
            "id": item["id"],
            "student_id": item.get("student_id"),
            "session_name": item.get("session_name"),
            "essay_type": item.get("essay_type", ""),
            "setup": json.loads(item["setup"]) if isinstance(item.get("setup"), str) else item.get("setup", {}),
            "messages": json.loads(item["messages"]) if isinstance(item.get("messages"), str) else item.get("messages", []),
            "current_essay": item.get("current_essay"),
            "setup_complete": item.get("setup_complete", False),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        }
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文书会话详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文书会话详情失败: {str(e)}")


@router.get("/latest/by-student")
def get_latest_essay_session(student_id: Optional[str] = None):
    """获取学生最新的文书会话"""
    try:
        query = supabase.table("essay_sessions").select("*")
        
        # 如果提供了student_id，进行过滤
        if student_id:
            query = query.eq("student_id", student_id)
        else:
            # 默认使用"guest"
            query = query.eq("student_id", "guest")
        
        # 按更新时间降序排序，取第一条
        query = query.order("updated_at", desc=True).limit(1)
        
        result = query.execute()
        
        if not result.data:
            return None
        
        item = result.data[0]
        
        # 解析JSON字段
        session = {
            "id": item["id"],
            "student_id": item.get("student_id"),
            "session_name": item.get("session_name"),
            "essay_type": item.get("essay_type", ""),
            "setup": json.loads(item["setup"]) if isinstance(item.get("setup"), str) else item.get("setup", {}),
            "messages": json.loads(item["messages"]) if isinstance(item.get("messages"), str) else item.get("messages", []),
            "current_essay": item.get("current_essay"),
            "setup_complete": item.get("setup_complete", False),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        }
        
        return session
        
    except Exception as e:
        logger.error(f"获取最新文书会话失败: {e}", exc_info=True)
        # 如果出错，返回None而不是抛出异常
        return None


@router.delete("/{session_id}")
def delete_essay_session(session_id: int):
    """删除文书会话"""
    try:
        result = supabase.table("essay_sessions").delete().eq("id", session_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="文书会话不存在")
        
        return {"message": "文书会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文书会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除文书会话失败: {str(e)}")

