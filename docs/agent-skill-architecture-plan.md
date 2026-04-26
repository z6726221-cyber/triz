# Plan: 从 Prompt 模板 Skill 升级为真正的 Agent Skill

## Context

当前系统的 Skill 本质上是 `.md` 文件（system prompt），由通用的 `SkillRunner` 统一执行。所有 skill-specific 逻辑（M5 格式校验、M4 强制 tool calls、温度映射、模型映射）都硬编码在 `SkillRunner` 和 `Orchestrator` 中。用户明确要求："用真正的 Agent skill，而不是当前的虚假的 skill（Prompt 模板）"。

用户的独立分析（`架构相关问题.txt`）已明确几个关键判断：
- M1-M3 不建议合并（门控确定性更重要）
- 当前 Skill 只是 prompt 模板，不是真正的 Agent Skill
- 内部数据传输必须保留 JSON
- 保留硬编码编排器（TRIZ 需要确定性流程）
- **每个 Skill 一个文件夹**，包含 `SKILL.md`（定义）+ `handler.py`（执行器）

## Goals

将 Skill 从"静态 prompt 模板"升级为"自包含的能力单元"：
1. 每个 Skill 是独立的 Python 类，包含自己的执行逻辑、验证逻辑、fallback 策略
2. Skill 有明确的输入/输出 Schema（Pydantic）
3. Skill 可以独立测试、独立迭代
4. Orchestrator 只负责编排流程，不硬编码 skill-specific 逻辑
5. SkillRegistry 负责动态发现和注册

## Architecture Design

### 1. Skill 基类（`triz/skills/base.py`）

```python
class Skill(ABC, Generic[InputT, OutputT]):
    name: str
    description: str
    version: str = "1.0"
    temperature: float = 0.3
    model: str | None = None
    max_retries: int = 1
    require_tool_calls: bool = False
    input_schema: Type[InputT]
    output_schema: Type[OutputT]

    @abstractmethod
    def execute(self, input_data: InputT, ctx: WorkflowContext) -> OutputT: ...
    def validate_output(self, raw: dict) -> OutputT: ...
    def fallback(self, input_data: InputT, error: Exception, ctx: WorkflowContext) -> OutputT | None: ...
    def _load_prompt(self) -> str: ...  # 从同级目录的 SKILL.md 加载
```

### 2. 具体 Skill 实现示例：M5GenerationSkill（`triz/skills/m5_generation.py`）

```python
class M5Input(BaseModel):
    question: str
    principles: list[int]
    cases: list[Case]
    contradiction_desc: str
    ifr: str
    resources: dict
    feedback: str = ""

class M5Output(BaseModel):
    solution_drafts: list[SolutionDraft]

class M5GenerationSkill(Skill[M5Input, M5Output]):
    name = "solution_generation"
    description = "基于发明原理生成解决方案草案"
    temperature = 0.4
    model = MODEL_M5
    input_schema = M5Input
    output_schema = M5Output

    def execute(self, input_data: M5Input, ctx: WorkflowContext) -> M5Output:
        system_prompt = self._load_prompt()  # 加载 m5_generation.md
        user_prompt = self._build_prompt(input_data)
        response = self._call_llm(system_prompt, user_prompt, json_mode=True)
        raw = self._parse_json(response)

        # M5 特有：检查 solution_drafts 存在
        if "solution_drafts" not in raw:
            raw = self._retry_for_format(input_data, user_prompt)

        return self.validate_output(raw)

    def fallback(self, input_data, error, ctx) -> M5Output:
        # M5 特有的 fallback：基于 principles 生成简化方案
        drafts = [...]
        return M5Output(solution_drafts=drafts)
```

### 3. SkillRegistry（`triz/skills/registry.py`）

```python
class SkillRegistry:
    def __init__(self, tool_registry: ToolRegistry | None = None):
        self._skills: dict[str, Skill] = {}
        self.tool_registry = tool_registry
        self._discover()

    def _discover(self):
        # 遍历 triz/skills/ 下的子文件夹，import 各 handler.py 并实例化

    def register(self, skill: Skill): ...
    def get(self, name: str) -> Skill | None: ...
    def list_skills(self) -> list[dict]: ...
```

### 4. Orchestrator 调整

- 移除 `SKILL_MODEL_MAP`（模型配置移到 Skill 类自身）
- 移除 `skill_runner`（替换为 `skill_registry`）
- 移除 `_execute_node` 中的 skill-specific 条件（如 `require_tools = step_name == "m4_solver"`）
- `_execute_node` 统一调用 `skill.execute()`，skill 自身决定是否用 tools

### 5. M4 Solver Skill 的特殊处理

M4 是唯一需要 tool calling 的 Skill。`M4SolverSkill` 内部管理多轮 tool calling 对话（当前这部分逻辑在 `SkillRunner.run()` lines 78-107），不再需要 `SkillRunner` 介入。

## 文件变更清单

### 新增文件
1. `triz/skills/__init__.py` - 包初始化
2. `triz/skills/base.py` - Skill 基类、LLM 调用辅助
3. `triz/skills/registry.py` - SkillRegistry
4. `triz/skills/m1_modeling/handler.py` - M1 Skill 执行器
5. `triz/skills/m2_causal/handler.py` - M2 Skill 执行器
6. `triz/skills/m3_formulation/handler.py` - M3 Skill 执行器
7. `triz/skills/m4_solver/handler.py` - M4 Skill 执行器（含 tool calling）
8. `triz/skills/m5_generation/handler.py` - M5 Skill 执行器
9. `triz/skills/m6_evaluation/handler.py` - M6 Skill 执行器

### 文件移动（重命名）
将现有的 prompt 文件移入对应 Skill 文件夹并重命名为 `SKILL.md`：
1. `triz/skills/m1_modeling.md` → `triz/skills/m1_modeling/SKILL.md`
2. `triz/skills/m2_causal.md` → `triz/skills/m2_causal/SKILL.md`
3. `triz/skills/m3_formulation.md` → `triz/skills/m3_formulation/SKILL.md`
4. `triz/skills/m4_solver.md` → `triz/skills/m4_solver/SKILL.md`
5. `triz/skills/m5_generation.md` → `triz/skills/m5_generation/SKILL.md`
6. `triz/skills/m6_evaluation.md` → `triz/skills/m6_evaluation/SKILL.md`

### 修改文件
1. `triz/orchestrator.py` - 使用 SkillRegistry 替代 SkillRunner
2. `triz/context.py` - 为每个 Skill 定义独立的 Input/Output 模型（或保留在 Skill 模块中）

### 保留（暂不删除）
1. `triz/core/skill_runner.py` - 暂时保留，供过渡期间使用

## 最终目录结构

```
triz/skills/
├── __init__.py
├── base.py              # Skill 基类
├── registry.py          # SkillRegistry
├── m1_modeling/
│   ├── SKILL.md         # Skill 定义 / system prompt
│   └── handler.py       # Python 执行器
├── m2_causal/
│   ├── SKILL.md
│   └── handler.py
├── m3_formulation/
│   ├── SKILL.md
│   └── handler.py
├── m4_solver/
│   ├── SKILL.md
│   └── handler.py
├── m5_generation/
│   ├── SKILL.md
│   └── handler.py
└── m6_evaluation/
    ├── SKILL.md
    └── handler.py
```

## 迁移策略

增量迁移，逐步替换：
1. **Step 1**: 创建 `base.py` + `registry.py`，搭建框架
2. **Step 2**: 迁移 M1 Skill（最简单，无特殊逻辑），创建 `m1_modeling/` 文件夹，移动 `m1_modeling.md` → `m1_modeling/SKILL.md`，编写 `m1_modeling/handler.py`
3. **Step 3**: 迁移 M5 Skill（有格式校验和 fallback），验证 skill-specific 逻辑可正常工作
4. **Step 4**: 迁移 M4 Skill（有 tool calling），这是最复杂的
5. **Step 5**: 迁移 M2、M3、M6
6. **Step 6**: 调整 Orchestrator，全面使用 SkillRegistry
7. **Step 7**: 删除旧的 SkillRunner，清理根目录下的 `.md` 文件

## Verification

- 每个新 Skill 的单元测试：验证 execute() 返回正确的 Output Schema
- 集成测试：跑 normal_test 中的用例，确保输出质量不下降
- 对比测试：同一问题，新旧架构输出一致（或新架构更好）

## 当前状态

本计划覆盖架构设计。用户确认后，按 Step 1 开始实施。
