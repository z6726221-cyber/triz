import pytest
from triz_pipeline.utils.markdown_renderer import render_node_start, render_final_report
from triz_pipeline.context import Solution, SolutionDraft, QualitativeTags


def test_render_node_start():
    output = render_node_start("问题建模", 1, 5)
    assert "节点 1/5" in output
    assert "问题建模" in output


def test_render_final_report():
    solution = Solution(
        draft=SolutionDraft(
            title="测试方案",
            description="描述",
            applied_principles=[1],
            resource_mapping="无",
        ),
        tags=QualitativeTags(
            feasibility_score=4,
            resource_fit_score=4,
            innovation_score=3,
            uniqueness_score=3,
            risk_level="low",
            ifr_deviation_reason="",
        ),
        ideality_score=0.75,
        evaluation_rationale="测试",
    )
    report = render_final_report(
        "如何提高续航", "改善速度恶化稳定性", [solution], "收敛"
    )
    assert "如何提高续航" in report
    assert "0.75" in report
