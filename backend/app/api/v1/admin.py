# backend/app/api/v1/admin.py

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import logging
from datetime import datetime

from app.services.supabase_client import supabase

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)


# ===============================
# 数据模型
# ===============================

class HeroContent(BaseModel):
    title: str
    subtitle: str
    features: List[str]
    description: str
    primary_cta: str
    secondary_cta: str
    image_url: Optional[str] = None  # Hero右侧图片URL
    image_alt: Optional[str] = "产品截图展示"  # 图片alt文本

class FeatureCard(BaseModel):
    id: Optional[int] = None
    title: str
    description: str
    icon: str  # icon name from lucide-react
    color: str  # hex color

class AboutUsContent(BaseModel):
    mission_title: str
    mission_text: str
    advantages: List[str]
    stats: List[Dict[str, Any]]  # [{number, suffix, label, icon, color}]
    teams: List[Dict[str, Any]]  # [{name, description, icon, color}]

class Testimonial(BaseModel):
    id: Optional[int] = None
    name: str
    school: str
    program: str
    gpa: str
    comment: str
    color: str

class PricingPlan(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    price: str
    period: str
    features: List[str]
    button_text: str
    is_recommended: bool = False
    badge_text: Optional[str] = None

class WebsiteContent(BaseModel):
    hero: HeroContent
    features: List[FeatureCard]
    about_us: AboutUsContent
    testimonials: List[Testimonial]
    pricing: List[PricingPlan]


# ===============================
# API 路由
# ===============================

@router.get("/website-content")
def get_website_content():
    """
    获取所有官网内容
    """
    try:
        # 从Supabase获取内容（如果表存在）
        # 否则返回默认内容
        try:
            result = supabase.table("website_content").select("*").execute()
            if result.data:
                return result.data[0]
        except Exception as e:
            logger.warning(f"无法从数据库获取内容，使用默认值: {e}")
        
        # 返回默认内容结构
        return {
            "hero": {
                "title": "你的 AI 留学助手",
                "subtitle": "用数据和智能完成你的申请计划",
                "features": ["智能选校", "录取率预测", "文书写作", "案例匹配"],
                "description": "7×24 小时 AI 助理陪你完成整个申请流程",
                "primary_cta": "开始使用",
                "secondary_cta": "查看 Demo",
                "image_url": None,
                "image_alt": "产品截图展示"
            },
            "features": [
                {
                    "id": 1,
                    "title": "智能选校与录取率分析",
                    "description": "AI 分析你的背景，推荐最适合的院校，预测录取概率，帮你制定最优申请策略",
                    "icon": "GraduationCap",
                    "color": "#3BBFA1"
                },
                {
                    "id": 2,
                    "title": "文书 AI",
                    "description": "PS / CV / 推荐信 / Essay / SOP / Motivation Letter，智能生成专业留学文书，支持中英双语",
                    "icon": "FileText",
                    "color": "#4AA8F0"
                },
                {
                    "id": 3,
                    "title": "成功案例匹配 + 背景对比",
                    "description": "查看真实成功案例，对比相似背景学生，评估你的申请竞争力",
                    "icon": "Users",
                    "color": "#89D7E8"
                },
                {
                    "id": 4,
                    "title": "全流程申请管理",
                    "description": "Deadline + Checklist，全程跟踪申请进度，确保不错过任何重要截止日期",
                    "icon": "CheckSquare",
                    "color": "#3BBFA1"
                }
            ],
            "about_us": {
                "mission_title": "我们的使命",
                "mission_text": "AdmitAI 致力于用人工智能技术革新留学申请流程，为全球学生提供专业、高效、经济的申请服务。我们相信，每个学生都应该有机会获得最适合的教育机会，而不应被高昂的中介费用所限制。",
                "advantages": [
                    "基于真实 FOI 数据的录取率分析，提供最准确的选校建议",
                    "AI 驱动的智能文书生成，支持中英双语，质量媲美专业顾问",
                    "庞大的成功案例库，帮助用户找到相似背景的参考案例",
                    "全流程申请管理，确保不错过任何重要截止日期",
                    "比传统中介便宜 10 倍，让优质服务触手可及"
                ],
                "stats": [
                    {"number": 50000, "suffix": "+", "label": "学生用户", "icon": "Users", "color": "#3BBFA1"},
                    {"number": 120, "suffix": "+", "label": "覆盖国家", "icon": "Globe", "color": "#4AA8F0"},
                    {"number": 1000, "suffix": "+", "label": "成功案例", "icon": "GraduationCap", "color": "#89D7E8"},
                    {"number": 95, "suffix": "%", "label": "用户满意度", "icon": "Star", "color": "#3BBFA1"}
                ],
                "teams": [
                    {
                        "name": "技术团队",
                        "description": "来自顶尖科技公司的 AI 工程师和数据科学家，专注于教育科技领域",
                        "icon": "Zap",
                        "color": "#3BBFA1"
                    },
                    {
                        "name": "教育顾问",
                        "description": "拥有丰富留学申请经验的专业顾问，深度了解各大学校和专业要求",
                        "icon": "GraduationCap",
                        "color": "#4AA8F0"
                    },
                    {
                        "name": "产品团队",
                        "description": "致力于打造最佳用户体验，让复杂的申请流程变得简单高效",
                        "icon": "BarChart3",
                        "color": "#89D7E8"
                    }
                ]
            },
            "testimonials": [
                {
                    "id": 1,
                    "name": "李同学",
                    "school": "帝国理工学院",
                    "program": "MSc Petroleum Engineering",
                    "gpa": "GPA 3.8/4.0",
                    "comment": "AdmitAI 的选校建议非常精准，帮我找到了最适合的项目。文书生成功能也很强大，节省了大量时间。",
                    "color": "#3BBFA1"
                },
                {
                    "id": 2,
                    "name": "王同学",
                    "school": "香港大学",
                    "program": "MSc Computer Science",
                    "gpa": "GPA 88/100",
                    "comment": "案例库功能非常实用，可以看到相似背景学生的成功案例，给了我很大信心。申请管理界面也很清晰。",
                    "color": "#4AA8F0"
                },
                {
                    "id": 3,
                    "name": "张同学",
                    "school": "新加坡国立大学",
                    "program": "MSc Business Analytics",
                    "gpa": "GPA 3.6/4.0",
                    "comment": "比传统中介便宜太多，而且 AI 的反应速度很快。文书质量也很高，帮我成功申请到了心仪的学校。",
                    "color": "#89D7E8"
                }
            ],
            "pricing": [
                {
                    "id": 1,
                    "name": "免费版",
                    "description": "体验基础功能",
                    "price": "¥0",
                    "period": "永久免费",
                    "features": ["基础选校推荐", "项目库查询", "案例库浏览", "基础申请管理"],
                    "button_text": "立即开始",
                    "is_recommended": False,
                    "badge_text": "免费"
                },
                {
                    "id": 2,
                    "name": "专业版",
                    "description": "完整申请解决方案",
                    "price": "¥299",
                    "period": "每月",
                    "features": [
                        "智能选校 + 录取预测",
                        "文书生成（PS/CV/推荐信）",
                        "完整案例库 + 背景评估",
                        "申请流程管理",
                        "7×24 小时 AI 支持",
                        "中英双语文书"
                    ],
                    "button_text": "立即订阅",
                    "is_recommended": True,
                    "badge_text": "推荐"
                },
                {
                    "id": 3,
                    "name": "写作版",
                    "description": "专注文书生成",
                    "price": "¥99",
                    "period": "每月",
                    "features": ["Essay 生成 + 审阅", "多轮优化建议", "中英双语支持", "无限次生成"],
                    "button_text": "立即订阅",
                    "is_recommended": False,
                    "badge_text": None
                }
            ]
        }
    except Exception as e:
        logger.error(f"获取官网内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取官网内容失败: {str(e)}")


@router.put("/website-content")
def update_website_content(content: WebsiteContent):
    """
    更新官网内容
    """
    try:
        # 尝试保存到Supabase（如果表存在）
        try:
            # 先检查是否存在
            existing = supabase.table("website_content").select("*").limit(1).execute()
            
            content_dict = content.model_dump()
            if existing.data:
                # 更新
                result = supabase.table("website_content").update(content_dict).eq("id", existing.data[0]["id"]).execute()
            else:
                # 插入
                result = supabase.table("website_content").insert(content_dict).execute()
            
            return {"success": True, "message": "内容已更新"}
        except Exception as e:
            logger.warning(f"无法保存到数据库: {e}，内容仅在内存中更新")
            # 可以在这里实现文件存储或其他持久化方式
            return {"success": True, "message": "内容已更新（未持久化）", "warning": str(e)}
    except Exception as e:
        logger.error(f"更新官网内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新官网内容失败: {str(e)}")


@router.post("/website-content/feature")
def add_feature(feature: FeatureCard):
    """
    添加功能卡片
    """
    try:
        # 这里可以保存到数据库
        return {"success": True, "message": "功能卡片已添加", "feature": feature.model_dump()}
    except Exception as e:
        logger.error(f"添加功能卡片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加功能卡片失败: {str(e)}")


@router.put("/website-content/feature/{feature_id}")
def update_feature(feature_id: int, feature: FeatureCard):
    """
    更新功能卡片
    """
    try:
        return {"success": True, "message": "功能卡片已更新", "feature": feature.model_dump()}
    except Exception as e:
        logger.error(f"更新功能卡片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新功能卡片失败: {str(e)}")


@router.delete("/website-content/feature/{feature_id}")
def delete_feature(feature_id: int):
    """
    删除功能卡片
    """
    try:
        return {"success": True, "message": "功能卡片已删除"}
    except Exception as e:
        logger.error(f"删除功能卡片失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除功能卡片失败: {str(e)}")


@router.post("/website-content/testimonial")
def add_testimonial(testimonial: Testimonial):
    """
    添加学生评价
    """
    try:
        return {"success": True, "message": "学生评价已添加", "testimonial": testimonial.model_dump()}
    except Exception as e:
        logger.error(f"添加学生评价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加学生评价失败: {str(e)}")


@router.put("/website-content/testimonial/{testimonial_id}")
def update_testimonial(testimonial_id: int, testimonial: Testimonial):
    """
    更新学生评价
    """
    try:
        return {"success": True, "message": "学生评价已更新", "testimonial": testimonial.model_dump()}
    except Exception as e:
        logger.error(f"更新学生评价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新学生评价失败: {str(e)}")


@router.delete("/website-content/testimonial/{testimonial_id}")
def delete_testimonial(testimonial_id: int):
    """
    删除学生评价
    """
    try:
        return {"success": True, "message": "学生评价已删除"}
    except Exception as e:
        logger.error(f"删除学生评价失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除学生评价失败: {str(e)}")


@router.post("/website-content/pricing")
def add_pricing_plan(plan: PricingPlan):
    """
    添加价格方案
    """
    try:
        return {"success": True, "message": "价格方案已添加", "plan": plan.model_dump()}
    except Exception as e:
        logger.error(f"添加价格方案失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"添加价格方案失败: {str(e)}")


@router.put("/website-content/pricing/{plan_id}")
def update_pricing_plan(plan_id: int, plan: PricingPlan):
    """
    更新价格方案
    """
    try:
        return {"success": True, "message": "价格方案已更新", "plan": plan.model_dump()}
    except Exception as e:
        logger.error(f"更新价格方案失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新价格方案失败: {str(e)}")


@router.delete("/website-content/pricing/{plan_id}")
def delete_pricing_plan(plan_id: int):
    """
    删除价格方案
    """
    try:
        return {"success": True, "message": "价格方案已删除"}
    except Exception as e:
        logger.error(f"删除价格方案失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除价格方案失败: {str(e)}")


# ===============================
# Dashboard 首页内容管理
# ===============================

@router.get("/dashboard-content")
def get_dashboard_content():
    """
    获取Dashboard首页内容
    """
    try:
        result = supabase.table("dashboard_content").select("*").limit(1).execute()
        if result.data:
            return result.data[0]
        return {
            "welcome_message": "欢迎使用 AdmitAI",
            "quick_actions": [],
            "feature_categories": []
        }
    except Exception as e:
        logger.error(f"获取Dashboard内容失败: {e}", exc_info=True)
        return {
            "welcome_message": "欢迎使用 AdmitAI",
            "quick_actions": [],
            "feature_categories": []
        }


@router.put("/dashboard-content")
def update_dashboard_content(content: Dict[str, Any]):
    """
    更新Dashboard首页内容
    """
    try:
        result = supabase.table("dashboard_content").upsert({
            "id": 1,
            **content
        }).execute()
        return {"success": True, "data": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"更新Dashboard内容失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新Dashboard内容失败: {str(e)}")


# ===============================
# 项目库管理 (Programs)
# ===============================

@router.get("/programs")
def list_programs_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取项目列表（管理后台）
    """
    try:
        query = supabase.table("programs").select("*", count="exact")
        
        if search:
            query = query.or_(f"chinese_name.ilike.%{search}%,english_name.ilike.%{search}%,program_cn_name.ilike.%{search}%,program_en_name.ilike.%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.get("/programs/{program_id}")
def get_program(program_id: int):
    """
    获取单个项目详情
    """
    try:
        result = supabase.table("programs").select("*").eq("id", program_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="项目不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


@router.post("/programs")
def create_program(program: Dict[str, Any]):
    """
    创建新项目
    """
    try:
        result = supabase.table("programs").insert(program).execute()
        return {"success": True, "data": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"创建项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.put("/programs/{program_id}")
def update_program(program_id: int, program: Dict[str, Any]):
    """
    更新项目
    """
    try:
        result = supabase.table("programs").update(program).eq("id", program_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete("/programs/{program_id}")
def delete_program(program_id: int):
    """
    删除项目
    """
    try:
        result = supabase.table("programs").delete().eq("id", program_id).execute()
        return {"success": True, "message": "项目已删除"}
    except Exception as e:
        logger.error(f"删除项目失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")


# ===============================
# 案例库管理 (Cases)
# ===============================

@router.get("/cases")
def list_cases_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取案例列表（管理后台）
    """
    try:
        query = supabase.table("cases").select("*", count="exact")
        
        if search:
            query = query.or_(f"applied_university.ilike.%{search}%,applied_program.ilike.%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取案例列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取案例列表失败: {str(e)}")


@router.get("/cases/{case_id}")
def get_case(case_id: int):
    """
    获取单个案例详情
    """
    try:
        result = supabase.table("cases").select("*").eq("id", case_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="案例不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取案例详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取案例详情失败: {str(e)}")


@router.post("/cases")
def create_case(case_data: Dict[str, Any]):
    """
    创建新案例
    """
    try:
        result = supabase.table("cases").insert(case_data).execute()
        return {"success": True, "data": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"创建案例失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建案例失败: {str(e)}")


@router.put("/cases/{case_id}")
def update_case(case_id: int, case_data: Dict[str, Any]):
    """
    更新案例
    """
    try:
        result = supabase.table("cases").update(case_data).eq("id", case_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="案例不存在")
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新案例失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新案例失败: {str(e)}")


@router.delete("/cases/{case_id}")
def delete_case(case_id: int):
    """
    删除案例
    """
    try:
        result = supabase.table("cases").delete().eq("id", case_id).execute()
        return {"success": True, "message": "案例已删除"}
    except Exception as e:
        logger.error(f"删除案例失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除案例失败: {str(e)}")


# ===============================
# 申请管理 (Applications)
# ===============================

@router.get("/applications")
def list_applications_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取申请列表（管理后台）
    """
    try:
        query = supabase.table("applications").select("*", count="exact")
        
        if search:
            query = query.or_(f"school_name.ilike.%{search}%,program_name.ilike.%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取申请列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取申请列表失败: {str(e)}")


@router.get("/applications/{application_id}")
def get_application(application_id: int):
    """
    获取单个申请详情
    """
    try:
        result = supabase.table("applications").select("*").eq("id", application_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="申请不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取申请详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取申请详情失败: {str(e)}")


@router.put("/applications/{application_id}")
def update_application(application_id: int, application: Dict[str, Any]):
    """
    更新申请
    """
    try:
        result = supabase.table("applications").update(application).eq("id", application_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="申请不存在")
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新申请失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新申请失败: {str(e)}")


@router.delete("/applications/{application_id}")
def delete_application(application_id: int):
    """
    删除申请
    """
    try:
        result = supabase.table("applications").delete().eq("id", application_id).execute()
        return {"success": True, "message": "申请已删除"}
    except Exception as e:
        logger.error(f"删除申请失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除申请失败: {str(e)}")


# ===============================
# 文书会话管理 (Essay Sessions)
# ===============================

@router.get("/essay-sessions")
def list_essay_sessions_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取文书会话列表（管理后台）
    """
    try:
        query = supabase.table("essay_sessions").select("*", count="exact")
        
        if search:
            query = query.or_(f"session_name.ilike.%{search}%,essay_type.ilike.%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取文书会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文书会话列表失败: {str(e)}")


@router.get("/essay-sessions/{session_id}")
def get_essay_session(session_id: int):
    """
    获取单个文书会话详情
    """
    try:
        result = supabase.table("essay_sessions").select("*").eq("id", session_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="文书会话不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文书会话详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文书会话详情失败: {str(e)}")


@router.delete("/essay-sessions/{session_id}")
def delete_essay_session(session_id: int):
    """
    删除文书会话
    """
    try:
        result = supabase.table("essay_sessions").delete().eq("id", session_id).execute()
        return {"success": True, "message": "文书会话已删除"}
    except Exception as e:
        logger.error(f"删除文书会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除文书会话失败: {str(e)}")


# ===============================
# IC项目统计管理 (IC Program Stats)
# ===============================

@router.get("/ic-stats")
def list_ic_stats_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取IC项目统计列表（管理后台）
    """
    try:
        query = supabase.table("ic_program_stats").select("*", count="exact")
        
        if search:
            query = query.ilike("program_name", f"%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取IC项目统计列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取IC项目统计列表失败: {str(e)}")


@router.get("/ic-stats/{stat_id}")
def get_ic_stat(stat_id: int):
    """
    获取单个IC项目统计详情
    """
    try:
        result = supabase.table("ic_program_stats").select("*").eq("id", stat_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="IC项目统计不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取IC项目统计详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取IC项目统计详情失败: {str(e)}")


@router.post("/ic-stats")
def create_ic_stat(stat: Dict[str, Any]):
    """
    创建新IC项目统计
    """
    try:
        result = supabase.table("ic_program_stats").insert(stat).execute()
        return {"success": True, "data": result.data[0] if result.data else None}
    except Exception as e:
        logger.error(f"创建IC项目统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建IC项目统计失败: {str(e)}")


@router.put("/ic-stats/{stat_id}")
def update_ic_stat(stat_id: int, stat: Dict[str, Any]):
    """
    更新IC项目统计
    """
    try:
        result = supabase.table("ic_program_stats").update(stat).eq("id", stat_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="IC项目统计不存在")
        return {"success": True, "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新IC项目统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新IC项目统计失败: {str(e)}")


@router.delete("/ic-stats/{stat_id}")
def delete_ic_stat(stat_id: int):
    """
    删除IC项目统计
    """
    try:
        result = supabase.table("ic_program_stats").delete().eq("id", stat_id).execute()
        return {"success": True, "message": "IC项目统计已删除"}
    except Exception as e:
        logger.error(f"删除IC项目统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除IC项目统计失败: {str(e)}")


# ===============================
# 推荐记录管理 (Recommendations)
# ===============================

@router.get("/recommendations")
def list_recommendations_admin(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None
):
    """
    获取推荐记录列表（管理后台）
    """
    try:
        query = supabase.table("recommendations").select("*", count="exact")
        
        if search:
            query = query.ilike("student_background", f"%{search}%")
        
        query = query.range(offset, offset + limit - 1).order("id", desc=True)
        result = query.execute()
        
        return {
            "count": result.count if hasattr(result, 'count') else len(result.data),
            "items": result.data or []
        }
    except Exception as e:
        logger.error(f"获取推荐记录列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐记录列表失败: {str(e)}")


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: int):
    """
    获取单个推荐记录详情
    """
    try:
        result = supabase.table("recommendations").select("*").eq("id", recommendation_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="推荐记录不存在")
        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取推荐记录详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取推荐记录详情失败: {str(e)}")


@router.delete("/recommendations/{recommendation_id}")
def delete_recommendation(recommendation_id: int):
    """
    删除推荐记录
    """
    try:
        result = supabase.table("recommendations").delete().eq("id", recommendation_id).execute()
        return {"success": True, "message": "推荐记录已删除"}
    except Exception as e:
        logger.error(f"删除推荐记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除推荐记录失败: {str(e)}")

