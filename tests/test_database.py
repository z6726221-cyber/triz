import pytest
from triz.database.triz_data import get_parameters, get_matrix_cell, get_separation_rules


def test_get_parameters_count():
    params = get_parameters()
    assert len(params) == 39


def test_get_parameters_first():
    params = get_parameters()
    assert params[0]["id"] == 1
    assert "Weight of moving object" in params[0]["name"]


def test_get_matrix_cell():
    principles = get_matrix_cell(9, 12)
    assert isinstance(principles, list)
    assert len(principles) > 0


def test_get_separation_rules():
    rules = get_separation_rules()
    types = {r["type"] for r in rules}
    assert "空间" in types or "时间" in types
