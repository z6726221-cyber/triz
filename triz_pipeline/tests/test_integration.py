"""集成测试：验证完整 workflow 的数据流"""

import pytest
import os
from triz_pipeline.context import (
    WorkflowContext,
    SAO,
    Solution,
    SolutionDraft,
    QualitativeTags,
)
from triz_pipeline.tools.m2_gate import should_trigger_m2
from tests.helpers import formulate_problem
from triz_pipeline.tools.query_parameters import query_parameters
from triz_pipeline.tools.query_matrix import query_matrix
from triz_pipeline.tools.m7_convergence import check_convergence
from triz_pipeline.database.init_db import init_database


def _make_solution(relevance=5, consistency=5, ideality=0.8):
    return Solution(
        draft=SolutionDraft(
            title="测试方案",
            description="测试描述",
            applied_principles=[1],
            resource_mapping="测试资源",
        ),
        tags=QualitativeTags(
            feasibility_score=4,
            resource_fit_score=4,
            innovation_score=4,
            uniqueness_score=3,
            risk_level="low",
            ifr_deviation_reason="",
            problem_relevance_score=relevance,
            logical_consistency_score=consistency,
        ),
        ideality_score=ideality,
        evaluation_rationale="测试评估",
    )


@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_triz.db"
    import triz_pipeline.config
    import triz_pipeline.database.init_db
    import triz_pipeline.database.queries

    triz_pipeline.config.DB_PATH = db_path
    triz_pipeline.database.init_db.DB_PATH = db_path
    triz_pipeline.database.queries.DB_PATH = db_path
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


class TestDataFlow:
    """测试从 M1 到 M7 的完整数据流（不使用 LLM）。"""

    def test_m1_to_m2_gate(self):
        ctx = WorkflowContext(question="如何提高续航")
        ctx.sao_list = [
            SAO(subject="电池", action="供电", object="手机", function_type="useful"),
            SAO(subject="热量", action="损耗", object="电能", function_type="harmful"),
        ]
        assert should_trigger_m2(ctx) is True

    def test_m2_to_m3_formulation(self):
        ctx = WorkflowContext(question="test")
        ctx.root_param = "能量转换效率低"
        ctx.key_problem = "热量损耗过多"
        ctx.candidate_attributes = ["转换效率", "热量"]
        ctx.causal_chain = ["续航短", "能量损耗", "转换效率低"]
        ctx.sao_list = []

        result = formulate_problem(ctx)
        assert result["problem_type"] == "tech"
        assert (
            "热量" in result["contradiction_desc"]
            or "效率" in result["contradiction_desc"]
        )

    def test_m3_to_m4_subtools(self):
        """M3 → M4 数据流：通过 sub-tools 查询矛盾矩阵"""
        # Step 1: 查询参数
        params = query_parameters(["速度", "形状"])
        assert len(params) >= 2
        improve = next(p for p in params if p["id"] == 9)
        worsen = next(p for p in params if p["id"] == 12)
        assert improve["name"] == "Speed"
        assert worsen["name"] == "Shape"

        # Step 2: 查询矩阵
        principles = query_matrix(improve["id"], worsen["id"])
        assert len(principles) > 0

    def test_m6_to_m7_convergence(self):
        ctx = WorkflowContext(question="test")
        ctx.max_ideality = 0.8
        ctx.iteration = 1
        ctx.unresolved_signals = []
        ctx.history_log = [{"max_ideality": 0.6}]
        ctx.ranked_solutions = [
            _make_solution(relevance=5, consistency=5, ideality=0.8)
        ]

        decision = check_convergence(ctx)
        assert decision.action == "TERMINATE"
