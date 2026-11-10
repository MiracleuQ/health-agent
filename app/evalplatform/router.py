"""评测中台 API 路由。"""
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.api.deps import get_current_active_user
from app.evalplatform.datasets import load_dataset, save_dataset, DEFAULT_DATASET
from app.evalplatform.runner import EvalRunner
from app.evalplatform.metrics import calculate_metrics
from app.evalplatform.report import generate_html_report
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/eval", tags=["评测中台"])

# 内存中保存最近一次评测结果（生产环境应存入数据库）
LAST_RUN_RESULT: Optional[Dict[str, Any]] = None


class EvalRunRequest(BaseModel):
    dataset_path: Optional[str] = None
    openid: Optional[str] = "eval_user"


class EvalRunResponse(BaseModel):
    run_id: str
    total_cases: int
    intent_accuracy: float
    tool_match_rate: float
    safety_rate: float


@router.post("/run", summary="执行离线评测", response_model=EvalRunResponse)
def run_eval(req: EvalRunRequest, current_user: str = Depends(get_current_active_user)):
    global LAST_RUN_RESULT
    try:
        dataset = load_dataset(req.dataset_path)
        runner = EvalRunner(dataset=dataset, openid=req.openid or "eval_user")
        result = runner.run_batch()
        LAST_RUN_RESULT = result

        # 生成 HTML 报告
        report_path = generate_html_report(result, output_path=f"./eval_report_{result['run_id']}.html")
        result["report_path"] = report_path

        logger.info("评测完成：run_id={}, intent_acc={}, safety_rate={}",
                    result["run_id"], result["intent_accuracy"], result["safety_rate"])

        return EvalRunResponse(
            run_id=result["run_id"],
            total_cases=result["total_cases"],
            intent_accuracy=result["intent_accuracy"],
            tool_match_rate=result["tool_match_rate"],
            safety_rate=result["safety_rate"],
        )
    except Exception as e:
        logger.exception("评测执行失败：{}", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/result", summary="获取最近一次评测结果")
def get_result(current_user: str = Depends(get_current_active_user)):
    if LAST_RUN_RESULT is None:
        raise HTTPException(status_code=404, detail="暂无评测结果，请先运行评测")
    return {"code": 0, "data": LAST_RUN_RESULT, "msg": "success"}


@router.get("/report/{run_id}", summary="获取评测报告文件")
def get_report(run_id: str, current_user: str = Depends(get_current_active_user)):
    path = f"./eval_report_{run_id}.html"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(path=path, media_type="text/html", filename=f"eval_report_{run_id}.html")


@router.get("/dataset", summary="获取内置数据集")
def get_dataset(current_user: str = Depends(get_current_active_user)):
    return {"code": 0, "data": DEFAULT_DATASET, "msg": "success"}
