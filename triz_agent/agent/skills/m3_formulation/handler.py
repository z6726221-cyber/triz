"""M3 问题定型 Agent Skill：将根因分析转化为标准化矛盾表述，输出 Markdown。"""

import re

from triz_agent.agent.skills.base import AgentSkill
from triz_agent.context import WorkflowContext


class M3FormulationSkill(AgentSkill):
    """M3 问题定型 Agent Skill。

    基于根因分析结果，提取标准化的 TRIZ 矛盾对（技术矛盾或物理矛盾）。

    输出 Markdown，由 Agent 自主理解并管理数据流转。
    """

    name = "formulation"
    description = """当 M2 根因分析已完成，需要：
- 提取技术矛盾（改善参数 vs 恶化参数）或物理矛盾（相反需求）
- 查询矛盾矩阵获得推荐发明原理
- 输出标准化矛盾表述供 M4 使用
适用场景：根因已找到，需要转化为 TRIZ 标准矛盾表述时。"""
    temperature = 0.1

    # post_validate 由 base.py 自动调用 scripts/validate_output.py
    # 如需额外校验，在此补充或覆盖 post_validate 方法

    def post_process(self, output: str) -> dict | None:
        """自动解析 M3 的 Markdown 输出，提取矛盾参数。

        技术矛盾 → 提取 improve_aspect / worsen_aspect，供矛盾矩阵查询
        物理矛盾 → 提取 parameter / state1 / state2 / sep_type，供分离原理查询
        """
        # 调用 scripts/parse_contradiction.py 进行脚本化解析
        try:
            import sys
            from pathlib import Path
            script_dir = Path(__file__).parent / "scripts"
            sys.path.insert(0, str(script_dir))
            from parse_contradiction import parse_m3_output
            result = parse_m3_output(output)
            return result
        except Exception:
            pass

        # Fallback：正则解析
        result = {
            "problem_type": "tech",
            "improve_aspect": "",
            "worsen_aspect": "",
            "contradiction_desc": "",
            "parameter": "",
            "state1": "",
            "state2": "",
            "sep_type": "",
        }

        # 判断矛盾类型
        if "物理矛盾" in output:
            result["problem_type"] = "phys"

        # 技术矛盾：提取改善方面 / 恶化方面
        imp = re.search(r"-\s*\*\*改善方面\*\*\s*[：:]\s*(.+)", output)
        wrn = re.search(r"-\s*\*\*恶化方面\*\*\s*[：:]\s*(.+)", output)

        # 物理矛盾：提取矛盾参数 / 状态1 / 状态2 / 分离类型
        param = re.search(r"-\s*\*\*矛盾参数\*\*\s*[：:]\s*(.+)", output)
        s1 = re.search(r"-\s*\*\*状态1\*\*\s*[：:]\s*(.+)", output)
        s2 = re.search(r"-\s*\*\*状态2\*\*\s*[：:]\s*(.+)", output)
        sep = re.search(r"-\s*\*\*分离类型\*\*\s*[：:]\s*(.+)", output)

        # 矛盾描述
        desc_match = re.search(r"###\s*矛盾描述\s*\n\s*（(.+?)）", output)
        if not desc_match:
            desc_match = re.search(r"###\s*矛盾描述\s*\n\s*(.+)", output)

        if imp:
            result["improve_aspect"] = imp.group(1).strip()
        if wrn:
            result["worsen_aspect"] = wrn.group(1).strip()
        if param:
            result["parameter"] = param.group(1).strip()
        if s1:
            result["state1"] = s1.group(1).strip()
        if s2:
            result["state2"] = s2.group(1).strip()
        if sep:
            sep_val = sep.group(1).strip()
            # 标准化分离类型
            if sep_val in ("空间", "Space"):
                result["sep_type"] = "空间"
            elif sep_val in ("时间", "Time"):
                result["sep_type"] = "时间"
            elif sep_val in ("条件", "Condition"):
                result["sep_type"] = "条件"
            elif sep_val in ("系统", "System"):
                result["sep_type"] = "系统"
            else:
                result["sep_type"] = sep_val
        if desc_match:
            result["contradiction_desc"] = desc_match.group(1).strip()

        return result
