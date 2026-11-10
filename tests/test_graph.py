"""Agent 图集成测试（需要 LLM，默认跳过，仅验证导入与构建）。"""
def test_graph_builds():
    from app.agents.graph import graph
    assert graph is not None


def test_state_keys():
    from app.agents.state import AgentState
    required = {"messages", "openid", "intent", "next_agent", "finished"}
    assert required.issubset(set(AgentState.__annotations__.keys()))
