"""解析 M3 输出，提取矛盾参数。供 post_process 调用。"""

import re
import json


def parse_m3_output(output: str) -> dict:
    """解析 M3 的 Markdown 输出，提取矛盾参数。

    返回 dict:
        - problem_type: "tech" 或 "phys"
        - improve_aspect: 改善方面（技术矛盾）或对立状态1（物理矛盾）
        - worsen_aspect: 恶化方面（技术矛盾）或对立状态2（物理矛盾）
        - contradiction_desc: 矛盾描述
    """
    result = {
        "problem_type": "tech",
        "improve_aspect": "",
        "worsen_aspect": "",
        "contradiction_desc": "",
    }

    # 判断矛盾类型
    if "物理矛盾" in output:
        result["problem_type"] = "phys"

    # 提取改善方面
    imp = re.search(r"-\s*\*\*改善方面\*\*\s*[：:]\s*(.+)", output)
    if imp:
        result["improve_aspect"] = imp.group(1).strip()

    # 提取恶化方面
    wrn = re.search(r"-\s*\*\*恶化方面\*\*\s*[：:]\s*(.+)", output)
    if wrn:
        result["worsen_aspect"] = wrn.group(1).strip()

    # 提取矛盾描述（支持多种格式）
    desc_match = re.search(r"###\s*矛盾描述\s*\n\s*（(.+?)）", output)
    if not desc_match:
        desc_match = re.search(r"###\s*矛盾描述\s*\n\s*(.+)", output)
    if desc_match:
        result["contradiction_desc"] = desc_match.group(1).strip()

    return result


if __name__ == "__main__":
    # 简单测试
    test_output = """
### 矛盾类型
技术矛盾

### 矛盾对
- **改善方面**：结构强度
- **恶化方面**：建造成本

### 矛盾描述
提高建筑物抗震能力需要增强结构强度，但会导致建造成本大幅上升

### 依据
测试依据
"""
    result = parse_m3_output(test_output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
