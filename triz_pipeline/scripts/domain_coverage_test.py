"""领域覆盖测试：不同工程领域的问题，验证方案逻辑相关性。"""

import sys
from test_runner import run_batch

TEST_CASES = [
    {"question": "如何提高手术刀片在多次使用后的锋利度", "domain": "机械/医疗"},
    {"question": "化工反应器内壁腐蚀导致产品污染", "domain": "化工/材料"},
    {"question": "软件系统在高并发下响应延迟严重", "domain": "软件/信息"},
    {"question": "数据中心服务器散热功耗过高", "domain": "电子/电气"},
    {"question": "药物靶向递送效率低，副作用大", "domain": "生物医学"},
    {"question": "太阳能电池板在阴雨天效率过低", "domain": "能源"},
    {"question": "飞机机翼需要轻薄但又要承受高压", "domain": "交通/航天"},
]


def main():
    summary = run_batch(TEST_CASES, "domain_coverage", verbose="-v" in sys.argv)
    return summary["failed"]


if __name__ == "__main__":
    sys.exit(main())
