"""TrizAgent 端到端 mock 测试：验证完整流程可正确走完。"""
import json
from unittest.mock import Mock, patch

from triz.agent import TrizAgent
from triz.context import WorkflowContext, SAO, ConvergenceDecision
from triz.skills.registry import SkillRegistry
from triz.utils.api_client import OpenAIClient


# 模拟 Agent 的 LLM 决策序列
def make_agent_decision_sequence(has_negative=True, converge_action="TERMINATE"):
    """生成 Agent 决策的 mock 响应序列。"""
    decisions = [
        {"next_state": "modeling", "skill": "m1_modeling", "reason": "开始功能建模"},
    ]

    if has_negative:
        decisions.append({"next_state": "causal", "skill": "m2_causal", "reason": "存在负面功能，需要根因分析"})

    decisions.extend([
        {"next_state": "formulation", "skill": "m3_formulation", "reason": "问题定型"},
        {"next_state": "solving", "skill": "m4_solver", "reason": "矛盾求解"},
        {"next_state": "search", "skill": "FOS", "reason": "跨界检索"},
        {"next_state": "generation", "skill": "m5_generation", "reason": "方案生成"},
        {"next_state": "evaluation", "skill": "m6_evaluation", "reason": "方案评估"},
        {"next_state": "convergence", "skill": "", "reason": "收敛判断"},
    ])

    if converge_action == "CONTINUE":
        # 第一轮 CONTINUE，需要再跑一轮 solving → generation → evaluation → convergence
        decisions.extend([
            {"next_state": "solving", "skill": "m4_solver", "reason": "继续迭代，重新求解"},
            {"next_state": "search", "skill": "FOS", "reason": "重新检索"},
            {"next_state": "generation", "skill": "m5_generation", "reason": "重新生成方案"},
            {"next_state": "evaluation", "skill": "m6_evaluation", "reason": "重新评估"},
            {"next_state": "convergence", "skill": "", "reason": "收敛判断"},
        ])

    # 最后一轮 TERMINATE
    decisions.append({"next_state": "convergence", "skill": "", "reason": "最终收敛判断"})

    idx = 0
    def mock_chat(self, *, prompt, system_prompt, temperature, json_mode):
        nonlocal idx
        if idx < len(decisions):
            resp = decisions[idx]
            idx += 1
            return json.dumps(resp)
        return json.dumps({"next_state": "report_generation", "skill": "", "reason": "完成"})

    return mock_chat


def test_agent_full_flow():
    """测试 Agent 完整流程（单次迭代）。"""
    events = []

    def callback(event_type, data):
        events.append((event_type, data))

    with patch('triz.agent.agent.classify_input', lambda text: {"category": "engineering", "proceed": True, "response": None}):
        with patch.object(OpenAIClient, 'chat', make_agent_decision_sequence(has_negative=True, converge_action="TERMINATE")):
            # Mock Skill 执行
            def mock_execute(self, input_data, ctx):
                skill_name = type(self).name
                if skill_name == "m1_modeling":
                    return {
                        "sao_list": [
                            {"subject": "刀片", "action": "切割", "object": "组织", "function_type": "useful"},
                            {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"},
                        ],
                        "resources": {"物质": ["刀片"]},
                        "ifr": "自锋利刀片",
                    }
                elif skill_name == "m2_causal":
                    return {
                        "root_param": "摩擦磨损",
                        "key_problem": "刀片磨损",
                        "candidate_attributes": ["摩擦系数", "硬度"],
                        "causal_chain": ["切割→摩擦→磨损→失效"],
                    }
                elif skill_name == "m3_formulation":
                    return {
                        "problem_type": "tech",
                        "improve_aspect": "耐磨性",
                        "worsen_aspect": "成本",
                    }
                elif skill_name == "m4_solver":
                    return {
                        "principles": [1, 15, 28],
                        "improve_param_id": 1,
                        "worsen_param_id": 2,
                        "match_conf": 0.8,
                    }
                elif skill_name == "m5_generation":
                    return {
                        "solution_drafts": [
                            {
                                "title": "涂层刀片",
                                "description": "在刀片表面涂覆硬质合金层",
                                "applied_principles": [1],
                                "resource_mapping": "现有刀片基材",
                            }
                        ]
                    }
                elif skill_name == "m6_evaluation":
                    return {
                        "ranked_solutions": [],
                        "max_ideality": 0.7,
                        "unresolved_signals": [],
                    }
                return {}

            # Mock check_convergence
            def mock_convergence(ctx):
                return ConvergenceDecision(action="TERMINATE", reason="完成", feedback="")

            with patch('triz.agent.agent.check_convergence', mock_convergence):
                # Patch all skill execute methods
                with patch.multiple(
                    'triz.skills.m1_modeling.handler.M1ModelingSkill',
                    execute=mock_execute,
                ):
                    with patch.multiple(
                        'triz.skills.m2_causal.handler.M2CausalSkill',
                        execute=mock_execute,
                    ):
                        with patch.multiple(
                            'triz.skills.m3_formulation.handler.M3FormulationSkill',
                            execute=mock_execute,
                        ):
                            with patch.multiple(
                                'triz.skills.m4_solver.handler.M4SolverSkill',
                                execute=mock_execute,
                            ):
                                with patch.multiple(
                                    'triz.skills.m5_generation.handler.M5GenerationSkill',
                                    execute=mock_execute,
                                ):
                                    with patch.multiple(
                                        'triz.skills.m6_evaluation.handler.M6EvaluationSkill',
                                        execute=mock_execute,
                                    ):
                                        with patch('triz.tools.fos_search.search_cases', return_value=[]):
                                            with patch('triz.utils.markdown_renderer.render_final_report', return_value="# 测试报告"):
                                                agent = TrizAgent(callback=callback)
                                                result = agent.run("如何减少手术刀片磨损")

    # 验证最终状态
    assert agent.state == "report_generation", f"期望 report_generation, 得到 {agent.state}"

    # 验证回调事件
    step_events = [e for e in events if e[0] in ("step_start", "step_complete", "step_error")]
    print(f"总事件数: {len(events)}")
    print(f"步骤事件: {len(step_events)}")

    # 验证执行了哪些 Skill
    skill_names = [e[1]["step_name"] for e in events if e[0] == "step_start"]
    print(f"执行的 Skills: {skill_names}")

    expected_skills = ["m1_modeling", "m2_causal", "m3_formulation", "m4_solver", "FOS", "m5_generation", "m6_evaluation"]
    assert skill_names == expected_skills, f"期望 {expected_skills}, 得到 {skill_names}"

    print("test_agent_full_flow PASSED")


if __name__ == "__main__":
    test_agent_full_flow()
