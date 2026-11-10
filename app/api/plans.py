"""健康计划相关 API（JWT 鉴权 + 数据中台埋点 + 人工审核）。"""
import time
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db import database as db
from app.api.deps import get_current_active_user
from app.dataplatform.collector import DataCollector

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanApprove(BaseModel):
    status: str  # "approved" 或 "rejected"


@router.get("", summary="列出用户所有历史计划")
def list_plans(current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        plans = db.list_plans(user["id"])
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_list",
            service_name="plans",
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/plans",
        )
        return {"code": 0, "data": plans, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_list",
            service_name="plans",
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/plans",
        )
        raise


@router.get("/{plan_id}", summary="获取单个计划详情")
def get_plan(plan_id: int, current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM plans WHERE id=? AND user_id=?", (plan_id, user["id"]))
        row = c.fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="计划不存在")
        result = dict(row)
        result["content"] = json.loads(result["content"])
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_get",
            service_name="plans",
            request_data={"plan_id": plan_id},
            response_data={"plan_id": plan_id, "status": result.get("status")},
            duration_ms=duration_ms,
            status_code=200,
            api_path=f"/api/plans/{plan_id}",
        )
        return {"code": 0, "data": result, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_get",
            service_name="plans",
            request_data={"plan_id": plan_id},
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path=f"/api/plans/{plan_id}",
        )
        raise


@router.post("/{plan_id}/approve", summary="人工审核计划（通过/拒绝）")
def approve_plan(plan_id: int, body: PlanApprove, current_user: str = Depends(get_current_active_user)):
    openid = current_user
    start_time = time.time()
    try:
        user = db.get_user_by_openid(openid)
        if not user:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        if body.status not in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="status 必须是 approved 或 rejected")
        ok = db.approve_plan(plan_id, body.status)
        if not ok:
            raise HTTPException(status_code=404, detail="计划不存在或无权操作")
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_approve",
            service_name="plans",
            request_data={"plan_id": plan_id, "status": body.status},
            response_data={"plan_id": plan_id, "status": body.status},
            duration_ms=duration_ms,
            status_code=200,
            api_path=f"/api/plans/{plan_id}/approve",
        )
        return {"code": 0, "data": {"plan_id": plan_id, "status": body.status}, "msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        DataCollector.log_event(
            openid=openid,
            event_type="plan_approve",
            service_name="plans",
            request_data={"plan_id": plan_id, "status": body.status},
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path=f"/api/plans/{plan_id}/approve",
        )
        raise
