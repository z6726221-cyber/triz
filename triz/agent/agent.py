"""TrizAgent：约束式自主 Agent，状态机 + LLM 决策编排 TRIZ 工作流。"""
import json
import time

from triz.agent.state_machine import (
    STATE_MACHINE,
    STATE_NAMES,
    get_available_skills,
    get_state_name,
    is_valid_transition,
)
from triz.context import WorkflowContext, ConvergenceDecision, SAO, Case, SolutionDraft
from triz.skills.registry import SkillRegistry
from triz.tools.input_classifier import classify_input
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m7_convergence import check_convergence
from triz.utils.markdown_renderer import render_final_report
from triz.utils.api_client import OpenAIClient


_AGENT_SYSTEM_PROMPT = """你是 TRIZ 分析 Agent，负责编排 TRIZ 创新问题解决流程。

你的工作流必须严格遵守以下状态跳转规则：
1. 必须从 "modeling"（问题建模）开始
2. "modeling" 之后可以进入 "causal"（根因分析）或 "formulation"（问题定型）
3. "causal" 之后必须进入 "formulation"
4. "formulation" 之后必须进入 "solving"（矛盾求解）
5. "solving" 之后必须进入 "search"（跨界检索）
6. "search" 之后必须进入 "generation"（方案生成）
7. "generation" 之后必须进入 "evaluation"（方案评估）
8. "evaluation" 之后必须进入 "convergence"（收敛判断）
9. "convergence" 之后可以返回 "solving"（需改进）或进入 "report_generation"（完成）

关键约束：
- 如果存在 harmful/excessive/insufficient 功能， modeling 之后应该先进入 causal
- 如果没有负面功能，可以从 modeling 直接进入 formulation
- 任何时候发现当前步骤输出为空或不合法，应该重试当前步骤（next_state 设为当前状态）
- 不要跳过任何必须的步骤

可用 Skills：
- m1_modeling: 功能建模（提取 SAO 三元组、资源、IFR）
- m2_causal: 根因分析（因果链、候选属性）
- m3_formulation: 问题定型（提取矛盾对）
- m4_solver: 矛盾求解（查询矩阵/分离原理）
- FOS: 跨界检索（搜索案例）
- m5_generation: 方案生成（基于原理生成方案草稿）
- m6_evaluation: 方案评估（8维度评分、理想度）

你必须输出 JSON 格式的决策：
{"next_state": "状态名", "skill": "Skill名或空字符串", "reason": "决策原因"}
"""


class TrizAgent:
    """约束式自主 Agent。

    通过状态机约束 + LLM 决策来编排 TRIZ 工作流。
    保持与 Orchestrator 相同的 callback 事件通知。
    """

    def __init__(self, skill_registry: SkillRegistry | None = None, callback=None):
        self.skill_registry = skill_registry or SkillRegistry()
        self.callback = callback
        self.client = OpenAIClient()
        self.state = "idle"
        self.ctx: WorkflowContext | None = None
        self._state_results: dict[str, dict] = {}  # 记录每个状态的执行结果

    def _notify(self, event_type: str, data: dict):
        if self.callback:
            self.callback(event_type, data)

    def run(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow。"""
        self.ctx = WorkflowContext(question=question, history=history or [])
        self.state = "idle"
        self._state_results = {}

        # 输入分类
        classification = classify_input(question)
        if not classification["proceed"]:
            msg = classification["response"]
            self._notify("report", {"content": msg})
            return msg

        # 进入 modeling
        self._transition_to("modeling")

        # Agent 主循环
        while self.state != "report_generation":
            # 特殊状态：convergence 不是 Skill，用现有逻辑
            if self.state == "convergence":
                self._handle_convergence()
                continue

            # 1. Agent 决策下一步
            decision = self._agent_decide()

            # 2. 验证决策合法性
            if not is_valid_transition(self.state, decision["next_state"]):
                # 非法跳转，强制保持在当前状态重试
                self._notify("step_error", {
                    "step_name": "agent_decision",
                    "error": f"非法状态跳转: {self.state} -> {decision['next_state']}",
                })
                continue

            # 3. 如果是重试当前状态（输出不合法）
            if decision["next_state"] == self.state:
                self._notify("step_start", {
                    "step_name": decision["skill"],
                    "step_type": "Skill",
                })
                result = self._execute_skill(decision["skill"])
                self._merge_result(result)
                self._notify("step_complete", {
                    "step_name": decision["skill"],
                    "step_type": "Skill",
                    "result": result,
                })
                continue

            # 4. 正常状态跳转
            self._transition_to(decision["next_state"])

            # 5. 执行该状态的 Skill
            if decision["skill"]:
                self._notify("step_start", {
                    "step_name": decision["skill"],
                    "step_type": "Skill" if decision["skill"] != "FOS" else "Tool",
                })
                result = self._execute_skill(decision["skill"])
                self._merge_result(result)
                self._notify("step_complete", {
                    "step_name": decision["skill"],
                    "step_type": "Skill" if decision["skill"] != "FOS" else "Tool",
                    "result": result,
                })

        # 生成最终报告
        return self._generate_report()

    def _agent_decide(self) -> dict:
        """调用 LLM 决策下一步。"""
        prompt = self._build_decision_prompt()

        response = self.client.chat(
            prompt=prompt,
            system_prompt=_AGENT_SYSTEM_PROMPT,
            temperature=0.1,
            json_mode=True,
        )

        try:
            data = json.loads(response)
            return {
                "next_state": data.get("next_state", self.state),
                "skill": data.get("skill", ""),
                "reason": data.get("reason", ""),
            }
        except json.JSONDecodeError:
            # 解析失败，保持当前状态
            return {"next_state": self.state, "skill": "", "reason": "解析失败，重试"}

    def _build_decision_prompt(self) -> str:
        """构建 Agent 决策 prompt。"""
        ctx = self.ctx

        lines = [
            f"当前状态: {self.state} ({get_state_name(self.state)})",
            f"用户问题: {ctx.question}",
            "",
            "=== 已完成的状态和结果 ===",
        ]

        # 按状态机顺序列出已完成的状态
        for state in ["modeling", "causal", "formulation", "solving", "search", "generation", "evaluation"]:
            if state in self._state_results:
                result = self._state_results[state]
                lines.append(f"- {state}: {self._summarize_result(state, result)}")

        lines.append("")
        lines.append("=== 当前上下文关键信息 ===")
        lines.append(f"- SAO 数量: {len(ctx.sao_list)}")
        lines.append(f"- 负面功能: {any(s.function_type in ('harmful', 'excessive', 'insufficient') for s in ctx.sao_list)}")
        lines.append(f"- 根因: {ctx.root_param or '未提取'}")
        lines.append(f"- 矛盾类型: {ctx.problem_type or '未定型'}")
        lines.append(f"- 发明原理: {ctx.principles}")
        lines.append(f"- 方案草稿数: {len(ctx.solution_drafts)}")
        lines.append(f"- 迭代次数: {ctx.iteration}")
        lines.append(f"- 反馈: {ctx.feedback or '无'}")

        lines.append("")
        lines.append(f"=== 从 '{self.state}' 可跳转的下一状态 ===")
        next_states = STATE_MACHINE.get(self.state, [])
        for ns in next_states:
            skills = get_available_skills(ns)
            lines.append(f"- {ns}: 可用 Skills {skills}")

        lines.append("")
        lines.append("请决定下一步应该进入哪个状态、执行哪个 Skill。")
        lines.append("如果当前步骤输出不合法（如空结果），请设置 next_state 为当前状态以重试。")
        lines.append("输出 JSON: {\"next_state\": \"...\", \"skill\": \"...\", \"reason\": \"...\"}")

        return "\n".join(lines)

    def _summarize_result(self, state: str, result: dict) -> str:
        """简要总结某个状态的执行结果。"""
        if state == "modeling":
            sao_count = len(result.get("sao_list", []))
            return f"提取了 {sao_count} 个 SAO"
        elif state == "causal":
            return f"根因: {result.get('root_param', 'N/A')}"
        elif state == "formulation":
            return f"矛盾类型: {result.get('problem_type', 'N/A')}"
        elif state == "solving":
            principles = result.get("principles", [])
            return f"原理: {principles}"
        elif state == "search":
            cases = result.get("cases", [])
            return f"案例: {len(cases)} 个"
        elif state == "generation":
            drafts = result.get("solution_drafts", [])
            return f"方案: {len(drafts)} 个"
        elif state == "evaluation":
            max_ideality = result.get("max_ideality", 0)
            return f"最高理想度: {max_ideality}"
        return "已完成"

    def _transition_to(self, next_state: str):
        """执行状态跳转，通知 UI。"""
        self._notify("node_start", {
            "node_name": get_state_name(next_state),
            "from_state": self.state,
            "to_state": next_state,
        })
        self.state = next_state

    def _execute_skill(self, skill_name: str) -> dict:
        """执行指定 Skill 或 Tool。"""
        if skill_name == "FOS":
            from triz.tools.fos_search import search_cases
            cases = search_cases(self.ctx)
            result = {"cases": cases}
            self._state_results["search"] = result
            return result

        skill = self.skill_registry.get(skill_name)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_name}")

        input_data = self._build_skill_input(skill)
        output = skill.execute(input_data, self.ctx)
        result = output.model_dump() if hasattr(output, "model_dump") else output

        # 记录结果
        state_map = {
            "m1_modeling": "modeling",
            "m2_causal": "causal",
            "m3_formulation": "formulation",
            "m4_solver": "solving",
            "m5_generation": "generation",
            "m6_evaluation": "evaluation",
        }
        state_key = state_map.get(skill_name)
        if state_key:
            self._state_results[state_key] = result

        return result

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
        ctx = self.ctx
        for key, value in result.items():
            if not hasattr(ctx, key):
                continue

            if key == "sao_list" and isinstance(value, list):
                from triz.context import SAO
                value = [
                    SAO.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "cases" and isinstance(value, list):
                from triz.context import Case
                value = [
                    Case.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "solution_drafts" and isinstance(value, list):
                from triz.context import SolutionDraft
                value = [
                    SolutionDraft.model_validate(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif key == "ranked_solutions" and isinstance(value, list):
                from triz.context import Solution, QualitativeTags
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

    def _handle_convergence(self):
        """处理收敛判断状态。"""
        decision = check_convergence(self.ctx)
        self._notify("decision", {
            "action": decision.action,
            "reason": decision.reason,
            "feedback": decision.feedback,
        })

        if decision.action == "TERMINATE":
            self._transition_to("report_generation")
        elif decision.action == "CLARIFY":
            msg = self._generate_clarification(decision.reason)
            self._notify("report", {"content": msg})
            # 设置一个标记状态，让 run() 方法返回
            self._clarify_result = msg
            self.state = "report_generation"
        elif decision.action == "CONTINUE":
            self.ctx.iteration += 1
            self.ctx.feedback = decision.feedback
            self.ctx.history_log.append({"max_ideality": self.ctx.max_ideality})
            self.ctx.principles = []
            self.ctx.cases = []
            self.ctx.solution_drafts = []
            self.ctx.ranked_solutions = []
            self.ctx.max_ideality = 0.0
            self.ctx.unresolved_signals = []
            # 清除相关状态结果，让 Agent 重新决策
            for s in ["solving", "search", "generation", "evaluation", "convergence"]:
                self._state_results.pop(s, None)
            self._transition_to("solving")

    def _generate_report(self) -> str:
        """生成最终报告。"""
        if hasattr(self, "_clarify_result"):
            return self._clarify_result

        contradiction = self.ctx.contradiction_desc or "未识别矛盾"
        decision_reason = self._state_results.get("convergence", {}).get("reason", "完成")
        report = render_final_report(
            self.ctx.question, contradiction, self.ctx.ranked_solutions, decision_reason
        )
        self._notify("report", {"content": report})
        return report

    def _generate_clarification(self, reason: str) -> str:
        return f"**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"
