"""LangGraph 共享状态定义。"""
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langchain_core.messages import BaseMessage, AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """多代理协作的共享状态。"""
    messages: Annotated[List[AnyMessage], add_messages]
    openid: Optional[str]
    user_id: Optional[int]
    user_profile: Optional[Dict[str, Any]]
    intent: Optional[str]  # plan | nutrition | fitness | record | query | unknown
    plan_content: Optional[Dict[str, Any]]
    plan_id: Optional[int]
    records: Optional[List[Dict[str, Any]]]
    knowledge_context: Optional[str]
    next_agent: Optional[str]  # 路由到的下一个代理名
    needs_approval: bool  # 是否需要人工审核
    finished: bool
