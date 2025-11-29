# app/schemas/program.py
from pydantic import BaseModel
from typing import Optional


class Program(BaseModel):
    id: int
    chinese_name: str
    english_name: str
    location: Optional[str] = None
    school: Optional[str] = None
    program_cn_name: Optional[str] = None
    program_en_name: Optional[str] = None
    objectives: Optional[str] = None
    requirements: Optional[str] = None
    language_requirement: Optional[str] = None
    duration: Optional[str] = None
    open_date: Optional[str] = None
    deadline: Optional[str] = None
    intake_seasion: Optional[str] = None
    estimated_cost: Optional[str] = None
    curriculum_detail: Optional[str] = None
    other: Optional[str] = None

    class Config:
        orm_mode = True
