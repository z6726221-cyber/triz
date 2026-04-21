"""M5 方案生成 Skill：将原理+跨界案例迁移到用户场景"""
import json
import re
from triz.context import WorkflowContext, SolutionDraft
from triz.utils.api_client import OpenAIClient


M5_SYSTEM_PROMPT = """你是一个TRIZ方案生成专家。你的任务是将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案。

约束：
1. 每个方案必须明确引用一个或多个发明原理编号
2. 优先使用用户已有的资源，避免引入新组件
3. 参考跨界案例进行类比迁移
4. 方案必须具体、可执行，避免泛泛而谈（至少100字描述）
5. 使用类比法将案例映射到用户场景

输出格式（JSON数组）：
[
    {
        "title": "方案标题",
        "description": "详细方案描述（具体、可执行）",
        "applied_principles": [15, 28],
        "resource_mapping": "使用了哪些现有资源"
    }
]"""


def generate_solutions(ctx: WorkflowContext) -> dict:
    """M5 方案生成：调用 LLM 生成方案草稿。"""
    client = OpenAIClient()

    cases_text = "\n".join([
        f"- 原理#{c.principle_id} [{c.source}] {c.title}: {c.description}"
        for c in ctx.cases
    ]) if ctx.cases else "无跨界案例"

    resources_text = json.dumps(ctx.resources, ensure_ascii=False)

    prompt = f"""矛盾描述：{ctx.contradiction_desc}
理想最终结果：{ctx.ifr}
可用资源：{resources_text}

匹配的发明原理：{ctx.principles}

跨界参考案例：
{cases_text}

{ctx.feedback if ctx.feedback else ""}

请生成 {len(ctx.principles)} 个方案草稿，每个方案对应一个或多个原理。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M5_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    drafts = []
    for item in data if isinstance(data, list) else [data]:
        drafts.append(SolutionDraft(
            title=item.get("title", "未命名方案"),
            description=item.get("description", ""),
            applied_principles=item.get("applied_principles", []),
            resource_mapping=item.get("resource_mapping", ""),
        ))

    return {"solution_drafts": drafts}
