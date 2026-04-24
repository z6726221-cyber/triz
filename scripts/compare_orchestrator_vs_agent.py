"""对比测试：Orchestrator（硬编码）vs TrizAgent（自主决策）。

用同一问题跑两个架构，对比：
1. 流程完整性（步骤数、是否跳过）
2. 决策差异（Agent 自主决策 vs 硬编码流程）
3. 输出质量（报告内容对比）
"""
import json
from datetime import datetime

QUESTION = "如何减少汽车发动机噪音"

print(f"对比问题: {QUESTION}")
print("=" * 70)

# ========== 1. 跑 Orchestrator ==========
print("\n[1/2] 运行 Orchestrator（硬编码流程）...")
orch_events = []

def orch_callback(event_type, data):
    orch_events.append({"event": event_type, "data": data, "time": datetime.now().isoformat()})

from triz.orchestrator import Orchestrator

orch = Orchestrator(callback=orch_callback)
try:
    orch_report = orch.run_workflow(QUESTION)
    orch_success = True
except Exception as e:
    orch_report = f"错误: {str(e)}"
    orch_success = False

orch_steps = [e for e in orch_events if e["event"] == "step_start"]
print(f"  步骤数: {len(orch_steps)}")
print(f"  执行流程: {[e['data']['step_name'] for e in orch_steps]}")
print(f"  成功: {orch_success}")

# ========== 2. 跑 TrizAgent ==========
print("\n[2/2] 运行 TrizAgent（自主决策）...")
agent_events = []

def agent_callback(event_type, data):
    agent_events.append({"event": event_type, "data": data, "time": datetime.now().isoformat()})

from triz.agent import TrizAgent

agent = TrizAgent(callback=agent_callback)
try:
    agent_report = agent.run(QUESTION)
    agent_success = True
except Exception as e:
    agent_report = f"错误: {str(e)}"
    agent_success = False

agent_steps = [e for e in agent_events if e["event"] == "step_start"]
print(f"  步骤数: {len(agent_steps)}")
print(f"  执行流程: {[e['data']['step_name'] for e in agent_steps]}")
print(f"  成功: {agent_success}")

# ========== 3. 对比分析 ==========
print("\n" + "=" * 70)
print("对比分析")
print("=" * 70)

print(f"\n流程差异:")
orch_flow = [e['data']['step_name'] for e in orch_steps]
agent_flow = [e['data']['step_name'] for e in agent_steps]

print(f"  Orchestrator: {' -> '.join(orch_flow)}")
print(f"  TrizAgent:    {' -> '.join(agent_flow)}")

# 检查 Agent 跳过了什么
orch_set = set(orch_flow)
agent_set = set(agent_flow)
skipped = orch_set - agent_set
extra = agent_set - orch_set
if skipped:
    print(f"  Agent 跳过: {skipped}")
if extra:
    print(f"  Agent 额外执行: {extra}")

# Agent thought 摘要
print(f"\nAgent 决策摘要:")
for e in agent_steps:
    thought = e['data'].get('agent_thought', '')
    if thought:
        print(f"  {e['data']['step_name']}: {thought[:80]}...")

# 报告长度对比
print(f"\n输出对比:")
print(f"  Orchestrator 报告: {len(orch_report)} 字符")
print(f"  TrizAgent 报告:    {len(agent_report)} 字符")

# 保存对比结果
result = {
    "question": QUESTION,
    "orchestrator": {
        "success": orch_success,
        "steps": orch_flow,
        "report_length": len(orch_report),
        "events": len(orch_events),
    },
    "agent": {
        "success": agent_success,
        "steps": agent_flow,
        "report_length": len(agent_report),
        "events": len(agent_events),
        "thoughts": [{"step": e['data']['step_name'], "thought": e['data'].get('agent_thought', '')} for e in agent_steps],
    },
}

with open("scripts/reports/compare_result.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n对比结果已保存到 scripts/reports/compare_result.json")
print("=" * 70)
