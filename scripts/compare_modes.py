"""Orchestrator vs Agent 双模式对比测试。

用同一组问题分别跑两个模式，对比流程、耗时、报告质量。
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 修复 Windows 终端中文编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 确保可以 import test_runner
sys.path.insert(0, str(Path(__file__).parent))

from test_runner import run_single
from triz.utils.vector_math import preload_model

# ========== 测试问题 ==========
TEST_QUESTIONS = [
    {
        "question": "汽车发动机噪音大，油耗高",
        "domain": "机械",
        "complexity": "低",
        "expected矛盾": "技术矛盾（噪音 vs 油耗）",
    },
    {
        "question": "手机电池续航短，用户需要轻薄手机",
        "domain": "电子",
        "complexity": "中",
        "expected矛盾": "物理矛盾（续航 vs 轻薄）",
    },
    {
        "question": "数据中心服务器散热功耗过高，降低风扇转速又导致芯片过热",
        "domain": "电子/散热",
        "complexity": "中",
        "expected矛盾": "技术矛盾（散热 vs 功耗）",
    },
    {
        "question": "手术刀片在多次使用后锋利度下降，频繁更换又增加手术风险和成本",
        "domain": "医疗机械",
        "complexity": "高",
        "expected矛盾": "技术矛盾（锋利度 vs 耐用性）",
    },
]


def run_comparison():
    """执行对比测试。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("Orchestrator vs Agent 双模式对比测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"问题数: {len(TEST_QUESTIONS)}")
    print("=" * 70)

    # 预加载模型
    print("\n预加载语义模型...")
    preload_model()
    print("预加载完成。\n")

    all_results = []

    for i, case in enumerate(TEST_QUESTIONS, 1):
        question = case["question"]
        print(f"\n{'─' * 70}")
        print(f"[{i}/{len(TEST_QUESTIONS)}] {question}")
        print(f"  领域: {case['domain']} | 复杂度: {case['complexity']}")
        print(f"{'─' * 70}")

        result = {"question": question, "meta": case}

        # --- Orchestrator ---
        print(f"\n  [Orchestrator] 运行中...")
        orch_result = run_single(question, verbose=False, mode="orchestrator")
        result["orchestrator"] = orch_result
        print(f"  [Orchestrator] {'PASS' if orch_result['success'] else 'FAIL'}"
              f" | 耗时: {orch_result['elapsed_seconds']}s"
              f" | 步骤: {len(orch_result['steps_log'])}"
              f" | 报告: {orch_result['report_length']}字符")

        time.sleep(3)  # 间隔避免 API 限流

        # --- Agent ---
        print(f"\n  [Agent] 运行中...")
        agent_result = run_single(question, verbose=False, mode="agent")
        result["agent"] = agent_result
        print(f"  [Agent] {'PASS' if agent_result['success'] else 'FAIL'}"
              f" | 耗时: {agent_result['elapsed_seconds']}s"
              f" | 步骤: {len(agent_result['steps_log'])}"
              f" | 报告: {agent_result['report_length']}字符")

        # Agent 决策摘要
        if agent_result.get("agent_thoughts"):
            print(f"\n  [Agent 决策链]")
            for t in agent_result["agent_thoughts"]:
                thought = t["thought"][:100] + "..." if len(t["thought"]) > 100 else t["thought"]
                print(f"    {t['step']}: {thought}")

        all_results.append(result)

        if i < len(TEST_QUESTIONS):
            time.sleep(5)

    # ========== 生成报告 ==========
    print(f"\n\n{'=' * 70}")
    print("生成对比报告...")
    print(f"{'=' * 70}")

    report_md = generate_report(all_results, timestamp)
    json_data = generate_json_data(all_results, timestamp)

    # 保存文件
    md_path = report_dir / f"mode_comparison_{timestamp}.md"
    json_path = report_dir / f"mode_comparison_{timestamp}.json"

    md_path.write_text(report_md, encoding="utf-8")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON:     {json_path}")
    print(f"\n{'=' * 70}")

    return all_results


def generate_report(results: list[dict], timestamp: str) -> str:
    """生成 Markdown 格式的对比报告。"""
    lines = []

    lines.append("# Orchestrator vs Agent 双模式对比测试报告\n")
    lines.append(f"- **测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **测试问题数**: {len(results)}")
    lines.append(f"- **模式**: Orchestrator（硬编码流程）vs Agent（ReAct 自主决策）")
    lines.append("")

    # --- 总体对比 ---
    lines.append("## 总体对比\n")

    orch_success = sum(1 for r in results if r["orchestrator"]["success"])
    agent_success = sum(1 for r in results if r["agent"]["success"])
    orch_avg_time = sum(r["orchestrator"]["elapsed_seconds"] for r in results) / len(results)
    agent_avg_time = sum(r["agent"]["elapsed_seconds"] for r in results) / len(results)
    orch_avg_len = sum(r["orchestrator"]["report_length"] for r in results) / len(results)
    agent_avg_len = sum(r["agent"]["report_length"] for r in results) / len(results)
    orch_avg_steps = sum(len(r["orchestrator"]["steps_log"]) for r in results) / len(results)
    agent_avg_steps = sum(len(r["agent"]["steps_log"]) for r in results) / len(results)

    lines.append("| 指标 | Orchestrator | Agent | 差异 |")
    lines.append("|------|-------------|-------|------|")
    lines.append(f"| 成功率 | {orch_success}/{len(results)} | {agent_success}/{len(results)} | - |")
    lines.append(f"| 平均耗时 | {orch_avg_time:.1f}s | {agent_avg_time:.1f}s | {agent_avg_time - orch_avg_time:+.1f}s |")
    lines.append(f"| 平均报告长度 | {orch_avg_len:.0f}字符 | {agent_avg_len:.0f}字符 | {agent_avg_len - orch_avg_len:+.0f} |")
    lines.append(f"| 平均步骤数 | {orch_avg_steps:.1f} | {agent_avg_steps:.1f} | {agent_avg_steps - orch_avg_steps:+.1f} |")
    lines.append("")

    # --- 逐题对比 ---
    lines.append("## 逐题对比\n")

    for i, r in enumerate(results, 1):
        q = r["question"]
        orch = r["orchestrator"]
        agent = r["agent"]

        lines.append(f"### 问题 {i}: {q}\n")
        lines.append(f"- **领域**: {r['meta']['domain']} | **复杂度**: {r['meta']['complexity']}")
        lines.append(f"- **预期矛盾**: {r['meta']['expected矛盾']}")
        lines.append("")

        # 流程对比
        lines.append("#### 流程对比\n")
        orch_flow = " → ".join(orch["steps_log"]) if orch["steps_log"] else "(无步骤)"
        agent_flow = " → ".join(agent["steps_log"]) if agent["steps_log"] else "(无步骤)"
        lines.append(f"**Orchestrator** ({len(orch['steps_log'])}步, {orch['elapsed_seconds']}s):")
        lines.append(f"```")
        lines.append(orch_flow)
        lines.append(f"```\n")
        lines.append(f"**Agent** ({len(agent['steps_log'])}步, {agent['elapsed_seconds']}s):")
        lines.append(f"```")
        lines.append(agent_flow)
        lines.append(f"```\n")

        # 步骤差异
        orch_set = set(orch["steps_log"])
        agent_set = set(agent["steps_log"])
        skipped = orch_set - agent_set
        extra = agent_set - orch_set
        if skipped or extra:
            lines.append("**差异分析**:\n")
            if skipped:
                lines.append(f"- Agent 跳过: {', '.join(skipped)}")
            if extra:
                lines.append(f"- Agent 额外执行: {', '.join(extra)}")
            lines.append("")

        # 报告质量
        lines.append("#### 报告质量\n")
        orch_has_report = "TRIZ 解决方案报告" in orch.get("report_preview", "")
        agent_has_report = "TRIZ 解决方案报告" in agent.get("report_preview", "")

        lines.append("| 指标 | Orchestrator | Agent |")
        lines.append("|------|-------------|-------|")
        lines.append(f"| 成功 | {'Y' if orch['success'] else 'N'} | {'Y' if agent['success'] else 'N'} |")
        lines.append(f"| 有效报告 | {'Y' if orch_has_report else 'N'} | {'Y' if agent_has_report else 'N'} |")
        lines.append(f"| 报告长度 | {orch['report_length']}字符 | {agent['report_length']}字符 |")
        lines.append(f"| 错误数 | {len(orch['errors'])} | {len(agent['errors'])} |")
        lines.append("")

        # 报告预览
        lines.append("<details>")
        lines.append(f"<summary>Orchestrator 报告预览 (前300字)</summary>\n")
        lines.append("```")
        lines.append(orch.get("report_preview", "(无)")[:300])
        lines.append("```\n</details>\n")

        lines.append("<details>")
        lines.append(f"<summary>Agent 报告预览 (前300字)</summary>\n")
        lines.append("```")
        lines.append(agent.get("report_preview", "(无)")[:300])
        lines.append("```\n</details>\n")

        # Agent 决策分析
        if agent.get("agent_thoughts"):
            lines.append("#### Agent 决策分析\n")
            for t in agent["agent_thoughts"]:
                thought = t["thought"][:200] + "..." if len(t["thought"]) > 200 else t["thought"]
                lines.append(f"- **{t['step']}**: {thought}")
            lines.append("")

        lines.append("---\n")

    # --- 结论 ---
    lines.append("## 结论\n")

    # 分析
    if agent_avg_steps > orch_avg_steps:
        step_note = f"Agent 平均多执行 {agent_avg_steps - orch_avg_steps:.1f} 步，流程更灵活但可能冗余"
    elif agent_avg_steps < orch_avg_steps:
        step_note = f"Agent 平均少执行 {orch_avg_steps - agent_avg_steps:.1f} 步，流程更精简"
    else:
        step_note = "两种模式步骤数相当"

    if agent_avg_time > orch_avg_time * 1.5:
        time_note = f"Agent 耗时显著更长（{agent_avg_time:.0f}s vs {orch_avg_time:.0f}s），主要来自 ReAct 决策开销"
    elif agent_avg_time > orch_avg_time:
        time_note = f"Agent 略慢（{agent_avg_time:.0f}s vs {orch_avg_time:.0f}s），决策开销可控"
    else:
        time_note = f"Agent 耗时与 Orchestrator 接近（{agent_avg_time:.0f}s vs {orch_avg_time:.0f}s）"

    lines.append(f"### 流程特征")
    lines.append(f"- {step_note}")
    lines.append(f"- {time_note}")
    lines.append("")

    lines.append("### 适用场景建议\n")
    lines.append("| 场景 | 推荐模式 | 原因 |")
    lines.append("|------|---------|------|")
    lines.append("| 标准工程问题 | Orchestrator | 流程确定、速度快、结果可预测 |")
    lines.append("| 复杂/非标问题 | Agent | 可跳过不相关步骤、灵活调整流程 |")
    lines.append("| 需要可解释性 | Agent | 每步有 thought 记录决策过程 |")
    lines.append("| 批量处理 | Orchestrator | 速度快、资源消耗低 |")
    lines.append("| 探索性分析 | Agent | 可能发现非标准路径 |")
    lines.append("")

    return "\n".join(lines)


def generate_json_data(results: list[dict], timestamp: str) -> dict:
    """生成 JSON 格式的原始数据。"""
    return {
        "timestamp": datetime.now().isoformat(),
        "total_questions": len(results),
        "results": [
            {
                "question": r["question"],
                "meta": r["meta"],
                "orchestrator": {
                    "success": r["orchestrator"]["success"],
                    "elapsed_seconds": r["orchestrator"]["elapsed_seconds"],
                    "report_length": r["orchestrator"]["report_length"],
                    "steps_log": r["orchestrator"]["steps_log"],
                    "errors": r["orchestrator"]["errors"],
                },
                "agent": {
                    "success": r["agent"]["success"],
                    "elapsed_seconds": r["agent"]["elapsed_seconds"],
                    "report_length": r["agent"]["report_length"],
                    "steps_log": r["agent"]["steps_log"],
                    "errors": r["agent"]["errors"],
                    "agent_thoughts": r["agent"].get("agent_thoughts", []),
                },
            }
            for r in results
        ],
    }


if __name__ == "__main__":
    run_comparison()
