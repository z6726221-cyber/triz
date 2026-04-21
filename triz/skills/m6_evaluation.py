"""M6 方案评估 Skill：独立评审 + 量化排序"""
import json
import re
from triz.context import WorkflowContext, Solution, SolutionDraft, QualitativeTags
from triz.utils.api_client import OpenAIClient


M6_SYSTEM_PROMPT = """你是一个TRIZ方案评估专家。你的任务是独立评审方案草案，并给出量化评分。

重要：你是评审者，不是方案生成者。你只对方案做客观评估，绝不修改方案内容。

评估维度（每个方案）：
1. feasibility_score (1-5): 技术可实现性
2. resource_fit_score (1-5): 资源匹配度
3. innovation_score (1-5): 创新性
4. uniqueness_score (1-5): 独特性
5. risk_level (low/medium/high/critical): 风险等级
6. ifr_deviation_reason (文本): 如果偏离IFR，说明原因；否则留空

同时，为每个方案综合计算 ideality_score (0.0-1.0)，并说明计算依据。

输出格式（JSON数组，按理想度从高到低排序）：
[
    {
        "draft": {"title": "...", "description": "...", "applied_principles": [15], "resource_mapping": "..."},
        "tags": {"feasibility_score": 4, "resource_fit_score": 5, "innovation_score": 4, "uniqueness_score": 3, "risk_level": "low", "ifr_deviation_reason": ""},
        "ideality_score": 0.78,
        "evaluation_rationale": "评分依据说明"
    }
]"""


def evaluate_solutions(ctx: WorkflowContext) -> dict:
    """M6 方案评估：调用 LLM 执行独立评审。"""
    client = OpenAIClient()

    drafts_text = "\n\n".join([
        f"方案 {i+1}:\n标题: {d.title}\n描述: {d.description}\n原理: {d.applied_principles}\n资源: {d.resource_mapping}"
        for i, d in enumerate(ctx.solution_drafts)
    ])

    prompt = f"""矛盾描述：{ctx.contradiction_desc}
理想最终结果：{ctx.ifr}
可用资源：{json.dumps(ctx.resources, ensure_ascii=False)}

待评估方案：
{drafts_text}

请对每个方案进行6维评估，计算理想度，并按理想度从高到低排序输出。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M6_SYSTEM_PROMPT,
        temperature=0.1
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    solutions = []
    unresolved_signals = []

    for item in data if isinstance(data, list) else [data]:
        draft_data = item.get("draft", {})
        tags_data = item.get("tags", {})

        tags = QualitativeTags(
            feasibility_score=tags_data.get("feasibility_score", 3),
            resource_fit_score=tags_data.get("resource_fit_score", 3),
            innovation_score=tags_data.get("innovation_score", 3),
            uniqueness_score=tags_data.get("uniqueness_score", 3),
            risk_level=tags_data.get("risk_level", "medium"),
            ifr_deviation_reason=tags_data.get("ifr_deviation_reason", ""),
        )

        if tags.risk_level in ["high", "critical"]:
            unresolved_signals.append(f"方案风险过高: {draft_data.get('title', '')}")
        if tags.ifr_deviation_reason:
            unresolved_signals.append(f"偏离IFR: {tags.ifr_deviation_reason}")

        ideality = float(item.get("ideality_score", 0.5))
        if ideality > 1.0:
            ideality = 1.0
        elif ideality < 0:
            ideality = 0.0

        sol = Solution(
            draft=SolutionDraft(
                title=draft_data.get("title", ""),
                description=draft_data.get("description", ""),
                applied_principles=draft_data.get("applied_principles", []),
                resource_mapping=draft_data.get("resource_mapping", ""),
            ),
            tags=tags,
            ideality_score=ideality,
            evaluation_rationale=item.get("evaluation_rationale", ""),
        )
        solutions.append(sol)

    solutions.sort(key=lambda s: s.ideality_score, reverse=True)
    unresolved_signals = unresolved_signals[:3]
    max_ideality = solutions[0].ideality_score if solutions else 0.0

    return {
        "ranked_solutions": solutions,
        "max_ideality": max_ideality,
        "unresolved_signals": unresolved_signals,
    }
