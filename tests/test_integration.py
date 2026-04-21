"""集成测试：验证完整 workflow 的数据流"""
import pytest
import os
from triz.context import WorkflowContext, SAO
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m4_solver import solve_contradiction
from triz.tools.m7_convergence import check_convergence
from triz.database.init_db import init_database


@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_triz.db"
    import triz.config
    import triz.database.init_db
    import triz.database.queries
    triz.config.DB_PATH = db_path
    triz.database.init_db.DB_PATH = db_path
    triz.database.queries.DB_PATH = db_path
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
        assert "热量" in result["contradiction_desc"] or "效率" in result["contradiction_desc"]

    def test_m3_to_m4_solver(self):
        ctx = WorkflowContext(question="test")
        ctx.problem_type = "tech"
        ctx.contradiction_desc = "改善速度，恶化形状稳定性"
        ctx.candidate_attributes = ["速度", "形状"]

        result = solve_contradiction(ctx)
        assert len(result["principles"]) > 0
        assert result["improve_param_id"] == 9
        assert result["worsen_param_id"] == 12

    def test_m6_to_m7_convergence(self):
        ctx = WorkflowContext(question="test")
        ctx.max_ideality = 0.8
        ctx.iteration = 1
        ctx.unresolved_signals = []
        ctx.history_log = [{"max_ideality": 0.6}]

        decision = check_convergence(ctx)
        assert decision.action == "TERMINATE"
