"""数据中台服务层：查询、聚合、脱敏、导出。"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from app.db import database as db


class DataService:
    """数据中台服务。"""

    @staticmethod
    def query_events(
        openid: str,
        event_type: Optional[str] = None,
        service_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        conn = db.get_conn()
        c = conn.cursor()
        sql = "SELECT * FROM event_logs WHERE openid = ?"
        params: list = [openid]
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if service_name:
            sql += " AND service_name = ?"
            params.append(service_name)
        if start_date:
            sql += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND created_at <= ?"
            params.append(end_date)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def count_events(
        openid: str,
        event_type: Optional[str] = None,
        service_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        conn = db.get_conn()
        c = conn.cursor()
        sql = "SELECT COUNT(*) as cnt FROM event_logs WHERE openid = ?"
        params: list = [openid]
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if service_name:
            sql += " AND service_name = ?"
            params.append(service_name)
        if start_date:
            sql += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND created_at <= ?"
            params.append(end_date)
        c.execute(sql, params)
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def get_dashboard(openid: str, days: int = 7) -> Dict[str, Any]:
        """数据看板聚合指标。"""
        end = date.today()
        start = end - timedelta(days=days - 1)
        start_iso = start.isoformat()
        end_iso = end.isoformat()

        conn = db.get_conn()
        c = conn.cursor()

        # 总对话次数
        c.execute(
            "SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='chat_turn' AND created_at>=? AND created_at<=?",
            (openid, start_iso, end_iso),
        )
        total_chats = c.fetchone()["cnt"]

        # 计划生成次数
        c.execute(
            "SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='plan_save' AND created_at>=? AND created_at<=?",
            (openid, start_iso, end_iso),
        )
        total_plans = c.fetchone()["cnt"]

        # 打卡次数
        c.execute(
            "SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='record_add' AND created_at>=? AND created_at<=?",
            (openid, start_iso, end_iso),
        )
        total_records = c.fetchone()["cnt"]

        # 工具调用成功率
        c.execute(
            "SELECT COUNT(*) as total FROM event_logs WHERE openid=? AND event_type='tool_call' AND created_at>=? AND created_at<=?",
            (openid, start_iso, end_iso),
        )
        tool_total = c.fetchone()["total"]
        c.execute(
            "SELECT COUNT(*) as success FROM event_logs WHERE openid=? AND event_type='tool_call' AND status_code=200 AND created_at>=? AND created_at<=?",
            (openid, start_iso, end_iso),
        )
        tool_success = c.fetchone()["success"]
        tool_success_rate = round(tool_success / tool_total, 4) if tool_total else 0.0

        # 每日活跃趋势
        c.execute(
            "SELECT substr(created_at,1,10) as day, COUNT(*) as cnt FROM event_logs WHERE openid=? AND created_at>=? AND created_at<=? GROUP BY day ORDER BY day",
            (openid, start_iso, end_iso),
        )
        daily_trend = [dict(r) for r in c.fetchall()]

        conn.close()

        return {
            "period": {"start": start_iso, "end": end_iso, "days": days},
            "metrics": {
                "total_chats": total_chats,
                "total_plans": total_plans,
                "total_records": total_records,
                "tool_success_rate": tool_success_rate,
            },
            "daily_trend": daily_trend,
        }

    @staticmethod
    def update_user_snapshot(openid: str) -> None:
        """根据事件日志更新用户快照。"""
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='chat_turn'", (openid,))
        total_chats = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='plan_save'", (openid,))
        total_plans = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM event_logs WHERE openid=? AND event_type='record_add'", (openid,))
        total_records = c.fetchone()["cnt"]
        c.execute("SELECT MAX(created_at) as last FROM event_logs WHERE openid=?", (openid,))
        row = c.fetchone()
        last_active = row["last"] if row else None
        now = datetime.now().isoformat()
        c.execute(
            """
            INSERT INTO user_snapshots (openid, total_chats, total_plans, total_records, last_active_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(openid) DO UPDATE SET
                total_chats=excluded.total_chats,
                total_plans=excluded.total_plans,
                total_records=excluded.total_records,
                last_active_at=excluded.last_active_at,
                updated_at=excluded.updated_at
            """,
            (openid, total_chats, total_plans, total_records, last_active, now, now),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def list_assets() -> List[Dict[str, Any]]:
        conn = db.get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM data_assets ORDER BY id")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
