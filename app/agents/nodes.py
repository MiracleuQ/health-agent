"""LangGraph 各代理节点实现。"""
import json
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.agents.state import AgentState
from app.tools.health_tools import ALL_TOOLS, TOOLS_BY_NAME, query_knowledge
from app.core.logging import logger
from app.core.config import settings


_llm = None
_llm_with_tools = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.MODEL_NAME,
            temperature=settings.TEMPERATURE,
            base_url=settings.BASE_URL,
            api_key=settings.OPENAI_API_KEY,
        )
    return _llm


def _get_llm_with_tools():
    global _llm_with_tools
    if _llm_with_tools is None:
        _llm_with_tools = _get_llm().bind_tools(ALL_TOOLS)
    return _llm_with_tools


def _find_tool(name: str):
    return TOOLS_BY_NAME.get(name)


# ---------------------------------------------------------------------------
# 协调器：意图识别与路由
# ---------------------------------------------------------------------------
COORDINATOR_SYSTEM = """你是健康管理 Agent 的协调器。根据用户输入和当前状态，判断用户意图并路由到合适的专业代理：

意图分类：
- plan：用户想制定减脂/增肌/维持计划（输入目标卡路里、训练周期等）
- nutrition：用户询问饮食、营养搭配、卡路里控制
- fitness：用户询问运动计划、训练安排
- record：用户要打卡记录体重/饮食/运动/饮水，或查看历史/趋势图表
- query：用户询问健康知识（如“减脂怎么吃”“BMI 正常范围”）
- food_estimate：用户描述或上传食物，想估算卡路里并记录
- meal_plan：用户想生成一周膳食计划与购物清单
- diet_preference：用户想设置饮食偏好、过敏原、菜系等
- report：用户想导出健康报告（PDF 周报/月报）
- unknown：无法确定，需向用户澄清

路由目标代理名：planner | nutritionist | fitness_coach | tracker | knowledge | food_estimator | meal_planner | diet_coach | report_generator | clarifier

只输出意图代理名，不要额外解释。"""


def coordinator_node(state: AgentState) -> AgentState:
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COORDINATOR_SYSTEM),
            ("human", "{input}"),
        ]
    )
    chain = prompt | _get_llm()
    result = chain.invoke({"input": user_text})
    intent = result.content.strip().lower()

    intent_map = {
        "plan": "planner",
        "nutrition": "nutritionist",
        "fitness": "fitness_coach",
        "record": "tracker",
        "query": "knowledge",
        "food_estimate": "food_estimator",
        "meal_plan": "meal_planner",
        "diet_preference": "diet_coach",
        "report": "report_generator",
    }
    next_agent = intent_map.get(intent, "clarifier")

    logger.info("协调器路由：intent={}, next_agent={}", intent, next_agent)
    return {
        **state,
        "intent": intent,
        "next_agent": next_agent,
    }


def clarifier_node(state: AgentState) -> AgentState:
    reply = (
        "你好！我是你的 AI 健康管理助手。我可以帮你：\n"
        "1. 📋 制定个性化减脂/增肌/维持计划（基于目标卡路里、训练周期等）\n"
        "2. 🍎 提供饮食营养建议与示例食谱\n"
        "3. 🏋️ 制定运动训练计划（力量/有氧/HIIT 安排）\n"
        "4. 📝 每日健康打卡与进度趋势分析\n"
        "5. 📚 回答健康管理专业问题\n\n"
        "请告诉我你需要什么，例如：“我想制定一个 8 周的减脂计划，目标每日 1800 大卡”。"
    )
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=reply)],
        "finished": True,
    }


# ---------------------------------------------------------------------------
# 通用工具调用代理工厂（planner / nutritionist / fitness_coach / tracker）
# ---------------------------------------------------------------------------
def make_agent_node(system_prompt: str, agent_name: str):
    def node(state: AgentState) -> AgentState:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        chain = prompt | _get_llm_with_tools()
        response = chain.invoke({"messages": state["messages"]})
        logger.debug("{} 生成回复，tool_calls={}", agent_name, bool(getattr(response, "tool_calls", None)))
        return {
            **state,
            "messages": state["messages"] + [response],
            "next_agent": agent_name,
        }
    return node


PLANNER_PROMPT = """你是资深健康计划制定师。用户希望制定减脂/增肌/维持计划。
任务：
1. 先调用 get_user_profile 获取用户档案；如没有档案，引导用户补充年龄、性别、身高、体重、活动水平。
2. 调用 calculate_bmr_tdee 计算基础代谢与总消耗。
3. 根据目标卡路里缺口（建议 300-500 大卡）和训练周期，生成结构化计划，包含：
   - 每日目标卡路里与宏量营养素分配（蛋白质/碳水/脂肪，用 calculate_macros 工具）
   - 每周运动安排（力量训练 + 有氧，频次与时长）
   - 饮食建议（主食/蛋白质/蔬菜示例）
   - 注意事项与安全提醒（最低安全卡路里、过度训练信号）
4. 调用 save_plan 将计划保存，plan_type 使用 "fat_loss" / "muscle_gain" / "maintain"。
   注意：计划保存后状态为 "pending"（待审核），需要人工审核通过后才正式生效。
5. 以清晰、可执行的中文输出最终计划，并告知用户计划已提交审核。

不要编造数据，所有计算必须通过工具完成。"""


NUTRITIONIST_PROMPT = """你是注册营养师。基于用户档案和目标卡路里，提供饮食方案。
任务：
1. 调用 get_user_profile 了解用户基础信息。
2. 调用 query_knowledge 查阅减脂/营养相关专业知识。
3. 给出每日膳食结构建议（三餐分配、主食粗细搭配、蛋白质来源、蔬菜水果）。
4. 提供 3 天示例食谱（每餐食材与大概卡路里）。
5. 强调蛋白质摄入（1.6-2.2g/kg 体重）和水分摄入（2000-3000ml）。

输出中文，结构清晰，可直接执行。"""


FITNESS_COACH_PROMPT = """你是健身教练。基于用户目标与训练周期，制定运动计划。
任务：
1. 调用 get_user_profile 获取用户信息。
2. 根据训练周期（周数）和当前基础，给出每周训练频次、每次时长、训练内容（力量/有氧/HIIT）。
3. 包含热身与拉伸建议，标注过度训练警示信号。
4. 约束：HIIT 每周不超过 3 次，力量训练每周 2-3 次，每次 40-60 分钟。

输出中文，计划可直接执行。"""


TRACKER_PROMPT = """你是健康数据助手。帮助用户记录与分析每日健康数据。
任务：
1. 如用户要打卡，调用 add_record 保存体重/卡路里/运动/饮水/备注。
2. 如用户要查看进度，调用 get_recent_records 或 get_records_chart 获取记录并分析趋势。
3. 根据记录给出简短反馈（如“本周平均卡略超标，建议下周调整”）。
4. 若无足够数据，提示用户补充。

输出中文，友好且专业。"""


planner_node = make_agent_node(PLANNER_PROMPT, "planner")
nutritionist_node = make_agent_node(NUTRITIONIST_PROMPT, "nutritionist")
fitness_coach_node = make_agent_node(FITNESS_COACH_PROMPT, "fitness_coach")
tracker_node = make_agent_node(TRACKER_PROMPT, "tracker")

FOOD_ESTIMATOR_PROMPT = """你是营养估算助手。用户描述食物（或上传食物照片描述），你需要估算卡路里和营养成分。
任务：
1. 调用 estimate_food_calories 工具根据食物描述估算卡路里、蛋白质/碳水/脂肪。
2. 如用户要求记录打卡，调用 save_food_record_with_estimate 自动写入记录（需 user_id，可先调用 get_user_profile 获取）。
3. 以友好中文输出估算结果，提示“估算值仅供参考，实际受分量和烹饪方式影响”。
不要编造数据，所有估算必须通过工具完成。"""


MEAL_PLANNER_PROMPT = """你是膳食计划师。为用户生成一周（7天）膳食计划与购物清单。
任务：
1. 调用 get_user_profile 获取用户基础信息（目标卡路里、体重、目标等）。
2. 调用 get_diet_preference 获取过敏原、忌口、菜系偏好、素食/清真等硬约束。
3. 基于目标卡路里和饮食约束，生成 7 天每日三餐（早餐/午餐/晚餐/加餐）建议，每餐含食材和大概卡路里。
4. 整理购物清单（去重后的食材列表）。
5. 调用 save_weekly_meal_plan 保存计划，week_start 为本周一的日期。
6. 输出清晰的中文计划表和购物清单，可直接执行。
所有计划必须尊重饮食偏好（如不过敏原、不过忌口等）。"""


DIET_COACH_PROMPT = """你是饮食偏好助手。帮助用户设置和查询饮食偏好、过敏原等信息。
任务：
1. 如用户想设置偏好（过敏原、忌口、菜系、素食/清真等），调用 save_diet_preference 保存。
2. 如用户想查看当前偏好，调用 get_diet_preference 查询。
3. 提示用户这些偏好将用于后续膳食计划生成，确保饮食安全。
输出中文，友好专业。"""


food_estimator_node = make_agent_node(FOOD_ESTIMATOR_PROMPT, "food_estimator")
meal_planner_node = make_agent_node(MEAL_PLANNER_PROMPT, "meal_planner")
diet_coach_node = make_agent_node(DIET_COACH_PROMPT, "diet_coach")


def report_generator_node(state: AgentState) -> AgentState:
    """生成健康报告 PDF。"""
    user_id = state.get("user_id")
    openid = state.get("openid")
    if not user_id:
        # 尝试从 openid 获取 user_id
        from app.tools.health_tools import get_user_profile
        profile_res = json.loads(get_user_profile.invoke({"openid": openid or ""}))
        if profile_res.get("found"):
            user_id = profile_res["profile"]["id"]

    if not user_id:
        reply = "❌ 无法获取用户信息，请先设置健康档案。"
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=reply)],
            "finished": True,
        }

    from app.tools.health_tools import generate_health_report_pdf
    result = json.loads(generate_health_report_pdf.invoke({"user_id": user_id, "report_type": "weekly"}))
    if result.get("error"):
        reply = f"❌ 报告生成失败：{result['error']}"
    else:
        pdf_path = result.get("pdf_path", "")
        reply = (
            f"✅ 健康周报 PDF 已生成！\n\n"
            f"文件路径：{pdf_path}\n\n"
            f"你可以通过 API 接口下载：`GET /api/reports/{user_id}/pdf?report_type=weekly`\n\n"
            f"报告包含：每日打卡记录、最新膳食计划与购物清单、健康计划记录。"
        )
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=reply)],
        "finished": True,
    }


# ---------------------------------------------------------------------------
# 知识代理
# ---------------------------------------------------------------------------
def knowledge_node(state: AgentState) -> AgentState:
    last_msg = state["messages"][-1] if state["messages"] else None
    query = last_msg.content if last_msg else ""
    context = query_knowledge.invoke({"query": query})
    reply = (
        "基于健康管理知识库，为你整理如下信息：\n\n"
        f"{context}\n\n"
        "如需更个性化的建议，请告诉我你的身高、体重、目标等信息。"
    )
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=reply)],
        "knowledge_context": context,
        "finished": True,
    }


# ---------------------------------------------------------------------------
# 人工审批节点（Human-in-the-loop）
# ---------------------------------------------------------------------------
def human_approval_node(state: AgentState) -> AgentState:
    """计划保存后进入人工审批节点。生成审批提示，等待后台通过 API 审核。"""
    plan_content = state.get("plan_content")
    plan_id = state.get("plan_id")
    reply = (
        f"📋 你的健康计划（ID: {plan_id}）已生成并提交审核，当前状态：pending（待审核）。\n\n"
        "计划摘要：\n"
        f"{json.dumps(plan_content, ensure_ascii=False, indent=2) if plan_content else '暂无详情'}\n\n"
        "⚠️ 健康计划涉及个人身体安全，需要经过专业教练/营养师审核后才正式生效。\n"
        "管理员可通过 `/api/plans/{plan_id}/approve` 接口审核通过或拒绝。\n"
        "审核通过后，计划将生效并可供执行。"
    )
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=reply)],
        "finished": True,
    }


# ---------------------------------------------------------------------------
# 工具执行节点（统一 ToolNode）
# ---------------------------------------------------------------------------
def tools_node(state: AgentState) -> AgentState:
    """执行 Agent 请求的工具调用，并将结果注入消息流。"""
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    results = []
    for call in tool_calls:
        name = call["name"]
        args = call.get("args", {})
        tool_fn = _find_tool(name)
        if tool_fn is None:
            results.append({"tool_call_id": call["id"], "output": "未知工具"})
            continue
        try:
            output = tool_fn.invoke(args)
            results.append({"tool_call_id": call["id"], "output": output})
            logger.debug("工具调用成功：{}", name)
        except Exception as e:
            logger.error("工具执行错误：{} - {}", name, e)
            results.append({"tool_call_id": call["id"], "output": f"工具执行错误：{e}"})

    tool_messages = [
        ToolMessage(content=r["output"], tool_call_id=r["tool_call_id"])
        for r in results
    ]
    return {
        **state,
        "messages": state["messages"] + tool_messages,
    }


# ---------------------------------------------------------------------------
# 路由逻辑
# ---------------------------------------------------------------------------
def route_after_coordinator(state: AgentState) -> str:
    next_agent = state.get("next_agent")
    mapping = {
        "planner": "planner",
        "nutritionist": "nutritionist",
        "fitness_coach": "fitness_coach",
        "tracker": "tracker",
        "knowledge": "knowledge",
        "food_estimator": "food_estimator",
        "meal_planner": "meal_planner",
        "diet_coach": "diet_coach",
        "report_generator": "report_generator",
    }
    return mapping.get(next_agent, "clarifier")


def route_after_agent(state: AgentState) -> str:
    """代理调用完工具后，继续执行工具；无工具调用则结束。"""
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", None) or []
    if tool_calls:
        return "tools"
    return "end"


def route_after_tools(state: AgentState) -> str:
    """工具执行完后，返回原代理继续推理；若已有最终自然语言回复则结束。"""
    last_msg = state["messages"][-1]
    if isinstance(last_msg, AIMessage) and not getattr(last_msg, "tool_calls", None):
        # 代理已给出最终回复
        # 如果该代理是 planner 且刚保存了计划，进入人工审批节点
        next_agent = state.get("next_agent")
        if next_agent == "planner":
            # 检查最近是否调用了 save_plan
            for m in reversed(state["messages"]):
                if isinstance(m, ToolMessage) and "save_plan" in str(m.content):
                    return "human_approval"
        return "end"
    return state.get("next_agent", "coordinator")


# ---------------------------------------------------------------------------
# 构建图
# ---------------------------------------------------------------------------
def build_graph():
    from langgraph.graph import StateGraph, END
    from app.agents.memory import get_checkpointer

    builder = StateGraph(AgentState)

    builder.add_node("coordinator", coordinator_node)
    builder.add_node("clarifier", clarifier_node)
    builder.add_node("planner", planner_node)
    builder.add_node("nutritionist", nutritionist_node)
    builder.add_node("fitness_coach", fitness_coach_node)
    builder.add_node("tracker", tracker_node)
    builder.add_node("knowledge", knowledge_node)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("food_estimator", food_estimator_node)
    builder.add_node("meal_planner", meal_planner_node)
    builder.add_node("diet_coach", diet_coach_node)
    builder.add_node("report_generator", report_generator_node)
    builder.add_node("tools", tools_node)

    builder.set_entry_point("coordinator")

    builder.add_conditional_edges("coordinator", route_after_coordinator)
    builder.add_edge("clarifier", END)

    for agent in (
        "planner",
        "nutritionist",
        "fitness_coach",
        "tracker",
        "food_estimator",
        "meal_planner",
        "diet_coach",
        "report_generator",
    ):
        builder.add_conditional_edges(
            agent,
            route_after_agent,
            {"tools": "tools", "end": END},
        )

    builder.add_conditional_edges("knowledge", lambda s: "end", {"end": END})
    builder.add_edge("human_approval", END)

    builder.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "planner": "planner",
            "nutritionist": "nutritionist",
            "fitness_coach": "fitness_coach",
            "tracker": "tracker",
            "food_estimator": "food_estimator",
            "meal_planner": "meal_planner",
            "diet_coach": "diet_coach",
            "report_generator": "report_generator",
            "human_approval": "human_approval",
            "end": END,
            "coordinator": "coordinator",
        },
    )

    checkpointer = get_checkpointer()
    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
