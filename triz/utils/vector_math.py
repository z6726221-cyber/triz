"""向量计算工具：余弦相似度、简单文本embedding"""
import math
from typing import List


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} vs {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def embed_text(text: str, dim: int = 128) -> List[float]:
    """使用简单的字符级hash编码将文本转为向量。
    生产环境应替换为 sentence-transformers 或 OpenAI Embedding API。
    """
    vec = [0.0] * dim
    for i, char in enumerate(text):
        idx = ord(char) % dim
        vec[idx] += hash(char) % 100 / 100.0
        vec[(idx + 1) % dim] += (i + 1) * 0.01

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec
