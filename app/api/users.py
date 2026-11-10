"""用户相关 API（JWT 鉴权 + 数据中台埋点）。"""
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db import database as db
from app.api.deps import get_current_active_user
from app.dataplatform.collector import DataCollector

router = APIRouter(prefix="/api/users", tags=["users"])


class ProfileIn(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    activity_level: Optional[str] = None
    goal: Optional[str] = None
    target_calories: Optional[int] = None
    training_weeks: Optional[int] = None


@router.post("/profile", summary="保存/更新用户健康档案")
def save_profile(profile: ProfileIn, current_user: str = Depends(get_current_active_user)):
    start_time = time.time()
    openid = current_user
    try:
        user_id = db.upsert_user(openid, profile.model_dump(exclude_unset=True))
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="profile_save",
            service_name="users",
            request_data=profile.model_dump(exclude_unset=True),
            response_data={"user_id": user_id},
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/users/profile",
        )
        return {"code": 0, "data": {"user_id": user_id, "openid": openid}, "msg": "success"}
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="profile_save",
            service_name="users",
            request_data=profile.model_dump(exclude_unset=True),
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/users/profile",
        )
        raise


@router.get("/profile", summary="查询用户健康档案")
def get_profile(current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="profile_query",
            service_name="users",
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/users/profile",
        )
        return {"code": 0, "data": user, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="profile_query",
            service_name="users",
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/users/profile",
        )
        raise
