"""工具层单元测试（无需 LLM，纯逻辑验证）。"""
import pytest
from app.tools.health_tools import calculate_bmr_tdee, calculate_bmi, calculate_macros
import json


def test_calculate_bmr_tdee_male():
    result = json.loads(calculate_bmr_tdee.invoke({
        "weight_kg": 70, "height_cm": 175, "age": 25,
        "gender": "male", "activity_level": "moderate",
    }))
    assert result["bmr"] > 0
    assert result["tdee"] > result["bmr"]
    assert result["activity_multiplier"] == 1.55


def test_calculate_bmr_tdee_female():
    result = json.loads(calculate_bmr_tdee.invoke({
        "weight_kg": 60, "height_cm": 165, "age": 30,
        "gender": "female", "activity_level": "light",
    }))
    assert result["bmr"] > 0
    assert result["min_safe_calories"] > 0


def test_calculate_bmi_categories():
    # 偏瘦: BMI = 50/1.7^2 = 17.3
    r = json.loads(calculate_bmi.invoke({"weight_kg": 50, "height_cm": 170}))
    assert r["bmi"] == 17.3
    assert r["category_en"] == "underweight"
    # 正常: BMI = 65/1.7^2 = 22.5
    r = json.loads(calculate_bmi.invoke({"weight_kg": 65, "height_cm": 170}))
    assert r["bmi"] == 22.5
    assert r["category_en"] == "normal"
    # 超重: BMI = 75/1.7^2 = 26.0 (< 28)
    r = json.loads(calculate_bmi.invoke({"weight_kg": 75, "height_cm": 170}))
    assert r["bmi"] == 26.0
    assert r["category_en"] == "overweight"
    # 肥胖: BMI = 85/1.7^2 = 29.4 (>= 28)
    r = json.loads(calculate_bmi.invoke({"weight_kg": 85, "height_cm": 170}))
    assert r["bmi"] == 29.4
    assert r["category_en"] == "obese"


def test_calculate_macros():
    r = json.loads(calculate_macros.invoke({
        "target_calories": 2000, "goal": "fat_loss", "weight_kg": 70,
    }))
    assert abs(r["protein_pct"] + r["carb_pct"] + r["fat_pct"] - 100) < 1
    assert r["protein_g"] > 0
    assert r["carb_g"] > 0
    assert r["fat_g"] > 0


def test_calculate_macros_muscle_gain():
    r = json.loads(calculate_macros.invoke({
        "target_calories": 2500, "goal": "muscle_gain", "weight_kg": 70,
    }))
    assert r["carb_pct"] == 50  # 增肌碳水占比更高
