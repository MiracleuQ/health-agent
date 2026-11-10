"""数据中台 API 路由。"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import date, timedelta

from app.api.deps import get_current_active_user
from app.dataplatform.service import DataService
from app.db import database as db

router = APIRouter(prefix="/api/v1/data", tags=["数据中台"])


@router.get("/events", summary="查询埋点事件")
def query_events(
    openid: str = Depends(get_current_active_user),
    event_type: Optional[str] = Query(None),
    service_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    data = DataService.query_events(
        openid=openid,
        event_type=event_type,
        service_name=service_name,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    total = DataService.count_events(
        openid=openid,
        event_type=event_type,
        service_name=service_name,
        start_date=start_date,
        end_date=end_date,
    )
    return {"code": 0, "data": data, "total": total, "msg": "success"}


@router.get("/dashboard", summary="数据看板聚合指标")
def dashboard(
    openid: str = Depends(get_current_active_user),
    days: int = Query(7, ge=1, le=90),
) -> Dict[str, Any]:
    return DataService.get_dashboard(openid=openid, days=days)


@router.post("/snapshot/{openid}", summary="刷新用户快照")
def refresh_snapshot(openid: str, current_user: str = Depends(get_current_active_user)):
    # 权限：只能刷新自己的快照，除非是管理员（演示版放宽）
    if current_user != openid:
        raise HTTPException(status_code=403, detail="无权操作他人快照")
    DataService.update_user_snapshot(openid)
    return {"code": 0, "msg": "success"}


@router.get("/assets", summary="列出数据资产目录")
def list_assets() -> Dict[str, Any]:
    assets = DataService.list_assets()
    return {"code": 0, "data": assets, "msg": "success"}
