"""FastAPI 应用入口（生产级）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.api import users, plans, records, chat, auth, reports
from app.dataplatform.router import router as data_router
from app.evalplatform.router import router as eval_router
from app.dataplatform.models import init_dataplatform_tables

app = FastAPI(
    title="AI 健康管理 Agent API",
    description="基于 LangGraph 多代理框架的健康管理大模型应用（生产级版本）",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(plans.router)
app.include_router(records.router)
app.include_router(chat.router)
app.include_router(reports.router)
app.include_router(data_router)
app.include_router(eval_router)


@app.on_event("startup")
def startup():
    from app.db.database import init_db
    init_db()
    init_dataplatform_tables()
    logger.info("FastAPI 应用启动完成，数据中台表已初始化")


@app.get("/", summary="健康检查")
def root():
    return {"service": "health-agent", "status": "ok", "version": "2.0.0"}
