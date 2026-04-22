"""对抗性输入测试：非工程问题，验证系统不会生成荒谬方案。"""
import sys
from test_runner import run_batch

TEST_CASES = [
    {"question": "今天天气怎么样", "expected": "clarify", "description": "天气询问"},
    {"question": "如何追女朋友", "expected": "clarify", "description": "社交问题"},
    {"question": "1+1 等于几", "expected": "clarify", "description": "数学问题"},
    {"question": "如何成为亿万富翁", "expected": "clarify", "description": "非工程目标"},
    {"question": "如何做饭更好吃", "expected": "clarify_or_low_score", "description": "烹饪问题"},
    {"question": "如何减肥", "expected": "clarify_or_low_score", "description": "健康问题"},
]


def main():
    summary = run_batch(TEST_CASES, "adversarial", verbose="-v" in sys.argv)

    # 额外分析：检查成功运行的报告中是否包含低相关性方案
    print("\n对抗性输入分析报告:")
    for r in summary["results"]:
        if r["success"]:
            print(f"  ⚠ {r['question']}: 系统生成了方案（应 clarify）")
            print(f"    预览: {r['report_preview'][:100]}...")

    return summary["failed"]


if __name__ == "__main__":
    sys.exit(main())
