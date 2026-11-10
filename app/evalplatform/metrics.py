"""评测指标计算工具。"""
from typing import List, Dict, Any


def calculate_metrics(details: List[Dict[str, Any]]) -> Dict[str, float]:
    """从评测明细中计算聚合指标。"""
    total = len(details)
    if total == 0:
        return {
            "intent_accuracy": 0.0,
            "tool_match_rate": 0.0,
            "safety_rate": 0.0,
        }
    intent_acc = sum(1 for d in details if d.get("intent_match")) / total
    tool_rate = sum(1 for d in details if d.get("tool_match")) / total
    safe_rate = sum(1 for d in details if d.get("safe")) / total
    return {
        "intent_accuracy": round(intent_acc, 4),
        "tool_match_rate": round(tool_rate, 4),
        "safety_rate": round(safe_rate, 4),
    }
