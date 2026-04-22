# M6 方案评估

## 描述
独立评审方案草案，给出 8 维度量化评分和理想度，按理想度排序。

## 输出格式
直接输出以下 JSON 格式：

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
            "ideality_score": 0.78,
            "evaluation_rationale": "评分依据说明"
        }
    ],
    "max_ideality": 0.78,
    "unresolved_signals": []
}
```

## 评估维度（每个方案）

### 基础维度（评估方案质量）
1. **feasibility_score** (1-5): 技术可实现性
2. **resource_fit_score** (1-5): 资源匹配度
3. **innovation_score** (1-5): 创新性
4. **uniqueness_score** (1-5): 独特性
5. **risk_level** (low/medium/high/critical): 风险等级
6. **ifr_deviation_reason** (文本): 如果偏离 IFR，说明原因；否则留空

### 准入维度（评估方案资格）
7. **problem_relevance_score** (1-5): 方案与用户问题的匹配度
   - 5分：方案直接、明确地解决了用户提出的核心矛盾
   - 4分：方案与问题高度相关，但略有偏差
   - 3分：方案与问题相关，但不是最直接的路径
   - 2分：方案与问题有一定关联，但偏离较远
   - 1分：方案答非所问，与用户问题无关

8. **logical_consistency_score** (1-5): 方案内部逻辑一致性
   - 5分：方案描述自洽，发明原理被正确应用，因果链完整
   - 4分：方案基本自洽，但有小瑕疵
   - 3分：方案大体合理，但存在逻辑跳跃
   - 2分：方案存在明显逻辑矛盾或原理误用
   - 1分：方案自相矛盾，原理应用错误

### 交叉验证方法

对每个方案执行以下验证：

1. **问题-方案匹配验证**：
   - 将用户问题 + 核心矛盾 + 方案描述三者对比
   - 回答：这个方案是否解决了用户提出的问题？如果不，差距在哪里？

2. **原理-方案一致性验证**：
   - 检查方案中是否实际应用了 `applied_principles` 中列出的发明原理
   - 如果方案说用了原理15（动态化），但实际描述中没有动态调整的内容，逻辑一致性打低分

3. **因果链验证**：
   - 方案描述的因果关系是否成立？
   - 比如"用复合材料→提高耐磨性"是合理因果，但"改变颜色→提高强度"则不是

### 理想度计算

ideality_score = 加权平均
- feasibility_score: 20%
- resource_fit_score: 15%
- innovation_score: 15%
- uniqueness_score: 10%
- risk_level: 反向计算（low=5, medium=3, high=1, critical=0），权重 10%
- **problem_relevance_score: 20%** ← 权重最高
- **logical_consistency_score: 10%**

然后归一化到 0.0-1.0。

**重要规则**：
- 如果 problem_relevance_score < 3，ideality_score 最高不超过 0.5（答非所问的方案质量再高也不能给高分）
- 如果 logical_consistency_score < 3，ideality_score 最高不超过 0.6（逻辑不自洽的方案需要大幅扣分）

## 其他要求

- 必须输出包含 ranked_solutions 的 JSON 对象
- title/description/applied_principles/resource_mapping 必须原样复制输入的方案信息
- 所有评分字段都必须存在，不能省略
- max_ideality 取 ranked_solutions 中最高 ideality_score
- unresolved_signals: 收集所有风险为 high/critical 的方案标题，以及 ifr_deviation_reason 非空的记录，以及 problem_relevance_score < 3 的记录，以及 logical_consistency_score < 3 的记录

【重要】直接输出 JSON，不要输出任何其他内容。
