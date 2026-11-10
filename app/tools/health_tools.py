"""Agent 可调用工具：封装计算、数据库与知识库能力。"""
import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timedelta

from langchain_core.tools import tool

from app.db import database as db
from app.core.logging import logger

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    _REPORTLAB_AVAILABLE = True
except Exception:  # pragma: no cover
    _REPORTLAB_AVAILABLE = False

# 全局知识库检索器单例
_retriever = None


def _get_retriever():
    global _retriever
    if _retriever is None:
        from app.services.knowledge import build_knowledge_base
        _retriever = build_knowledge_base()
    return _retriever


# ---------------------------------------------------------------------------
# 基础设施工具
# ---------------------------------------------------------------------------
@tool
def init_database() -> str:
    """初始化 SQLite 数据库表结构。系统首次启动前建议调用一次。"""
    db.init_db()
    return "数据库已初始化。"


# ---------------------------------------------------------------------------
# 生理计算工具（所有计算必须通过工具，避免 LLM 幻觉）
# ---------------------------------------------------------------------------
@tool
def calculate_bmr_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
) -> str:
    """
    使用 Mifflin-St Jeor 公式计算基础代谢率 (BMR) 和每日总能量消耗 (TDEE)。
    activity_level: sedentary(久坐), light(轻度), moderate(中度), active(重度), very_active(极重)
    返回 JSON 字符串。
    """
    gender_key = gender.lower()
    if gender_key in ("male", "男", "m"):
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    multiplier = activity_multipliers.get(activity_level.lower(), 1.2)
    tdee = bmr * multiplier

    result = {
        "bmr": round(bmr, 1),
        "tdee": round(tdee, 1),
        "activity_multiplier": multiplier,
        "suggested_deficit_calories": 300,  # 建议减脂缺口
        "min_safe_calories": round(max(bmr, tdee - 500), 1),
        "formula": "Mifflin-St Jeor",
    }
    logger.debug("BMR/TDEE 计算完成：{}", result)
    return json.dumps(result, ensure_ascii=False)


@tool
def calculate_bmi(weight_kg: float, height_cm: float) -> str:
    """计算 BMI 并给出中国成人分类建议。返回 JSON 字符串。"""
    h_m = height_cm / 100
    bmi = weight_kg / (h_m * h_m)
    if bmi < 18.5:
        category = "偏瘦"
        category_en = "underweight"
        advice = "建议适当增重，均衡营养"
    elif bmi < 24:
        category = "正常"
        category_en = "normal"
        advice = "保持当前体重，关注体脂率"
    elif bmi < 28:
        category = "超重"
        category_en = "overweight"
        advice = "建议适度减脂，控制热量摄入"
    else:
        category = "肥胖"
        category_en = "obese"
        advice = "建议在专业指导下制定减重计划"
    return json.dumps(
        {
            "bmi": round(bmi, 1),
            "category": category,
            "category_en": category_en,
            "advice": advice,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
        },
        ensure_ascii=False,
    )


@tool
def calculate_macros(
    target_calories: int,
    goal: str,
    weight_kg: float,
) -> str:
    """
    根据目标卡路里和目标（fat_loss/muscle_gain/maintain）计算宏量营养素分配。
    返回 JSON：蛋白质/碳水/脂肪的克数和百分比。
    """
    goal = (goal or "fat_loss").lower()
    # 默认分配比例（蛋白质/碳水/脂肪）
    ratios = {
        "fat_loss": (0.40, 0.40, 0.20),   # 高蛋白、中碳水、低脂肪
        "muscle_gain": (0.30, 0.50, 0.20),  # 高碳水支持训练
        "maintain": (0.25, 0.55, 0.20),
    }
    p_ratio, c_ratio, f_ratio = ratios.get(goal, ratios["fat_loss"])

    p_cal = target_calories * p_ratio
    c_cal = target_calories * c_ratio
    f_cal = target_calories * f_ratio

    result = {
        "target_calories": target_calories,
        "goal": goal,
        "protein_g": round(p_cal / 4, 1),
        "carb_g": round(c_cal / 4, 1),
        "fat_g": round(f_cal / 9, 1),
        "protein_pct": int(p_ratio * 100),
        "carb_pct": int(c_ratio * 100),
        "fat_pct": int(f_ratio * 100),
    }
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 用户档案工具
# ---------------------------------------------------------------------------
@tool
def save_user_profile(
    openid: str,
    name: Optional[str] = None,
    age: Optional[int] = None,
    gender: Optional[str] = None,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    activity_level: Optional[str] = None,
    goal: Optional[str] = None,
    target_calories: Optional[int] = None,
    training_weeks: Optional[int] = None,
) -> str:
    """保存或更新用户健康档案。"""
    profile = {
        "name": name,
        "age": age,
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_level": activity_level,
        "goal": goal,
        "target_calories": target_calories,
        "training_weeks": training_weeks,
    }
    user_id = db.upsert_user(openid, profile)
    return json.dumps({"user_id": user_id, "openid": openid, "saved": True}, ensure_ascii=False)


@tool
def get_user_profile(openid: str) -> str:
    """查询用户健康档案。"""
    user = db.get_user_by_openid(openid)
    if not user:
        return json.dumps({"found": False, "message": "未找到该用户档案"}, ensure_ascii=False)
    return json.dumps({"found": True, "profile": user}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 计划管理工具
# ---------------------------------------------------------------------------
@tool
def save_plan(user_id: int, plan_type: str, content: Dict[str, Any]) -> str:
    """保存生成的健康计划（默认状态 pending，需人工审核后才生效）。"""
    plan_id = db.save_plan(user_id, plan_type, content, status="pending")
    return json.dumps({"saved": True, "plan_id": plan_id, "status": "pending"}, ensure_ascii=False)


@tool
def get_latest_plan(user_id: int, plan_type: str) -> str:
    """获取用户最近的某类型计划。"""
    plan = db.get_latest_plan(user_id, plan_type)
    if not plan:
        return json.dumps({"found": False, "message": "暂无该类型计划"}, ensure_ascii=False)
    return json.dumps({"found": True, "plan": plan}, ensure_ascii=False)


@tool
def list_user_plans(user_id: int) -> str:
    """列出用户所有历史计划及其审核状态。"""
    plans = db.list_plans(user_id)
    return json.dumps({"plans": plans}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 打卡记录工具
# ---------------------------------------------------------------------------
@tool
def add_record(
    user_id: int,
    date: Optional[str] = None,
    weight_kg: Optional[float] = None,
    calories_eaten: Optional[int] = None,
    workout_minutes: Optional[int] = None,
    water_ml: Optional[int] = None,
    note: Optional[str] = None,
) -> str:
    """添加每日健康打卡记录。"""
    record_id = db.add_record(
        user_id,
        {
            "date": date,
            "weight_kg": weight_kg,
            "calories_eaten": calories_eaten,
            "workout_minutes": workout_minutes,
            "water_ml": water_ml,
            "note": note,
        },
    )
    return json.dumps({"saved": True, "record_id": record_id}, ensure_ascii=False)


@tool
def get_recent_records(user_id: int, limit: int = 7) -> str:
    """获取用户最近的打卡记录，用于进度分析与计划调整。"""
    records = db.get_recent_records(user_id, limit)
    return json.dumps({"records": records}, ensure_ascii=False)


@tool
def get_records_chart(user_id: int, days: int = 30) -> str:
    """获取指定天数内的记录，用于前端图表展示（体重/卡路里趋势）。"""
    end = date.today()
    start = end - timedelta(days=days - 1)
    records = db.get_records_by_date_range(
        user_id, start.isoformat(), end.isoformat()
    )
    return json.dumps({"records": records, "days": days}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 知识库工具（RAG）
# ---------------------------------------------------------------------------
@tool
def query_knowledge(query: str) -> str:
    """查询健康管理知识库（减脂、营养、运动、睡眠等专业知识）。"""
    retriever = _get_retriever()
    docs = retriever.get_relevant_documents(query)
    context = "\n".join([d.page_content for d in docs])
    return context or "未检索到相关知识。"


# ---------------------------------------------------------------------------
# 食物卡路里估算（多模态友好：支持文本描述，后续可接图片多模态模型）
# ---------------------------------------------------------------------------
@tool
def estimate_food_calories(food_description: str) -> str:
    """
    根据食物描述估算卡路里和营养成分。
    food_description: 用户描述的食物，如“中午吃了鸡胸肉沙拉，配一碗糙米饭”
    返回 JSON 字符串，包含估算卡路里、蛋白质/碳水/脂肪克数、置信度。
    """
    # 这里使用简单的基于关键词的估算逻辑作为兜底，实际生产中可调用多模态 LLM
    import re
    desc = food_description.lower()
    calories = 0
    protein = 0
    carb = 0
    fat = 0
    items = []

    # 非常简化的食物数据库（实际应接入更完整的营养数据库或多模态模型）
    food_db = [
        (["鸡胸肉", "chicken breast"], 165, 31, 0, 3.6),
        (["白米饭", "rice"], 130, 2.7, 28, 0.3),
        (["糙米饭", "brown rice"], 111, 2.6, 23, 0.9),
        (["鸡蛋", "egg"], 155, 13, 1.1, 11),
        (["牛奶", "milk"], 42, 3.4, 4.8, 1),
        (["苹果", "apple"], 52, 0.3, 14, 0.2),
        (["香蕉", "banana"], 89, 1.1, 23, 0.3),
        (["西兰花", "broccoli"], 34, 2.8, 7, 0.4),
        (["牛肉", "beef"], 250, 26, 0, 17),
        (["三文鱼", "salmon"], 208, 20, 0, 13),
        (["面包", "bread"], 265, 9, 49, 3.2),
        (["面条", "noodles"], 138, 5, 28, 1.5),
    ]

    for keywords, cal, p, c, f in food_db:
        if any(k in desc for k in keywords):
            items.append({"food": keywords[0], "calories": cal, "protein_g": p, "carb_g": c, "fat_g": f})
            calories += cal
            protein += p
            carb += c
            fat += f

    if not items:
        # 未识别到具体食物，给出通用估算提示
        return json.dumps(
            {
                "food_description": food_description,
                "estimated_calories": 0,
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
                "confidence": "low",
                "items": [],
                "message": "未识别到具体食物，建议更详细描述食物名称和分量。",
            },
            ensure_ascii=False,
        )

    result = {
        "food_description": food_description,
        "estimated_calories": calories,
        "protein_g": round(protein, 1),
        "carb_g": round(carb, 1),
        "fat_g": round(fat, 1),
        "confidence": "medium",
        "items": items,
        "note": "估算值仅供参考，实际卡路里受分量和烹饪方式影响。",
    }
    return json.dumps(result, ensure_ascii=False)


@tool
def save_food_record_with_estimate(
    user_id: int,
    food_description: str,
    date: Optional[str] = None,
    meal_type: Optional[str] = None,  # breakfast / lunch / dinner / snack
) -> str:
    """根据食物描述估算卡路里并自动写入打卡记录。"""
    from datetime import datetime as _dt
    est = json.loads(estimate_food_calories.invoke({"food_description": food_description}))
    record_id = db.add_record(
        user_id,
        {
            "date": date or _dt.now().date().isoformat(),
            "weight_kg": None,
            "calories_eaten": est.get("estimated_calories"),
            "workout_minutes": None,
            "water_ml": None,
            "note": f"{meal_type or '餐食'}: {food_description}（AI 估算 {est.get('estimated_calories')} 大卡）",
        },
    )
    return json.dumps(
        {
            "saved": True,
            "record_id": record_id,
            "estimate": est,
        },
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# 饮食偏好与过敏原管理
# ---------------------------------------------------------------------------
@tool
def save_diet_preference(
    user_id: int,
    allergens: Optional[List[str]] = None,
    dislike_foods: Optional[List[str]] = None,
    prefer_cuisine: Optional[str] = None,
    vegetarian: Optional[bool] = None,
    halal: Optional[bool] = None,
) -> str:
    """保存用户饮食偏好与过敏原信息，用于后续膳食计划生成时的硬约束。"""
    pref_id = db.upsert_diet_preference(
        user_id,
        {
            "allergens": allergens or [],
            "dislike_foods": dislike_foods or [],
            "prefer_cuisine": prefer_cuisine,
            "vegetarian": vegetarian,
            "halal": halal,
        },
    )
    return json.dumps({"saved": True, "preference_id": pref_id}, ensure_ascii=False)


@tool
def get_diet_preference(user_id: int) -> str:
    """查询用户饮食偏好与过敏原信息。"""
    pref = db.get_diet_preference(user_id)
    if not pref:
        return json.dumps({"found": False, "message": "未设置饮食偏好"}, ensure_ascii=False)
    return json.dumps({"found": True, "preference": pref}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 一周膳食计划与购物清单
# ---------------------------------------------------------------------------
@tool
def save_weekly_meal_plan(
    user_id: int,
    week_start: str,
    calories_target: int,
    meals: List[Dict[str, Any]],
    shopping_list: List[str],
) -> str:
    """保存一周膳食计划与购物清单。"""
    content = {
        "calories_target": calories_target,
        "week_start": week_start,
        "meals": meals,
        "shopping_list": shopping_list,
    }
    plan_id = db.save_meal_plan(user_id, week_start, content)
    return json.dumps({"saved": True, "plan_id": plan_id}, ensure_ascii=False)


@tool
def get_latest_meal_plan(user_id: int) -> str:
    """获取用户最近的一周膳食计划。"""
    plan = db.get_latest_meal_plan(user_id)
    if not plan:
        return json.dumps({"found": False, "message": "暂无膳食计划"}, ensure_ascii=False)
    return json.dumps({"found": True, "plan": plan}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 健康周报 PDF 生成
# ---------------------------------------------------------------------------
@tool
def generate_health_report_pdf(user_id: int, report_type: str = "weekly") -> str:
    """
    为用户生成健康周报/月报 PDF。
    report_type: "weekly" 或 "monthly"
    返回 PDF 文件路径。
    """
    if not _REPORTLAB_AVAILABLE:
        return json.dumps({"error": "reportlab 未安装，无法生成 PDF"}, ensure_ascii=False)

    user = db.get_user_by_openid("")  # placeholder, will be replaced below
    # 这里需要通过 user_id 查用户，但 database 层只按 openid 查。先按 user_id 反查（简化：直接查 records）
    records = db.get_recent_records(user_id, limit=30 if report_type == "monthly" else 7)
    plans = db.list_plans(user_id)
    meal_plan = db.get_latest_meal_plan(user_id)

    # 注册中文字体（Windows 系统自带）
    font_path = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/simhei.ttf"  # 黑体
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
    else:
        font_name = "Helvetica"
    font_name = "ChineseFont" if os.path.exists(font_path) else "Helvetica"

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=20,
        textColor=colors.HexColor("#2E86AB"),
        alignment=1,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=14,
        textColor=colors.HexColor("#2E86AB"),
    )
    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
    )

    out_dir = "./reports"
    os.makedirs(out_dir, exist_ok=True)
    filename = f"{out_dir}/health_report_{user_id}_{report_type}_{date.today().isoformat()}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm)
    story = []

    story.append(Paragraph(f"AI 健康管理{'周报' if report_type == 'weekly' else '月报'}", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"生成日期：{date.today().isoformat()}", normal_style))
    story.append(Spacer(1, 10))

    # 打卡记录表
    story.append(Paragraph("📝 每日打卡记录", heading_style))
    if records:
        table_data = [["日期", "体重(kg)", "摄入卡路里", "运动(分钟)", "饮水(ml)", "备注"]]
        for r in records:
            table_data.append([
                str(r.get("date", "")),
                str(r.get("weight_kg", "-")),
                str(r.get("calories_eaten", "-")),
                str(r.get("workout_minutes", "-")),
                str(r.get("water_ml", "-")),
                str(r.get("note", "-")[:20]),
            ])
        tbl = Table(table_data, colWidths=[25 * mm, 22 * mm, 28 * mm, 26 * mm, 24 * mm, 45 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), font_name),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("暂无打卡记录", normal_style))
    story.append(Spacer(1, 15))

    # 膳食计划
    story.append(Paragraph("🍎 最新膳食计划", heading_style))
    if meal_plan:
        content = meal_plan.get("content", {})
        story.append(Paragraph(f"目标卡路里：{content.get('calories_target', '-')} 大卡", normal_style))
        story.append(Spacer(1, 5))
        shopping = content.get("shopping_list", [])
        if shopping:
            story.append(Paragraph("购物清单：", normal_style))
            story.append(Paragraph("、".join(shopping), normal_style))
    else:
        story.append(Paragraph("暂无膳食计划", normal_style))
    story.append(Spacer(1, 15))

    # 健康计划
    story.append(Paragraph("📋 健康计划记录", heading_style))
    if plans:
        for p in plans[:3]:
            story.append(Paragraph(f"计划 #{p['id']} - {p['plan_type']} - 状态：{p['status']}", normal_style))
    else:
        story.append(Paragraph("暂无健康计划", normal_style))

    doc.build(story)

    return json.dumps({"saved": True, "pdf_path": filename, "report_type": report_type}, ensure_ascii=False)


# 所有可暴露给 Agent 调用的工具列表
ALL_TOOLS = [
    init_database,
    calculate_bmr_tdee,
    calculate_bmi,
    calculate_macros,
    save_user_profile,
    get_user_profile,
    save_plan,
    get_latest_plan,
    list_user_plans,
    add_record,
    get_recent_records,
    get_records_chart,
    query_knowledge,
    estimate_food_calories,
    save_food_record_with_estimate,
    save_diet_preference,
    get_diet_preference,
    save_weekly_meal_plan,
    get_latest_meal_plan,
    generate_health_report_pdf,
]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
