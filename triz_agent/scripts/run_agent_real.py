"""TrizAgent 真实用例测试：记录 Agent 每一步的决策过程。"""

import json
from triz_agent.agent import TrizAgent

QUESTION = "如何减少汽车发动机噪音"

print(f"问题: {QUESTION}")
print("=" * 60)

steps_log = []


def callback(event_type, data):
    if event_type == "step_start":
        print(f"\n[STEP START] {data['step_name']}")
        if "agent_thought" in data:
            print(f"  Thought: {data['agent_thought']}")
    elif event_type == "step_complete":
        result = data.get("result", {})
        summary = ""
        if data["step_name"] == "m1_modeling":
            summary = f"SAO: {len(result.get('sao_list', []))} 个"
        elif data["step_name"] == "m2_causal":
            summary = f"根因: {result.get('root_param', 'N/A')}"
        elif data["step_name"] == "m3_formulation":
            summary = f"矛盾: {result.get('problem_type', 'N/A')}"
        elif data["step_name"] == "m4_solver":
            summary = f"原理: {result.get('principles', [])}"
        elif data["step_name"] == "FOS":
            summary = f"案例: {len(result.get('cases', []))} 个"
        elif data["step_name"] == "m5_generation":
            summary = f"方案: {len(result.get('solution_drafts', []))} 个"
        elif data["step_name"] == "m6_evaluation":
            summary = f"理想度: {result.get('max_ideality', 0)}"
        print(f"[STEP DONE] {data['step_name']} -> {summary}")
    elif event_type == "report":
        print(f"\n[REPORT] {data['content'][:200]}...")
    elif event_type == "step_error":
        print(f"[ERROR] {data['step_name']}: {data['error']}")

    steps_log.append({"event": event_type, "data": data})


agent = TrizAgent(callback=callback)
result = agent.run(QUESTION)

print(f"\n{'=' * 60}")
print(f"总步数: {len([s for s in steps_log if s['event'] == 'step_start'])}")
print(f"结果长度: {len(result)} 字符")

# 保存详细日志（过滤掉不可序列化的对象）
import datetime


def json_safe(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


with open("scripts/reports/agent_run_log.json", "w", encoding="utf-8") as f:
    json.dump(steps_log, f, ensure_ascii=False, indent=2, default=json_safe)
print("日志已保存到 scripts/reports/agent_run_log.json")
