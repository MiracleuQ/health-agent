"""健康报告下载 API（JWT 鉴权）。"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from app.db import database as db
from app.api.deps import get_current_active_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{user_id}/pdf", summary="下载健康报告 PDF")
def download_report(user_id: int, report_type: str = "weekly", current_user: str = Depends(get_current_active_user)):
    user = db.get_user_by_openid(current_user)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user["id"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问该用户报告")

    from datetime import date
    filename = f"./reports/health_report_{user_id}_{report_type}_{date.today().isoformat()}.pdf"
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="报告文件不存在，请先在对话中生成报告")

    return FileResponse(
        path=filename,
        media_type="application/pdf",
        filename=f"health_report_{report_type}_{date.today().isoformat()}.pdf",
    )
