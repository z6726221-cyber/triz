import pytest
import os
from triz_pipeline.tools.query_parameters import query_parameters
from triz_pipeline.tools.query_matrix import query_matrix
from triz_pipeline.tools.query_separation import query_separation
from triz_pipeline.database.init_db import init_database


@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    """初始化测试数据库（模块级）。"""
    db_path = tmp_path_factory.mktemp("data") / "test_triz.db"
    import triz_pipeline.config
    import triz_pipeline.database.init_db
    import triz_pipeline.database.queries
    triz.config.DB_PATH = db_path
    triz.database.init_db.DB_PATH = db_path
    triz.database.queries.DB_PATH = db_path
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


def test_query_parameters_by_keyword():
    """关键词直接匹配参数"""
    results = query_parameters(["速度"])
    assert len(results) >= 1
    assert any(r["id"] == 9 for r in results)


def test_query_parameters_empty():
    """空关键词返回空列表"""
    results = query_parameters([])
    assert results == []


def test_query_matrix_valid_params():
    """查询有效的矛盾矩阵组合"""
    results = query_matrix(9, 12)  # Speed vs Shape
    assert isinstance(results, list)


def test_query_separation_phys_contradiction():
    """物理矛盾查询分离原理"""
    result = query_separation("接触面积既要大又要小")
    assert "sep_type" in result
    assert "principles" in result
    assert isinstance(result["principles"], list)
