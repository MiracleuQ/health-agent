"""LangGraph 检查点（Checkpoint）持久化：支持多轮对话记忆与断点续对。"""
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

try:
    from app.core.config import settings as _settings
    DB_PATH = _settings.DB_PATH
except Exception:  # pragma: no cover
    DB_PATH = "./health_agent.db"


def get_checkpointer():
    """返回基于 SQLite 的检查点保存器。

    显式创建 sqlite3 连接（check_same_thread=False 支持多线程 FastAPI），
    避免 SqliteSaver.from_conn_string 返回上下文管理器导致类型错误。
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return SqliteSaver(conn)
