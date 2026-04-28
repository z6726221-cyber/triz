"""M3 输出校验脚本。供 post_validate 调用。"""

import re


def validate(output: str, ctx=None) -> list:
    """校验 M3 输出，返回警告列表。"""
    warnings = []
    output_lower = output.lower()

    # 检查矛盾类型
    has_tech = "技术矛盾" in output
    has_phys = "物理矛盾" in output
    if not has_tech and not has_phys:
        if "tech" in output_lower or "phys" in output_lower:
            warnings.append("矛盾类型应使用中文（技术矛盾/物理矛盾），而非英文")
        else:
            warnings.append("输出中未明确矛盾类型（技术矛盾/物理矛盾）")

    # 检查矛盾对
    imp = re.search(r"-\s*\*\*改善方面\*\*\s*[：:]\s*(.+)", output)
    wrn = re.search(r"-\s*\*\*恶化方面\*\*\s*[：:]\s*(.+)", output)

    if not imp:
        warnings.append("输出中未找到「改善方面」")
    elif imp:
        val = imp.group(1).strip()
        if len(val) > 20:
            warnings.append(f"改善方面描述过长（{len(val)} 字符），应是 2-6 个中文词")

    if not wrn:
        warnings.append("输出中未找到「恶化方面」")
    elif wrn:
        val = wrn.group(1).strip()
        if len(val) > 20:
            warnings.append(f"恶化方面描述过长（{len(val)} 字符），应是 2-6 个中文词")

    # 检查矛盾描述
    if "矛盾描述" in output:
        desc_section = output.split("矛盾描述")[1].split("###")[0].strip()
        if len(desc_section) < 10:
            warnings.append("矛盾描述过于简短，应是一句完整描述矛盾关系的话")
    else:
        warnings.append("输出中未发现「矛盾描述」章节")

    return warnings


if __name__ == "__main__":
    test = "### 矛盾类型\n技术矛盾\n### 矛盾对\n- **改善方面**：结构强度\n- **恶化方面**：建造成本"
    print(validate_m3_output(test))
