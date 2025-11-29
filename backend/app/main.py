# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.programs import router as programs_router
from app.api.v1.cases import router as cases_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.recommend_v2 import router as recommend_v2_router
from app.api.v1.essay import router as essay_router
from app.api.v1.applications import router as applications_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.essay_sessions import router as essay_sessions_router
from app.api.v1.auth import router as auth_router
from app.api.v1.canonical import router as canonical_router
from app.api.v1.ic_stats import router as ic_stats_router
from app.api.v1.admin import router as admin_router

app = FastAPI(
    title="Study Abroad AI Backend",
    version="0.1.0",
)

# 允许前端访问（先全开，之后再收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # MVP 阶段先不限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


# 注册路由
app.include_router(auth_router)
app.include_router(programs_router)
app.include_router(cases_router)
app.include_router(recommend_router)
app.include_router(recommend_v2_router)
app.include_router(essay_router)
app.include_router(applications_router)
app.include_router(recommendations_router)
app.include_router(essay_sessions_router)
app.include_router(canonical_router)
app.include_router(ic_stats_router)
app.include_router(admin_router)
