---
name: m6_evaluation
description: >
  当需要评估方案质量、筛选最优解、决定是否需要迭代改进时使用。
version: "1.0"
gotchas:
  - 评分必须有区分度，不能所有方案都给 3 分
  - problem_relevance_score 必须与用户原始问题对比，而非中间矛盾描述
  - 非工程问题的 relevance_score 必须 ≤ 2
---

# M6 方案评估

## 描述
独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。

## 输出格式
直接输出以下 JSON 格式（注意：`ideality_score` 和 `max_ideality` 由系统自动计算，不需要你输出）：

```json
{
    "ranked_solutions": [
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
            "problem_relevance_score": 4,
            "logical_consistency_score": 5,
            "evaluation_rationale": "评分依据说明"
        }
    ],
    "unresolved_signals": []
}
```

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

**注意**：`ideality_score` 由系统自动计算（脚本），你只需输出原始评分。`max_ideality` 也由系统自动填充。

## 其他要求

- 必须输出包含 ranked_solutions 的 JSON 对象
- title/description/applied_principles/resource_mapping 必须原样复制输入的方案信息
- 所有评分字段都必须存在，不能省略
- max_ideality 取 ranked_solutions 中最高 ideality_score
- unresolved_signals: 收集所有风险为 high/critical 的方案标题，以及 ifr_deviation_reason 非空的记录，以及 problem_relevance_score < 3 的记录，以及 logical_consistency_score < 3 的记录

【重要】直接输出 JSON，不要输出任何其他内容。

## Gotchas（常见陷阱）

1. **评分趋中**：LLM 倾向于给所有方案都打 3 分 → 必须有区分度，好方案 4-5 分，差方案 1-2 分
2. **对比对象错误**：problem_relevance_score 必须与用户原始问题（ctx.question）对比，而非中间提取的矛盾描述
3. **非工程问题未识别**：如果用户问的是"今天天气怎么样"之类的问题，relevance_score 必须 ≤ 2
4. **原理应用未验证**：方案说用了原理 15（动态化），但描述中没有动态调整的内容 → logical_consistency_score 应打低分
5. **title/description 未原样复制**：ranked_solutions 中的 title/description 必须与输入的 solution_drafts 一致
