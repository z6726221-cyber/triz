---
name: evaluation
description: >
  独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序并给出推荐。
  当用户说"评估方案"、"哪个方案最好"、"方案评分"、"理想度排序"、"需要迭代改进"时使用。
  Do NOT use when：尚未生成方案（方案生成未完成），或已给出评分且用户未要求重新评估，或仅有一个方案无需排序。
  详细评分标准见 references/scoring_rubric.md，按需使用 Read 工具读取。
version: "1.0"
gotchas:
  - 评分必须有区分度，不能所有方案都给 3 分
  - problem_relevance_score 必须与用户原始问题对比，而非中间矛盾描述
  - 非工程问题的 relevance_score 必须 <= 2
allowed-tools: ["Read", "Write", "Glob", "Grep"]
---

# 方案评估

## 任务
独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。

## 输入
你会收到用户问题和之前的分析结果（包括待评估的方案）。基于这些信息进行独立评估。

## 评估维度（8个）

1. **feasibility_score** (1-5): 技术可实现性
2. **resource_fit_score** (1-5): 资源匹配度
3. **innovation_score** (1-5): 创新性
4. **uniqueness_score** (1-5): 独特性
5. **risk_level** (low/medium/high/critical): 风险等级
6. **problem_relevance_score** (1-5): 方案与用户原始问题的匹配度（最重要，权重20%）
7. **logical_consistency_score** (1-5): 方案内部逻辑一致性（权重10%）
8. **ifr_deviation_reason**: 如果偏离 IFR，说明原因；否则留空

详细的评分标准和交叉验证方法，请参考 `references/scoring_rubric.md`。

## 输出格式

请输出以下 Markdown 内容：

### 方案评估

#### 方案 1：（标题）

| 维度 | 评分 |
|------|------|
| 技术可实现性 | X/5 |
| 资源匹配度 | X/5 |
| 创新性 | X/5 |
| 独特性 | X/5 |
| 风险等级 | low/medium/high/critical |
| 问题匹配度 | X/5 |
| 逻辑一致性 | X/5 |
| IFR偏离原因 | （无/原因说明） |

**评分依据**：（简要说明评分理由）

#### 方案 2：（标题）

...

### 综合排序

| 排名 | 方案 | 理想度 |
|------|------|--------|
| 1 | ... | ... |
| 2 | ... | ... |

### 未解决问题

- （风险为 high/critical 的方案）
- （偏离 IFR 的方案）
- （问题匹配度低的方案）

## 约束

- 评分必须有区分度，好方案 4-5 分，差方案 1-2 分
- problem_relevance_score 必须与用户原始问题对比，而非中间提取的矛盾描述
- 如果用户问的是非工程问题（如"今天天气怎么样"），relevance_score 必须 <= 2

## Gotchas（常见陷阱）

1. **评分趋中**：LLM 倾向于给所有方案都打 3 分 → 必须有区分度，好方案 4-5 分，差方案 1-2 分
2. **对比对象错误**：problem_relevance_score 必须与用户原始问题对比，而非中间提取的矛盾描述
3. **非工程问题未识别**：如果用户问的是非工程问题，relevance_score 必须 <= 2
4. **原理应用未验证**：方案说用了原理 15（动态化），但描述中没有动态调整的内容 → logical_consistency_score 应打低分

## 完整输出示例

如需查看完整输出示例，请使用 Read 工具读取 `references/examples.md`。
