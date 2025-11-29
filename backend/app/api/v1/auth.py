# app/api/v1/auth.py
"""
用户认证模块 - 简单的登录/注册系统
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.services.supabase_client import supabase
import hashlib
import secrets

router = APIRouter(prefix="/auth", tags=["Auth"])


# ===============================
# 数据模型
# ===============================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    created_at: Optional[str] = None


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


# ===============================
# 工具函数
# ===============================
def hash_password(password: str) -> str:
    """简单的密码哈希（生产环境应使用 bcrypt）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def generate_token() -> str:
    """生成简单的token"""
    return secrets.token_urlsafe(32)


# ===============================
# API 端点
# ===============================
@router.post("/register", response_model=UserResponse)
def register(user: UserRegister):
    """
    用户注册
    """
    try:
        # 检查用户是否已存在
        existing = supabase.table("users").select("*").eq("email", user.email).execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="该邮箱已被注册")
        
        # 创建新用户
        user_data = {
            "email": user.email,
            "password_hash": hash_password(user.password),
            "name": user.name,
            "created_at": datetime.now().isoformat(),
        }
        
        result = supabase.table("users").insert(user_data).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=500, detail="注册失败")
        
        user_data = result.data[0]
        return UserResponse(
            id=str(user_data["id"]),
            email=user_data["email"],
            name=user_data["name"],
            created_at=user_data.get("created_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=LoginResponse)
def login(credentials: UserLogin):
    """
    用户登录
    """
    try:
        # 查找用户
        result = supabase.table("users").select("*").eq("email", credentials.email).execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        user_data = result.data[0]
        password_hash = user_data.get("password_hash", "")
        
        # 验证密码
        if not verify_password(credentials.password, password_hash):
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        # 生成token
        token = generate_token()
        
        # 保存token（可选：将token存储到数据库，用于验证）
        # 这里简化处理，直接返回token
        
        return LoginResponse(
            token=token,
            user=UserResponse(
                id=str(user_data["id"]),
                email=user_data["email"],
                name=user_data.get("name", ""),
                created_at=user_data.get("created_at")
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/verify")
def verify_token(token: str):
    """
    验证token（简化版本）
    """
    # 简化实现：实际应该从数据库验证token
    return {"valid": True}


@router.get("/me", response_model=UserResponse)
def get_current_user(token: str):
    """
    获取当前用户信息
    """
    # 简化实现：实际应该从token中解析用户信息
    try:
        # 这里应该从token解析用户ID，暂时简化
        # 实际应该使用JWT或从数据库查询token对应的用户
        return {"message": "需要实现token验证逻辑"}
    except Exception as e:
        raise HTTPException(status_code=401, detail="未授权")

