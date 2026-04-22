# TRIZ 系统全面测试计划

## Context

当前 TRIZ 系统已完成核心功能开发（M1-M7 workflow），多模型配置已上线（M1/M2/M4=Qwen3.5-Plus, M5=DeepSeek-V3.2, M6=Kimi-K2.5）。现有 53 个单元测试覆盖了基础路径，但缺乏：

1. 真实 LLM 调用的稳定性验证（偶发性错误如 M5 递归问题）
2. 不同领域输入的覆盖
3. 边界/异常输入的降级行为
4. 对抗性输入的鲁棒性
5. 错误恢复路径（API 超时、空结果、网络中断）
6. CLI 交互和输出渲染

## Goal

通过 5 类测试全面暴露系统薄弱环节，收集数据指导下一步优化方向。

## Test Categories

### 1. 批量回归测试（Stress Test）

**目的**：暴露偶发性错误，统计各模块成功率。

**方法**：
- 选取 3 个代表性问题，每个连续跑 10 次
- 记录每次的成功/失败、失败环节（M1/M2/M3/M4/M5/M6/M7）、错误类型
- 统计：成功率、平均耗时、各节点失败率

**测试用例**：
| # | 问题 | 领域 | 选取理由 |
|---|------|------|---------|
| 1 | 汽车发动机噪音大，油耗高 | 机械 | M4 需匹配多组参数，Function Calling 压力大 |
| 2 | 手机电池续航短，用户需要轻薄手机 | 电子 | 此前触发过 M5 递归错误 |
| 3 | 建筑物抗震能力不足，建造成本高 | 土木 | M2 因果链较长 |

**执行脚本**：`scripts/stress_test.py`
**预期输出**：CSV/JSON 报告，包含每次运行的详细结果

### 2. 领域覆盖测试

**目的**：验证不同工程领域的问题是否都能产生逻辑通顺的方案。

**方法**：
- 准备 15 个跨领域问题（每个领域 2-3 个）
- 每个问题运行 1 次
- 人工检查最终方案是否与输入问题逻辑相关

**领域列表**：
1. 机械工程（轴承磨损、刀具耐用性）
2. 电子/电气（散热、电磁干扰）
3. 化工/材料（腐蚀、反应效率）
4. 软件/信息（系统延迟、数据安全）
5. 生物医学（手术器械、药物递送）
6. 能源/环境（污染、储能）
7. 交通/航天（阻力、重量）

**测试用例**（部分示例）：
- "如何提高手术刀片在多次使用后的锋利度"
- "化工反应器内壁腐蚀导致产品污染"
- "软件系统在高并发下响应延迟"
- "太阳能电池板在阴雨天效率过低"
- "飞机机翼需要轻薄但又要承受高压"

**执行脚本**：`scripts/domain_coverage_test.py`
**验证方式**：脚本运行后，对每个问题的 top-1 方案，人工或使用 LLM 判断"方案是否与问题相关"（是/否/部分）

### 3. 边界/异常输入测试

**目的**：验证系统对异常输入的降级行为，不崩溃、给出合理提示。

**测试用例**：
| # | 输入 | 预期行为 |
|---|------|---------|
| 1 | 空字符串 "" | M1 无法提取 SAO，触发 clarify |
| 2 | 超长文本（>2000 字） | 正常运行，不截断丢失信息 |
| 3 | 无意义文字 "asdfghjkl" | M1 无法建模，触发 clarify |
| 4 | 中文古诗/歌词 | 非工程问题，应 clarify 或给出低相关性方案 |
| 5 | 纯数字 "123456" | 无法建模，触发 clarify |
| 6 | 只有 emoji | 无法建模，触发 clarify |
| 7 | 英文问题 "How to reduce engine noise" | 正常处理（验证多语言支持） |
| 8 | 混合中英文 "如何提高car的fuel efficiency" | 正常处理 |
| 9 | 包含特殊字符/SQL 注入尝试 | 安全处理，不报错 |
| 10 | 反问句 "为什么我的手机电池不耐用？" | 正常转换为正向问题处理 |

**执行方式**：pytest 自动化测试 + 脚本批量运行

### 4. 对抗性输入测试

**目的**：测试系统是否会为与工程无关的问题生成"看似合理"但实则荒谬的方案。

**测试用例**：
| # | 输入 | 预期行为 |
|---|------|---------|
| 1 | "今天天气怎么样" | M6 给出极低 relevance_score，最终 clarify |
| 2 | "如何追女朋友" | 同上 |
| 3 | "1+1 等于几" | 同上 |
| 4 | "如何成为亿万富翁" | 同上 |
| 5 | "如何做饭更好吃" | 非工程问题，M6 应打低分 |
| 6 | "如何减肥" | 同上 |

**验证方式**：检查最终方案的 `problem_relevance_score`，预期 < 3，触发 clarify 或低 ideality。

### 5. 错误恢复路径测试

**目的**：验证系统在各环节出错时的恢复能力。

**测试用例**：
| # | 场景 | 模拟方法 | 预期行为 |
|---|------|---------|---------|
| 1 | API 超时 | mock client 抛出 TimeoutError | Orchestrator 捕获，返回空结果，workflow 继续（或硬终止） |
| 2 | API 返回非 JSON | mock client 返回纯文本 | SkillRunner._parse_result 提取 JSON 或抛出异常 |
| 3 | M1 返回空 sao_list | mock M1 返回 `{}` | Orchestrator 触发 clarify |
| 4 | M4 返回空 principles | mock M4 返回 `{}` | Orchestrator 触发 fallback |
| 5 | M5 返回空 solution_drafts | mock M5 返回 `{}` | Orchestrator 触发 fallback |
| 6 | M4 不调用 tools（ require_tool_calls=True 时） | mock 直接返回 JSON | SkillRunner 强制重试一次 |
| 7 | 数据库查询无结果 | 传入不存在的 param_id | query_matrix 返回 fallback principles |
| 8 | SerpApi 调用失败 | 删除 SERP_API_KEY | FOS search 静默失败，返回本地结果 |
| 9 | Skill .md 文件缺失 | 删除 skills/m1_modeling.md | FileNotFoundError，workflow 中断 |
| 10 | 多轮迭代（CONTINUE） | mock M7 返回 CONTINUE | 状态正确重置，iteration 递增，不泄露上轮数据 |

**执行方式**：pytest 自动化（mock API client、monkeypatch）

### 6. CLI 输出渲染测试

**目的**：验证 CLI 在各种事件下的显示是否正常。

**测试用例**：
| # | 场景 | 验证点 |
|---|------|--------|
| 1 | 正常 workflow 完成 | 所有节点显示、最终报告渲染 |
| 2 | M2 gate skip | "无负面功能" 提示显示正确 |
| 3 | step_error 事件 | 错误信息不破坏 UI 布局 |
| 4 | /save 命令 | 文件正确写入 |
| 5 | /show <node> 命令 | 正确显示指定节点历史 |
| 6 | /history 命令 | 历史列表正确显示 |
| 7 | 长文本输出 | Markdown 渲染不溢出 |

**执行方式**：pytest（mock console 输出，捕获 rich.renderables）

## Implementation Plan

### Task 1: 创建测试基础设施
- 创建 `scripts/` 目录存放批量测试脚本
- 创建 `scripts/stress_test.py`：批量运行同一问题多次，记录结果
- 创建 `scripts/domain_coverage_test.py`：批量运行领域问题集
- 创建 `scripts/boundary_test.py`：批量运行边界输入
- 创建 `scripts/adversarial_test.py`：批量运行对抗性输入
- 统一输出格式为 JSON，方便分析

### Task 2: 运行批量回归测试
- 执行 stress_test.py（3 个问题 x 10 次 = 30 次运行）
- 分析结果：成功率、失败分布、耗时

### Task 3: 运行领域覆盖测试
- 执行 domain_coverage_test.py（15 个问题）
- 收集最终方案，人工/LLM 判断相关性

### Task 4: 运行边界和对抗性测试
- 执行 boundary_test.py（10 个用例）
- 执行 adversarial_test.py（6 个用例）
- 验证系统是否正确降级

### Task 5: 补充 pytest 错误恢复测试
- 在 `tests/` 下新增 `test_error_recovery.py`
- 覆盖 API 超时、空结果、文件缺失、多轮迭代等场景
- 使用 monkeypatch + Mock 模拟各种错误

### Task 6: 补充 CLI 测试
- 在 `tests/test_cli.py` 中新增事件渲染测试
- 覆盖 node_start, step_error, decision 等事件

### Task 7: 汇总报告
- 汇总所有测试结果到一个 Markdown 报告
- 列出发现的问题、成功率统计、优化建议

## Verification

每个测试类别完成后：
1. 检查输出日志是否有未捕获的异常
2. 检查各模块成功率是否符合预期（>90% 为合格）
3. 检查降级行为是否优雅（不崩溃、有提示）

最终验证：
- 所有 pytest 测试通过：`pytest tests/ -v`
- 批量测试脚本运行成功，输出报告完整
