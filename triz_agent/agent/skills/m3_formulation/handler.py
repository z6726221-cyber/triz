"""M3 问题定型 Agent Skill：将根因分析转化为标准化矛盾表述，输出 Markdown。"""

import re

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M3FormulationSkill(AgentSkill):
    """M3 问题定型 Agent Skill。

    基于根因分析结果，提取标准化的 TRIZ 矛盾对（技术矛盾或物理矛盾）。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "m3_formulation"
    description = """当 M2 根因分析已完成，需要：
- 提取技术矛盾（改善参数 vs 恶化参数）或物理矛盾（相反需求）
- 查询矛盾矩阵获得推荐发明原理
- 输出标准化矛盾表述供 M4 使用
适用场景：根因已找到，需要转化为 TRIZ 标准矛盾表述时。"""
    temperature = 0.1

    def post_validate(self, output: str, ctx: WorkflowContext) -> list[str]:
        warnings = []
        output_lower = output.lower()
        if "技术矛盾" not in output and "物理矛盾" not in output:
            if "tech" not in output_lower and "phys" not in output_lower:
                warnings.append("输出中未明确矛盾类型（技术矛盾/物理矛盾）")
        if "改善" not in output and "improve" not in output_lower:
            warnings.append("输出中未发现改善方面")
        if "恶化" not in output and "worsen" not in output_lower:
            warnings.append("输出中未发现恶化方面")
        return warnings

    def post_process(self, output: str) -> dict | None:
        """自动解析 M3 的 Markdown 输出，提取矛盾参数。

        技术矛盾 → 提取 improve_aspect / worsen_aspect，供 solve_contradiction 使用
        物理矛盾 → 提取 contradiction_desc，供 query_separation 使用
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

        # 提取改善方面 / 恶化方面 / 矛盾描述
        imp = re.search(r"-\s*\*\*改善方面\*\*\s*[：:]\s*(.+)", output)
        wrn = re.search(r"-\s*\*\*恶化方面\*\*\s*[：:]\s*(.+)", output)
        # ### 矛盾描述后可能跟空行和括号，提取实际描述文本
        desc_match = re.search(r"### 矛盾描述\s*\n\s*（(.+?)）", output)
        if not desc_match:
            desc_match = re.search(r"### 矛盾描述\s*\n\s*(.+)", output)
        desc = desc_match

        if imp:
            result["improve_aspect"] = imp.group(1).strip()
        if wrn:
            result["worsen_aspect"] = wrn.group(1).strip()
        if desc:
            result["contradiction_desc"] = desc.group(1).strip()

        return result
