"""向量计算工具：余弦相似度、语义文本嵌入（sentence-transformers）"""

import math
from typing import List

# 延迟加载 sentence-transformers，避免启动时耗时
_model = None


def _get_model():
    """懒加载 sentence-transformers 模型。"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        # paraphrase-multilingual-MiniLM-L12-v2：支持中文，~100MB，效果足够
        _model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2", local_files_only=True
        )
    return _model


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度。"""
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} vs {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def embed_text(text: str) -> List[float]:
    """使用 sentence-transformers 将文本转为语义向量。"""
    if not text:
        return []
    model = _get_model()
    return model.encode(text).tolist()


def preload_model() -> None:
    """预加载 sentence-transformers 模型，避免首次调用时延迟。"""
    _get_model()
