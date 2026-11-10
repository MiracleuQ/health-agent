"""数据中台数据模型定义与建表语句。"""
from datetime import datetime

CREATE_TABLES_SQL = [
    # 埋点事件表
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
    """,
    # 用户行为快照（用于用户画像与分析）
    """
    CREATE TABLE IF NOT EXISTS user_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        openid TEXT NOT NULL UNIQUE,
        total_chats INTEGER DEFAULT 0,
        total_plans INTEGER DEFAULT 0,
        total_records INTEGER DEFAULT 0,
        last_active_at TEXT,
        risk_tags TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """,
    # 数据资产目录（元数据管理）
    """
    CREATE TABLE IF NOT EXISTS data_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_name TEXT NOT NULL,
        asset_type TEXT,
        owner TEXT,
        sensitivity_level TEXT,
        description TEXT,
        created_at TEXT
    )
    """,
]

INSERT_DEFAULT_ASSETS = [
    ("INSERT OR IGNORE INTO data_assets (asset_name, asset_type, owner, sensitivity_level, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
     ("users", "table", "health_agent", "confidential", "用户健康档案", datetime.now().isoformat())),
    ("INSERT OR IGNORE INTO data_assets (asset_name, asset_type, owner, sensitivity_level, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
     ("plans", "table", "health_agent", "confidential", "健康计划与审核记录", datetime.now().isoformat())),
    ("INSERT OR IGNORE INTO data_assets (asset_name, asset_type, owner, sensitivity_level, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
     ("records", "table", "health_agent", "confidential", "每日健康打卡记录", datetime.now().isoformat())),
    ("INSERT OR IGNORE INTO data_assets (asset_name, asset_type, owner, sensitivity_level, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
     ("event_logs", "table", "health_agent", "internal", "埋点事件日志", datetime.now().isoformat())),
]

def init_dataplatform_tables() -> None:
    """初始化数据中台所有表。"""
    from app.db import database as db
    conn = db.get_conn()
    c = conn.cursor()
    for sql in CREATE_TABLES_SQL:
        c.execute(sql)
    for sql, params in INSERT_DEFAULT_ASSETS:
        c.execute(sql, params)
    conn.commit()
    conn.close()
