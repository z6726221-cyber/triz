# TRIZ Skill-MD 架构重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TRIZ 系统的 Skill 层从 `.py` 重构为 `.md` 文件，建立 Skill Runner + Tool Registry 架构，使 Skill 可内部决策调用 Tool（Function Calling）。

**Architecture:** 创建 `triz/core/` 模块包含 `tool_registry.py`（Tool 注册表）和 `skill_runner.py`（Skill 执行器）。Skill Runner 读取 `.md` 文件作为 system prompt，调用 LLM 时注入可用 Tool schemas，拦截 LLM 的 tool_calls 执行 Tool 并返回结果。M4 从单一 Tool 拆分为 Skill（`.md`）+ 3 个 sub-Tools（`query_parameters`, `query_matrix`, `query_separation`）。Orchestrator 通过 Skill Runner 执行 Skill，直接调用 Tool。

**Tech Stack:** Python 3.10+, Pydantic v2, OpenAI Python SDK, SQLite

---

## 文件结构映射

### 新增文件

| 文件 | 职责 |
|------|------|
| `triz/core/__init__.py` | core 模块初始化 |
| `triz/core/tool_registry.py` | Tool 注册表：注册、查询 schemas、执行 Tool |
| `triz/core/skill_runner.py` | Skill 执行器：读取 `.md`，调用 LLM with tools，拦截 tool_calls |
| `triz/skills/m1_modeling.md` | M1 功能建模 Skill（声明式） |
| `triz/skills/m2_causal.md` | M2 根因分析 Skill（声明式） |
| `triz/skills/m4_solver.md` | M4 矛盾求解 Skill（声明式，内部调用 Tools） |
| `triz/skills/m5_generation.md` | M5 方案生成 Skill（声明式） |
| `triz/skills/m6_evaluation.md` | M6 方案评估 Skill（声明式） |
| `triz/tools/query_parameters.py` | 参数查询 Tool（从 m4_solver 拆分） |
| `triz/tools/query_matrix.py` | 矩阵查询 Tool（从 m4_solver 拆分） |
| `triz/tools/query_separation.py` | 分离原理查询 Tool（从 m4_solver 拆分） |
| `tests/test_tool_registry.py` | Tool Registry 测试 |
| `tests/test_skill_runner.py` | Skill Runner 测试（mock LLM） |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `triz/utils/api_client.py` | 新增 `chat_with_tools()` 方法支持 Function Calling |
| `triz/orchestrator.py` | 使用 Skill Runner 执行 Skills，保留直接调用 Tools |

### 删除文件（测试通过后执行）

| 文件 | 原因 |
|------|------|
| `triz/skills/m1_modeling.py` | 替换为 `.md` |
| `triz/skills/m2_causal.py` | 替换为 `.md` |
| `triz/skills/m5_generation.py` | 替换为 `.md` |
| `triz/skills/m6_evaluation.py` | 替换为 `.md` |
| `triz/tools/m4_solver.py` | 功能拆分到 M4 Skill + sub-Tools |

---

## Task 1: 创建 Core 基础设施（API Client + Tool Registry + Skill Runner）

**Files:**
- Modify: `triz/utils/api_client.py`
- Create: `triz/core/__init__.py`
- Create: `triz/core/tool_registry.py`
- Create: `triz/core/skill_runner.py`
- Create: `tests/test_tool_registry.py`
- Create: `tests/test_skill_runner.py`

### Step 1: 写 API Client 扩展测试

```python
# tests/test_api_client.py 新增测试（追加到现有文件末尾）

from unittest.mock import Mock, MagicMock

def test_chat_with_tools_returns_response():
    """验证 chat_with_tools 能正确调用底层 API 并返回 response"""
    client = OpenAIClient()
    # Mock 底层 client
    mock_choice = Mock()
    mock_choice.message.content = "Test response"
    mock_choice.message.tool_calls = None
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    client.client.chat.completions.create = Mock(return_value=mock_response)

    messages = [{"role": "user", "content": "test"}]
    tools = [{"type": "function", "function": {"name": "test_tool"}}]

    result = client.chat_with_tools(messages=messages, tools=tools)

    assert result == mock_response
    client.client.chat.completions.create.assert_called_once()
    call_kwargs = client.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["messages"] == messages
    assert call_kwargs["tools"] == tools
    assert call_kwargs["tool_choice"] == "auto"
```

### Step 2: 运行测试确认失败

```bash
pytest tests/test_api_client.py::test_chat_with_tools_returns_response -v
```
Expected: FAIL - `AttributeError: 'OpenAIClient' object has no attribute 'chat_with_tools'`

### Step 3: 扩展 API Client

```python
# triz/utils/api_client.py - 在 class OpenAIClient 中添加方法

    def chat_with_tools(self, messages: list, tools: list,
                        temperature: float = 0.3):
        """支持 function calling 的对话，返回原始 response 对象。

        调用方需要检查 response.choices[0].message.tool_calls 来决定是否继续对话。
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
        )
        return response
```

### Step 4: 运行 API Client 测试

```bash
pytest tests/test_api_client.py::test_chat_with_tools_returns_response -v
```
Expected: PASS

### Step 5: 写 Tool Registry 测试

```python
# tests/test_tool_registry.py

import pytest
from triz.core.tool_registry import ToolRegistry


def test_register_and_execute():
    registry = ToolRegistry()

    def add(a: int, b: int) -> int:
        return a + b

    registry.register(
        name="add",
        func=add,
        schema={
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        }
    )

    schemas = registry.get_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "add"

    result = registry.execute("add", {"a": 2, "b": 3})
    assert result == 5


def test_execute_unknown_tool():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="未知 Tool"):
        registry.execute("unknown", {})
```

### Step 6: 运行 Tool Registry 测试（预期失败）

```bash
pytest tests/test_tool_registry.py -v
```
Expected: FAIL - `ModuleNotFoundError: No module named 'triz.core.tool_registry'`

### Step 7: 创建 Tool Registry

```python
# triz/core/__init__.py
# 空文件

# triz/core/tool_registry.py
"""Tool Registry：注册和管理可供 Skill 调用的 Tools。"""
import json
from typing import Callable, Any


class ToolRegistry:
    """Tool 注册表。

    每个 Tool 包含：
    - func: 实际执行函数
    - schema: OpenAI function calling 格式的 schema
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, func: Callable, schema: dict) -> None:
        """注册一个 Tool。"""
        self._tools[name] = {"func": func, "schema": schema}

    def get_schemas(self) -> list[dict]:
        """获取所有注册 Tool 的 OpenAI function schemas。"""
        return [
            {"type": "function", "function": tool["schema"]}
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> Any:
        """执行指定 Tool，传入参数 dict。"""
        if name not in self._tools:
            raise ValueError(f"未知 Tool: {name}")
        return self._tools[name]["func"](**arguments)

    def list_tools(self) -> list[str]:
        """返回所有已注册 Tool 的名称列表。"""
        return list(self._tools.keys())
```

### Step 8: 运行 Tool Registry 测试

```bash
pytest tests/test_tool_registry.py -v
```
Expected: PASS

### Step 9: 写 Skill Runner 测试

```python
# tests/test_skill_runner.py

import json
from unittest.mock import Mock
import pytest
from triz.context import WorkflowContext
from triz.core.skill_runner import SkillRunner
from triz.core.tool_registry import ToolRegistry


def _make_mock_response(content: str = None, tool_calls: list = None):
    """辅助函数：构造 mock LLM response。"""
    mock_message = Mock()
    mock_message.content = content
    mock_message.tool_calls = tool_calls
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    return mock_response


def _make_mock_tool_call(id: str, name: str, arguments: dict):
    """辅助函数：构造 mock tool call。"""
    mock_func = Mock()
    mock_func.name = name
    mock_func.arguments = json.dumps(arguments)
    mock_tc = Mock()
    mock_tc.id = id
    mock_tc.type = "function"
    mock_tc.function = mock_func
    return mock_tc


def test_skill_runner_parses_json_output(tmp_path, monkeypatch):
    """Skill Runner 能正确解析 LLM 返回的 JSON。"""
    registry = ToolRegistry()
    runner = SkillRunner(registry)

    # Mock client
    mock_client = Mock()
    mock_response = _make_mock_response(content='{"sao_list": [], "ifr": "test"}')
    mock_client.chat_with_tools = Mock(return_value=mock_response)
    runner.client = mock_client

    # 创建临时 skill md 文件
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1\n输出JSON。", encoding="utf-8")

    # 替换 skill 路径
    monkeypatch.setattr(
        "triz.core.skill_runner.Path",
        lambda *args: tmp_path / "/".join(args[1:]) if args else tmp_path
    )

    ctx = WorkflowContext(question="test")
    result = runner.run("m1_modeling", ctx)

    assert result["ifr"] == "test"


def test_skill_runner_executes_tool_call(tmp_path, monkeypatch):
    """Skill Runner 能拦截 tool_call 并执行 Tool。"""
    registry = ToolRegistry()

    def mock_tool(x: int) -> int:
        return x * 2

    registry.register(
        name="mock_tool",
        func=mock_tool,
        schema={
            "name": "mock_tool",
            "description": "Mock tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        }
    )

    runner = SkillRunner(registry)

    # 第一轮：返回 tool_call
    tc = _make_mock_tool_call("call_1", "mock_tool", {"x": 5})
    response1 = _make_mock_response(tool_calls=[tc])
    # 第二轮：返回最终结果
    response2 = _make_mock_response(content='{"result": 10}')

    mock_client = Mock()
    mock_client.chat_with_tools = Mock(side_effect=[response1, response2])
    runner.client = mock_client

    # 创建临时 skill md
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1", encoding="utf-8")

    monkeypatch.setattr(
        "triz.core.skill_runner.Path",
        lambda *args: tmp_path / "/".join(args[1:]) if args else tmp_path
    )

    ctx = WorkflowContext(question="test")
    result = runner.run("m1_modeling", ctx)

    assert result["result"] == 10
    # 验证 tool 被执行
    assert mock_client.chat_with_tools.call_count == 2


def test_skill_runner_exceeds_max_rounds(tmp_path, monkeypatch):
    """超过最大轮数时抛出 RuntimeError。"""
    registry = ToolRegistry()

    def loop_tool():
        return {}

    registry.register(
        name="loop_tool",
        func=loop_tool,
        schema={
            "name": "loop_tool",
            "description": "Loops forever",
            "parameters": {"type": "object", "properties": {}},
        }
    )

    runner = SkillRunner(registry)

    # 永远返回 tool_call
    tc = _make_mock_tool_call("call_1", "loop_tool", {})
    response = _make_mock_response(tool_calls=[tc])

    mock_client = Mock()
    mock_client.chat_with_tools = Mock(return_value=response)
    runner.client = mock_client

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "m1_modeling.md"
    skill_file.write_text("# M1", encoding="utf-8")

    monkeypatch.setattr(
        "triz.core.skill_runner.Path",
        lambda *args: tmp_path / "/".join(args[1:]) if args else tmp_path
    )

    ctx = WorkflowContext(question="test")
    with pytest.raises(RuntimeError, match="超过最大轮数"):
        runner.run("m1_modeling", ctx)
```

### Step 10: 运行 Skill Runner 测试（预期失败）

```bash
pytest tests/test_skill_runner.py -v
```
Expected: FAIL - `ModuleNotFoundError: No module named 'triz.core.skill_runner'`

### Step 11: 创建 Skill Runner

```python
# triz/core/skill_runner.py
"""Skill Runner：读取 .md Skill 文件，调用 LLM 执行，支持 Function Calling。"""
import json
import re
from pathlib import Path
from triz.context import WorkflowContext
from triz.utils.api_client import OpenAIClient
from triz.core.tool_registry import ToolRegistry


class SkillRunner:
    """Skill 执行器。

    执行流程：
    1. 读取 skills/{skill_name}.md 作为 system prompt
    2. 将 WorkflowContext 序列化为 user prompt
    3. 调用 LLM with available tools
    4. 如果 LLM 返回 tool_calls，执行 Tools 并将结果返回给 LLM
    5. 重复直到 LLM 返回最终结果（无 tool_calls）
    6. 解析最终 JSON 输出
    """

    MAX_ROUNDS = 5

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.client = OpenAIClient()

    def run(self, skill_name: str, ctx: WorkflowContext) -> dict:
        """执行指定 Skill，返回解析后的 dict。"""
        skill_path = Path(__file__).parent.parent / "skills" / f"{skill_name}.md"
        if not skill_path.exists():
            raise FileNotFoundError(f"Skill 文件不存在: {skill_path}")

        system_prompt = skill_path.read_text(encoding="utf-8")
        user_prompt = self._build_context_prompt(ctx)
        tools = self.tool_registry.get_schemas()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for _ in range(self.MAX_ROUNDS):
            response = self.client.chat_with_tools(
                messages=messages,
                tools=tools,
                temperature=0.3,
            )

            message = response.choices[0].message

            if message.tool_calls:
                # 添加 assistant 的 tool_call 请求到 messages
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or "",
                }
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]
                messages.append(assistant_msg)

                # 执行每个 tool call，添加结果到 messages
                for tc in message.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    result = self.tool_registry.execute(name, args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
            else:
                # LLM 返回最终结果
                return self._parse_result(message.content)

        raise RuntimeError(f"Skill '{skill_name}' 执行超过最大轮数 {self.MAX_ROUNDS}")

    def _build_context_prompt(self, ctx: WorkflowContext) -> str:
        """将 WorkflowContext 序列化为 JSON prompt。"""
        return json.dumps(ctx.model_dump(), ensure_ascii=False, indent=2)

    def _parse_result(self, content: str) -> dict:
        """解析 LLM 返回的 JSON。"""
        if not content:
            return {}
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"无法解析 LLM 输出: {content[:200]}")
```

### Step 12: 运行 Skill Runner 测试

```bash
pytest tests/test_skill_runner.py -v
```
Expected: PASS

### Step 13: 提交 Task 1

```bash
git add triz/core/ triz/utils/api_client.py tests/test_tool_registry.py tests/test_skill_runner.py tests/test_api_client.py
git commit -m "feat(core): add Tool Registry and Skill Runner infrastructure"
```

---

## Task 2: 创建 M4 Sub-Tools

**Files:**
- Create: `triz/tools/query_parameters.py`
- Create: `triz/tools/query_matrix.py`
- Create: `triz/tools/query_separation.py`
- Create: `tests/test_m4_subtools.py`

### Step 1: 写 M4 Sub-Tools 测试

```python
# tests/test_m4_subtools.py

import pytest
from triz.tools.query_parameters import query_parameters
from triz.tools.query_matrix import query_matrix
from triz.tools.query_separation import query_separation


def test_query_parameters_by_keyword():
    """关键词直接匹配参数"""
    results = query_parameters(["速度"])
    assert len(results) >= 1
    assert any(r["id"] == 9 for r in results)


def test_query_parameters_empty():
    """空关键词返回空列表"""
    results = query_parameters([])
    assert results == []


def test_query_matrix_valid_params():
    """查询有效的矛盾矩阵组合"""
    results = query_matrix(9, 12)  # Speed vs Shape
    assert isinstance(results, list)


def test_query_separation_phys_contradiction():
    """物理矛盾查询分离原理"""
    result = query_separation("接触面积既要大又要小")
    assert "sep_type" in result
    assert "principles" in result
    assert isinstance(result["principles"], list)
```

### Step 2: 运行测试（预期失败）

```bash
pytest tests/test_m4_subtools.py -v
```
Expected: FAIL - `ModuleNotFoundError`

### Step 3: 创建 query_parameters.py

```python
# triz/tools/query_parameters.py
"""参数查询 Tool：将自然语言属性匹配到 39 工程参数。"""
from triz.config import SIMILARITY_THRESHOLD
from triz.database.queries import get_all_parameters
from triz.utils.vector_math import cosine_similarity, embed_text


# 关键词到参数ID的映射（fallback 用）
KEYWORD_PARAM_MAP = {
    "速度": 9, "speed": 9, "快": 9, "慢": 9,
    "力": 10, "force": 10, "压力": 11, "强度": 14, "strength": 14,
    "形状": 12, "shape": 12, "形态": 12,
    "稳定": 13, "稳定性": 13, "可靠": 27, "可靠性": 27,
    "重量": 1, "质量": 1, "weight": 1,
    "面积": 5, "area": 5, "体积": 7, "volume": 7,
    "温度": 17, "temperature": 17, "热": 17,
    "能量": 19, "energy": 19, "功率": 21, "power": 21,
    "时间": 25, "time": 25, "损耗": 22,
    "精度": 28, "accuracy": 28, "制造": 32,
    "复杂": 36, "complexity": 36, "生产率": 39, "productivity": 39,
}


def query_parameters(keywords: list[str]) -> list[dict]:
    """根据关键词查询最匹配的 39 工程参数。

    每个关键词先尝试关键词直接匹配，失败则使用余弦相似度匹配。

    返回: [{"id": int, "name": str, "name_cn": str, "similarity": float, "match_type": str}, ...]
    """
    if not keywords:
        return []

    all_params = get_all_parameters()
    results = []
    seen_ids = set()

    for keyword in keywords:
        if not keyword:
            continue

        # 策略1: 关键词直接匹配
        matched = False
        for kw, param_id in KEYWORD_PARAM_MAP.items():
            if kw in keyword:
                if param_id not in seen_ids:
                    for param in all_params:
                        if param["id"] == param_id:
                            results.append({
                                "id": param_id,
                                "name": param["name"],
                                "name_cn": param["name_cn"],
                                "similarity": 1.0,
                                "match_type": "keyword",
                            })
                            seen_ids.add(param_id)
                            break
                matched = True
                break

        if matched:
            continue

        # 策略2: 余弦相似度匹配
        attr_vec = embed_text(keyword)
        best_match = None
        best_score = -1.0

        for param in all_params:
            desc = param.get("description", "")
            param_vec = embed_text(f"{param['name']} {param['name_cn']} {desc}")
            score = cosine_similarity(attr_vec, param_vec)
            if score > best_score:
                best_score = score
                best_match = param

        if best_match and best_score >= SIMILARITY_THRESHOLD:
            if best_match["id"] not in seen_ids:
                results.append({
                    "id": best_match["id"],
                    "name": best_match["name"],
                    "name_cn": best_match["name_cn"],
                    "similarity": best_score,
                    "match_type": "similarity",
                })
                seen_ids.add(best_match["id"])

    return results
```

### Step 4: 创建 query_matrix.py

```python
# triz/tools/query_matrix.py
"""矩阵查询 Tool：查询阿奇舒勒矛盾矩阵。"""
from triz.database.queries import get_matrix_principles


def query_matrix(improve_param_id: int, worsen_param_id: int) -> list[int]:
    """查询矛盾矩阵，返回发明原理列表。

    参数:
        improve_param_id: 改善参数 ID (1-39)
        worsen_param_id: 恶化参数 ID (1-39)

    返回: 发明原理编号列表
    """
    return get_matrix_principles(improve_param_id, worsen_param_id)
```

### Step 5: 创建 query_separation.py

```python
# triz/tools/query_separation.py
"""分离原理查询 Tool：查询物理矛盾的分离原理。"""
from triz.database.queries import get_separation_principles_by_type, get_all_separation_types


def query_separation(contradiction_desc: str) -> dict:
    """查询分离原理。

    参数:
        contradiction_desc: 物理矛盾描述

    返回: {"sep_type": str, "principles": list[int]}
    """
    sep_type = _classify_separation(contradiction_desc)
    principles = get_separation_principles_by_type(sep_type)

    # fallback: 如果该类型没有原理，返回所有分离类型的原理并集
    if not principles:
        all_types = get_all_separation_types()
        all_prins = set()
        for t in all_types:
            all_prins.update(t.get("principles", []))
        principles = sorted(list(all_prins))

    return {"sep_type": sep_type, "principles": principles}


def _classify_separation(desc: str) -> str:
    """判定分离类型（空间/时间/条件/系统）。"""
    if any(kw in desc for kw in ["位置", "空间", "区域", "地方", "上面", "下面", "内部", "外部"]):
        return "空间"
    if any(kw in desc for kw in ["时间", "之前", "之后", "同时", "顺序", "阶段", "周期"]):
        return "时间"
    if any(kw in desc for kw in ["条件", "温度", "压力", "速度", "状态", "高", "低", "大", "小"]):
        return "条件"
    return "条件"
```

### Step 6: 运行 M4 Sub-Tools 测试

```bash
pytest tests/test_m4_subtools.py -v
```
Expected: PASS

### Step 7: 提交 Task 2

```bash
git add triz/tools/query_parameters.py triz/tools/query_matrix.py triz/tools/query_separation.py tests/test_m4_subtools.py
git commit -m "feat(tools): add M4 sub-tools (query_parameters, query_matrix, query_separation)"
```

---

## Task 3: 创建 M1/M2/M4/M5/M6 Skills (.md)

**Files:**
- Create: `triz/skills/m1_modeling.md`
- Create: `triz/skills/m2_causal.md`
- Create: `triz/skills/m4_solver.md`
- Create: `triz/skills/m5_generation.md`
- Create: `triz/skills/m6_evaluation.md`

### Step 1: 创建 m1_modeling.md

```markdown
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
```

### Step 2: 创建 m2_causal.md

```markdown
# M2 根因分析

## 描述
从负面功能出发，执行 RCA+因果链分析，找到根因节点和候选物理属性。

## 可用 Tools
无

## 输出格式
直接输出以下 JSON 格式：

```json
{
    "root_param": "根因参数描述",
    "key_problem": "关键问题陈述",
    "candidate_attributes": ["属性1", "属性2"],
    "causal_chain": ["Level 0: 表面问题", "Level 1: 直接原因", "Level 2: 深层原因", "Level 3: 根因节点"]
}
```

## 指令
你是一个 TRIZ 根因分析专家。你的任务是从给定的负面功能出发，执行 RCA+因果链分析。

分析步骤：
1. 从负面功能（harmful/excessive/insufficient）出发
2. 追问"为什么"，构建 3-4 层深度的因果链
3. 找到根因节点（最根本的矛盾所在）
4. 从根因节点提取候选物理属性

【重要】直接输出 JSON，不要输出任何其他内容。
```

### Step 3: 创建 m4_solver.md

```markdown
# M4 矛盾求解

## 描述
将自然语言矛盾映射到 TRIZ 工程参数，查询发明原理或分离原理。

## 可用 Tools

### query_parameters
- **描述**: 根据关键词查询 39 个 TRIZ 工程参数
- **参数**: `keywords` (list[str]) — 描述改善/恶化参数的关键词列表
- **返回**: 匹配参数列表，每个参数包含 id, name, name_cn, similarity, match_type

### query_matrix
- **描述**: 查询阿奇舒勒矛盾矩阵
- **参数**:
  - `improve_param_id` (int) — 改善参数 ID (1-39)
  - `worsen_param_id` (int) — 恶化参数 ID (1-39)
- **返回**: 发明原理编号列表

### query_separation
- **描述**: 查询物理矛盾的分离原理
- **参数**: `contradiction_desc` (str) — 矛盾描述
- **返回**: `{"sep_type": "空间|时间|条件", "principles": [1, 2, 3]}`

## 工作流程

1. 如果是技术矛盾（problem_type == "tech"）：
   - 从 contradiction_desc 和 candidate_attributes 中提取改善参数和恶化参数的关键词
   - 调用 `query_parameters` 获取参数 ID
   - 调用 `query_matrix` 获取发明原理

2. 如果是物理矛盾（problem_type == "phys"）：
   - 调用 `query_separation` 获取分离类型和原理

## 输出格式

技术矛盾：
```json
{
    "principles": [1, 15, 28],
    "improve_param_id": 9,
    "worsen_param_id": 12,
    "match_conf": 0.8,
    "sep_type": null,
    "need_state": null,
    "need_not_state": null
}
```

物理矛盾：
```json
{
    "principles": [1, 2, 3],
    "sep_type": "空间",
    "match_conf": 0.7,
    "improve_param_id": null,
    "worsen_param_id": null,
    "need_state": "大",
    "need_not_state": "小"
}
```

match_conf: 如果 improve_param_id 和 worsen_param_id 都有效则为 0.8，否则为 0.5

## 指令
你是一个 TRIZ 矛盾求解专家。请根据输入的矛盾信息，调用合适的 Tools 查询发明原理。

【重要】如果需要调用 Tool，请输出 function call；获得结果后，直接输出最终 JSON，不要输出思考过程。
```

### Step 4: 创建 m5_generation.md

```markdown
# M5 方案生成

## 描述
将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案草稿。

## 可用 Tools
无

## 输出格式
直接输出以下 JSON 数组格式：

```json
[
    {
        "title": "方案标题",
        "description": "详细方案描述（具体、可执行，至少100字）",
        "applied_principles": [15, 28],
        "resource_mapping": "使用了哪些现有资源"
    }
]
```

## 指令
你是一个 TRIZ 方案生成专家。你的任务是将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案。

约束：
1. 每个方案必须明确引用一个或多个发明原理编号
2. 优先使用用户已有的资源，避免引入新组件
3. 参考跨界案例进行类比迁移
4. 方案必须具体、可执行，避免泛泛而谈（至少100字描述）
5. 使用类比法将案例映射到用户场景

【重要】直接输出 JSON 数组，不要输出任何其他内容。不要在 JSON 前后添加文字说明。
```

### Step 5: 创建 m6_evaluation.md

```markdown
# M6 方案评估

## 描述
独立评审方案草案，给出 6 维度量化评分和理想度，按理想度排序。

## 可用 Tools
无

## 输出格式
直接输出以下 JSON 数组格式：

```json
[
    {
        "title": "方案标题（原样复制输入的方案标题）",
        "description": "方案描述（原样复制输入的方案描述）",
        "applied_principles": [15],
        "resource_mapping": "资源映射（原样复制输入的资源映射）",
        "feasibility_score": 4,
        "resource_fit_score": 5,
        "innovation_score": 4,
        "uniqueness_score": 3,
        "risk_level": "low",
        "ifr_deviation_reason": "",
        "ideality_score": 0.78,
        "evaluation_rationale": "评分依据说明"
    }
]
```

## 指令
你是一个 TRIZ 方案评估专家。你的任务是独立评审方案草案，并给出量化评分。

重要：你是评审者，不是方案生成者。你只对方案做客观评估，绝不修改方案内容。

评估维度（每个方案）：
1. feasibility_score (1-5): 技术可实现性
2. resource_fit_score (1-5): 资源匹配度
3. innovation_score (1-5): 创新性
4. uniqueness_score (1-5): 独特性
5. risk_level (low/medium/high/critical): 风险等级
6. ifr_deviation_reason (文本): 如果偏离 IFR，说明原因；否则留空

同时，为每个方案综合计算 ideality_score (0.0-1.0)，并说明计算依据。

注意：
- 必须输出 JSON 数组，即使只有一个方案
- title/description/applied_principles/resource_mapping 必须原样复制输入的方案信息
- 所有评分字段都必须存在，不能省略

【重要】直接输出 JSON，不要输出任何其他内容。
```

### Step 6: 验证 Skill 文件存在

```bash
ls -la triz/skills/*.md
```
Expected: 5 个 .md 文件

### Step 7: 提交 Task 3

```bash
git add triz/skills/*.md
git commit -m "feat(skills): add M1/M2/M4/M5/M6 as .md skill files"
```

---

## Task 4: 更新 Orchestrator 使用新架构

**Files:**
- Modify: `triz/orchestrator.py`
- Create: `tests/test_orchestrator_refactor.py`

### Step 1: 更新 Orchestrator

```python
# triz/orchestrator.py
"""编排器核心：持有 WorkflowContext，按序调用 Skill/Tool，渲染 Markdown 输出"""
from triz.context import WorkflowContext, ConvergenceDecision
from triz.core.skill_runner import SkillRunner
from triz.core.tool_registry import ToolRegistry
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m7_convergence import check_convergence
from triz.tools.fos_search import search_cases
from triz.tools.query_parameters import query_parameters
from triz.tools.query_matrix import query_matrix
from triz.tools.query_separation import query_separation
from triz.utils.markdown_renderer import (
    render_node_start, render_step_complete,
    render_node_complete, render_final_report
)


def _register_m4_tools() -> ToolRegistry:
    """注册 M4 Skill 可调用的 sub-tools。"""
    registry = ToolRegistry()

    registry.register(
        name="query_parameters",
        func=query_parameters,
        schema={
            "name": "query_parameters",
            "description": "根据关键词查询 39 个 TRIZ 工程参数，返回最匹配的参数 ID 和名称",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "描述改善/恶化参数的关键词列表，如 ['速度', '形状']",
                    }
                },
                "required": ["keywords"],
            },
        }
    )

    registry.register(
        name="query_matrix",
        func=query_matrix,
        schema={
            "name": "query_matrix",
            "description": "查询阿奇舒勒矛盾矩阵，给定改善参数和恶化参数，返回推荐的发明原理",
            "parameters": {
                "type": "object",
                "properties": {
                    "improve_param_id": {
                        "type": "integer",
                        "description": "改善参数 ID (1-39)",
                    },
                    "worsen_param_id": {
                        "type": "integer",
                        "description": "恶化参数 ID (1-39)",
                    },
                },
                "required": ["improve_param_id", "worsen_param_id"],
            },
        }
    )

    registry.register(
        name="query_separation",
        func=query_separation,
        schema={
            "name": "query_separation",
            "description": "查询物理矛盾的分离原理，给定矛盾描述，返回分离类型和推荐原理",
            "parameters": {
                "type": "object",
                "properties": {
                    "contradiction_desc": {
                        "type": "string",
                        "description": "物理矛盾的自然语言描述",
                    }
                },
                "required": ["contradiction_desc"],
            },
        }
    )

    return registry


class Orchestrator:
    """TRIZ Workflow 编排器。"""

    def __init__(self):
        self.output_buffer = []
        self.tool_registry = _register_m4_tools()
        self.skill_runner = SkillRunner(self.tool_registry)

    def run_workflow(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow，返回 Markdown 格式的最终报告。"""
        ctx = WorkflowContext(question=question, history=history or [])
        self.output_buffer = []

        # ===== 问题建模 =====
        ctx = self._execute_node("问题建模", 1, 5, ctx, [
            ("m1_modeling", "Skill"),
            ("m2_causal", "Skill"),
            ("M3", "Tool", formulate_problem),
        ])

        if not ctx.sao_list:
            return self._generate_clarification("无法从问题中提取功能模型，请补充描述")

        # ===== 迭代主循环 =====
        while True:
            # 矛盾求解
            ctx = self._execute_node("矛盾求解", 2, 5, ctx, [
                ("m4_solver", "Skill"),
            ])

            if not ctx.principles:
                return self._generate_fallback("无法从矛盾定义中匹配到发明原理")

            # 跨界检索
            ctx = self._execute_node("跨界检索", 3, 5, ctx, [
                ("FOS", "Tool", search_cases),
            ])

            # 方案生成
            ctx = self._execute_node("方案生成", 4, 5, ctx, [
                ("m5_generation", "Skill"),
            ])

            if not ctx.solution_drafts:
                return self._generate_fallback("未能生成有效方案")

            # 方案评估
            ctx = self._execute_node("方案评估", 5, 5, ctx, [
                ("m6_evaluation", "Skill"),
            ])

            # 收敛控制（内部调用，不渲染为用户可见节点）
            decision = check_convergence(ctx)
            self.output_buffer.append(f"\n[编排器] 决策: {decision.action} - {decision.reason}\n")

            if decision.action == "TERMINATE":
                contradiction = ctx.contradiction_desc or "未识别矛盾"
                report = render_final_report(
                    ctx.question, contradiction, ctx.ranked_solutions, decision.reason
                )
                return "\n".join(self.output_buffer) + "\n" + report

            elif decision.action == "CLARIFY":
                return self._generate_clarification(decision.reason)

            elif decision.action == "CONTINUE":
                ctx.iteration += 1
                ctx.feedback = decision.feedback
                ctx.history_log.append({"max_ideality": ctx.max_ideality})
                ctx.principles = []
                ctx.cases = []
                ctx.solution_drafts = []
                ctx.ranked_solutions = []
                ctx.max_ideality = 0.0
                ctx.unresolved_signals = []

    def _execute_node(self, node_name: str, current: int, total: int,
                      ctx: WorkflowContext, steps: list) -> WorkflowContext:
        """执行一个用户可见节点，渲染 Markdown 输出。

        steps 格式: [(step_name, step_type), ...] 或 [(step_name, step_type, tool_func), ...]
        """
        self.output_buffer.append(render_node_start(node_name, current, total))

        for step in steps:
            if len(step) == 2:
                step_name, step_type = step
                step_func = None
            else:
                step_name, step_type, step_func = step

            if step_name == "m2_causal":
                if not should_trigger_m2(ctx):
                    self.output_buffer.append(f"- Tool: M2 门控 -> 跳过（无负面功能）\n")
                    continue

            if step_type == "Skill":
                result = self.skill_runner.run(step_name, ctx)
            else:
                result = step_func(ctx)

            # FOS search_cases 返回 list[Case]，需要包装为 dict
            if isinstance(result, list):
                result = {"cases": result}

            ctx = self._merge_result(ctx, result)
            self.output_buffer.append(render_step_complete(step_name, step_type, result))

        self.output_buffer.append(render_node_complete(node_name, ctx))
        return ctx

    def _merge_result(self, ctx: WorkflowContext, result: dict) -> WorkflowContext:
        """将模块输出合并到 WorkflowContext。"""
        for key, value in result.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
        return ctx

    def _generate_clarification(self, reason: str) -> str:
        return "\n".join(self.output_buffer) + f"\n\n**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"

    def _generate_fallback(self, reason: str) -> str:
        return "\n".join(self.output_buffer) + f"\n\n**流程中断**：{reason}\n\n建议：尝试用更具体的工程语言描述问题，或提供更多技术细节。"
```

### Step 2: 写 Orchestrator 重构测试

```python
# tests/test_orchestrator_refactor.py

import pytest
from triz.orchestrator import Orchestrator, _register_m4_tools
from triz.core.tool_registry import ToolRegistry


def test_register_m4_tools():
    """验证 M4 tools 注册正确"""
    registry = _register_m4_tools()
    tools = registry.list_tools()
    assert "query_parameters" in tools
    assert "query_matrix" in tools
    assert "query_separation" in tools
    assert len(tools) == 3


def test_orchestrator_initialization():
    """Orchestrator 能正确初始化"""
    orch = Orchestrator()
    assert orch.tool_registry is not None
    assert orch.skill_runner is not None
    assert isinstance(orch.tool_registry, ToolRegistry)
```

### Step 3: 运行 Orchestrator 测试

```bash
pytest tests/test_orchestrator_refactor.py -v
```
Expected: PASS

### Step 4: 运行完整测试套件

```bash
pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: 所有测试通过（除了可能依赖旧 skill 文件的测试）

### Step 5: 提交 Task 4

```bash
git add triz/orchestrator.py tests/test_orchestrator_refactor.py
git commit -m "feat(orchestrator): integrate Skill Runner and M4 sub-tools"
```

---

## Task 5: 清理旧文件并运行集成测试

**Files:**
- Delete: `triz/skills/m1_modeling.py`
- Delete: `triz/skills/m2_causal.py`
- Delete: `triz/skills/m5_generation.py`
- Delete: `triz/skills/m6_evaluation.py`
- Delete: `triz/tools/m4_solver.py`
- Modify: `tests/test_skills.py`（更新或删除）
- Modify: `tests/test_tools.py`（更新删除 M4 测试）

### Step 1: 删除旧 Skill 文件

```bash
git rm triz/skills/m1_modeling.py
git rm triz/skills/m2_causal.py
git rm triz/skills/m5_generation.py
git rm triz/skills/m6_evaluation.py
git rm triz/tools/m4_solver.py
```

### Step 2: 更新 tests/test_skills.py

原 `test_skills.py` 测试的是 `.py` skill 文件。这些 skill 现在变为 `.md` 文件，通过 Skill Runner 执行。

有两种选择：
1. 删除 `test_skills.py`，因为 Skill 的核心逻辑现在在 `.md` 中（由 LLM 执行）
2. 保留测试但改为测试 Skill Runner 的集成

选择方案 1：删除旧的 `test_skills.py`，因为 `.md` skill 的测试需要调用 LLM，属于集成测试范畴。

```bash
git rm tests/test_skills.py
```

### Step 3: 更新 tests/test_tools.py

删除 M4 solver 相关的测试（功能已拆分到 sub-tools 和 M4 skill）：

```python
# tests/test_tools.py - 删除以下测试：
# - test_solve_tech_contradiction_speed_shape
# - test_solve_phys_contradiction
# - test_solve_fallback_on_empty_matrix

# 保留以下测试：
# - test_formulate_tech_contradiction
# - test_formulate_phys_contradiction
# - test_formulate_fallback
# - test_convergence_terminate_signals_cleared
# - test_convergence_continue
# - test_convergence_high_ideality_terminate
# - test_convergence_clarify_low_ideality
# - test_convergence_max_iterations
# - test_m2_gate_trigger_with_harmful_sao
# - test_m2_gate_skip_all_useful
# - test_search_local_cases
# - test_search_returns_empty_when_no_match
```

修改后的 `tests/test_tools.py`：

```python
import pytest
import os
from triz.context import WorkflowContext, SAO, ConvergenceDecision
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m7_convergence import check_convergence
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.fos_search import search_cases
from triz.database.init_db import init_database


# --- M3 问题定型 ---

def test_formulate_tech_contradiction():
    ctx = WorkflowContext(question="test")
    ctx.root_param = "刀片磨损太快"
    ctx.key_problem = "摩擦热量过高导致接触面积问题"
    ctx.candidate_attributes = ["接触面积", "摩擦热"]
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]

    result = formulate_problem(ctx)
    assert result["problem_type"] == "tech"
    assert "磨损" in result["contradiction_desc"] or "摩擦" in result["contradiction_desc"]


def test_formulate_phys_contradiction():
    ctx = WorkflowContext(question="test")
    ctx.root_param = "接触面积既要大又要小"
    ctx.key_problem = "强度与摩擦的矛盾"
    ctx.candidate_attributes = ["接触面积"]
    ctx.sao_list = []

    result = formulate_problem(ctx)
    assert result["problem_type"] == "phys"
    assert "既要" in result["contradiction_desc"] or "大" in result["contradiction_desc"]


def test_formulate_fallback():
    ctx = WorkflowContext(question="test")
    ctx.root_param = ""
    ctx.key_problem = ""
    ctx.candidate_attributes = []
    ctx.sao_list = []

    result = formulate_problem(ctx)
    assert result["problem_type"] == "tech"
    assert result["contradiction_desc"] == "" or result["contradiction_desc"] == "未识别矛盾"


# --- M7 收敛控制 ---

def test_convergence_terminate_signals_cleared():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.7
    ctx.iteration = 1
    ctx.unresolved_signals = []
    ctx.history_log = [{"max_ideality": 0.5}]

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"
    assert "信号已清空" in decision.reason


def test_convergence_continue():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.5
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.3}]

    decision = check_convergence(ctx)
    assert decision.action == "CONTINUE"


def test_convergence_high_ideality_terminate():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.86
    ctx.iteration = 0
    ctx.unresolved_signals = ["方案风险过高: XX"]
    ctx.history_log = []

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"
    assert "较高水平" in decision.reason


def test_convergence_clarify_low_ideality():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.1
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.05}]

    decision = check_convergence(ctx)
    assert decision.action == "CLARIFY"


def test_convergence_max_iterations():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.7
    ctx.iteration = 5
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.6}, {"max_ideality": 0.65}, {"max_ideality": 0.7}]

    decision = check_convergence(ctx)
    assert decision.action == "TERMINATE"


# --- M2 门控 ---

def test_m2_gate_trigger_with_harmful_sao():
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="损坏", object="B", function_type="harmful")]
    assert should_trigger_m2(ctx) is True


def test_m2_gate_skip_all_useful():
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="切割", object="B", function_type="useful")]
    assert should_trigger_m2(ctx) is False


# --- FOS 跨界检索 ---

@pytest.fixture(scope="module", autouse=True)
def setup_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("data") / "test_triz.db"
    import triz.config
    import triz.database.init_db
    import triz.database.queries
    triz.config.DB_PATH = db_path
    triz.database.init_db.DB_PATH = db_path
    triz.database.queries.DB_PATH = db_path
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)


def test_search_local_cases():
    ctx = WorkflowContext(question="如何提高手术刀片耐用性")
    ctx.principles = [15, 28]
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]

    cases = search_cases(ctx)
    assert len(cases) > 0
    assert all(hasattr(c, "principle_id") for c in cases)


def test_search_returns_empty_when_no_match():
    ctx = WorkflowContext(question="test")
    ctx.principles = [999]
    ctx.sao_list = []

    cases = search_cases(ctx)
    local_cases = [c for c in cases if c.source == "本地库"]
    assert local_cases == []
```

### Step 4: 运行完整测试套件

```bash
pytest tests/ -v --ignore=tests/test_integration.py
```
Expected: ALL PASS

### Step 5: 运行集成测试（可选，需要 API key）

```bash
pytest tests/test_integration.py -v
```
Expected: PASS（验证端到端流程）

### Step 6: 提交 Task 5

```bash
git add tests/
git commit -m "refactor: remove old .py skills, update tests for new architecture"
```

---

## Self-Review

### 1. Spec Coverage

| 要求 | 实现任务 |
|------|----------|
| Skills 改为 .md 文件 | Task 3 |
| Skill 内部可决策调用 Tool | Task 1 (Skill Runner + Tool Registry) |
| M4 拆分为 Skill + sub-Tools | Task 2 + Task 3 |
| Orchestrator 使用新架构 | Task 4 |
| 运行时可见每个节点输出 | Task 4 (保留 Markdown 渲染) |
| 删除旧 .py skill 文件 | Task 5 |

### 2. Placeholder Scan

- 无 "TBD" / "TODO" / "implement later"
- 每个步骤包含完整代码
- 每个任务包含测试命令和预期输出

### 3. Type Consistency

- `SkillRunner.run()` 返回 `dict`，与旧 skill 函数一致
- `ToolRegistry.execute()` 接受 `dict` 参数，与 OpenAI function calling 格式一致
- Orchestrator `_merge_result` 逻辑不变，兼容新旧输出格式

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-22-triz-skill-md-refactor.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints for review

**Which approach?**
