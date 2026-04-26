"""端到端测试： Orchestrator 与 Agent 双模式。
用法: python e2e_test.py <mode>
  mode: orchestrator 或 agent
"""

import sys
from test_runner import run_batch

from normal_test import TEST_CASES as NORMAL_CASES
from adversarial_test import TEST_CASES as ADVERSARIAL_CASES
from boundary_test import TEST_CASES as BOUNDARY_CASES

ALL_CASES = NORMAL_CASES + ADVERSARIAL_CASES + BOUNDARY_CASES


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "orchestrator"
    if mode not in ("orchestrator", "agent"):
        print(f"错误: mode 必须是 orchestrator 或 agent， got {mode}")
        sys.exit(1)

    delay = 15.0 if mode == "agent" else 8.0
    log_file = f"e2e_{mode}.log"
    print(f"端到端测试开始 | 模式: {mode} | 用例数: {len(ALL_CASES)} | 间隔: {delay}s")
    print(f"实时日志: {log_file}")

    summary = run_batch(
        ALL_CASES, "e2e_full", mode=mode, delay=delay, log_file=log_file
    )

    failed = summary["failed"] + summary["timeouts"]
    print(
        f"\n最终结果: {summary['passed']}/{summary['total']} 通过, {failed} 失败/超时"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
