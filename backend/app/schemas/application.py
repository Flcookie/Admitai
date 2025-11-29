# app/schemas/application.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplicationPlan(BaseModel):
    id: Optional[int] = None
    student_id: str  # 学生ID（可以用用户名或邮箱，暂时用简单ID）
    program_id: int  # 项目ID（关联programs表）
    program_name: str  # 项目名称（冗余存储，便于查询）
    university: str  # 学校名称（冗余存储）
    status: str = "planned"  # 状态: planned(计划中), in_progress(申请中), submitted(已提交), accepted(已录取), rejected(已拒绝), waitlisted(候补)
    priority: int = 0  # 优先级: 0=低, 1=中, 2=高
    application_deadline: Optional[str] = None  # 申请截止日期
    notes: Optional[str] = None  # 备注
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        orm_mode = True


class ApplicationPlanCreate(BaseModel):
    student_id: str
    program_id: int
    program_name: str
    university: str
    priority: int = 0
    application_deadline: Optional[str] = None
    notes: Optional[str] = None


class ApplicationPlanUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    application_deadline: Optional[str] = None
    notes: Optional[str] = None

