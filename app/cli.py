"""命令行交互入口。"""
from langchain_core.messages import HumanMessage
from app.agents.graph import graph
from app.agents.state import AgentState
from app.core.logging import logger


def main():
    print("=== AI 健康管理 Agent (命令行版) ===")
    openid = input("请输入你的用户标识（如 handset_id / wechat_openid）: ").strip() or "default_user"
    print("输入 'exit' 退出，输入 'help' 查看帮助。\n")

    config = {"configurable": {"thread_id": openid}}

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！祝健康。")
            break

        if user_input.lower() in ("exit", "quit"):
            print("再见！祝健康。")
            break
        if user_input.lower() == "help":
            print("示例：")
            print("  - 我想制定一个 8 周减脂计划，目标每日 1800 大卡")
            print("  - 我的档案：25岁，男，175cm，70kg，中度活动")
            print("  - 记录今天：体重 70kg，摄入 1700 大卡，运动 40 分钟")
            print("  - 减脂期间怎么吃主食？")
            continue

        state: AgentState = {
            "messages": [HumanMessage(content=user_input)],
            "openid": openid,
            "user_id": None,
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
            msgs = result.get("messages", [])
            for m in reversed(msgs):
                if m.type == "ai" and m.content:
                    print(f"\nAgent: {m.content}\n")
                    break
        except Exception as e:
            logger.exception("对话出错：{}", e)
            print(f"\n出错：{e}\n")


if __name__ == "__main__":
    main()
