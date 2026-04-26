import pytest
from triz_pipeline.utils.vector_math import cosine_similarity, embed_text


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert cosine_similarity(v1, v2) == pytest.approx(0.0)


def test_cosine_similarity_opposite():
    v1 = [1.0, 0.0]
    v2 = [-1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(-1.0)


def test_embed_text_returns_list():
    vec = embed_text("速度")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(x, float) for x in vec)
