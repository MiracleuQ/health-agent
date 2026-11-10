"""每日打卡记录 API（JWT 鉴权 + 数据中台埋点）。"""
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, timedelta

from app.db import database as db
from app.api.deps import get_current_active_user
from app.dataplatform.collector import DataCollector

router = APIRouter(prefix="/api/records", tags=["records"])


class RecordIn(BaseModel):
    date: Optional[str] = None
    weight_kg: Optional[float] = None
    calories_eaten: Optional[int] = None
    workout_minutes: Optional[int] = None
    water_ml: Optional[int] = None
    note: Optional[str] = None


@router.post("", summary="添加每日打卡记录")
def add_record(record: RecordIn, current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        record_id = db.add_record(user["id"], record.model_dump(exclude_unset=True))
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_add",
            service_name="records",
            request_data=record.model_dump(exclude_unset=True),
            response_data={"record_id": record_id},
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/records",
        )
        return {"code": 0, "data": {"record_id": record_id}, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_add",
            service_name="records",
            request_data=record.model_dump(exclude_unset=True),
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/records",
        )
        raise


@router.get("/recent", summary="获取最近打卡记录")
def get_recent_records(limit: int = 7, current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        records = db.get_recent_records(user["id"], limit)
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_query",
            service_name="records",
            request_data={"limit": limit},
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/records/recent",
        )
        return {"code": 0, "data": records, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_query",
            service_name="records",
            request_data={"limit": limit},
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/records/recent",
        )
        raise


@router.get("/chart", summary="获取图表数据（指定天数内记录）")
def get_chart(days: int = 30, current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        end = date.today()
        start = end - timedelta(days=days - 1)
        records = db.get_records_by_date_range(user["id"], start.isoformat(), end.isoformat())
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_chart",
            service_name="records",
            request_data={"days": days},
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/records/chart",
        )
        return {"code": 0, "data": {"records": records, "days": days, "start": start.isoformat(), "end": end.isoformat()}, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="record_chart",
            service_name="records",
            request_data={"days": days},
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/records/chart",
        )
        raise
