"""对抗性输入测试：非工程问题，验证系统被 input_classifier 拦截或给出低分方案。"""
import sys
from test_runner import run_batch

TEST_CASES = [
    {"question": "今天天气怎么样", "expected": "rejected", "description": "天气询问"},
    {"question": "如何追女朋友", "expected": "rejected", "description": "社交问题"},
    {"question": "1+1 等于几", "expected": "rejected_or_clarify", "description": "数学问题"},
    {"question": "如何成为亿万富翁", "expected": "rejected", "description": "非工程目标"},
    {"question": "如何做饭更好吃", "expected": "rejected", "description": "烹饪问题"},
    {"question": "如何减肥", "expected": "rejected", "description": "健康问题"},
    {"question": "怎么写快速排序算法", "expected": "rejected_or_clarify", "description": "编程问题（技术但非工程）"},
    {"question": "如何申请发明专利", "expected": "rejected", "description": "法律咨询（专业但非工程）"},
    {"question": "王者荣耀怎么上王者段位", "expected": "rejected", "description": "游戏/娱乐"},
    {"question": "推荐一款性价比高的手机", "expected": "rejected", "description": "购物推荐"},
    {"question": "考研数学怎么复习", "expected": "rejected", "description": "教育/考试"},
    {"question": "最近有什么国际新闻", "expected": "rejected", "description": "新闻/时事"},
]


def _is_rejected(report: str) -> bool:
    """判断是否被 input_classifier 拦截。"""
    return any(marker in report for marker in [
        "不涉及工程技术矛盾",
        "请输入一个具体的技术问题描述",
        "需要补充信息",
        "流程中断",
    ])


def main():
    summary = run_batch(TEST_CASES, "adversarial", verbose="-v" in sys.argv)

    print("\n对抗性输入分析报告:")
    rejected_count = 0
    for r in summary["results"]:
        q = r["question"]
        report = r.get("report_preview", "")
        if _is_rejected(report):
            print(f"  已拦截: {q}")
            rejected_count += 1
        else:
            print(f"  未拦截: {q} (报告长度 {r['report_length']})")
            print(f"    预览: {report[:120]}...")

    total = len(TEST_CASES)
    print(f"\n结果: {rejected_count}/{total} 被拦截")
    return 0 if rejected_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
