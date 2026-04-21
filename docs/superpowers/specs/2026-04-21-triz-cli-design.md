# TRIZ智能系统CLI - 架构设计文档

> 版本: v1.0
> 日期: 2026-04-21
> 状态: 已批准

---

## 1. 概述

### 1.1 目标

将 TRIZ（发明问题解决理论）workflow 实现为一个可运行的 CLI 工具，采用 Agent Skills + Tools 架构（不使用 LangGraph 等编排框架）。用户输入问题后，系统按节点执行并输出解决方案，每个节点的执行过程和输出对用户可见。

### 1.2 核心约束

1. **Agent Skills + Tools 架构**: LLM 推理模块封装为 Skill，确定性计算模块封装为 Tool，由编排器（Orchestrator）协调执行
2. **节点输出可见**: 运行时每个用户可见节点的输入输出以 Markdown 格式展示
3. **逻辑自洽**: 输入问题与输出方案需经大模型判断为逻辑通顺
4. **内部结构化**: 节点间数据流转使用 Python Pydantic 对象，对外展示时渲染为 Markdown

### 1.3 架构原则

- **对外合并，对内保留边界**: 用户可见节点数精简，内部模块保持独立职责
- **确定性节点与LLM节点分离**: Tool 做可靠计算，Skill 做语义推理
- **M7 收敛控制归编排器**: M7 不是用户可见节点，其决策逻辑作为 Tool 被编排器调用

---

## 2. 架构总览

### 2.1 用户可见节点（5个）

```
用户输入
  |
  v
[问题建模] (Skill+Skill+Tool, 内部 M1->M2->M3)
  |
  v
[矛盾求解] (Tool, 内部 M4)
  |
  v
[跨界检索] (Tool, 内部 FOS)
  |
  v
[方案生成] (Skill, 内部 M5)
  |
  v
[方案评估] (Skill, 内部 M6_LLM)
  |
  v
编排器内部 -> [M7 收敛控制] (Tool) -> CONTINUE / TERMINATE / CLARIFY
```

### 2.2 模块职责速查表

| 用户可见节点 | 内部模块 | 封装类型 | 核心职责 | LLM调用 |
|:---|:---|:---|:---|:---|
| **问题建模** | M1_功能建模 | **Skill** | 从自然语言提取 SAO、IFR、资源盘点 | Call #1 |
| | M2_根因分析 | **Skill** | RCA+因果链分析，定位根因节点和候选物理属性 | Call #2 |
| | M3_问题定型 | **Tool** | 从根因提取矛盾类型和矛盾描述（自然语言） | 无 |
| **矛盾求解** | M4_矛盾求解 | **Tool** | 双步参数映射匹配39参数ID，查矩阵/分离规则库 | 无 |
| **跨界检索** | FOS_检索 | **Tool** | 本地案例库查询 -> 不足时调用 Google Patent Search API | 无 |
| **方案生成** | M5_方案生成 | **Skill** | 将原理+跨界案例迁移到用户场景 | Call #3 |
| **方案评估** | M6_LLM评估 | **Skill** | 独立实例对草案做6维定性打标 + 量化排序 | Call #4 |
| *(不可见)* | M7_收敛控制 | **Tool** | 四重阈值判定，输出控制指令 | 无 |
| *(不可见)* | M2_门控 | **Tool** | 判断是否需要触发 M2（默认触发，仅当无SAO时跳过） | 无 |

---

## 3. 内部模块详细设计

### 3.1 M1_功能建模（Skill）

**职责**: 把用户问题拆解成结构化功能模型，为后续矛盾识别打地基。

**输入**:
- `question: str` - 用户原始问题
- `history: list[dict]` - 会话历史（交互模式时传递）

**核心逻辑**:
1. LLM 提取 S-A-O（Subject-Action-Object）三元组
2. 标记功能属性：Useful / Insufficient / Harmful
3. 盘点可用资源（物质、场、空间、时间、信息、功能）
4. 声明 IFR（理想最终结果）

**输出**:
- `sao_list: list[SAO]` - 功能三元组列表
- `resources: dict[str, list[str]]` - 按类型分类的资源
- `ifr: str` - 理想最终结果

**输出格式**: LLM 返回结构化 JSON，经 Pydantic `SAO` / `FunctionModelingOutput` 校验。

**边界处理**:
- 若 LLM 无法提取任何 SAO，直接返回 CLARIFY，提示用户补充信息
- 若提取的 SAO 为空或格式异常，重试 1 次后仍失败则返回 CLARIFY

### 3.2 M2_根因分析（Skill）

**职责**: 从 SAO 中的负面功能（Harmful/Insufficient）出发，执行 RCA+ 因果链分析，定位根因节点，并提取候选物理属性。

**门控**:
- 默认触发（只要有 SAO 中的负面功能就触发）
- 仅当 M1 输出为空或全为 Useful 功能时跳过

**输入**:
- `sao_list: list[SAO]`
- `resources: dict[str, list[str]]`

**核心逻辑**:
1. LLM 从负面功能出发构建因果链（3-4 层深度）
2. 追问"为什么"直到收敛到根因节点
3. 从根因节点提取候选物理属性（自然语言描述）

**输出**:
- `root_param: str` - 根因参数描述
- `key_problem: str` - 关键问题陈述
- `candidate_attributes: list[str]` - 候选物理属性列表（如 `["接触面积", "摩擦热", "切割强度"]`）
- `causal_chain: list[str]` - 因果链文本（用于展示）

**边界处理**:
- 因果链无法收敛时，编排器从 SAO 中的负面功能构造简化 fallback：
  ```python
  harmful_sao = find_first_harmful_sao(sao_list)
  fallback_root_param = f"{harmful_sao.subject}的{harmful_sao.action}导致{harmful_sao.object}受损"
  fallback_key_problem = f"{harmful_sao.action}过度"
  fallback_candidate_attributes = [harmful_sao.action, harmful_sao.object]
  ```
- RCA 结果与 M1 SAO 矛盾时，优先采信 RCA 结果（根因更准确）

### 3.3 M3_问题定型（Tool）

**职责**: 确定性模块，从 M2 的根因输出中提取矛盾类型和矛盾描述（自然语言），不做参数ID映射。

**输入**:
- `root_param: str`
- `key_problem: str`
- `candidate_attributes: list[str]`
- `sao_list: list[SAO]`

**核心逻辑**:

```python
# Step 1: 识别矛盾类型
if "既要" in root_param or "又要" in root_param or "同时" in key_problem:
    problem_type = "phys"
else:
    problem_type = "tech"  # 默认技术矛盾

# Step 2: 提取矛盾描述（自然语言）
if problem_type == "tech":
    # 从 root_param / key_problem 中提取改善方向和恶化方向
    # 例如："改善速度导致形状稳定性下降"
    contradiction_desc = extract_tech_contradiction(root_param, key_problem)
elif problem_type == "phys":
    # 从 root_param 中提取"既要...又要..."
    # 例如："接触面积既要大又要小"
    contradiction_desc = extract_phys_contradiction(root_param)
```

**输出**:
- `problem_type: Literal["tech", "phys"]` - 技术矛盾或物理矛盾
- `contradiction_desc: str` - 矛盾的自然语言描述
  - 技术矛盾示例：`"改善速度，恶化形状稳定性"`
  - 物理矛盾示例：`"接触面积既要大（保证强度）又要小（减少摩擦热）"`
- `evidence: list[str]` - 支持证据（来自因果链）

**边界处理**:
- 矛盾类型无法判定（root_param 语义模糊）时，默认 `problem_type="tech"`
- 矛盾描述提取失败时，fallback 使用 root_param 原文作为描述

### 3.4 M4_矛盾求解（Tool）

**职责**: 接收 M3 的矛盾描述，通过双步参数映射精确匹配到 39 个工程参数 ID，然后查表获取发明原理。

**输入**:
- `problem_type: Literal["tech", "phys"]`
- `contradiction_desc: str` - 矛盾的自然语言描述
- `candidate_attributes: list[str]` - M2 提取的候选物理属性

**核心逻辑（双步参数映射）**:

```python
# Step 1: 从矛盾描述中解析改善/恶化参数（自然语言）
if problem_type == "tech":
    improve_attr = parse_improve_param(contradiction_desc)   # "速度"
    worsen_attr = parse_worsen_param(contradiction_desc)     # "形状稳定性"
    
    # 用 candidate_attributes 辅助消歧
    improve_attr = disambiguate(improve_attr, candidate_attributes)
    worsen_attr = disambiguate(worsen_attr, candidate_attributes)
    
    # Step 2: 余弦相似度匹配到 39 参数 ID
    improve_param_id = match_param_id(improve_attr)   # -> 9
    worsen_param_id = match_param_id(worsen_attr)     # -> 12
    
    # Step 3: 查阿奇舒勒矩阵
    principles = matrix[improve_param_id][worsen_param_id]
    sep_type = None
    
elif problem_type == "phys":
    # 物理矛盾：提取"需要的状态"和"不需要的状态"
    need_state, need_not_state = parse_phys_states(contradiction_desc)
    
    # 判定分离类型（空间/时间/条件/系统）
    sep_type = classify_separation(need_state, need_not_state)
    
    # 查分离规则库
    principles = separation_rules[sep_type]
```

**参数匹配算法**:
```python
def match_param_id(attribute: str) -> int:
    """将自然语言属性匹配到 39 参数 ID"""
    # 加载预计算的参数向量
    param_vectors = load_param_embeddings()  # {param_id: vector}
    
    # 将属性文本转为向量
    attr_vector = embed_text(attribute)
    
    # 余弦相似度匹配
    best_match = max(
        param_vectors.items(),
        key=lambda kv: cosine_similarity(attr_vector, kv[1])
    )
    
    return best_match[0]  # param_id
```

**输出**:
- `principles: list[int]` - 发明原理编号列表
- `sep_type: str | None` - 分离类型（物理矛盾时）
- `match_conf: float` - 参数匹配置信度
- `improve_param_id: int | None` - 改善参数ID（技术矛盾时）
- `worsen_param_id: int | None` - 恶化参数ID（技术矛盾时）
- `need_state: str | None` - 需要的状态（物理矛盾时）
- `need_not_state: str | None` - 不需要的状态（物理矛盾时）

**数据库依赖**: SQLite `parameters` 表（id, name, description, embedding_json），`matrix` 表，`separation_rules` 表

**边界处理**:
- 参数相似度低于阈值（0.6）时，fallback 到预定义的关键词映射表
- 矩阵单元格为空时，返回该参数行/列的 top-3 高频原理
- 物理矛盾分离类型无法判定时，返回所有分离类型对应的原理并集

### 3.5 FOS_跨界检索（Tool）

**职责**: 根据原理 ID 和用户场景，检索跨行业可落地案例。

**分层检索策略**:

```python
# L1: 本地 SQLite cases 表查询
cases = query_local_cases(principles, function, context)

if len(cases) >= 3:
    return cases

# L2: Google Patent Search API 补充
patents = call_google_patent_api(
    query=construct_patent_query(principles, sao_list, domain_hint),
    max_results=10
)
cases.extend(patents_to_cases(patents))
return cases
```

**输入**:
- `principles: list[int]`
- `sao_list: list[SAO]` - 用于提取核心功能词
- `domain_hint: str` - 从用户问题推断的领域上下文

**输出**:
- `cases: list[Case]`
  - `principle_id: int`
  - `source: str` - 来源（"本地库" / "Google Patents: US1234567"）
  - `title: str`
  - `description: str` - 案例简述
  - `function: str` - 该案例实现的功能

**数据库依赖**: SQLite `cases` 表（MVP 阶段预置 100-200 条经典案例）

**外部依赖**: Google Patent Search API（可选，L1 不足时启用）

**边界处理**:
- API 调用失败时，仅返回本地案例，不中断流程
- 无任何案例召回时，返回空列表，M5 降级为直接原理迁移（无案例参照）

### 3.6 M5_方案生成（Skill）

**职责**: 将抽象原理和跨界案例迁移到用户场景，生成具体可执行的方案草稿。

**输入**:
- `principles: list[int]`
- `cases: list[Case]`
- `contradiction_desc: str`
- `resources: dict[str, list[str]]`
- `ifr: str`

**核心逻辑**:
1. 为每个 principle 生成一个方案草稿
2. Prompt 约束：必须使用"类比法"将跨界案例迁移到用户场景
3. 强制使用可用资源，优先系统内资源

**Prompt 关键约束**:
```
生成创新方案时遵循以下约束：
1. 每个方案必须明确引用一个或多个发明原理编号
2. 优先使用以下已有资源：{resources}
3. 参考以下跨界案例进行类比迁移：{cases}
4. 方案必须具体、可执行，避免泛泛而谈
5. 当前矛盾：{contradiction_desc}
6. 理想最终结果：{ifr}
```

**输出**:
- `solution_drafts: list[SolutionDraft]`
  - `title: str`
  - `description: str`
  - `applied_principles: list[int]`
  - `resource_mapping: str` - 资源使用说明

**输出格式**: LLM 返回结构化 JSON，经 Pydantic 校验。

**边界处理**:
- 生成空草稿时，返回 fallback 方案（"基于原理X的直接应用"）
- 方案描述过于泛泛（少于50字）时，要求 LLM 补充具体实现细节

### 3.7 M6_方案评估（Skill + Tool）

**职责**: 对方案草案做独立评审和量化排序。生成与评估严格隔离，M6 只读取 M5 的只读草稿，绝不参与生成。

**输入**:
- `solution_drafts: list[SolutionDraft]`
- `contradiction_desc: str`
- `resources: dict[str, list[str]]`
- `ifr: str`
- `domain_context: str`

**核心逻辑**:

**M6_LLM（Skill）- 定性评估与量化排序**:
- 使用独立 LLM 实例（temperature=0.1，与 M5 的 0.3 不同）
- 对每个草案做 6 维定性评估 + 直接输出理想度分数：
  - 技术可行性 feasibility（1-5）
  - 资源匹配度 resource_fit（1-5）
  - 创新性 innovation（1-5）
  - 独特性 uniqueness（1-5）
  - 风险等级 risk（low/medium/high/critical）
  - IFR 偏离原因 ifr_deviation（文本）
- LLM 基于上述评分综合计算理想度（0-1 浮点数），附带计算依据说明

**输出**:
- `ranked_solutions: list[Solution]`
  - `draft: SolutionDraft`
  - `tags: QualitativeTags`
  - `ideality_score: float`
  - `feasibility_flag: bool` - 硬规则拦截（如风险=critical 直接不可行）
  - `evaluation_rationale: str` - 评估依据摘要
- `max_ideality: float`
- `unresolved_signals: list[str]` - 仍未解决的问题信号（用于 M7 判断）

**边界处理**:
- LLM 理想度分数异常（>1.0 或 <0）时，归一化到 [0, 1]
- 所有方案 risk_level="critical" 时，标记为不可行，M7 返回 CONTINUE 重新迭代
- unresolved_signals 生成规则（由 M6 基于评估结果派生）：
  ```python
  unresolved_signals = []
  for solution in ranked_solutions:
      if solution.tags.risk_level in ["high", "critical"]:
          unresolved_signals.append(f"方案风险过高: {solution.draft.title}")
      if solution.tags.ifr_deviation_reason:
          unresolved_signals.append(f"偏离IFR: {solution.tags.ifr_deviation_reason}")
  # 若所有方案均存在未解决信号，取 top-3 最紧急的传入 M7
  ```

### 3.8 M7_收敛控制（Tool，编排器内部调用）

**职责**: 根据迭代状态做四重阈值判定，输出控制指令。

**输入**:
- `max_ideality: float` - 当前最高理想度
- `iteration: int` - 当前迭代次数
- `history_log: list[dict]` - 历次迭代的理想度变化
- `unresolved_signals: list[str]` - 未解决的问题信号

**核心逻辑（四重判定）**:

```python
1. 信号清空判定: if not unresolved_signals -> TERMINATE
2. 停滞判定: if iteration > 0 and max_ideality == history[-1].max_ideality -> TERMINATE
3. 收益递减判定: if iteration >= 2 and improvement_rate < 0.05 -> TERMINATE
4. 触达上限判定: if iteration >= max_iterations(5) -> TERMINATE
5. 若 max_ideality < min_threshold(0.3) -> CLARIFY（方案质量不足，需用户补充信息）
6. 否则 -> CONTINUE
```

**输出**:
- `action: Literal["CONTINUE", "TERMINATE", "CLARIFY"]`
- `reason: str` - 决策原因
- `feedback: str` - 若 CONTINUE，返回给 M3 的反馈信息

---

## 4. 编排器（Orchestrator）设计

### 4.1 职责

- 持有 `WorkflowContext`，管理整个执行流程
- 按序调用 Skill/Tool，传递结构化数据
- 每个用户可见节点执行后，渲染 Markdown 日志输出
- 调用 M7 做收敛判断，控制迭代循环

### 4.2 执行流程

```python
def run_workflow(question: str, history: list = None) -> str:
    ctx = WorkflowContext(question=question, history=history or [])

    # ===== 问题建模 =====
    ctx = execute_node("问题建模", ctx, [
        ("M1", m1_function_modeling, Skill),
        ("M2", m2_causal_analysis, Skill),  # 默认触发
        ("M3", m3_problem_formulation, Tool),
    ])
    if not ctx.sao_list:
        return generate_clarification("无法从问题中提取功能模型")

    # ===== 迭代主循环 =====
    while True:
        # 矛盾求解
        ctx = execute_node("矛盾求解", ctx, [
            ("M4", m4_contradiction_solver, Tool),
        ])

        if not ctx.principles:
            return generate_fallback("无法从矛盾定义中匹配到发明原理")

        # 跨界检索
        ctx = execute_node("跨界检索", ctx, [
            ("FOS", fos_cross_domain_search, Tool),
        ])

        # 方案生成
        ctx = execute_node("方案生成", ctx, [
            ("M5", m5_solution_generation, Skill),
        ])

        if not ctx.solution_drafts:
            return generate_fallback("未能生成有效方案")

        # 方案评估
        ctx = execute_node("方案评估", ctx, [
            ("M6_LLM", m6_solution_evaluation, Skill),
        ])

        # 收敛控制（内部调用，不渲染为用户可见节点）
        decision = m7_convergence_control(ctx)

        if decision.action == "TERMINATE":
            return format_final_output(ctx.ranked_solutions, decision.reason)
        elif decision.action == "CLARIFY":
            return generate_clarification(decision.reason)
        elif decision.action == "CONTINUE":
            ctx.iteration += 1
            # 仅重跑矛盾求解及后续节点，保留问题建模结果
            # feedback 注入 M5 方案生成，调整生成策略
            ctx.feedback = decision.feedback
```

### 4.3 节点执行与渲染

```python
def execute_node(node_name: str, ctx: WorkflowContext, steps: list) -> WorkflowContext:
    """执行一个用户可见节点，渲染 Markdown 输出"""
    render_node_start(node_name)

    for step_name, step_func, step_type in steps:
        result = step_func(ctx)
        ctx = merge_result(ctx, result)
        render_step_complete(step_name, step_type, result)

    render_node_complete(node_name, ctx)
    return ctx
```

---

## 5. 数据层设计（SQLite）

### 5.1 数据库文件

`data/triz_knowledge.db` - 首次运行时自动初始化。

### 5.2 表结构

```sql
-- 39个工程参数
CREATE TABLE parameters (
    id INTEGER PRIMARY KEY,  -- 1-39
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding_json TEXT  -- 预计算的向量(JSON数组)
);

-- 40个发明原理
CREATE TABLE principles (
    id INTEGER PRIMARY KEY,  -- 1-40
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    examples TEXT  -- JSON数组，典型应用案例
);

-- 阿奇舒勒矛盾矩阵
CREATE TABLE matrix (
    improve_param INTEGER,
    worsen_param INTEGER,
    principles TEXT,  -- JSON数组，如 [15, 28, 35]
    PRIMARY KEY (improve_param, worsen_param)
);

-- 分离原理规则库
CREATE TABLE separation_rules (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,  -- "空间"/"时间"/"条件"/"系统"
    condition TEXT NOT NULL,
    principles TEXT  -- JSON数组
);

-- 本地案例库（MVP预置）
CREATE TABLE cases (
    id INTEGER PRIMARY KEY,
    principle_id INTEGER,
    function TEXT NOT NULL,  -- 如"切割"、"固定"、"加热"
    context TEXT,  -- 如"轻量化"、"医疗"
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding_json TEXT
);

-- 执行日志（交互模式时用于历史查询）
CREATE TABLE execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    step_name TEXT,
    input_json TEXT,
    output_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 初始化数据

- `parameters` / `principles` / `matrix` / `separation_rules`：硬编码初始化（标准TRIZ数据）
- `cases`：MVP 阶段预置 100-200 条经典案例，按行业分类（医疗、航天、汽车、电子等）
- 所有 embedding 在初始化时预计算并存储

---

## 6. CLI 设计

### 6.1 命令行入口

```bash
# 单次执行模式
python -m triz "如何提高手术刀片的耐用性"

# 交互会话模式
python -m triz --interactive
# 或
python -m triz -i
```

### 6.2 交互模式命令集

| 命令 | 功能 |
|:---|:---|
| `<问题文本>` | 执行完整 workflow |
| `show <节点名>` | 查看指定节点的详细输出（如 `show 问题建模`） |
| `show all` | 查看所有节点输出 |
| `history` | 查看会话历史（所有执行记录） |
| `iterate` | 基于当前结果继续迭代（强制 CONTINUE） |
| `reset` | 清空当前上下文 |
| `exit` / `quit` | 退出会话 |

### 6.3 输出格式

每个用户可见节点输出结构化的 Markdown：

```markdown
## [节点 1/5] 问题建模
- M1 功能建模... (1.2s)
- M2 根因分析... (2.1s)
- M3 问题定型... (0.3s)

### M1 输出
- **SAO**:
  - [刀片] -> [切割] -> [组织] (Useful)
  - [摩擦] -> [磨损] -> [刀片] (Harmful)
- **IFR**: 刀片在无限切割组织时保持零磨损
- **资源**: {物质: [刀片, 组织], 场: [热场]}

### M2 输出
- **根因**: 接触面积过大导致摩擦热积累
- **候选属性**: ["接触面积", "摩擦热", "切割强度"]
- **因果链**: 刀片磨损 -> 摩擦热量过高 -> 接触面积大+切割时间长 -> 根因节点

### M3 输出
- **矛盾类型**: 技术矛盾
- **矛盾描述**: 改善速度，恶化形状稳定性
---
```

### 6.4 最终方案输出

```markdown
# TRIZ 解决方案报告

## 问题
如何提高手术刀片的耐用性

## 核心矛盾
改善「速度」-> 恶化「形状稳定性」

## 推荐方案（按理想度排序）

### 方案 1 [理想度: 0.78]
**原理**: #15 动态化, #28 机械系统替代
**标题**: 动态压力调节切割头
**描述**: 参考F1赛车动态悬挂设计，在刀片接触组织时根据组织密度实时调整接触压力...
**资源使用**: 利用系统内[热场]资源进行热切割辅助
**可行性**: 5/5 | 风险: low

### 方案 2 [理想度: 0.65]
...

## 跨界参考案例
- F1赛车悬挂系统（原理15）
- 半导体超声波切割（原理28）

## 评估依据
本轮迭代最高理想度 0.78，信号已清空，系统收敛。
```

---

## 7. 核心数据结构（Pydantic）

```python
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal

class SAO(BaseModel):
    subject: str
    action: str
    object: str
    function_type: Literal["useful", "harmful", "excessive", "insufficient"]

class Case(BaseModel):
    principle_id: int
    source: str
    title: str
    description: str
    function: str

class SolutionDraft(BaseModel):
    title: str
    description: str
    applied_principles: List[int]
    resource_mapping: str

class QualitativeTags(BaseModel):
    feasibility_score: int      # 1-5
    resource_fit_score: int     # 1-5
    innovation_score: int       # 1-5
    uniqueness_score: int       # 1-5
    risk_level: Literal["low", "medium", "high", "critical"]
    ifr_deviation_reason: str

class Solution(BaseModel):
    draft: SolutionDraft
    tags: QualitativeTags
    ideality_score: float       # LLM综合评分（0-1）
    evaluation_rationale: str   # 评分依据说明

class WorkflowContext(BaseModel):
    # 输入
    question: str
    history: List[Dict] = []

    # M1 输出
    sao_list: List[SAO] = []
    resources: Dict[str, List[str]] = {}
    ifr: str = ""

    # M2 输出
    root_param: Optional[str] = None
    key_problem: Optional[str] = None
    candidate_attributes: List[str] = []
    causal_chain: List[str] = []

    # M3 输出
    problem_type: Optional[Literal["tech", "phys"]] = None
    contradiction_desc: str = ""  # 矛盾自然语言描述
    evidence: List[str] = []  # 矛盾判定的支持证据（来自因果链）

    # M4 输出
    principles: List[int] = []
    sep_type: Optional[str] = None
    match_conf: float = 0.0
    improve_param_id: Optional[int] = None
    worsen_param_id: Optional[int] = None
    need_state: Optional[str] = None
    need_not_state: Optional[str] = None

    # FOS 输出
    cases: List[Case] = []

    # M5 输出
    solution_drafts: List[SolutionDraft] = []

    # M6 输出
    ranked_solutions: List[Solution] = []
    max_ideality: float = 0.0
    unresolved_signals: List[str] = []

    # 迭代控制
    iteration: int = 0
    history_log: List[Dict] = []
    feedback: str = ""

class ConvergenceDecision(BaseModel):
    action: Literal["CONTINUE", "TERMINATE", "CLARIFY"]
    reason: str
    feedback: str = ""
```

---

## 8. 边界处理汇总

| 场景 | 处理策略 |
|:---|:---|
| M1 无法提取 SAO | 返回 CLARIFY，提示用户补充信息 |
| M2 因果链无法收敛 | 以 M1 表面矛盾作为 fallback |
| M3 矛盾类型无法判定 | 默认 `problem_type="tech"` |
| M3 矛盾描述提取失败 | fallback 使用 root_param 原文 |
| M4 参数相似度低于阈值 | fallback 到关键词映射表 |
| M4 矩阵单元格为空 | 返回行/列 top-3 高频原理 |
| M4 物理矛盾分离类型不明 | 返回所有分离类型原理并集 |
| FOS 本地案例不足 | 调用 Google Patent Search API |
| FOS API 调用失败 | 仅返回本地案例，不中断流程 |
| M5 生成空草稿 | 返回 fallback 直接应用方案 |
| M5 方案过于泛泛 | 要求 LLM 补充具体实现细节 |
| M6 所有方案风险=critical | M7 返回 CONTINUE 重新迭代 |
| M7 理想度低于阈值 | 返回 CLARIFY |
| 迭代超过最大次数(5) | 强制 TERMINATE，返回当前最优 |
| OpenAI API 失败 | 重试 3 次后退出，保留已执行节点日志 |

---

## 9. 技术栈

| 层级 | 技术 |
|:---|:---|
| 语言 | Python 3.11+ |
| LLM API | OpenAI (GPT-4o / GPT-4o-mini) |
| 数据结构 | Pydantic v2 |
| 数据库 | SQLite |
| 向量计算 | NumPy + 预计算 embedding |
| CLI 框架 | Python `argparse` + 自定义交互循环 |
| 外部 API | SerpApi (Google Patents) |
| 日志/展示 | 标准输出 Markdown 渲染 |

---

## 10. 目录结构（预期）

```
triz/
|-- __init__.py
|-- __main__.py              # CLI 入口
|-- cli.py                   # 命令行解析 + 交互循环
|-- orchestrator.py          # 编排器核心
|-- context.py               # WorkflowContext + 数据模型
|-- config.py                # 配置管理（API Key、模型名等）
|-- skills/                  # Skill 模块（LLM调用）
|   |-- __init__.py
|   |-- m1_modeling.py
|   |-- m2_causal.py
|   |-- m5_generation.py
|   |-- m6_evaluation.py
|-- tools/                   # Tool 模块（确定性计算）
|   |-- __init__.py
|   |-- m2_gate.py
|   |-- m3_formulation.py
|   |-- m4_solver.py
|   |-- m7_convergence.py
|   |-- fos_search.py
|-- database/                # 数据库层
|   |-- __init__.py
|   |-- init_db.py           # 数据库初始化
|   |-- triz_data.py         # TRIZ 标准数据（参数、原理、矩阵）
|   |-- queries.py           # 查询接口
|-- utils/                   # 工具函数
|   |-- __init__.py
|   |-- markdown_renderer.py # Markdown 渲染
|   |-- vector_math.py       # 余弦相似度计算
|   |-- api_client.py        # OpenAI / Google API 客户端
|-- data/
|   |-- triz_knowledge.db    # SQLite 数据库
```

---

## 附录：39个工程参数列表

| ID | 参数名（英文） | 参数名（中文） |
|:---|:---|:---|
| 1 | Weight of moving object | 运动物体的重量 |
| 2 | Weight of stationary object | 静止物体的重量 |
| 3 | Length of moving object | 运动物体的长度 |
| 4 | Length of stationary object | 静止物体的长度 |
| 5 | Area of moving object | 运动物体的面积 |
| 6 | Area of stationary object | 静止物体的面积 |
| 7 | Volume of moving object | 运动物体的体积 |
| 8 | Volume of stationary object | 静止物体的体积 |
| 9 | Speed | 速度 |
| 10 | Force | 力 |
| 11 | Stress or pressure | 应力或压力 |
| 12 | Shape | 形状 |
| 13 | Stability of the object's composition | 物体结构的稳定性 |
| 14 | Strength | 强度 |
| 15 | Durability of moving object | 运动物体的耐用性 |
| 16 | Durability of stationary object | 静止物体的耐用性 |
| 17 | Temperature | 温度 |
| 18 | Illumination intensity | 照度 |
| 19 | Energy spent by moving object | 运动物体消耗的能量 |
| 20 | Energy spent by stationary object | 静止物体消耗的能量 |
| 21 | Power | 功率 |
| 22 | Loss of energy | 能量损失 |
| 23 | Loss of substance | 物质损失 |
| 24 | Loss of information | 信息损失 |
| 25 | Loss of time | 时间损失 |
| 26 | Quantity of substance/the matter | 物质的量 |
| 27 | Reliability | 可靠性 |
| 28 | Measurement accuracy | 测量精度 |
| 29 | Manufacturing precision | 制造精度 |
| 30 | External harm affects the object | 作用于物体的外部有害因素 |
| 31 | Harmful side effects | 有害的副作用 |
| 32 | Manufacturability | 可制造性 |
| 33 | Ease of use | 使用的便利性 |
| 34 | Ease of repair | 修理的便利性 |
| 35 | Adaptability/Versatility | 适应性/通用性 |
| 36 | Device complexity | 装置的复杂性 |
| 37 | Difficulty of detecting and measuring | 检测和测量的困难 |
| 38 | Extent of automation | 自动化程度 |
| 39 | Productivity/Capacity | 生产率/产能 |

---

> 本文档经设计讨论后定稿，涵盖了 TRIZ 智能系统 CLI 的完整架构设计。下一步将进入实现计划制定阶段。
