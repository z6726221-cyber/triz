"""TrizAgent：ReAct 风格的自主 Agent，通过方法论文档约束行为。

与硬编码 Orchestrator 的区别：
- Agent 自主决定下一步调用哪个 Skill
- 方法论约束通过 AGENT.md 提供（类似 CLAUDE.md）
- 状态机仅作为可选兜底，不强制约束流程
"""
import json
from pathlib import Path

from triz.context import WorkflowContext, SAO, Case, SolutionDraft, Solution, QualitativeTags
from triz.skills.registry import SkillRegistry
from triz.tools.input_classifier import classify_input
from triz.tools.m7_convergence import check_convergence
from triz.utils.markdown_renderer import render_final_report
from triz.utils.api_client import OpenAIClient


class TrizAgent:
    """ReAct 风格 TRIZ Agent。

    Agent 维护一个记忆列表（已完成步骤 + 结果），每次调用 LLM 时：
    - system prompt = AGENT.md（方法论约束）
    - user prompt = 当前记忆 + 上下文 + 可用 Skills

    LLM 输出 thought + action，Agent 执行 action，结果加入记忆，循环继续。
    """

    def __init__(self, skill_registry: SkillRegistry | None = None, callback=None):
        self.skill_registry = skill_registry or SkillRegistry()
        self.callback = callback
        self.client = OpenAIClient()
        self.memory: list[dict] = []  # ReAct 记忆
        self.ctx: WorkflowContext | None = None

    def _load_methodology(self) -> str:
        """加载 AGENT.md 方法论文档。"""
        agent_md = Path(__file__).parent / "AGENT.md"
        if agent_md.exists():
            return agent_md.read_text(encoding="utf-8")
        return "你是 TRIZ 分析专家。"

    def _notify(self, event_type: str, data: dict):
        if self.callback:
            self.callback(event_type, data)

    def run(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow。"""
        self.ctx = WorkflowContext(question=question, history=history or [])
        self.memory = []

        # 输入分类
        classification = classify_input(question)
        if not classification["proceed"]:
            msg = classification["response"]
            self._notify("report", {"content": msg})
            return msg

        # ReAct 主循环
        max_steps = 20
        consecutive_errors = {}  # skill_name -> count
        for step in range(max_steps):
            # 1. Agent 思考并决策
            decision = self._think_and_act()

            # 2. 执行 action
            action = decision["action"]

            if action["type"] == "clarify":
                msg = self._generate_clarification(action.get("message", "需要补充信息"))
                self._notify("report", {"content": msg})
                return msg

            elif action["type"] == "report":
                return self._generate_report()

            elif action["type"] == "skill":
                skill_name = action.get("name", "")
                if not skill_name:
                    self.memory.append({
                        "role": "system",
                        "content": "错误：skill 名称不能为空，请重新决策。",
                    })
                    continue

                # 执行 Skill
                self._notify("step_start", {
                    "step_name": skill_name,
                    "step_type": "Skill" if skill_name != "FOS" else "Tool",
                    "agent_thought": decision.get("thought", ""),
                })

                try:
                    result = self._execute_skill(skill_name)
                    self._merge_result(result)

                    # 记录到记忆
                    self.memory.append({
                        "role": "assistant",
                        "skill": skill_name,
                        "thought": decision.get("thought", ""),
                    })
                    self.memory.append({
                        "role": "system",
                        "skill_result": skill_name,
                        "result_summary": self._summarize_result(skill_name, result),
                    })

                    self._notify("step_complete", {
                        "step_name": skill_name,
                        "step_type": "Skill" if skill_name != "FOS" else "Tool",
                        "result": result,
                    })

                except Exception as e:
                    consecutive_errors[skill_name] = consecutive_errors.get(skill_name, 0) + 1
                    err_msg = f"执行 {skill_name} 出错 ({consecutive_errors[skill_name]}/3): {str(e)}"
                    self.memory.append({
                        "role": "system",
                        "content": err_msg,
                    })
                    self._notify("step_error", {
                        "step_name": skill_name,
                        "error": str(e),
                    })
                    # 连续失败 3 次，跳过该 Skill
                    if consecutive_errors[skill_name] >= 3:
                        self.memory.append({
                            "role": "system",
                            "content": f"{skill_name} 连续失败 3 次，跳过此步骤。",
                        })
                        consecutive_errors[skill_name] = 0

            else:
                self.memory.append({
                    "role": "system",
                    "content": f"未知的 action 类型: {action.get('type')}",
                })

        # 达到最大步数，强制生成报告
        return self._generate_report()

    def _think_and_act(self) -> dict:
        """调用 LLM 思考当前状态并决策下一步行动。"""
        system_prompt = self._load_methodology()
        user_prompt = self._build_react_prompt()

        response = self.client.chat(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,  # 稍低温度，保持方法论遵循
            json_mode=True,
        )

        try:
            data = json.loads(response)
            return {
                "thought": data.get("thought", ""),
                "action": data.get("action", {"type": "skill", "name": ""}),
            }
        except json.JSONDecodeError:
            return {
                "thought": "解析失败",
                "action": {"type": "skill", "name": "m1_modeling"},
            }

    def _build_react_prompt(self) -> str:
        """构建 ReAct 风格的 prompt。"""
        ctx = self.ctx

        lines = [
            f"用户问题: {ctx.question}",
            f"当前迭代次数: {ctx.iteration}",
            f"当前反馈（如有）: {ctx.feedback or '无'}",
            "",
            "=== 当前上下文 ===",
            f"- SAO 数量: {len(ctx.sao_list)}",
            f"- 负面功能: {any(s.function_type in ('harmful', 'excessive', 'insufficient') for s in ctx.sao_list)}",
            f"- 根因: {ctx.root_param or '未提取'}",
            f"- 矛盾类型: {ctx.problem_type or '未定型'}",
            f"- 发明原理: {ctx.principles}",
            f"- 案例数: {len(ctx.cases)}",
            f"- 方案草稿数: {len(ctx.solution_drafts)}",
            f"- 评估方案数: {len(ctx.ranked_solutions)}",
            f"- 最高理想度: {ctx.max_ideality}",
            "",
            "=== 已完成的分析步骤 ===",
        ]

        for mem in self.memory:
            if mem.get("role") == "assistant":
                lines.append(f"- 执行了 {mem['skill']}: {mem.get('thought', '')}")
            elif mem.get("role") == "system" and "skill_result" in mem:
                lines.append(f"  结果: {mem['result_summary']}")

        lines.append("")
        lines.append("=== 可用 Skills ===")
        for skill_meta in self.skill_registry.list_skills():
            lines.append(f"- {skill_meta['name']}: {skill_meta['description']}")
        lines.append("- FOS: 跨界检索（搜索参考案例）")

        lines.append("")
        lines.append("请思考当前状态，决定下一步行动。")
        lines.append("输出 JSON: {\"thought\": \"...\", \"action\": {\"type\": \"...\", \"name\": \"...\"}}")

        return "\n".join(lines)

    def _execute_skill(self, skill_name: str) -> dict:
        """执行指定 Skill 或 Tool。"""
        if skill_name == "FOS":
            from triz.tools.fos_search import search_cases
            cases = search_cases(self.ctx)
            return {"cases": cases}

        skill = self.skill_registry.get(skill_name)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_name}")

        input_data = self._build_skill_input(skill)
        output = skill.execute(input_data, self.ctx)
        return output.model_dump() if hasattr(output, "model_dump") else output

    def _build_skill_input(self, skill, ctx: WorkflowContext | None = None):
        """从 WorkflowContext 提取 Skill 输入模型所需的字段。"""
        from pydantic import BaseModel

        ctx = ctx or self.ctx
        input_data = {}
        for field_name in skill.input_schema.model_fields:
            if hasattr(ctx, field_name):
                input_data[field_name] = getattr(ctx, field_name)
        return skill.input_schema(**input_data)

    def _merge_result(self, result: dict):
        """将模块输出合并到 WorkflowContext。"""
        from triz.context import SAO, Case, SolutionDraft, Solution, QualitativeTags

        ctx = self.ctx
        for key, value in result.items():
            if not hasattr(ctx, key):
                continue

            if key == "sao_list" and isinstance(value, list):
                value = [
                    SAO.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "cases" and isinstance(value, list):
                value = [
                    Case.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "solution_drafts" and isinstance(value, list):
                value = [
                    SolutionDraft.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "ranked_solutions" and isinstance(value, list):
                converted = []
                for item in value:
                    if isinstance(item, dict):
                        if "draft" in item and isinstance(item["draft"], dict):
                            converted.append(Solution.model_validate(item))
                        else:
                            draft = SolutionDraft(
                                title=item.get("title", ""),
                                description=item.get("description", ""),
                                applied_principles=item.get("applied_principles", []),
                                resource_mapping=item.get("resource_mapping", ""),
                            )
                            tags = QualitativeTags(
                                feasibility_score=item.get("feasibility_score", 3),
                                resource_fit_score=item.get("resource_fit_score", 3),
                                innovation_score=item.get("innovation_score", 3),
                                uniqueness_score=item.get("uniqueness_score", 3),
                                risk_level=item.get("risk_level", "medium"),
                                ifr_deviation_reason=item.get("ifr_deviation_reason", ""),
                                problem_relevance_score=item.get("problem_relevance_score", 3),
                                logical_consistency_score=item.get("logical_consistency_score", 3),
                            )
                            converted.append(Solution(
                                draft=draft, tags=tags,
                                ideality_score=item.get("ideality_score", 0.5),
                                evaluation_rationale=item.get("evaluation_rationale", ""),
                            ))
                    else:
                        converted.append(item)
                value = converted

            setattr(ctx, key, value)

    def _summarize_result(self, skill_name: str, result: dict) -> str:
        """简要总结执行结果。"""
        if skill_name == "m1_modeling":
            return f"提取了 {len(result.get('sao_list', []))} 个 SAO"
        elif skill_name == "m2_causal":
            return f"根因: {result.get('root_param', 'N/A')}"
        elif skill_name == "m3_formulation":
            return f"矛盾类型: {result.get('problem_type', 'N/A')}"
        elif skill_name == "m4_solver":
            return f"原理: {result.get('principles', [])}"
        elif skill_name == "FOS":
            return f"案例: {len(result.get('cases', []))} 个"
        elif skill_name == "m5_generation":
            return f"方案: {len(result.get('solution_drafts', []))} 个"
        elif skill_name == "m6_evaluation":
            return f"最高理想度: {result.get('max_ideality', 0)}"
        return "已完成"

    def _generate_report(self) -> str:
        """生成最终报告。"""
        contradiction = self.ctx.contradiction_desc or "未识别矛盾"
        report = render_final_report(
            self.ctx.question, contradiction, self.ctx.ranked_solutions, "Agent 完成分析"
        )
        self._notify("report", {"content": report})
        return report

    def _generate_clarification(self, reason: str) -> str:
        return f"**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"
