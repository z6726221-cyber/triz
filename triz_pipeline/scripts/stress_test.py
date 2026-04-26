"""批量回归测试（Stress Test）：同一问题多次运行，暴露偶发性错误。"""

import sys
from test_runner import run_batch

PROBLEMS = [
    {
        "question": "汽车发动机噪音大，油耗高",
        "category": "机械",
        "reason": "M4 需匹配多组参数，Function Calling 压力大",
    },
    {
        "question": "手机电池续航短，用户需要轻薄手机",
        "category": "电子",
        "reason": "此前触发过 M5 递归错误",
    },
    {
        "question": "建筑物抗震能力不足，建造成本高",
        "category": "土木",
        "reason": "M2 因果链较长",
    },
]

REPEAT = 5


def main():
    test_cases = []
    for p in PROBLEMS:
        for i in range(REPEAT):
            test_cases.append(
                {
                    "question": p["question"],
                    "category": p["category"],
                    "reason": p["reason"],
                    "run_id": i + 1,
                }
            )

    summary = run_batch(test_cases, "stress_test", verbose="-v" in sys.argv)

    # 按问题分组统计
    print("\n按问题统计:")
    for p in PROBLEMS:
        q = p["question"]
        q_results = [r for r in summary["results"] if r["question"] == q]
        q_pass = sum(1 for r in q_results if r["success"])
        q_fail = sum(1 for r in q_results if not r["success"])
        avg_t = sum(r["elapsed_seconds"] for r in q_results) / len(q_results)
        print(f"  {q[:30]}...: {q_pass}/{len(q_results)} 通过, 平均 {avg_t:.1f}s")
        if q_fail > 0:
            for r in q_results:
                if not r["success"]:
                    print(
                        f"    FAIL [{r['run_id']}]: {r['failure_stage']} - {r['errors']}"
                    )

    return summary["failed"]


if __name__ == "__main__":
    sys.exit(main())
