# M6 评分标准详细参考

## 评估维度详解

### 基础维度（评估方案质量）
1. **feasibility_score** (1-5): 技术可实现性
2. **resource_fit_score** (1-5): 资源匹配度
3. **innovation_score** (1-5): 创新性
4. **uniqueness_score** (1-5): 独特性
5. **risk_level** (low/medium/high/critical): 风险等级
6. **ifr_deviation_reason** (文本): 如果偏离 IFR，说明原因；否则留空

### 准入维度（评估方案资格）
7. **problem_relevance_score** (1-5): 方案与用户**原始问题**的匹配度（必须与 `ctx.question` 直接对比，而非中间提取的矛盾描述）
   - 5分：方案直接、明确地解决了用户提出的核心矛盾
   - 4分：方案与问题高度相关，但略有偏差
   - 3分：方案与问题相关，但不是最直接的路径
   - 2分：方案与问题有一定关联，但偏离较远
   - 1分：方案答非所问，与用户问题无关（特别是非工程问题硬套工程方案的情况）

8. **logical_consistency_score** (1-5): 方案内部逻辑一致性
   - 5分：方案描述自洽，发明原理被正确应用，因果链完整
   - 4分：方案基本自洽，但有小瑕疵
   - 3分：方案大体合理，但存在逻辑跳跃
   - 2分：方案存在明显逻辑矛盾或原理误用
   - 1分：方案自相矛盾，原理应用错误

## 交叉验证方法

对每个方案执行以下验证：

1. **问题-方案匹配验证（最重要）**：
   - **必须将方案与用户原始问题（`ctx.question`）直接对比，而不是与中间提取的"矛盾描述"对比**
   - 回答：这个方案是否解决了用户**实际提出的原始问题**？如果不，差距在哪里？
   - **对抗性示例**（这些输入不是工程问题，任何方案的 problem_relevance_score 必须 ≤ 2）：
     - 用户问"今天天气怎么样" → 方案讨论"天气监测传感器优化" → relevance_score = 1（答非所问）
     - 用户问"如何追女朋友" → 方案讨论"社交算法改进" → relevance_score = 1（非工程问题）
     - 用户问"1+1等于几" → 方案讨论"计算芯片架构" → relevance_score = 1（数学问题，非工程矛盾）
     - 用户问"如何成为亿万富翁" → 方案讨论"投资策略优化" → relevance_score = 1（非工程问题）
   - **判断标准**：如果原始问题不包含具体的技术对象（设备、材料、结构）或性能参数冲突，就是非工程问题，relevance_score 必须打低分

2. **原理-方案一致性验证**：
   - 检查方案中是否实际应用了 `applied_principles` 中列出的发明原理
   - 如果方案说用了原理15（动态化），但实际描述中没有动态调整的内容，逻辑一致性打低分

3. **因果链验证**：
   - 方案描述的因果关系是否成立？
   - 比如"用复合材料→提高耐磨性"是合理因果，但"改变颜色→提高强度"则不是

## 理想度计算

**注意**：`ideality_score` 现在由 `scripts/calculate_ideality.py` 自动计算，你只需输出原始评分。

计算公式（供参考）：
- feasibility_score: 20%
- resource_fit_score: 15%
- innovation_score: 15%
- uniqueness_score: 10%
- risk_level: 反向计算（low=5, medium=3, high=1, critical=0），权重 10%
- **problem_relevance_score: 20%** ← 权重最高
- **logical_consistency_score: 10%**

硬约束：
- 如果 problem_relevance_score < 3，ideality_score 最高不超过 0.5
- 如果 logical_consistency_score < 3，ideality_score 最高不超过 0.6
