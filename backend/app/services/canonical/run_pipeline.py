# app/services/canonical/run_pipeline.py
"""
规范化管道运行模块
批量处理所有表，更新canonical_program_id和category
支持暂停/恢复和断点续传
"""
from typing import Dict, Any, Optional
import logging
import threading

from app.services.supabase_client import supabase
from .canonical_mapper import map_to_canonical
from .category_classifier import classify_category

logger = logging.getLogger(__name__)

# 全局状态管理（用于暂停/恢复）
_pipeline_state = {
    "is_running": False,
    "is_paused": False,
    "should_stop": False,
    "current_table": None,
    "last_processed_id": None,
    "progress": {
        "programs_processed": 0,
        "programs_total": 0,
        "stats_processed": 0,
        "stats_total": 0,
        "cases_processed": 0,
        "cases_total": 0,
    }
}
_state_lock = threading.Lock()


def pause_pipeline():
    """暂停管道处理"""
    with _state_lock:
        _pipeline_state["is_paused"] = True
        logger.info("管道已暂停")
    return {"status": "paused", "message": "管道已暂停"}


def resume_pipeline():
    """恢复管道处理"""
    with _state_lock:
        _pipeline_state["is_paused"] = False
        logger.info("管道已恢复")
    return {"status": "resumed", "message": "管道已恢复"}


def stop_pipeline():
    """停止管道处理"""
    with _state_lock:
        _pipeline_state["should_stop"] = True
        _pipeline_state["is_paused"] = False
        logger.info("管道已停止")
    return {"status": "stopped", "message": "管道已停止"}


def get_pipeline_status() -> Dict[str, Any]:
    """获取管道当前状态"""
    with _state_lock:
        return {
            "is_running": _pipeline_state["is_running"],
            "is_paused": _pipeline_state["is_paused"],
            "current_table": _pipeline_state["current_table"],
            "last_processed_id": _pipeline_state["last_processed_id"],
            "progress": _pipeline_state["progress"].copy()
        }


def reset_pipeline_state():
    """重置管道状态（用于重新开始）"""
    with _state_lock:
        _pipeline_state["is_running"] = False
        _pipeline_state["is_paused"] = False
        _pipeline_state["should_stop"] = False
        _pipeline_state["current_table"] = None
        _pipeline_state["last_processed_id"] = None
        _pipeline_state["progress"] = {
            "programs_processed": 0,
            "programs_total": 0,
            "stats_processed": 0,
            "stats_total": 0,
            "cases_processed": 0,
            "cases_total": 0,
        }


def run_pipeline(
    resume_from_id: Optional[int] = None,
    resume_from_table: Optional[str] = None,
    only_unmatched: bool = True
) -> Dict[str, Any]:
    """
    运行完整的规范化管道
    
    Args:
        resume_from_id: 从指定ID继续处理（断点续传）
        resume_from_table: 从指定表继续处理（"programs", "ic_program_stats", "cases"）
        only_unmatched: 如果为True，只处理canonical_program_id为空的记录
    
    Returns:
        处理结果
    """
    with _state_lock:
        if _pipeline_state["is_running"]:
            return {
                "status": "error",
                "message": "管道正在运行中，请先暂停或停止",
                "programs_updated": 0,
                "stats_updated": 0,
                "cases_updated": 0
            }
        _pipeline_state["is_running"] = True
        _pipeline_state["is_paused"] = False
        _pipeline_state["should_stop"] = False
    
    try:
        logger.info("开始运行规范化管道...")
        if resume_from_id and resume_from_table:
            logger.info(f"从 {resume_from_table} 表的 ID {resume_from_id} 继续处理")
        if only_unmatched:
            logger.info("只处理未匹配的记录（canonical_program_id为空）")
        
        # 0. 检查数据库连接和规范化项目表是否存在
        # 强制从数据库重新加载最新数据（不使用任何缓存）
        try:
            logger.info("正在从数据库加载最新的规范化项目列表...")
            canonical_data = supabase.table("canonical_programs").select("*").execute().data
            if canonical_data is None:
                logger.warning("规范化项目表为空或不存在，停止管道运行")
                with _state_lock:
                    _pipeline_state["is_running"] = False
                return {
                    "status": "stopped",
                    "message": "规范化项目表为空或不存在，请先创建canonical_programs表",
                    "programs_updated": 0,
                    "stats_updated": 0,
                    "cases_updated": 0
                }
        except Exception as e:
            logger.error(f"无法连接到数据库或表不存在: {e}")
            with _state_lock:
                _pipeline_state["is_running"] = False
            return {
                "status": "error",
                "message": f"数据库连接失败: {str(e)}",
                "programs_updated": 0,
                "stats_updated": 0,
                "cases_updated": 0
            }
        
        logger.info(f"✅ 成功加载了 {len(canonical_data)} 个规范化项目（最新数据）")
        # 打印前几个项目名称用于验证
        if canonical_data:
            sample_names = [c.get("canonical_program_name_en", "N/A") for c in canonical_data[:3]]
            logger.info(f"示例项目: {', '.join(sample_names)}")
        
        if len(canonical_data) == 0:
            logger.warning("规范化项目列表为空，停止管道运行")
            with _state_lock:
                _pipeline_state["is_running"] = False
            return {
                "status": "stopped",
                "message": "规范化项目列表为空，请先添加规范化项目",
                "programs_updated": 0,
                "stats_updated": 0,
                "cases_updated": 0
            }
        
        # 2. 处理programs表
        with _state_lock:
            _pipeline_state["current_table"] = "programs"
        
        try:
            query = supabase.table("programs").select("*")
            # 如果设置了只处理未匹配的记录，添加过滤条件
            if only_unmatched:
                query = query.is_("canonical_program_id", "null")
            # 如果设置了断点续传，从指定ID开始
            if resume_from_table == "programs" and resume_from_id:
                query = query.gt("id", resume_from_id)
            query = query.order("id")
            programs = query.execute().data
        except Exception as e:
            logger.error(f"无法读取programs表: {e}")
            programs = []
        
        with _state_lock:
            _pipeline_state["progress"]["programs_total"] = len(programs)
            _pipeline_state["progress"]["programs_processed"] = 0
        
        programs_updated = 0
        
        for p in programs:
            # 检查是否需要暂停或停止
            with _state_lock:
                if _pipeline_state["should_stop"]:
                    logger.info("收到停止信号，停止处理")
                    with _state_lock:
                        _pipeline_state["is_running"] = False
                    return {
                        "status": "stopped",
                        "message": "管道已停止",
                        "programs_updated": programs_updated,
                        "stats_updated": 0,
                        "cases_updated": 0,
                        "last_processed_id": p.get("id"),
                        "last_processed_table": "programs"
                    }
                while _pipeline_state["is_paused"]:
                    import time
                    time.sleep(0.5)  # 等待恢复
                _pipeline_state["last_processed_id"] = p.get("id")
                _pipeline_state["progress"]["programs_processed"] += 1
            
            program_id = p.get("id")
            program_en_name = p.get("program_en_name") or ""
            requirements = p.get("requirements") or ""
            
            # 查找规范化项目ID
            cid = map_to_canonical(program_en_name, canonical_data)
            
            # 分类项目
            category = classify_category(program_en_name, requirements)
            
            # 更新数据库
            update_data = {"category": category}
            if cid:
                update_data["canonical_program_id"] = cid
            
            try:
                supabase.table("programs").update(update_data).eq("id", program_id).execute()
                programs_updated += 1
            except Exception as e:
                logger.error(f"更新program {program_id}失败: {e}")
        
        # 3. 处理ic_program_stats表
        with _state_lock:
            _pipeline_state["current_table"] = "ic_program_stats"
            _pipeline_state["last_processed_id"] = None
        
        try:
            query = supabase.table("ic_program_stats").select("*")
            if only_unmatched:
                query = query.is_("canonical_program_id", "null")
            if resume_from_table == "ic_program_stats" and resume_from_id:
                query = query.gt("id", resume_from_id)
            query = query.order("id")
            stats = query.execute().data
        except Exception as e:
            logger.error(f"无法读取ic_program_stats表: {e}")
            stats = []
        
        with _state_lock:
            _pipeline_state["progress"]["stats_total"] = len(stats)
            _pipeline_state["progress"]["stats_processed"] = 0
        
        stats_updated = 0
    
        # 无效项目名称关键词（跳过这些）
        invalid_keywords = [
            "faculty", "school", "college", "department", "research masters",
            "pg research", "masters", "phd", "doctorate", "degree"
        ]
        
        for s in stats:
            # 检查是否需要暂停或停止
            with _state_lock:
                if _pipeline_state["should_stop"]:
                    logger.info("收到停止信号，停止处理")
                    with _state_lock:
                        _pipeline_state["is_running"] = False
                    return {
                        "status": "stopped",
                        "message": "管道已停止",
                        "programs_updated": programs_updated,
                        "stats_updated": stats_updated,
                        "cases_updated": 0,
                        "last_processed_id": s.get("id"),
                        "last_processed_table": "ic_program_stats"
                    }
                while _pipeline_state["is_paused"]:
                    import time
                    time.sleep(0.5)  # 等待恢复
                _pipeline_state["last_processed_id"] = s.get("id")
                _pipeline_state["progress"]["stats_processed"] += 1
            
            stat_id = s.get("id")
            program_name = s.get("program_name") or ""
            
            # 跳过无效的项目名称（只包含学院名、学位类型等）
            if not program_name:
                continue
            
            program_name_lower = program_name.lower()
            # 如果项目名称只包含无效关键词（如"Faculty of Engineering"、"PG Research Masters"），跳过
            # 检查是否是纯学院名或学位类型（单词数少且包含无效关键词）
            word_count = len(program_name.split())
            if word_count <= 3 and any(keyword in program_name_lower for keyword in invalid_keywords):
                logger.debug(f"跳过无效项目名称（学院/学位类型）: {program_name}")
                continue
            # 如果项目名称以"Faculty of"或"School of"开头，通常是学院名，跳过
            if program_name_lower.startswith(("faculty of", "school of", "college of", "department of")):
                logger.debug(f"跳过学院名称: {program_name}")
                continue
            
            cid = map_to_canonical(program_name, canonical_data)
            
            if cid:
                try:
                    supabase.table("ic_program_stats").update({
                        "canonical_program_id": cid
                    }).eq("id", stat_id).execute()
                    stats_updated += 1
                except Exception as e:
                    logger.error(f"更新ic_program_stats {stat_id}失败: {e}")
        
        # 4. 处理cases表
        with _state_lock:
            _pipeline_state["current_table"] = "cases"
            _pipeline_state["last_processed_id"] = None
        
        try:
            query = supabase.table("cases").select("*")
            if only_unmatched:
                query = query.is_("canonical_program_id", "null")
            if resume_from_table == "cases" and resume_from_id:
                query = query.gt("id", resume_from_id)
            query = query.order("id")
            cases = query.execute().data
        except Exception as e:
            logger.error(f"无法读取cases表: {e}")
            cases = []
        
        with _state_lock:
            _pipeline_state["progress"]["cases_total"] = len(cases)
            _pipeline_state["progress"]["cases_processed"] = 0
        
        cases_updated = 0
        
        for c in cases:
            # 检查是否需要暂停或停止
            with _state_lock:
                if _pipeline_state["should_stop"]:
                    logger.info("收到停止信号，停止处理")
                    with _state_lock:
                        _pipeline_state["is_running"] = False
                    return {
                        "status": "stopped",
                        "message": "管道已停止",
                        "programs_updated": programs_updated,
                        "stats_updated": stats_updated,
                        "cases_updated": cases_updated,
                        "last_processed_id": c.get("id"),
                        "last_processed_table": "cases"
                    }
                while _pipeline_state["is_paused"]:
                    import time
                    time.sleep(0.5)  # 等待恢复
                _pipeline_state["last_processed_id"] = c.get("id")
                _pipeline_state["progress"]["cases_processed"] += 1
            
            case_id = c.get("id")
            applied_program = c.get("applied_program") or ""
            
            # 跳过无效的项目名称（使用与ic_program_stats相同的过滤逻辑）
            if not applied_program:
                continue
            
            applied_program_lower = applied_program.lower()
            word_count = len(applied_program.split())
            if word_count <= 3 and any(keyword in applied_program_lower for keyword in invalid_keywords):
                logger.debug(f"跳过无效项目名称（学院/学位类型）: {applied_program}")
                continue
            if applied_program_lower.startswith(("faculty of", "school of", "college of", "department of")):
                logger.debug(f"跳过学院名称: {applied_program}")
                continue
            
            cid = map_to_canonical(applied_program, canonical_data)
            
            if cid:
                try:
                    supabase.table("cases").update({
                        "canonical_program_id": cid
                    }).eq("id", case_id).execute()
                    cases_updated += 1
                except Exception as e:
                    logger.error(f"更新case {case_id}失败: {e}")
        
        logger.info("规范化管道运行完成")
        
        with _state_lock:
            _pipeline_state["is_running"] = False
            _pipeline_state["current_table"] = None
            _pipeline_state["last_processed_id"] = None
        
        return {
            "status": "ok",
            "programs_updated": programs_updated,
            "stats_updated": stats_updated,
            "cases_updated": cases_updated
        }
    except Exception as e:
        logger.error(f"管道运行出错: {e}", exc_info=True)
        with _state_lock:
            _pipeline_state["is_running"] = False
        return {
            "status": "error",
            "message": f"管道运行出错: {str(e)}",
            "programs_updated": programs_updated if 'programs_updated' in locals() else 0,
            "stats_updated": stats_updated if 'stats_updated' in locals() else 0,
            "cases_updated": cases_updated if 'cases_updated' in locals() else 0,
            "last_processed_id": _pipeline_state.get("last_processed_id"),
            "last_processed_table": _pipeline_state.get("current_table")
        }

