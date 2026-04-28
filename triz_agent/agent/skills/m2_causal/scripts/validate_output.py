"""M2 输出校验脚本。供 post_validate 调用。"""

import re


def validate(output: str, ctx=None) -> list:
    """校验 M2 输出，返回警告列表。"""
    warnings = []
    output_lower = output.lower()

    # 检查因果链
    causal_pattern = r"第\s*\d+\s*层"
    causal_matches = re.findall(causal_pattern, output)
    if len(causal_matches) < 3:
        warnings.append(f"因果链层数不足（当前 {len(causal_matches)} 层），应至少 3 层")

    # 检查根因参数
    if "根因参数" in output:
        root_section = output.split("根因参数")[1].split("###")[0].strip()
        if not root_section or root_section.count("\n") < 2:
            warnings.append("根因参数描述过于简短，应包含具体的物理/工程属性词")
    else:
        warnings.append("输出中未发现「根因参数」章节")

    # 检查候选物理属性
    if "候选物理属性" in output:
        attr_section = output.split("候选物理属性")[1].split("###")[0]
        attrs = [l.strip("- ").strip() for l in attr_section.splitlines() if l.strip().startswith("-")]
        if len(attrs) < 2:
            warnings.append(f"候选物理属性不足（当前 {len(attrs)} 个），应提取 2-4 个")
    else:
        warnings.append("输出中未发现「候选物理属性」章节")

    # 检查是否误输出矛盾对
    if "矛盾对" in output or "改善方面" in output:
        warnings.append("M2 不应输出矛盾对（如'X 与 Y 的矛盾'），矛盾定型是 M3 的工作")

    return warnings


if __name__ == "__main__":
    test = "### 因果链\n1. 第1层：...\n2. 第2层：...\n3. 第3层：..."
    print(validate_m2_output(test))
