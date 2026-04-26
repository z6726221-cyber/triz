"""FOS 跨界检索 Tool：接收 query 列表，执行搜索，返回结构化报告。

架构：
- search_patents(queries, principles) → 新接口，M5 驱动
- search_cases(ctx) → 兼容旧接口，内部调用 search_patents
"""

import hashlib
import json
import time
from pathlib import Path

from triz_agent.context import WorkflowContext, Case, SearchResult, FOSReport
from triz_agent.config import SERP_API_KEY, FOS_CACHE_DIR, FOS_CACHE_TTL_HOURS
from triz_agent.utils.vector_math import embed_text, cosine_similarity


def search_patents(
    queries: list[str],
    principles: list[int],
    limit_per_query: int = 5,
) -> FOSReport:
    """接收 M5 生成的 query 列表，执行搜索，返回结构化报告。

    FOS 不再自主提取 function/domain，只负责"怎么搜"。
    """
    if not queries:
        return FOSReport()

    all_results: list[SearchResult] = []
    cache_hits = 0
    api_calls = 0

    for query in queries:
        cached = _get_cache(query)
        if cached is not None:
            all_results.extend(cached)
            cache_hits += 1
        else:
            if not SERP_API_KEY:
                continue
            try:
                results = _search_serpapi(query, limit_per_query)
                all_results.extend(results)
                _set_cache(query, results)
                api_calls += 1
            except Exception:
                pass

    # 按 title 去重
    seen_titles = set()
    unique_results = []
    for r in all_results:
        key = r.title.lower().strip()
        if key not in seen_titles:
            seen_titles.add(key)
            unique_results.append(r)

    # 语义过滤：用 embedding 相似度排序，保留最相关的结果
    if unique_results and len(unique_results) > limit_per_query:
        unique_results = _semantic_filter(queries, unique_results, limit_per_query)

    # 转为 Case 列表
    cases = [
        Case(
            principle_id=principles[0] if principles else 0,
            source=r.source,
            title=r.title,
            description=r.snippet,
            function="",
        )
        for r in unique_results
    ]

    return FOSReport(
        cases=cases[: limit_per_query * len(queries)],
        raw_results=unique_results,
        queries_used=queries,
        cache_hits=cache_hits,
        api_calls=api_calls,
    )


def _search_serpapi(query: str, num: int = 5) -> list[SearchResult]:
    """调用 SerpApi 搜索 Google Patents（单个 query）。"""
    from serpapi import GoogleSearch

    params = {
        "engine": "google_patents",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": num,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    cases = []
    for result in results.get("organic_results", [])[:num]:
        cases.append(
            SearchResult(
                title=result.get("title", "Unknown Patent"),
                snippet=result.get("snippet", ""),
                url=result.get("link", ""),
                source="Google Patents",
                query=query,
            )
        )
    return cases


def _semantic_filter(
    queries: list[str],
    results: list[SearchResult],
    top_k: int,
) -> list[SearchResult]:
    """用 embedding 相似度对搜索结果重排序，保留最相关的 top_k 条。"""
    try:
        # 将搜索词合并为参考文本
        query_text = " ".join(queries)
        query_vec = embed_text(query_text)
        if not query_vec:
            return results[:top_k]

        # 计算每条结果的相关性分数
        scored = []
        for r in results:
            doc_text = f"{r.title} {r.snippet}"
            doc_vec = embed_text(doc_text)
            if not doc_vec:
                scored.append((r, 0.0))
                continue
            score = cosine_similarity(query_vec, doc_vec)
            scored.append((r, score))

        # 按分数降序排列，取 top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in scored[:top_k]]

    except Exception:
        # 语义过滤失败时，回退到原始顺序
        return results[:top_k]


# --- 缓存机制 ---


def _get_cache_dir() -> Path:
    """获取缓存目录。"""
    cache_dir = Path(FOS_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_key(query: str) -> str:
    """生成缓存文件名（query 的 MD5 hash）。"""
    return hashlib.md5(query.encode("utf-8")).hexdigest()


def _get_cache(query: str) -> list[SearchResult] | None:
    """查询缓存，过期返回 None。"""
    cache_file = _get_cache_dir() / f"{_cache_key(query)}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        cached_time = data.get("timestamp", 0)
        if time.time() - cached_time > FOS_CACHE_TTL_HOURS * 3600:
            return None
        return [SearchResult(**r) for r in data.get("results", [])]
    except Exception:
        return None


def _set_cache(query: str, results: list[SearchResult]):
    """写入缓存。"""
    cache_file = _get_cache_dir() / f"{_cache_key(query)}.json"
    data = {
        "query": query,
        "timestamp": time.time(),
        "results": [r.model_dump() for r in results],
    }
    cache_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --- 兼容旧接口 ---


def search_cases(ctx: WorkflowContext) -> list[Case]:
    """兼容旧接口：从 ctx 提取信息调用 search_patents。"""
    function = ""
    if ctx.sao_list:
        for sao in ctx.sao_list:
            if sao.function_type == "useful":
                function = sao.action
                break
        if not function:
            function = ctx.sao_list[0].action

    query_parts = [f"principle {p}" for p in ctx.principles[:3]]
    if function:
        query_parts.append(function)
    query = " ".join(query_parts) if query_parts else ctx.question

    report = search_patents(
        queries=[query],
        principles=ctx.principles,
        limit_per_query=5,
    )
    return report.cases
