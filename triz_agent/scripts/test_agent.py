"""TrizAgent 端到端 mock 测试：验证 ReAct 风格完整流程。"""

import json
from unittest.mock import Mock, patch

from triz_agent.agent import TrizAgent
from triz_agent.context import WorkflowContext
from triz_agent.utils.api_client import OpenAIClient


def test_react_agent_full_flow():
    """测试 ReAct Agent 完整流程。"""
    events = []

    def callback(event_type, data):
        events.append((event_type, data))

    # Mock Agent 决策序列（ReAct 风格：thought + action）
    mock_decisions = [
        {
            "thought": "用户问的是手术刀片磨损，这是一个工程问题。我需要先进行功能建模，提取 SAO 三元组。",
            "action": {"type": "skill", "name": "m1_modeling"},
        },
        {
            "thought": "M1 完成了，提取到 2 个 SAO，其中有 harmful 功能（摩擦磨损）。根据 TRIZ 方法论，有负面功能时应该做根因分析。",
            "action": {"type": "skill", "name": "m2_causal"},
        },
        {
            "thought": "根因找到了，是摩擦磨损。现在需要把问题定型为技术矛盾或物理矛盾。",
            "action": {"type": "skill", "name": "m3_formulation"},
        },
        {
            "thought": "问题已定型为技术矛盾（耐磨性 vs 成本）。现在需要查询矛盾矩阵获取发明原理。",
            "action": {"type": "skill", "name": "m4_solver"},
        },
        {
            "thought": "获得了发明原理 [1, 15, 28]。接下来搜索跨界案例作为参考。",
            "action": {"type": "skill", "name": "FOS"},
        },
        {
            "thought": "检索到案例。现在基于原理和案例生成具体方案草稿。",
            "action": {"type": "skill", "name": "m5_generation"},
        },
        {
            "thought": "方案已生成。现在需要评估方案质量，给出量化评分。",
            "action": {"type": "skill", "name": "m6_evaluation"},
        },
        {
            "thought": "评估完成，最高理想度 0.7，无高风险方案。分析可以结束了，生成最终报告。",
            "action": {"type": "report"},
        },
    ]

    idx = 0

    def mock_chat(self, *, prompt, system_prompt, temperature, json_mode):
        nonlocal idx
        if idx < len(mock_decisions):
            resp = mock_decisions[idx]
            idx += 1
            return json.dumps(resp)
        return json.dumps({"thought": "完成", "action": {"type": "report"}})

    with patch(
        "triz.agent.agent.classify_input",
        lambda text: {"category": "engineering", "proceed": True, "response": None},
    ):
        with patch.object(OpenAIClient, "chat", mock_chat):
            with patch("triz.tools.fos_search.search_cases", return_value=[]):
                with patch(
                    "triz.utils.markdown_renderer.render_final_report",
                    return_value="# 测试报告",
                ):
                    # Mock all skill executes
                    def mock_execute(self, input_data, ctx):
                        skill_name = type(self).name
                        if skill_name == "m1_modeling":
                            return {
                                "sao_list": [
                                    {
                                        "subject": "刀片",
                                        "action": "切割",
                                        "object": "组织",
                                        "function_type": "useful",
                                    },
                                    {
                                        "subject": "摩擦",
                                        "action": "磨损",
                                        "object": "刀片",
                                        "function_type": "harmful",
                                    },
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

                    with patch.multiple(
                        "triz.skills.m1_modeling.handler.M1ModelingSkill",
                        execute=mock_execute,
                    ):
                        with patch.multiple(
                            "triz.skills.m2_causal.handler.M2CausalSkill",
                            execute=mock_execute,
                        ):
                            with patch.multiple(
                                "triz.skills.m3_formulation.handler.M3FormulationSkill",
                                execute=mock_execute,
                            ):
                                with patch.multiple(
                                    "triz.skills.m4_solver.handler.M4SolverSkill",
                                    execute=mock_execute,
                                ):
                                    with patch.multiple(
                                        "triz.skills.m5_generation.handler.M5GenerationSkill",
                                        execute=mock_execute,
                                    ):
                                        with patch.multiple(
                                            "triz.skills.m6_evaluation.handler.M6EvaluationSkill",
                                            execute=mock_execute,
                                        ):
                                            agent = TrizAgent(callback=callback)
                                            result = agent.run("如何减少手术刀片磨损")

    # 验证
    step_events = [e for e in events if e[0] == "step_start"]
    skill_names = [e[1]["step_name"] for e in step_events]

    print(f"总事件数: {len(events)}")
    print(f"执行的 Skills: {skill_names}")

    # 验证是否包含 thought
    for e in step_events:
        assert "agent_thought" in e[1], f"step_start 缺少 agent_thought: {e[1]}"
        print(f"  {e[1]['step_name']}: {e[1]['agent_thought'][:40]}...")

    expected = [
        "m1_modeling",
        "m2_causal",
        "m3_formulation",
        "m4_solver",
        "FOS",
        "m5_generation",
        "m6_evaluation",
    ]
    assert skill_names == expected, f"期望 {expected}, 得到 {skill_names}"

    print("test_react_agent_full_flow PASSED")


if __name__ == "__main__":
    test_react_agent_full_flow()
