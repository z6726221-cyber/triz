"""批量测试基础模块：统一结果记录和报告格式。支持 Orchestrator 和 Agent 双模式。"""

import concurrent.futures
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

from triz_agent.utils.vector_math import preload_model


def _log(msg: str, log_file=None):
    """同时输出到 stdout 和日志文件。"""
    print(msg, flush=True)
    if log_file:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
            f.flush()


def run_single(
    question: str, verbose: bool = False, mode: str = "orchestrator"
) -> dict:
    """运行单个问题，返回详细结果。mode: 'orchestrator' 或 'agent'。"""
    start = time.time()

    def _execute():
        nodes_info = []
        errors = []
        steps_log = []
        agent_thoughts = []

        def capture_callback(event_type, data):
            if event_type == "step_start":
                steps_log.append(data.get("step_name"))
                if "agent_thought" in data:
                    agent_thoughts.append(
                        {
                            "step": data.get("step_name"),
                            "thought": data.get("agent_thought", ""),
                        }
                    )
            elif event_type == "step_error":
                errors.append(
                    {
                        "node": nodes_info[-1]["name"] if nodes_info else "unknown",
                        "step": data.get("step_name"),
                        "error": data.get("error"),
                    }
                )
            elif event_type == "node_start":
                nodes_info.append(
                    {
                        "name": data["node_name"],
                        "current": data["current"],
                        "started_at": time.time(),
                    }
                )

        if mode == "agent":
            from triz_agent.agent import TrizAgent

            runner = TrizAgent(callback=capture_callback)
            run_method = lambda q: runner.run(q)
        else:
            from triz_agent.orchestrator import Orchestrator

            runner = Orchestrator(callback=None)
            runner.callback = capture_callback
            run_method = runner.run_workflow

        try:
            report = run_method(question)
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
            "steps_log": steps_log,
            "agent_thoughts": agent_thoughts,
            "mode": mode,
        }

    return _execute()


def run_batch(
    test_cases: list[dict],
    name: str,
    mode: str = "orchestrator",
    verbose: bool = False,
    delay: float = 8.0,
    log_file: str = None,
) -> dict:
    """批量运行测试用例。

    test_cases: [{"question": str, "expected_behavior": str, ...}]
    mode: 'orchestrator' 或 'agent'
    delay: 用例之间的间隔秒数
    log_file: 实时日志文件路径
    """
    _log(f"\n{'='*60}", log_file)
    _log(f"开始运行: {name} | 模式: {mode}", log_file)
    _log(f"用例数: {len(test_cases)}", log_file)
    _log(f"{'='*60}", log_file)

    # 预加载 sentence-transformers 模型，避免第一个用例额外耗时
    _log("预加载语义模型...", log_file)
    preload_model()
    _log("预加载完成。\n", log_file)

    results = []
    for i, case in enumerate(test_cases, 1):
        question = case["question"]
        _log(f"[{i}/{len(test_cases)}] {question[:60]}...", log_file)
        result = run_single(question, verbose=verbose, mode=mode)
        result.update(case)  # 合并元数据
        results.append(result)
        status = "PASS" if result["success"] else "FAIL"
        if result.get("timeout"):
            status = "TIMEOUT"
        _log(f"      -> {status} ({result['elapsed_seconds']}s)", log_file)
        if i < len(test_cases):
            time.sleep(delay)

    summary = {
        "test_name": name,
        "mode": mode,
        "timestamp": datetime.now().isoformat(),
        "total": len(test_cases),
        "passed": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"] and not r.get("timeout")),
        "timeouts": sum(1 for r in results if r.get("timeout")),
        "avg_time": round(sum(r["elapsed_seconds"] for r in results) / len(results), 2),
        "results": results,
    }

    # 保存报告
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report_path = (
        report_dir / f"{name}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    _log(f"\n{'='*60}", log_file)
    _log(f"完成: {name} | 模式: {mode}", log_file)
    _log(f"通过: {summary['passed']}/{summary['total']}", log_file)
    _log(f"失败: {summary['failed']}/{summary['total']}", log_file)
    _log(f"超时: {summary['timeouts']}/{summary['total']}", log_file)
    _log(f"平均耗时: {summary['avg_time']}s", log_file)
    _log(f"报告保存: {report_path}", log_file)
    _log(f"{'='*60}\n", log_file)

    return summary
