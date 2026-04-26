"""边界/异常输入测试：验证系统对异常输入的降级行为。"""
import sys
from test_runner import run_batch

TEST_CASES = [
    {"question": "", "expected": "rejected", "description": "空字符串"},
    {"question": "   \t\n", "expected": "rejected", "description": "纯空格/制表符"},
    {"question": "asdfghjkl", "expected": "rejected_or_clarify", "description": "无意义文字"},
    {"question": "床前明月光疑是地上霜举头望明月低头思故乡", "expected": "rejected", "description": "中文古诗"},
    {"question": "123456", "expected": "rejected", "description": "纯数字"},
    {"question": "😀😁😂", "expected": "rejected", "description": "只有 emoji"},
    {"question": "！？。，；：", "expected": "rejected", "description": "只有标点符号"},
    {"question": "How to reduce engine noise in a car", "expected": "success", "description": "英文问题"},
    {"question": "如何提高car的fuel efficiency", "expected": "success", "description": "混合中英文"},
    {"question": "问题'; DROP TABLE users; --", "expected": "rejected_or_clarify", "description": "SQL 注入尝试"},
    {"question": "<script>alert('xss')</script>", "expected": "rejected_or_clarify", "description": "HTML/脚本注入"},
    {"question": "为什么我的手机电池不耐用？", "expected": "success", "description": "反问句"},
    {
        "question": "这是一个超长的问题描述。" * 200,
        "expected": "rejected_or_clarify",
        "description": "超长文本（>2000字）",
    },
]


def _is_rejected(report: str) -> bool:
    """判断是否被 input_classifier 拦截。"""
    return any(marker in report for marker in [
        "不涉及工程技术矛盾",
        "请输入一个具体的技术问题描述",
    ])


def _is_clarify(report: str) -> bool:
    return "需要补充信息" in report or "流程中断" in report


def main():
    summary = run_batch(TEST_CASES, "boundary", verbose="-v" in sys.argv)

    print("\n边界输入分析报告:")
    failures = 0
    for r in summary["results"]:
        q = r["question"][:30]
        report = r.get("report_preview", "")
        expected = r.get("expected", "")

        if expected == "rejected":
            ok = _is_rejected(report)
        elif expected == "rejected_or_clarify":
            ok = _is_rejected(report) or _is_clarify(report)
        elif expected == "success":
            ok = "TRIZ 解决方案报告" in report
        else:
            ok = True

        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {r['description']} ({r['elapsed_seconds']}s)")
        if not ok:
            failures += 1
            print(f"    报告前80字: {report[:80]}")

    return failures


if __name__ == "__main__":
    sys.exit(main())
