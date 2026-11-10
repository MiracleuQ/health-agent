"""Streamlit 前端：健康管理 Agent 可视化界面（增强版）。"""
import streamlit as st
import os
import sys
import json
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import plotly.express as px
import pandas as pd

from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI 健康管理 Agent",
    page_icon="🏃‍♂️",
    layout="wide",
)

st.title("🏃‍♂️ AI 健康管理 Agent")
st.caption("基于 LangGraph 多代理框架 · 多模态食物估算 · 膳食计划 · PDF 报告 · 人工审核")

# ---------------------------------------------------------------------------
# 侧边栏
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("👤 用户信息")
    openid = st.text_input("用户标识（OpenID）", value="default_user", key="openid_input")
    st.divider()

    st.markdown("### 💡 快速示例")
    st.code("我想制定一个 8 周减脂计划，目标每日 1800 大卡")
    st.code("记录今天：体重 70kg，摄入 1700 大卡，运动 40 分钟")
    st.code("中午吃了鸡胸肉沙拉，配一碗糙米饭，估算卡路里")
    st.code("我想设置过敏原：花生、贝类")
    st.code("生成一周膳食计划与购物清单")
    st.code("导出健康周报 PDF")
    st.divider()

    if st.button("🔧 初始化数据库"):
        try:
            requests.post(f"{API_BASE}/api/users/profile", json={}, headers={"X-OpenID": openid}, timeout=10)
            st.success("后端连接正常")
        except Exception as e:
            st.error(f"无法连接后端：{e}")

# ---------------------------------------------------------------------------
# 会话状态
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# 顶部：聊天对话
# ---------------------------------------------------------------------------
st.subheader("💬 与健康管理 Agent 对话")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入你的需求……"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent 思考中……"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/chat",
                    json={"message": prompt, "openid": openid or "default_user"},
                    headers={"X-OpenID": openid or "default_user"},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data.get("reply", "无回复")
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                err = f"❌ 请求失败：{e}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})

st.divider()

# ---------------------------------------------------------------------------
# 功能模块标签页
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 健康计划", "🍎 食物估算", "🥗 膳食计划", "⚙️ 饮食偏好", "📊 进度图表", "📄 报告导出"
])

# ---------- Tab 1: 健康计划 ----------
with tab1:
    st.subheader("我的健康计划")
    if st.button("刷新计划列表", key="refresh_plans_v2"):
        try:
            r = requests.get(f"{API_BASE}/api/plans", headers={"X-OpenID": openid}, timeout=10)
            st.session_state["_plans_v2"] = r.json().get("data", [])
        except Exception as e:
            st.error(f"获取失败：{e}")
    if "_plans_v2" not in st.session_state:
        try:
            r = requests.get(f"{API_BASE}/api/plans", headers={"X-OpenID": openid}, timeout=10)
            st.session_state["_plans_v2"] = r.json().get("data", [])
        except Exception:
            st.session_state["_plans_v2"] = []
    plans = st.session_state["_plans_v2"]
    if plans:
        for p in plans:
            with st.expander(f"计划 #{p['id']} - {p['plan_type']} - {p['status']}"):
                content = p.get("content", {})
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except Exception:
                        content = {}
                st.json(content)
                if p["status"] == "pending":
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ 审核通过", key=f"approve_v2_{p['id']}"):
                            try:
                                requests.post(
                                    f"{API_BASE}/api/plans/{p['id']}/approve",
                                    json={"status": "approved"},
                                    headers={"X-OpenID": openid},
                                    timeout=10,
                                )
                                st.success("已审核通过")
                                st.session_state["_plans_v2"] = requests.get(
                                    f"{API_BASE}/api/plans", headers={"X-OpenID": openid}, timeout=10
                                ).json().get("data", [])
                                st.rerun()
                            except Exception as e:
                                st.error(f"审核失败：{e}")
                    with col2:
                        if st.button("❌ 拒绝", key=f"reject_v2_{p['id']}"):
                            try:
                                requests.post(
                                    f"{API_BASE}/api/plans/{p['id']}/approve",
                                    json={"status": "rejected"},
                                    headers={"X-OpenID": openid},
                                    timeout=10,
                                )
                                st.success("已拒绝")
                                st.session_state["_plans_v2"] = requests.get(
                                    f"{API_BASE}/api/plans", headers={"X-OpenID": openid}, timeout=10
                                ).json().get("data", [])
                                st.rerun()
                            except Exception as e:
                                st.error(f"审核失败：{e}")
    else:
        st.info("暂无计划，先在对话中制定一个吧。")

# ---------- Tab 2: 食物估算 ----------
with tab2:
    st.subheader("🍎 食物卡路里估算与自动打卡")
    st.write("描述你吃的食物，AI 将估算卡路里和营养成分，并可自动写入打卡记录。")
    food_desc = st.text_area("食物描述", placeholder="例如：中午吃了鸡胸肉沙拉，配一碗糙米饭，一根香蕉")
    meal_type = st.selectbox("餐食类型", ["breakfast", "lunch", "dinner", "snack"], format_func=lambda x: {
        "breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐", "snack": "加餐"
    }[x])
    auto_record = st.checkbox("估算后自动写入打卡记录", value=True)
    if st.button("估算卡路里", key="estimate_food"):
        if not food_desc.strip():
            st.warning("请先输入食物描述")
        else:
            with st.spinner("AI 估算中……"):
                try:
                    # 调用聊天接口，让 Agent 处理
                    resp = requests.post(
                        f"{API_BASE}/api/chat",
                        json={"message": f"估算这个食物的卡路里：{food_desc}，餐食类型：{meal_type}"},
                        headers={"X-OpenID": openid or "default_user"},
                        timeout=120,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    st.markdown(data.get("reply", "无回复"))
                except Exception as e:
                    st.error(f"估算失败：{e}")

# ---------- Tab 3: 膳食计划 ----------
with tab3:
    st.subheader("🥗 一周膳食计划与购物清单")
    st.write("AI 根据你的目标卡路里和饮食偏好，生成 7 天膳食计划与购物清单。")
    if st.button("生成一周膳食计划", key="gen_meal_plan"):
        with st.spinner("生成膳食计划中……"):
            try:
                resp = requests.post(
                    f"{API_BASE}/api/chat",
                    json={"message": "帮我生成一周的膳食计划与购物清单，请基于我的档案和饮食偏好"},
                    headers={"X-OpenID": openid or "default_user"},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                st.markdown(data.get("reply", "无回复"))
            except Exception as e:
                st.error(f"生成失败：{e}")

    st.divider()
    st.write("查看已保存的膳食计划：")
    try:
        # 这里需要 user_id，简化通过对话获取；前端直接提示用户在对话中查看
        st.info("膳食计划会保存在后端，你可以在对话中询问“我的膳食计划”来查看详情。")
    except Exception:
        pass

# ---------- Tab 4: 饮食偏好 ----------
with tab4:
    st.subheader("⚙️ 饮食偏好与过敏原管理")
    st.write("设置你的饮食约束，AI 制定膳食计划时会自动避开过敏原和忌口食物。")
    allergens = st.text_input("过敏原（逗号分隔）", placeholder="例如：花生、贝类、牛奶")
    dislike_foods = st.text_input("忌口食物（逗号分隔）", placeholder="例如：香菜、苦瓜")
    prefer_cuisine = st.selectbox("偏好菜系", ["不限", "中式", "西式", "日式", "粤式"])
    vegetarian = st.checkbox("素食")
    halal = st.checkbox("清真")
    if st.button("保存饮食偏好", key="save_diet_pref"):
        with st.spinner("保存中……"):
            try:
                # 先通过对话获取 user_id，或者直接调用聊天接口
                pref_msg = (
                    f"保存我的饮食偏好：过敏原={allergens}, 忌口={dislike_foods}, "
                    f"菜系={prefer_cuisine}, 素食={vegetarian}, 清真={halal}"
                )
                resp = requests.post(
                    f"{API_BASE}/api/chat",
                    json={"message": pref_msg, "openid": openid or "default_user"},
                    headers={"X-OpenID": openid or "default_user"},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                st.markdown(data.get("reply", "保存完成"))
            except Exception as e:
                st.error(f"保存失败：{e}")

# ---------- Tab 5: 进度图表 ----------
with tab5:
    st.subheader("📊 进度趋势图表")
    days = st.selectbox("查看天数", [7, 14, 30, 60, 90], index=2, key="chart_days_v2")
    try:
        resp = requests.get(
            f"{API_BASE}/api/records/chart",
            params={"days": days},
            headers={"X-OpenID": openid or "default_user"},
            timeout=10,
        )
        resp.raise_for_status()
        chart_data = resp.json().get("data", {})
        records = chart_data.get("records", [])
        if records:
            df = pd.DataFrame(records)
            df["date"] = pd.to_datetime(df["date"])
            if "weight_kg" in df.columns and df["weight_kg"].notna().any():
                fig_w = px.line(df, x="date", y="weight_kg", markers=True, title="体重趋势 (kg)")
                st.plotly_chart(fig_w, use_container_width=True)
            if "calories_eaten" in df.columns and df["calories_eaten"].notna().any():
                fig_c = px.bar(df, x="date", y="calories_eaten", title="每日摄入卡路里")
                st.plotly_chart(fig_c, use_container_width=True)
            if "workout_minutes" in df.columns and df["workout_minutes"].notna().any():
                fig_wk = px.bar(df, x="date", y="workout_minutes", title="每日运动时长 (分钟)")
                st.plotly_chart(fig_wk, use_container_width=True)
        else:
            st.info("暂无数据，去对话中记录一些打卡数据吧。")
    except Exception as e:
        st.error(f"获取图表失败：{e}")

# ---------- Tab 6: 报告导出 ----------
with tab6:
    st.subheader("📄 健康报告导出")
    st.write("生成 PDF 格式的健康周报/月报，包含打卡记录、膳食计划、购物清单。")
    report_type = st.selectbox("报告类型", ["weekly", "monthly"], format_func=lambda x: "周报" if x == "weekly" else "月报")
    if st.button("生成并下载 PDF 报告", key="gen_pdf_report"):
        with st.spinner("生成 PDF 报告中……"):
            try:
                # 先通过对话触发报告生成
                resp = requests.post(
                    f"{API_BASE}/api/chat",
                    json={"message": f"为我生成一份{report_type}健康报告并导出 PDF"},
                    headers={"X-OpenID": openid or "default_user"},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                st.markdown(data.get("reply", "无回复"))

                # 尝试提供下载链接（需知道 user_id，这里提示用户通过 API 下载）
                st.info("💡 PDF 已生成，你可以通过以下 API 下载：")
                st.code(f"GET {API_BASE}/api/reports/{{user_id}}/pdf?report_type={report_type}")
                st.info("需要先在对话中获取你的 user_id，或替换 {{user_id}} 为实际用户 ID。")
            except Exception as e:
                st.error(f"生成失败：{e}")
