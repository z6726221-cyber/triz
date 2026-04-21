"""M2 根因分析 Skill：RCA+因果链分析"""
import json
import re
from triz.context import WorkflowContext
from triz.utils.api_client import OpenAIClient


M2_SYSTEM_PROMPT = """你是一个TRIZ根因分析专家。你的任务是从给定的负面功能出发，执行RCA+因果链分析。

分析步骤：
1. 从负面功能（harmful/excessive/insufficient）出发
2. 追问"为什么"，构建3-4层深度的因果链
3. 找到根因节点（最根本的矛盾所在）
4. 从根因节点提取候选物理属性

【重要】直接输出JSON，不要输出任何其他内容（不要输出思考过程、分析说明等）：

```json
{
    "root_param": "根因参数描述",
    "key_problem": "关键问题陈述",
    "candidate_attributes": ["属性1", "属性2"],
    "causal_chain": ["Level 0: 表面问题", "Level 1: 直接原因", "Level 2: 深层原因", "Level 3: 根因节点"]
}
```"""


def analyze_cause(ctx: WorkflowContext) -> dict:
    """M2 根因分析：调用 LLM 执行因果链分析。"""
    client = OpenAIClient()

    sao_text = "\n".join([
        f"- [{s.subject}] {s.action} [{s.object}] ({s.function_type})"
        for s in ctx.sao_list
    ])
    resources_text = json.dumps(ctx.resources, ensure_ascii=False)

    prompt = f"""功能模型：
{sao_text}

可用资源：{resources_text}

请执行根因分析，输出因果链和根因节点。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M2_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    return {
        "root_param": data.get("root_param", ""),
        "key_problem": data.get("key_problem", ""),
        "candidate_attributes": data.get("candidate_attributes", []),
        "causal_chain": data.get("causal_chain", []),
    }
