"""M6 输出校验脚本。供 post_validate 调用。"""

import re


def validate(output: str, ctx=None) -> list:
    """校验 M6 输出，返回警告列表。"""
    warnings = []
    output_lower = output.lower()

    # 检查评分
    if "评分" not in output and "score" not in output_lower:
        warnings.append("输出中未发现评分内容")
        return warnings

    # 检查理想度
    if "理想度" not in output and "ideality" not in output_lower:
        warnings.append("输出中未发现理想度相关内容")

    # 检查评分区分度
    score_pattern = r"(\d)\s*/\s*5"
    scores = re.findall(score_pattern, output)
    if scores:
        unique_scores = set(scores)
        if len(unique_scores) == 1:
            warnings.append(
                f"评分缺乏区分度，所有方案都被打了 {list(unique_scores)[0]}/5；"
                "好方案应 4-5 分，差方案应 1-2 分"
            )

    # 检查问题匹配度
    if "问题匹配度" in output or "problem_relevance" in output_lower:
        # 提取数值
        rel_scores = re.findall(r"问题匹配度\s*\|\s*(\d)\s*/\s*5", output)
        for s in rel_scores:
            if int(s) > 2 and ctx and hasattr(ctx, "question"):
                # 检查是否非工程问题
                question = ctx.question.lower()
                non_eng = ["天气", "几点", "今天", "明天", "笑话"]
                if any(w in question for w in non_eng):
                    warnings.append(
                        f"非工程问题的问题匹配度应为 <= 2，但当前为 {s}/5"
                    )

    # 检查综合排序
    if "综合排序" in output:
        ranking = re.findall(r"\|\s*(\d+)\s*\|.*\|\s*([\d.]+)\s*\|", output)
        if ranking:
            scores = [(int(r[0]), float(r[1])) for r in ranking]
            scores.sort(key=lambda x: x[1], reverse=True)
            expected_rank = list(range(1, len(scores) + 1))
            actual_rank = [s[0] for s in scores]
            if actual_rank != expected_rank:
                warnings.append("综合排序未按理想度从高到低排列")
    else:
        warnings.append("输出中未发现「综合排序」章节")

    return warnings


if __name__ == "__main__":
    test = "### 综合排序\n| 排名 | 方案 | 理想度 |\n| 1 | A | 0.9 |\n| 2 | B | 0.8 |"
    print(validate_m6_output(test))
