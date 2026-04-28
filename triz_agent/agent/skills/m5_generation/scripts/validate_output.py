"""M5 输出校验脚本。供 post_validate 调用。"""

import re


def validate(output: str, ctx=None) -> list:
    """校验 M5 输出，返回警告列表。"""
    warnings = []
    output_lower = output.lower()

    # 检查是否包含"方案"
    if "方案" not in output and "solution" not in output_lower:
        warnings.append("输出中未发现方案内容")
        return warnings  # 无方案则无需继续检查

    # 检查是否引用发明原理
    principle_pattern = r"原理\s*(\d+)"
    principles = re.findall(principle_pattern, output)
    if not principles:
        # 尝试英文匹配
        principles = re.findall(r"principle\s*(\d+)", output_lower)
    if not principles:
        warnings.append("方案未引用具体发明原理编号（如'原理 15'），不能泛泛而谈")

    # 检查方案描述长度（至少 100 字）
    # 提取所有方案描述
    desc_pattern = r"\*\*方案描述\*\*\s*：\s*(.+?)(?=\*\*资源映射\*\*|\*\*应用原理\*\*|####|$)"
    descs = re.findall(desc_pattern, output, re.DOTALL)
    for i, desc in enumerate(descs, 1):
        clean_desc = desc.strip()
        if len(clean_desc) < 100:
            warnings.append(f"方案 {i} 描述仅 {len(clean_desc)} 字，应至少 100 字，包含具体技术实现细节")

    # 检查是否使用已有资源
    if ctx and hasattr(ctx, "sao_list") and ctx.sao_list:
        resource_mentioned = False
        if "资源" in output or "resource" in output_lower:
            resource_mentioned = True
        if not resource_mentioned:
            warnings.append("方案未提及使用用户已有资源（来自 M1 资源盘点）")

    return warnings


if __name__ == "__main__":
    test = "**应用原理**：原理 15\n**方案描述**：这是一个具体方案描述，长度超过100字。" + "具体实现细节 " * 10
    print(validate_m5_output(test))
