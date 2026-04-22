"""边界/异常输入测试：验证系统对异常输入的降级行为。"""
import sys
from test_runner import run_batch

TEST_CASES = [
    {"question": "", "expected": "clarify", "description": "空字符串"},
    {"question": "asdfghjkl", "expected": "clarify", "description": "无意义文字"},
    {"question": "床前明月光疑是地上霜举头望明月低头思故乡", "expected": "clarify_or_low_score", "description": "中文古诗"},
    {"question": "123456", "expected": "clarify", "description": "纯数字"},
    {"question": "😀😁😂", "expected": "clarify", "description": "只有 emoji"},
    {"question": "How to reduce engine noise in a car", "expected": "success", "description": "英文问题"},
    {"question": "如何提高car的fuel efficiency", "expected": "success", "description": "混合中英文"},
    {"question": "问题'; DROP TABLE users; --", "expected": "safe", "description": "SQL 注入尝试"},
    {"question": "为什么我的手机电池不耐用？", "expected": "success", "description": "反问句"},
    {
        "question": "这是一个超长的问题描述。" * 200,
        "expected": "success",
        "description": "超长文本（>2000字）",
    },
]


def main():
    summary = run_batch(TEST_CASES, "boundary", verbose="-v" in sys.argv)
    return summary["failed"]


if __name__ == "__main__":
    sys.exit(main())
