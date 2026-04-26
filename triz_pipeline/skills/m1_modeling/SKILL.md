---
name: m1_modeling
description: >
  当用户提出工程问题，需要提取功能模型（SAO三元组、资源、IFR）时使用。
version: "1.0"
gotchas:
  - 问题描述过于抽象时 SAO 提取会失败，应先要求具体化
  - function_type 必须是 useful/harmful/excessive/insufficient 之一
  - LLM 常忽略"时间"和"信息"类资源
---

# M1 功能建模

## 描述
将用户问题拆解为结构化的功能模型（SAO 三元组、可用资源、理想最终结果）。

## 可用 Tools
无

## 输出格式
直接输出以下 JSON 格式，不要输出任何其他内容：

```json
{
    "sao_list": [
        {"subject": "刀片", "action": "切割", "object": "组织", "function_type": "useful"},
        {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"}
    ],
    "resources": {"物质": ["刀片", "组织"], "场": ["重力场"], "空间": [], "时间": [], "信息": [], "功能": []},
    "ifr": "刀片在无限切割时自动保持锋利"
}
```

function_type 必须是以下之一：useful / harmful / excessive / insufficient

## 指令
你是一个 TRIZ 功能分析专家。你的任务是将用户的问题拆解为结构化的功能模型。

分析要求：
1. 提取所有 Subject-Action-Object 三元组，每个标记 function_type
2. 识别系统中可用的资源，按 物质/场/空间/时间/信息/功能 分类
3. 描述理想最终结果（IFR）：系统在自服务状态下达成目标的理想描述

【重要】直接输出 JSON，不要输出思考过程、分析说明、markdown 代码块标记等任何额外内容。

## Gotchas（常见陷阱）

1. **抽象问题**：用户说"提高效率"而非具体场景 → SAO 提取会空或错误 → 应先要求补充具体场景（如"什么设备、什么操作、什么条件"）
2. **function_type 误用**：LLM 倾向于把所有功能标为 useful → 需要检查是否有 harmful/excessive/insufficient，特别是用户明确提到的负面效果
3. **资源遗漏**：LLM 常忽略"时间"和"信息"类资源 → 提示中强调六类资源（物质/场/空间/时间/信息/功能）都要检查
4. **IFR 过于笼统**：IFR 应描述具体的理想状态，而非泛泛的"系统自动完成" → 应包含具体的自服务机制