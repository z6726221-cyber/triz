"""批量测试基础模块：统一结果记录和报告格式。"""
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# 修复 Windows 终端中文编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from triz.orchestrator import Orchestrator
from triz.utils.vector_math import preload_model


def run_single(question: str, verbose: bool = False) -> dict:
    """运行单个问题，返回详细结果。"""
    start = time.time()
    orch = Orchestrator(callback=None)

    # 收集节点信息
    nodes_info = []
    errors = []

    def capture_callback(event_type, data):
        if event_type == "step_error":
            errors.append({
                "node": nodes_info[-1]["name"] if nodes_info else "unknown",
                "step": data.get("step_name"),
                "error": data.get("error"),
            })
        elif event_type == "node_start":
            nodes_info.append({
                "name": data["node_name"],
                "current": data["current"],
                "started_at": time.time(),
            })

    orch.callback = capture_callback

    try:
        report = orch.run_workflow(question)
        success = True
        failure_stage = None
    except Exception as e:
        success = False
        report = str(e)
        failure_stage = errors[-1]["step"] if errors else "unknown"
        if verbose:
            traceback.print_exc()

    elapsed = time.time() - start

    return {
        "question": question,
        "success": success,
        "elapsed_seconds": round(elapsed, 2),
        "report_length": len(report),
        "errors": errors,
        "failure_stage": failure_stage,
        "report_preview": report[:500] if report else "",
    }


def run_batch(test_cases: list[dict], name: str, verbose: bool = False) -> dict:
    """批量运行测试用例。

    test_cases: [{"question": str, "expected_behavior": str, ...}]
    """
    print(f"\n{'='*60}")
    print(f"开始运行: {name}")
    print(f"用例数: {len(test_cases)}")
    print(f"{'='*60}")

    # 预加载 sentence-transformers 模型，避免第一个用例额外耗时
    print("预加载语义模型...")
    preload_model()
    print("预加载完成。\n")

    results = []
    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        print(f"[{i}/{len(test_cases)}] {question[:60]}...")
        result = run_single(question, verbose=verbose)
        result.update(case)  # 合并元数据
        results.append(result)
        status = "PASS" if result["success"] else "FAIL"
        print(f"      -> {status} ({result['elapsed_seconds']}s)")
        # 用例之间延迟，避免 API 速率限制（M3 改为 LLM Skill 后每次请求更多）
        if i < len(test_cases):
            time.sleep(8.0)

    summary = {
        "test_name": name,
        "timestamp": datetime.now().isoformat(),
        "total": len(test_cases),
        "passed": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "avg_time": round(sum(r["elapsed_seconds"] for r in results) / len(results), 2),
        "results": results,
    }

    # 保存报告
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"完成: {name}")
    print(f"通过: {summary['passed']}/{summary['total']}")
    print(f"失败: {summary['failed']}/{summary['total']}")
    print(f"平均耗时: {summary['avg_time']}s")
    print(f"报告保存: {report_path}")
    print(f"{'='*60}\n")

    return summary
