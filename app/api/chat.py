"""Agent 对话 API（LangGraph 调用入口，带详细异常日志）。"""
import json
import time
import traceback
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agents.graph import graph
from app.agents.state import AgentState
from app.api.deps import get_current_active_user
from app.core.logging import logger
from app.dataplatform.collector import DataCollector

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    openid: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    finished: bool = False


def _extract_ai_reply(messages: List[Any]) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content
    return "抱歉，未生成回复，请稍后再试。"


@router.post("", summary="与健康管理 Agent 对话")
def chat(req: ChatRequest, current_user: str = Depends(get_current_active_user)):
    openid = req.openid or current_user
    start_time = time.time()
    logger.info("收到对话请求：openid={}, message={}", openid, req.message[:80])

    from app.db import database as db
    user = db.get_user_by_openid(openid)
    user_id = user["id"] if user else None

    config = {"configurable": {"thread_id": openid}}
    state: AgentState = {
        "messages": [HumanMessage(content=req.message)],
        "openid": openid,
        "user_id": user_id,
        "user_profile": None,
        "intent": None,
        "plan_content": None,
        "plan_id": None,
        "records": None,
        "knowledge_context": None,
        "next_agent": None,
        "needs_approval": False,
        "finished": False,
    }

    try:
        result = graph.invoke(state, config=config)
        reply = _extract_ai_reply(result.get("messages", []))
        duration_ms = int((time.time() - start_time) * 1000)

        DataCollector.log_event(
            openid=openid,
            event_type="chat_turn",
            service_name="chat",
            request_data={"message": req.message},
            response_data={"reply": reply[:200], "intent": result.get("intent")},
            duration_ms=duration_ms,
            status_code=200,
            api_path="/api/chat",
        )

        return ChatResponse(
            reply=reply,
            intent=result.get("intent"),
            finished=bool(result.get("finished")),
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_detail = traceback.format_exc()
        logger.error("Agent 调用失败：{}\n{}", e, error_detail)

        DataCollector.log_event(
            openid=openid,
            event_type="chat_turn",
            service_name="chat",
            request_data={"message": req.message},
            duration_ms=duration_ms,
            status_code=500,
            error_msg=str(e),
            api_path="/api/chat",
        )
        raise HTTPException(status_code=500, detail=f"Agent 内部错误：{str(e)}")
