"""端到端模型基准测试：同一问题，不同模型，两种模式，对比耗时和报告质量。"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from triz.utils.vector_math import preload_model

TEST_QUESTION = "手机电池续航短，用户需要轻薄手机"

MODELS = [
    "Ali-dashscope/DeepSeek-V3.2",
    "Ali-dashscope/Qwen3-Max",
    "Ali-dashscope/Qwen3.5-Plus",
    "SDU-AI/DeepSeek-V4-Flash",
    "SDU-AI/Qwen3-235B-A22B-Instruct-2507",
]


def run_e2e(question: str, model: str, mode: str) -> dict:
    """用指定模型运行端到端测试。"""
    import triz.config as config

    # 保存原始值
    orig = {}
    for attr in ["MODEL_NAME", "MODEL_M1", "MODEL_M2", "MODEL_M3", "MODEL_M5", "MODEL_M6"]:
        orig[attr] = getattr(config, attr)
        setattr(config, attr, model)

    steps_log = []
    errors = []
    agent_thoughts = []

    def callback(event_type, data):
        if event_type == "step_start":
            steps_log.append(data.get("step_name"))
            if "agent_thought" in data:
                agent_thoughts.append({
                    "step": data.get("step_name"),
                    "thought": data.get("agent_thought", "")[:200],
                })
        elif event_type == "step_error":
            errors.append(data.get("error", ""))

    try:
        start = time.time()
        if mode == "agent":
            from triz.agent import TrizAgent
            from triz.agent.skills.registry import AgentSkillRegistry
            from triz.tools.registry import register_default_tools
            tool_reg = register_default_tools()
            registry = AgentSkillRegistry()
            runner = TrizAgent(skill_registry=registry, tool_registry=tool_reg, callback=callback)
            report = runner.run(question)
        else:
            from triz.orchestrator import Orchestrator
            runner = Orchestrator(callback=callback)
            report = runner.run_workflow(question)

        elapsed = time.time() - start
        success = True
    except Exception as e:
        report = str(e)
        elapsed = time.time() - start if 'start' in dir() else 0
        success = False

    # 恢复原始值
    for attr, val in orig.items():
        setattr(config, attr, val)

    return {
        "model": model.split("/")[-1],
        "mode": mode,
        "success": success,
        "elapsed": round(elapsed, 1),
        "report_len": len(report) if report else 0,
        "steps": len(steps_log),
        "steps_log": steps_log,
        "errors": errors,
        "agent_thoughts": agent_thoughts,
        "preview": report[:200] if report else "",
    }


def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("端到端模型基准测试")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"问题: {TEST_QUESTION}")
    print(f"模型: {len(MODELS)} 个")
    print("=" * 70)

    print("\n预加载语义模型...")
    preload_model()
    print("完成。\n")

    all_results = []

    for model in MODELS:
        short_name = model.split("/")[-1]
        for mode in ["orchestrator", "agent"]:
            print(f"[{mode[:5].upper()}] {short_name} ...", end=" ", flush=True)
            result = run_e2e(TEST_QUESTION, model, mode)
            status = "PASS" if result["success"] else "FAIL"
            print(f"{status} | {result['elapsed']}s | {result['report_len']}字符 | {result['steps']}步")
            if result["errors"]:
                for e in result["errors"][:2]:
                    print(f"  ERR: {e[:100]}")
            all_results.append(result)
            time.sleep(3)

    # 汇总表格
    print(f"\n\n{'=' * 70}")
    print("汇总")
    print(f"{'=' * 70}\n")

    header = f"{'模型':<30} {'Orch耗时':>8} {'Orch长度':>8} {'Agent耗时':>9} {'Agent长度':>10}"
    print(header)
    print("-" * len(header))

    for model in MODELS:
        short = model.split("/")[-1]
        orch = next((r for r in all_results if r["model"] == short and r["mode"] == "orchestrator"), None)
        agent = next((r for r in all_results if r["model"] == short and r["mode"] == "agent"), None)
        ot = f"{orch['elapsed']}s" if orch and orch["success"] else "FAIL"
        ol = str(orch["report_len"]) if orch and orch["success"] else "-"
        at = f"{agent['elapsed']}s" if agent and agent["success"] else "FAIL"
        al = str(agent["report_len"]) if agent and agent["success"] else "-"
        print(f"{short:<30} {ot:>8} {ol:>8} {at:>9} {al:>10}")

    # 保存
    json_path = report_dir / f"model_benchmark_e2e_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n结果: {json_path}")


if __name__ == "__main__":
    main()
