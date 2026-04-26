"""生成 Orchestrator vs Agent 双模式对比报告。
用法: python generate_report.py <orch_json> <agent_json>
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def load_results(filepath: str) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_report(orch_path: str, agent_path: str, output_path: str = None):
    orch = load_results(orch_path)
    agent = load_results(agent_path)

    orch_results = {r["question"]: r for r in orch["results"]}
    agent_results = {r["question"]: r for r in agent["results"]}
    all_questions = sorted(set(orch_results.keys()) | set(agent_results.keys()))

    lines = []
    lines.append("# TRIZ 双模式端到端测试报告")
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # 摘要
    lines.append("## 执行摘要")
    lines.append("")
    lines.append("| 指标 | Orchestrator | Agent |")
    lines.append("|------|-------------|-------|")
    lines.append(f"| 总用例数 | {orch['total']} | {agent['total']} |")
    lines.append(f"| 通过 | {orch['passed']} | {agent['passed']} |")
    lines.append(f"| 失败 | {orch.get('failed', 0)} | {agent.get('failed', 0)} |")
    lines.append(f"| 超时 | {orch.get('timeouts', 0)} | {agent.get('timeouts', 0)} |")
    lines.append(f"| 平均耗时 | {orch['avg_time']}s | {agent['avg_time']}s |")
    lines.append("")

    # 逐用例对比
    lines.append("## 逐用例对比")
    lines.append("")
    lines.append("| # | 问题 | Orch 状态 | Orch 耗时 | Agent 状态 | Agent 耗时 | 步骤差异 |")
    lines.append("|---|------|-----------|-----------|------------|------------|----------|")

    for i, q in enumerate(all_questions, 1):
        o = orch_results.get(q, {})
        a = agent_results.get(q, {})

        o_status = "PASS" if o.get("success") else ("TIMEOUT" if o.get("timeout") else "FAIL")
        a_status = "PASS" if a.get("success") else ("TIMEOUT" if a.get("timeout") else "FAIL")

        o_time = o.get("elapsed_seconds", 0)
        a_time = a.get("elapsed_seconds", 0)

        o_steps = set(o.get("steps_log", []))
        a_steps = set(a.get("steps_log", []))
        skipped = o_steps - a_steps if o_steps else set()
        extra = a_steps - o_steps if o_steps else set()
        diff = ""
        if skipped:
            diff += f"跳过:{','.join(skipped)} "
        if extra:
            diff += f"额外:{','.join(extra)}"
        if not diff:
            diff = "一致"

        q_short = q[:40] + "..." if len(q) > 40 else q
        lines.append(f"| {i} | {q_short} | {o_status} | {o_time}s | {a_status} | {a_time}s | {diff} |")

    lines.append("")

    # Agent 决策摘要
    lines.append("## Agent 决策摘要")
    lines.append("")
    for q in all_questions:
        a = agent_results.get(q, {})
        thoughts = a.get("agent_thoughts", [])
        if thoughts:
            lines.append(f"**{q[:50]}**")
            for t in thoughts:
                thought = t.get("thought", "")[:80]
                lines.append(f"- {t.get('step', '?')}: {thought}...")
            lines.append("")

    # 失败详情
    failures = []
    for q in all_questions:
        o = orch_results.get(q, {})
        a = agent_results.get(q, {})
        if not o.get("success") or not a.get("success"):
            failures.append((q, o, a))

    if failures:
        lines.append("## 失败/超时详情")
        lines.append("")
        for q, o, a in failures:
            lines.append(f"### {q}")
            if not o.get("success"):
                lines.append(f"- Orchestrator: {o.get('failure_stage', 'unknown')} - {o.get('errors', [])}")
            if not a.get("success"):
                lines.append(f"- Agent: {a.get('failure_stage', 'unknown')} - {a.get('errors', [])}")
            lines.append("")
    else:
        lines.append("## 失败/超时详情")
        lines.append("")
        lines.append("全部用例通过，无失败/超时。")
        lines.append("")

    # 结论
    lines.append("## 结论")
    lines.append("")
    orch_ok = orch["passed"] == orch["total"]
    agent_ok = agent["passed"] == agent["total"]
    if orch_ok and agent_ok:
        lines.append("两种模式全部通过测试，功能正确性一致。")
    elif orch_ok and not agent_ok:
        lines.append("Orchestrator 全部通过，Agent 存在失败用例，需排查 Agent 决策逻辑。")
    elif not orch_ok and agent_ok:
        lines.append("Agent 全部通过，Orchestrator 存在失败用例，需排查硬编码流程。")
    else:
        lines.append("两种模式均存在失败用例，需分别排查。")
    lines.append("")

    report_text = "\n".join(lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"报告已保存: {output_path}")
    else:
        print(report_text)

    return report_text


def main():
    if len(sys.argv) < 3:
        print("用法: python generate_report.py <orch_json> <agent_json> [output_md]")
        sys.exit(1)

    orch_path = sys.argv[1]
    agent_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(orch_path).parent / f"e2e_report_{ts}.md")

    generate_report(orch_path, agent_path, output_path)


if __name__ == "__main__":
    main()
