"""数据中台埋点采集器：自动记录业务事件、API 调用、Agent 对话、工具调用等。"""
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from functools import wraps

from app.db import database as db


class DataCollector:
    """数据中台埋点采集器（单例模式）。"""

    @staticmethod
    def generate_trace_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def mask_pii(text: Optional[str]) -> Optional[str]:
        """脱敏个人敏感信息（手机号、邮箱、姓名等）。"""
        if text is None:
            return None
        import re
        # 手机号脱敏：138****1234
        text = re.sub(r"1\d{10}", lambda m: m.group()[:3] + "****" + m.group()[-4:], text)
        # 邮箱脱敏：ab****@example.com
        text = re.sub(
            r"[\w\.-]+@[\w\.-]+",
            lambda m: (m.group().split("@")[0][:2] + "****@" + m.group().split("@")[1]),
            text,
        )
        # 身份证号脱敏（18位）：*******1234
        text = re.sub(r"\d{17}[\dXx]", lambda m: "********" + m.group()[-4:], text)
        return text

    @classmethod
    def log_event(
        cls,
        openid: str,
        event_type: str,
        service_name: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        status_code: int = 200,
        error_msg: Optional[str] = None,
        trace_id: Optional[str] = None,
        api_path: Optional[str] = None,
    ) -> None:
        """将一条埋点事件写入 event_logs 表。"""
        conn = db.get_conn()
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS event_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                openid TEXT NOT NULL,
                event_type TEXT NOT NULL,
                service_name TEXT,
                api_path TEXT,
                request_summary TEXT,
                response_summary TEXT,
                duration_ms INTEGER,
                status_code INTEGER,
                error_msg TEXT,
                created_at TEXT
            )
            """
        )
        c.execute(
            """
            INSERT INTO event_logs
            (trace_id, openid, event_type, service_name, api_path,
             request_summary, response_summary, duration_ms, status_code, error_msg, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id or cls.generate_trace_id(),
                openid,
                event_type,
                service_name,
                api_path,
                cls.mask_pii(json.dumps(request_data, ensure_ascii=False)) if request_data else None,
                cls.mask_pii(json.dumps(response_data, ensure_ascii=False)) if response_data else None,
                duration_ms,
                status_code,
                error_msg,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()


def track_event(event_type: str, service_name: str):
    """给同步/异步函数加装饰器，自动埋点。

    用法示例：
        @track_event("chat_turn", "chat")
        def chat_handler(...): ...
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = datetime.now()
            trace_id = DataCollector.generate_trace_id()
            openid = kwargs.get("openid", "system")
            api_path = kwargs.get("api_path", func.__name__)
            try:
                result = func(*args, **kwargs)
                duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                DataCollector.log_event(
                    openid=openid,
                    event_type=event_type,
                    service_name=service_name,
                    api_path=api_path,
                    duration_ms=duration_ms,
                    status_code=200,
                    trace_id=trace_id,
                )
                return result
            except Exception as e:
                duration_ms = int((datetime.now() - start).total_seconds() * 1000)
                DataCollector.log_event(
                    openid=openid,
                    event_type=event_type,
                    service_name=service_name,
                    api_path=api_path,
                    duration_ms=duration_ms,
                    status_code=500,
                    error_msg=str(e),
                    trace_id=trace_id,
                )
                raise

        return wrapper

    return decorator
