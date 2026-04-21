"""FOS 跨界检索 Tool：本地案例库查询 -> Google Patent API 补充"""
from triz.context import WorkflowContext, Case
from triz.config import SERP_API_KEY
from triz.database.queries import query_cases


def search_cases(ctx: WorkflowContext) -> list[Case]:
    """检索跨行业可落地案例。"""
    principles = ctx.principles
    sao_list = ctx.sao_list
    question = ctx.question

    # 从 SAO 提取核心功能词
    function = _extract_function(sao_list)
    domain_hint = _extract_domain(question)

    # L1: 本地查询
    local_cases = query_cases(principles, function=function, limit=10)
    cases = [_db_row_to_case(c) for c in local_cases]

    # L2: 如果本地不足 3 条，尝试 SerpApi
    if len(cases) < 3 and SERP_API_KEY:
        try:
            patent_cases = _search_serpapi(principles, function, domain_hint)
            cases.extend(patent_cases)
        except Exception:
            pass

    return cases[:10]


def _extract_function(sao_list: list) -> str:
    """从 SAO 中提取核心功能词。"""
    if not sao_list:
        return ""
    for sao in sao_list:
        if sao.function_type == "useful":
            return sao.action
    return sao_list[0].action


def _extract_domain(question: str) -> str:
    """从问题中提取领域上下文。"""
    domain_keywords = {
        "医疗": ["手术", "医院", "病人", "医生", "治疗", "药物", "器械"],
        "汽车": ["汽车", "车辆", "发动机", "轮胎", "驾驶"],
        "航天": ["航天", "飞机", "火箭", "卫星", "航空"],
        "电子": ["芯片", "电路", "电池", "手机", "电脑", "半导体"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in question for kw in keywords):
            return domain
    return ""


def _db_row_to_case(row: dict) -> Case:
    return Case(
        principle_id=row["principle_id"],
        source=row["source"],
        title=row["title"],
        description=row["description"],
        function=row.get("function", ""),
    )


def _search_serpapi(principles: list, function: str, domain: str) -> list[Case]:
    """调用 SerpApi 搜索 Google Patents。"""
    from serpapi import GoogleSearch

    query_parts = [f"principle {p}" for p in principles[:3]]
    if function:
        query_parts.append(function)
    if domain:
        query_parts.append(domain)
    query = " ".join(query_parts)

    params = {
        "engine": "google_patents",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": 10,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    cases = []
    for result in results.get("organic_results", [])[:5]:
        title = result.get("title", "Unknown Patent")
        snippet = result.get("snippet", "")
        cases.append(Case(
            principle_id=principles[0] if principles else 0,
            source="Google Patents",
            title=title,
            description=snippet,
            function=function,
        ))
    return cases
