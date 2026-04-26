"""正常工程问题测试：验证标准TRIZ流程对不同复杂度/领域问题的方案生成质量。"""

import sys
from test_runner import run_batch

TEST_CASES = [
    # 简单明确 — 单一技术矛盾
    {
        "question": "汽车发动机噪音大，油耗高",
        "expected": "success",
        "description": "机械-简单：发动机噪音与油耗",
        "complexity": "low",
    },
    # 物理矛盾 — 对立需求
    {
        "question": "手机电池续航短，用户需要轻薄手机",
        "expected": "success",
        "description": "电子-物理矛盾：续航 vs 轻薄",
        "complexity": "medium",
    },
    # 材料/化学 — 腐蚀/污染
    {
        "question": "化工反应器内壁腐蚀导致产品污染，更换材料又成本太高",
        "expected": "success",
        "description": "化工-材料矛盾：腐蚀 vs 成本",
        "complexity": "medium",
    },
    # 软件/IT — 性能矛盾
    {
        "question": "软件系统在高并发下响应延迟严重，增加服务器又导致成本上升",
        "expected": "success",
        "description": "软件-性能矛盾：延迟 vs 成本",
        "complexity": "medium",
    },
    # 生物医学 — 精准与安全
    {
        "question": "药物靶向递送效率低，副作用大，提高浓度又增加毒性",
        "expected": "success",
        "description": "生物医学-安全矛盾：效率 vs 毒性",
        "complexity": "high",
    },
    # 能源 — 环境适应性
    {
        "question": "太阳能电池板在阴雨天效率过低，增加储能又提高系统重量",
        "expected": "success",
        "description": "能源-环境矛盾：效率 vs 重量",
        "complexity": "medium",
    },
    # 航空航天 — 结构强度与重量
    {
        "question": "飞机机翼需要轻薄但又要承受高压气流，增加厚度又降低燃油效率",
        "expected": "success",
        "description": "航天-结构矛盾：强度 vs 重量",
        "complexity": "high",
    },
    # 建筑/土木 — 安全与成本
    {
        "question": "建筑物抗震能力不足，提高抗震等级又导致建造成本大幅增加",
        "expected": "success",
        "description": "土木-安全矛盾：抗震 vs 成本",
        "complexity": "medium",
    },
    # 电子/散热 — 功耗与散热
    {
        "question": "数据中心服务器散热功耗过高，降低风扇转速又导致芯片过热",
        "expected": "success",
        "description": "电子-热管理矛盾：散热 vs 功耗",
        "complexity": "medium",
    },
    # 机械/医疗 — 精度与耐用
    {
        "question": "手术刀片在多次使用后锋利度下降，频繁更换又增加手术风险和成本",
        "expected": "success",
        "description": "机械医疗-精度矛盾：锋利度 vs 耐用性",
        "complexity": "high",
    },
]


def main():
    summary = run_batch(TEST_CASES, "normal", verbose="-v" in sys.argv)

    print("\n正常工程问题分析报告:")
    failures = 0
    for r in summary["results"]:
        desc = r.get("description", "")
        report = r.get("report_preview", "")
        elapsed = r.get("elapsed_seconds", 0)

        has_report = "TRIZ 解决方案报告" in report
        status = "PASS" if has_report else "FAIL"

        print(f"  [{status}] {desc} ({elapsed:.1f}s)")
        if not has_report:
            failures += 1
            print(f"    报告前80字: {report[:80]}")

    total = len(TEST_CASES)
    passed = total - failures
    print(f"\n结果: {passed}/{total} 生成有效报告")
    return failures


if __name__ == "__main__":
    sys.exit(main())
