import pytest
import os
from triz_agent.database.init_db import init_database, ensure_data_dir
from triz_agent.config import DB_PATH

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """创建临时数据库用于测试。"""
    db_path = tmp_path / "test_triz.db"
    monkeypatch.setattr("triz_agent.config.DB_PATH", db_path)
    monkeypatch.setattr("triz_agent.database.init_db.DB_PATH", db_path)
    monkeypatch.setattr("triz_agent.database.queries.DB_PATH", db_path)
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


# === query_parameters 测试 ===

def test_map_to_parameters_keyword(temp_db):
    from triz_agent.tools.core.query_parameters import map_to_parameters

    result = map_to_parameters("抗震", "成本")
    assert result["improve_param_id"] == 14  # 强度
    assert result["worsen_param_id"] == 32  # 成本
    assert result["improve_match_type"] == "keyword"
    assert result["worsen_match_type"] == "keyword"


def test_map_to_parameters_known_words(temp_db):
    from triz_agent.tools.core.query_parameters import map_to_parameters

    # 速度=9, 重量=1
    result = map_to_parameters("速度", "重量")
    assert result["improve_param_id"] == 9
    assert result["worsen_param_id"] == 1


def test_query_parameters_by_similarity(temp_db):
    from triz_agent.tools.core.query_parameters import query_parameters

    results = query_parameters(["速度"])
    assert len(results) > 0
    assert "id" in results[0]
    assert results[0]["match_type"] in ("keyword", "similarity")


def test_query_parameters_empty(temp_db):
    from triz_agent.tools.core.query_parameters import query_parameters

    results = query_parameters([])
    assert results == []


# === query_matrix 测试 ===

def test_query_matrix_direct(temp_db):
    from triz_agent.tools.core.query_matrix import query_matrix

    # 强度(14) vs 运动物体成本(19)
    result = query_matrix(14, 19)
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(p, int) for p in result)


def test_query_matrix_no_result_returns_fallback(temp_db):
    from triz_agent.tools.core.query_matrix import query_matrix

    # 用无效 ID，应返回兜底推荐
    result = query_matrix(999, 998)
    assert isinstance(result, list)
    assert len(result) > 0


def test_query_matrix_swap_fallback(temp_db):
    from triz_agent.tools.core.query_matrix import query_matrix

    # 矩阵可能不对称，测试交换参数
    r1 = query_matrix(13, 19)
    r2 = query_matrix(19, 13)
    assert isinstance(r1, list)
    assert isinstance(r2, list)


# === query_separation 测试 ===

def test_query_separation_space(temp_db):
    from triz_agent.tools.core.query_separation import query_separation

    result = query_separation("上方空间要放东西，下方要保持空")
    assert "sep_type" in result
    assert "principles" in result
    assert isinstance(result["principles"], list)


def test_query_separation_time(temp_db):
    from triz_agent.tools.core.query_separation import query_separation

    result = query_separation("启动时要求快速，运行时要求稳定")
    assert result["sep_type"] in ("时间", "条件", "空间", "系统")


def test_query_separation_default(temp_db):
    from triz_agent.tools.core.query_separation import query_separation

    # 无关键词匹配，应返回默认
    result = query_separation("既要又要")
    assert "principles" in result
    assert len(result["principles"]) > 0


# === solve_contradiction 测试 ===

def test_solve_contradiction_tech(temp_db):
    from triz_agent.tools.solve_contradiction import solve_contradiction

    result = solve_contradiction(
        problem_type="tech",
        improve_aspect="结构强度",
        worsen_aspect="建造成本",
    )
    assert "principles" in result
    assert isinstance(result["principles"], list)
    assert len(result["principles"]) > 0
    assert result["problem_type"] == "tech"
    assert result["improve_param_id"] is not None
    assert result["worsen_param_id"] is not None


def test_solve_contradiction_phys(temp_db):
    from triz_agent.tools.solve_contradiction import solve_contradiction

    result = solve_contradiction(
        problem_type="phys",
        contradiction_desc="既要电池容量大又要手机轻薄",
    )
    assert "principles" in result
    assert "sep_type" in result
    assert isinstance(result["principles"], list)
    assert result["problem_type"] == "phys"
    assert result["sep_type"] in ("空间", "时间", "条件", "系统")


def test_solve_contradiction_from_ctx(temp_db):
    from triz_agent.tools.solve_contradiction import solve_contradiction

    # 模拟 WorkflowContext 对象
    class FakeCtx:
        problem_type = "tech"
        improve_aspect = "抗震"
        worsen_aspect = "成本"
        contradiction_desc = ""
        candidate_attributes = []

    ctx = FakeCtx()
    result = solve_contradiction(ctx)
    assert "principles" in result
    assert len(result["principles"]) > 0
