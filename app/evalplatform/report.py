"""评测报告生成：HTML 格式报告。"""
from typing import Dict, Any, List
from datetime import datetime
import os


def generate_html_report(
    run_result: Dict[str, Any],
    output_path: str = "./eval_report.html",
) -> str:
    """生成 HTML 评测报告，返回报告文件路径。"""
    total = run_result.get("total_cases", 0)
    metrics = {
        "intent_accuracy": run_result.get("intent_accuracy", 0),
        "tool_match_rate": run_result.get("tool_match_rate", 0),
        "safety_rate": run_result.get("safety_rate", 0),
    }
    details = run_result.get("details", [])

    rows = ""
    for d in details:
        status_icon = "✅" if (d.get("intent_match") and d.get("safe")) else "❌"
        rows += f"""
        <tr>
            <td>{d.get('case_id','')}</td>
            <td>{d.get('input','')}</td>
            <td>{d.get('expected_intent','')}</td>
            <td>{d.get('actual_intent','')}</td>
            <td>{'✅' if d.get('intent_match') else '❌'}</td>
            <td>{'✅' if d.get('safe') else '❌'}</td>
            <td>{d.get('reply','')[:100]}...</td>
            <td>{status_icon}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>健康管理 Agent 评测报告</title>
    <style>
        body {{ font-family: "Microsoft YaHei", sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 24px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1890ff; border-bottom: 2px solid #1890ff; padding-bottom: 10px; }}
        .metrics {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric-card {{ flex: 1; background: #f0f7ff; padding: 16px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1890ff; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f0f7ff; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        .badge-safe {{ color: #52c41a; }}
        .badge-unsafe {{ color: #ff4d4f; }}
        .footer {{ margin-top: 30px; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 健康管理 Agent 评测报告</h1>
        <p><strong>运行时间：</strong>{run_result.get('created_at', datetime.now().isoformat())}</p>
        <p><strong>用例总数：</strong>{total}</p>

        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{metrics['intent_accuracy']*100:.1f}%</div>
                <div class="metric-label">意图识别准确率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['tool_match_rate']*100:.1f}%</div>
                <div class="metric-label">工具调用匹配率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{metrics['safety_rate']*100:.1f}%</div>
                <div class="metric-label">安全拒绝率</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>用例 ID</th>
                    <th>用户输入</th>
                    <th>预期意图</th>
                    <th>实际意图</th>
                    <th>意图匹配</th>
                    <th>安全检查</th>
                    <th>Agent 回复（摘要）</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>

        <div class="footer">
            生成于健康管理 Agent 评测中台 · 仅供内部评测使用
        </div>
    </div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
