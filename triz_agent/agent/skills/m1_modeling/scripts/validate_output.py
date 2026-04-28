"""M1 输出校验脚本。供 post_validate 调用。"""

import re


def validate(output: str, ctx=None) -> list:
    """校验 M1 输出，返回警告列表。"""
    warnings = []
    output_lower = output.lower()

    # 检查 SAO 三元组
    if not re.search(r"\|.*\|.*\|.*\|", output):
        warnings.append("输出中未发现 SAO 三元组表格（主体|动作|客体|类型）")

    # 检查 IFR
    if "ifr" not in output_lower and "理想最终结果" not in output:
        warnings.append("输出中未发现 IFR（理想最终结果）相关内容")

    # 检查资源盘点
    resource_sections = ["物质", "场", "空间", "时间", "信息", "功能"]
    found_resources = [s for s in resource_sections if s in output]
    if len(found_resources) < 3:
        warnings.append(
            f"输出中资源盘点不全，仅找到：{', '.join(found_resources)}；"
            f"应包含六类：{', '.join(resource_sections)}"
        )

    return warnings


if __name__ == "__main__":
    test = "### SAO\n| 主体 | 动作 | 客体 | 类型 |\n| 电池 | 提供 | 电能 | useful |"
    print(validate_m1_output(test))
