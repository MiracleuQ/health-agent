"""SQLite 持久化层：用户档案、健康计划、每日打卡记录。"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.logging import logger

# 优先使用全局 settings，降低循环导入风险
try:
    from app.core.config import settings as _settings
    DB_PATH = _settings.DB_PATH
except Exception:  # pragma: no cover - 配置缺失时的降级
    DB_PATH = "./health_agent.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 开启外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化所有数据表。"""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
            name TEXT,
            age INTEGER,
            gender TEXT,
            height_cm REAL,
            weight_kg REAL,
            activity_level TEXT,
            goal TEXT,
            target_calories INTEGER,
            training_weeks INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT DEFAULT 'pending',   -- pending / approved / rejected
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            weight_kg REAL,
            calories_eaten INTEGER,
            workout_minutes INTEGER,
            water_ml INTEGER,
            note TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成：{}", DB_PATH)


def upsert_user(openid: str, profile: Dict[str, Any]) -> int:
    """插入或更新用户档案，返回 user_id。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE openid = ?", (openid,))
    row = c.fetchone()
    now = datetime.now().isoformat()
    if row:
        user_id = row["id"]
        c.execute(
            """
            UPDATE users SET name=?, age=?, gender=?, height_cm=?, weight_kg=?,
                activity_level=?, goal=?, target_calories=?, training_weeks=?, updated_at=?
            WHERE id=?
            """,
            (
                profile.get("name"),
                profile.get("age"),
                profile.get("gender"),
                profile.get("height_cm"),
                profile.get("weight_kg"),
                profile.get("activity_level"),
                profile.get("goal"),
                profile.get("target_calories"),
                profile.get("training_weeks"),
                now,
                user_id,
            ),
        )
    else:
        c.execute(
            """
            INSERT INTO users (openid, name, age, gender, height_cm, weight_kg,
                activity_level, goal, target_calories, training_weeks, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                openid,
                profile.get("name"),
                profile.get("age"),
                profile.get("gender"),
                profile.get("height_cm"),
                profile.get("weight_kg"),
                profile.get("activity_level"),
                profile.get("goal"),
                profile.get("target_calories"),
                profile.get("training_weeks"),
                now,
                now,
            ),
        )
        user_id = c.lastrowid
    conn.commit()
    conn.close()
    logger.debug("用户档案已保存：openid={}, user_id={}", openid, user_id)
    return user_id


def get_user_by_openid(openid: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE openid = ?", (openid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def save_plan(user_id: int, plan_type: str, content: Dict[str, Any], status: str = "pending") -> int:
    """保存生成的健康计划，返回 plan_id。默认 pending 待审核。"""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO plans (user_id, plan_type, content, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, plan_type, json.dumps(content, ensure_ascii=False), status, now, now),
    )
    plan_id = c.lastrowid
    conn.commit()
    conn.close()
    logger.info("计划已保存：user_id={}, plan_type={}, plan_id={}, status={}",
                user_id, plan_type, plan_id, status)
    return plan_id


def get_latest_plan(user_id: int, plan_type: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM plans WHERE user_id=? AND plan_type=? ORDER BY id DESC LIMIT 1",
        (user_id, plan_type),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["content"] = json.loads(result["content"])
    return result


def approve_plan(plan_id: int, status: str = "approved") -> bool:
    """人工审核通过/拒绝计划。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "UPDATE plans SET status=?, updated_at=? WHERE id=?",
        (status, datetime.now().isoformat(), plan_id),
    )
    conn.commit()
    changed = c.rowcount > 0
    conn.close()
    return changed


def list_plans(user_id: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, plan_type, status, created_at FROM plans WHERE user_id=? ORDER BY id DESC",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_record(user_id: int, record: Dict[str, Any]) -> int:
    """添加每日健康打卡记录，返回 record_id。"""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute(
        """
        INSERT INTO records (user_id, date, weight_kg, calories_eaten, workout_minutes, water_ml, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            record.get("date", datetime.now().date().isoformat()),
            record.get("weight_kg"),
            record.get("calories_eaten"),
            record.get("workout_minutes"),
            record.get("water_ml"),
            record.get("note"),
            now,
        ),
    )
    record_id = c.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_recent_records(user_id: int, limit: int = 7) -> List[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM records WHERE user_id=? ORDER BY date DESC LIMIT ?",
        (user_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_records_by_date_range(user_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """按日期范围查询记录，用于前端图表展示。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM records WHERE user_id=? AND date BETWEEN ? AND ? ORDER BY date ASC",
        (user_id, start_date, end_date),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 饮食偏好与过敏原管理（新增表）
# ---------------------------------------------------------------------------
def upsert_diet_preference(user_id: int, preference: Dict[str, Any]) -> int:
    """保存/更新用户饮食偏好与过敏原信息。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS diet_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            allergens TEXT,           -- JSON 数组，如 ["花生", "贝类"]
            dislike_foods TEXT,       -- JSON 数组，如 ["香菜", "苦瓜"]
            prefer_cuisine TEXT,      -- 偏好菜系，如 "中式", "西式"
            vegetarian INTEGER DEFAULT 0,  -- 0/1
            halal INTEGER DEFAULT 0,       -- 0/1
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    c.execute("SELECT id FROM diet_preferences WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    now = datetime.now().isoformat()
    if row:
        pref_id = row["id"]
        c.execute(
            """
            UPDATE diet_preferences SET allergens=?, dislike_foods=?, prefer_cuisine=?,
                vegetarian=?, halal=?, updated_at=?
            WHERE id=?
            """,
            (
                json.dumps(preference.get("allergens", []), ensure_ascii=False),
                json.dumps(preference.get("dislike_foods", []), ensure_ascii=False),
                preference.get("prefer_cuisine"),
                1 if preference.get("vegetarian") else 0,
                1 if preference.get("halal") else 0,
                now,
                pref_id,
            ),
        )
    else:
        c.execute(
            """
            INSERT INTO diet_preferences (user_id, allergens, dislike_foods, prefer_cuisine,
                vegetarian, halal, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                json.dumps(preference.get("allergens", []), ensure_ascii=False),
                json.dumps(preference.get("dislike_foods", []), ensure_ascii=False),
                preference.get("prefer_cuisine"),
                1 if preference.get("vegetarian") else 0,
                1 if preference.get("halal") else 0,
                now,
                now,
            ),
        )
        pref_id = c.lastrowid
    conn.commit()
    conn.close()
    return pref_id


def get_diet_preference(user_id: int) -> Optional[Dict[str, Any]]:
    """查询用户饮食偏好。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS diet_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            allergens TEXT,
            dislike_foods TEXT,
            prefer_cuisine TEXT,
            vegetarian INTEGER DEFAULT 0,
            halal INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    c.execute("SELECT * FROM diet_preferences WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["allergens"] = json.loads(result["allergens"] or "[]")
    result["dislike_foods"] = json.loads(result["dislike_foods"] or "[]")
    result["vegetarian"] = bool(result["vegetarian"])
    result["halal"] = bool(result["halal"])
    return result


# ---------------------------------------------------------------------------
# 一周膳食计划与购物清单（新增表）
# ---------------------------------------------------------------------------
def save_meal_plan(user_id: int, week_start: str, content: Dict[str, Any]) -> int:
    """保存一周膳食计划与购物清单。"""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """
    )
    now = datetime.now().isoformat()
    c.execute(
        "INSERT INTO meal_plans (user_id, week_start, content, created_at) VALUES (?, ?, ?, ?)",
        (user_id, week_start, json.dumps(content, ensure_ascii=False), now),
    )
    plan_id = c.lastrowid
    conn.commit()
    conn.close()
    return plan_id


def get_latest_meal_plan(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM meal_plans WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["content"] = json.loads(result["content"])
    return result
