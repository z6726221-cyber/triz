"""M1 功能建模 Skill：从自然语言提取 SAO、IFR、资源"""
import json
import re
from triz.context import WorkflowContext, SAO
from triz.utils.api_client import OpenAIClient


M1_SYSTEM_PROMPT = """你是一个TRIZ功能分析专家。你的任务是将用户的问题拆解为结构化的功能模型。

你需要输出以下内容的JSON格式：
1. sao_list: S-A-O（Subject-Action-Object）三元组列表，每个三元组包含 function_type（useful/harmful/excessive/insufficient）
2. resources: 可用资源，按类型分类（物质、场、空间、时间、信息、功能）
3. ifr: 理想最终结果（Ideal Final Result），用一句话描述理想状态

【重要】直接输出JSON，不要输出任何其他内容（不要输出思考过程、分析说明等）：

```json
{
    "sao_list": [
        {"subject": "刀片", "action": "切割", "object": "纸张", "function_type": "useful"},
        {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"}
    ],
    "resources": {"物质": ["刀片", "纸张"], "场": ["重力场"]},
    "ifr": "刀片在无限切割时自动保持锋利"
}
```"""


def model_function(ctx: WorkflowContext) -> dict:
    """M1 功能建模：调用 LLM 提取结构化信息。"""
    client = OpenAIClient()

    prompt = f"用户问题：{ctx.question}\n\n请分析并输出功能模型。"
    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M1_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析为 JSON: {response[:200]}")

    sao_list = []
    for item in data.get("sao_list", []):
        sao_list.append(SAO(
            subject=item.get("subject", ""),
            action=item.get("action", ""),
            object=item.get("object", ""),
            function_type=item.get("function_type", "useful")
        ))

    return {
        "sao_list": sao_list,
        "resources": data.get("resources", {}),
        "ifr": data.get("ifr", ""),
    }
