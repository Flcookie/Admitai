# app/schemas/case.py
from pydantic import BaseModel
from typing import Optional, Dict, Any


class Case(BaseModel):
    id: int
    student_profile_json: Dict[str, Any]   # 存 JSON
    applied_program: Optional[str] = None
    applied_university: Optional[str] = None
    result: Optional[str] = None
    admission_year: Optional[str] = None

    class Config:
        orm_mode = True
