# M5 方案生成详细参考

## 四步流程详解

### 第一步：生成搜索词
基于用户问题、矛盾描述和发明原理，生成 3 个不同角度的搜索词：
1. **功能角度**：聚焦核心功能的专利（如"principle 15 dynamic cutting surgical"）
2. **原理角度**：聚焦发明原理的跨领域应用（如"principle 28 ultrasonic vibration mechanical replacement"）
3. **问题角度**：聚焦用户的具体问题（如"reduce noise without losing power efficiency"）

每个搜索词 3-8 个英文关键词，用空格分隔。不要用中文（Google Patents 不支持中文搜索）。

### 第二步：过滤搜索结果
系统会返回大量原始搜索结果。你需要：
- 评估每个结果与用户问题的相关性（1-5分）
- 只保留相关性 ≥ 3 的结果
- 为每个保留的结果写一句 relevance_reason（为什么相关）

### 第三步：提取关键模式
从过滤后的案例中，提取 2-3 个可迁移的工程模式（如"利用场效应代替机械接触"、"动态调节参数同时满足矛盾需求"）。

### 第四步：生成方案
基于发明原理、过滤后的案例和关键模式，生成具体方案。

约束：
1. 每个方案必须明确引用一个或多个发明原理编号
2. 方案必须具体、可执行，避免泛泛而谈（至少100字描述）
3. 参考过滤后的案例进行类比迁移
4. 优先使用用户已有的资源，避免引入新组件
5. 如果无法生成方案，solution_drafts 必须为空数组 []

## 示例

输入：
- 问题：如何减少手术刀对组织的损伤
- 发明原理：[15, 28]
- 矛盾描述：刀片锋利度提高导致组织损伤增加

输出：
```json
{
    "search_queries": [
        "principle 15 dynamic cutting force surgical blade",
        "principle 28 ultrasonic vibration cutting tissue",
        "minimize tissue damage precision cutting surgery"
    ],
    "filtered_cases": [
        {
            "principle_id": 15,
            "source": "Google Patents",
            "title": "Adaptive Force Surgical Scalpel",
            "description": "A surgical scalpel with embedded force sensors that dynamically adjust cutting pressure based on tissue resistance...",
            "function": "",
            "relevance_score": 5,
            "relevance_reason": "直接解决切割力与组织损伤的矛盾，通过动态调节实现精准切割"
        }
    ],
    "key_patterns": [
        "利用反馈控制动态调节切割参数",
        "超声波辅助切割可减少机械接触力"
    ],
    "solution_drafts": [
        {
            "title": "基于压电反馈的自适应手术刀系统",
            "description": "在手术刀片内嵌入微型压电传感器，实时检测切割阻力。当检测到组织硬度变化时，通过微控制器动态调节刀片振动频率和切割角度。低阻力区域（软组织）降低切割力以减少损伤，高阻力区域（疤痕/筋膜）增加切割力以保证效率。结合原理15（动态化）和原理28（机械系统替代），用电子反馈系统替代传统固定锋利度的刀片。预期组织损伤降低40-60%，切割精度提升。",
            "applied_principles": [15, 28],
            "resource_mapping": "利用现有手术刀结构，仅增加传感器和微控制器"
        }
    ]
}
```
