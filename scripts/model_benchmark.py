"""模型评测脚本：测试各模型在 TRIZ 各模块任务上的表现。

测试维度：
1. JSON 模式合规性 — 能否输出纯 JSON
2. 结构化输出 — 能否按 schema 输出
3. 中文质量 — 中文表达是否自然准确
4. 推理能力 — 因果推理、评分区分度
5. 延迟 — 首 token 时间 + 总耗时
"""
import json
import time
import sys
from openai import OpenAI

# ── 配置 ──────────────────────────────────────────────────────────────
API_KEY = "sk-Hnuk2fq0lebL2rTF9q4TBw"
BASE_URL = "https://xplt.sdu.edu.cn:4000/v1"

MODELS = {
    # 本地部署
    "local/DeepSeek-V4-Flash": "SDU-AI/DeepSeek-V4-Flash",
    "local/GLM-5": "SDU-AI/GLM-5",
    "local/Qwen3-235B": "SDU-AI/Qwen3-235B-A22B-Instruct-2507",
    # 阿里云部署
    "cloud/DeepSeek-V3.2": "Ali-dashscope/DeepSeek-V3.2",
    "cloud/Kimi-K2.5": "Ali-dashscope/Kimi-K2.5",
    "cloud/Qwen3.5-Plus": "Ali-dashscope/Qwen3.5-Plus",
    "cloud/Qwen3.6-Plus": "Ali-dashscope/Qwen3.6-Plus",
    "cloud/Qwen3-Max": "Ali-dashscope/Qwen3-Max",
}

# ── 测试用例 ──────────────────────────────────────────────────────────

TESTS = [
    # ── Test 1: JSON 模式 (M1 难度) ──
    {
        "name": "T1_JSON基础",
        "desc": "M1 难度：提取 SAO + 资源盘点",
        "task": "json_schema",
        "system": "你是一个TRIZ功能分析专家。请严格按JSON格式输出。",
        "prompt": """分析以下工程问题，提取功能模型：

问题：汽车发动机在高速运转时产生过大噪音，影响驾驶舒适性。

请输出JSON：
{
  "sao_list": [{"subject":"...","action":"...","object":"...","function_type":"useful/harmful/excessive/insufficient"}],
  "resources": {"material":[],"energy":[],"information":[],"space":[],"time":[],"function":[]},
  "ifr": "理想最终结果描述"
}""",
        "schema": {
            "sao_list": "list[dict] with keys: subject, action, object, function_type",
            "resources": "dict with 6 keys",
            "ifr": "str"
        },
        "temperature": 0.1,
    },

    # ── Test 2: JSON 模式 (M5 难度 - 复杂嵌套) ──
    {
        "name": "T2_JSON复杂",
        "desc": "M5 难度：生成方案草稿（多层嵌套+长文本）",
        "task": "json_schema",
        "system": "你是一个TRIZ创新方案生成专家。请严格按JSON格式输出。",
        "prompt": """基于以下信息生成2个解决方案草稿：

矛盾：需要提高发动机散热效率（改善），但不能增加噪音（恶化）。
发明原理：[15 动态化, 35 参数变化, 28 机械系统替代]
相关专利：US20200123456 - 使用可变几何形状的散热通道

每个方案描述必须≥100字。

请输出JSON：
{
  "solution_drafts": [
    {
      "title": "方案标题",
      "description": "≥100字的方案描述",
      "applied_principles": [15, 35],
      "resource_mapping": "如何利用可用资源"
    }
  ]
}""",
        "schema": {
            "solution_drafts": "list[dict] with 4 keys, description>=100 chars"
        },
        "temperature": 0.4,
    },

    # ── Test 3: 因果推理 (M2) ──
    {
        "name": "T3_因果推理",
        "desc": "M2 难度：构建3-4层因果链",
        "task": "reasoning",
        "system": "你是一个工程问题因果分析专家。",
        "prompt": """分析以下问题的因果链（至少3层"为什么"）：

负面功能：发动机冷却液在高温工况下性能下降，导致散热不足。

请输出JSON：
{
  "root_param": "根因参数（物理量）",
  "causal_chain": ["第1层为什么→...", "第2层为什么→...", "第3层为什么→..."],
  "candidate_attributes": ["物理属性1", "物理属性2"]
}""",
        "schema": {
            "root_param": "str - 物理参数",
            "causal_chain": "list[str] - 3+ layers",
            "candidate_attributes": "list[str] - 物理属性"
        },
        "temperature": 0.3,
    },

    # ── Test 4: 简洁结构化 (M3) ──
    {
        "name": "T4_简洁结构化",
        "desc": "M3 难度：翻译为矛盾对（极简输出）",
        "task": "json_schema",
        "system": "你是一个TRIZ矛盾定义专家。",
        "prompt": """将以下根因分析转化为TRIZ矛盾：

根因：冷却液粘度随温度升高而降低，导致流动性变好但密封性变差。
问题类型：物理矛盾

请输出JSON：
{
  "problem_type": "phys",
  "improve_desc": "改善方面描述（2-6个中文字）",
  "worsen_desc": "恶化方面描述（2-6个中文字）"
}""",
        "schema": {
            "problem_type": "str - 'tech' or 'phys'",
            "improve_desc": "str - 2-6 Chinese chars",
            "worsen_desc": "str - 2-6 Chinese chars"
        },
        "temperature": 0.1,
    },

    # ── Test 5: 评分区分度 (M6) ──
    {
        "name": "T5_评分区分度",
        "desc": "M6 难度：对3个方案打8维评分，要求有区分度",
        "task": "scoring",
        "system": "你是一个TRIZ方案评估专家。请对每个方案独立评分，确保分数有区分度（不能所有方案都打相同分数）。",
        "prompt": """评估以下3个方案：

方案A：使用压电材料将振动转化为电能，同时降低噪音。应用原理：能量转换。
方案B：在发动机外壳加装隔音棉。应用原理：隔离。
方案C：重新设计排气管路径，使气流远离驾驶舱。应用原理：空间分离。

请输出JSON：
{
  "ranked_solutions": [
    {
      "title": "方案标题",
      "tags": {
        "feasibility_score": 1-5,
        "resource_fit_score": 1-5,
        "innovation_score": 1-5,
        "uniqueness_score": 1-5,
        "risk_level": "low/medium/high/critical",
        "problem_relevance_score": 1-5,
        "logical_consistency_score": 1-5
      },
      "evaluation_rationale": "评分理由"
    }
  ]
}""",
        "schema": {
            "ranked_solutions": "list[3 dicts] with 7 score fields"
        },
        "temperature": 0.3,
    },

    # ── Test 6: Agent 决策 (ReAct) ──
    {
        "name": "T6_Agent决策",
        "desc": "Agent 模式：判断下一步调用哪个 Skill",
        "task": "react",
        "system": """你是一个TRIZ方法论Agent。根据当前工作状态，决定下一步行动。

可用Skills：
- m1_modeling: 功能建模（提取SAO、资源、IFR）
- m2_causal: 因果分析（构建因果链）
- m3_formulation: 矛盾定义（翻译为技术/物理矛盾）
- m5_generation: 方案生成（检索专利+生成方案）
- m6_evaluation: 方案评估（8维度评分）

输出格式：{"thought": "...", "action": "skill_name"}""",
        "prompt": """当前状态：
- 用户问题：手机电池续航不足
- 已完成：m1_modeling（SAO已提取）、m2_causal（因果链已构建）
- 未完成：m3_formulation、m5_generation、m6_evaluation

下一步应该做什么？""",
        "schema": {
            "thought": "str",
            "action": "str - one of the skill names"
        },
        "temperature": 0.2,
    },
]


# ── 评测引擎 ──────────────────────────────────────────────────────────

def run_test(client: OpenAI, model_id: str, test: dict) -> dict:
    """运行单个测试，返回结果。"""
    result = {
        "test": test["name"],
        "model": model_id,
        "latency_s": None,
        "raw_output": None,
        "json_valid": False,
        "schema_match": False,
        "scores": {},
        "error": None,
    }

    try:
        messages = [
            {"role": "system", "content": test["system"]},
            {"role": "user", "content": test["prompt"]},
        ]

        kwargs = {
            "model": model_id,
            "messages": messages,
            "temperature": test["temperature"],
            "timeout": 120,
        }
        # Test 5 (评分) 不强制 json_mode，让模型自由输出以测试自然 JSON 能力
        if test["task"] != "scoring":
            kwargs["response_format"] = {"type": "json_object"}

        t0 = time.time()
        response = client.chat.completions.create(**kwargs)
        latency = time.time() - t0

        content = response.choices[0].message.content or ""
        result["latency_s"] = round(latency, 2)
        result["raw_output"] = content[:2000]  # 截断保存

        # 检查 JSON 合规性
        parsed = _parse_json(content)
        result["json_valid"] = parsed is not None

        if parsed:
            result["schema_match"] = _check_schema(parsed, test["schema"])
            result["scores"] = _score_output(parsed, test)

    except Exception as e:
        result["error"] = str(e)[:500]

    return result


def _parse_json(text: str) -> dict | None:
    """尝试从文本中解析 JSON。"""
    text = text.strip()
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 提取 ```json ... ``` 代码块
    import re
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass
    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def _check_schema(parsed: dict, schema: dict) -> bool:
    """检查输出是否包含 schema 要求的字段。"""
    for key, expected_type in schema.items():
        if key not in parsed:
            return False
    return True


def _score_output(parsed: dict, test: dict) -> dict:
    """对输出质量打分（0-5）。"""
    scores = {}

    if test["name"] == "T1_JSON基础":
        # SAO 数量
        sao_list = parsed.get("sao_list", [])
        scores["sao_count"] = min(len(sao_list), 5)
        # function_type 合法性
        valid_types = {"useful", "harmful", "excessive", "insufficient"}
        types_ok = all(
            s.get("function_type") in valid_types
            for s in sao_list if isinstance(s, dict)
        )
        scores["type_validity"] = 5 if types_ok else 1
        # 资源完整性
        resources = parsed.get("resources", {})
        scores["resource_completeness"] = min(len(resources), 5)
        # IFR 存在
        scores["ifr_present"] = 5 if parsed.get("ifr") else 0

    elif test["name"] == "T2_JSON复杂":
        drafts = parsed.get("solution_drafts", [])
        scores["draft_count"] = min(len(drafts), 5)
        # 描述长度
        long_descs = sum(1 for d in drafts if len(d.get("description", "")) >= 100)
        scores["desc_length"] = min(long_descs * 3, 5)
        # 原理引用
        has_principles = all(d.get("applied_principles") for d in drafts)
        scores["principles_cited"] = 5 if has_principles else 1

    elif test["name"] == "T3_因果推理":
        chain = parsed.get("causal_chain", [])
        scores["chain_depth"] = min(len(chain), 5)
        attrs = parsed.get("candidate_attributes", [])
        scores["attributes_count"] = min(len(attrs), 5)
        scores["root_param_present"] = 5 if parsed.get("root_param") else 0

    elif test["name"] == "T4_简洁结构化":
        scores["problem_type_valid"] = 5 if parsed.get("problem_type") in ("tech", "phys") else 0
        imp = parsed.get("improve_desc", "")
        wor = parsed.get("worsen_desc", "")
        scores["improve_length"] = 5 if 2 <= len(imp) <= 6 else (3 if len(imp) <= 10 else 1)
        scores["worsen_length"] = 5 if 2 <= len(wor) <= 6 else (3 if len(wor) <= 10 else 1)

    elif test["name"] == "T5_评分区分度":
        solutions = parsed.get("ranked_solutions", [])
        scores["solution_count"] = min(len(solutions), 5)
        # 区分度：检查评分是否有差异
        if len(solutions) >= 2:
            feasibility_scores = [
                s.get("tags", {}).get("feasibility_score", 0)
                for s in solutions if isinstance(s, dict)
            ]
            if feasibility_scores:
                unique_scores = len(set(feasibility_scores))
                scores["score_diversity"] = min(unique_scores * 2, 5)
            else:
                scores["score_diversity"] = 0
        else:
            scores["score_diversity"] = 0

    elif test["name"] == "T6_Agent决策":
        scores["has_thought"] = 5 if parsed.get("thought") else 0
        valid_actions = {"m1_modeling", "m2_causal", "m3_formulation", "m5_generation", "m6_evaluation"}
        scores["valid_action"] = 5 if parsed.get("action") in valid_actions else 0
        # 检查是否选择了正确的下一步（m3_formulation）
        scores["correct_action"] = 5 if parsed.get("action") == "m3_formulation" else 1

    return scores


# ── 主程序 ──────────────────────────────────────────────────────────

def main():
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # 选择要测试的模型（可通过命令行参数指定）
    if len(sys.argv) > 1:
        model_keys = sys.argv[1:]
    else:
        model_keys = list(MODELS.keys())

    all_results = []

    for model_key in model_keys:
        if model_key not in MODELS:
            print(f"Unknown model: {model_key}")
            continue

        model_id = MODELS[model_key]
        print(f"\n{'='*60}")
        print(f"  测试模型: {model_key} ({model_id})")
        print(f"{'='*60}")

        for test in TESTS:
            print(f"\n  > {test['name']}: {test['desc']} ... ", end="", flush=True)
            result = run_test(client, model_id, test)
            all_results.append(result)

            if result["error"]:
                print(f"ERROR: {result['error'][:80]}")
            else:
                json_ok = "Y" if result["json_valid"] else "N"
                schema_ok = "Y" if result["schema_match"] else "N"
                latency = result["latency_s"]
                total_score = sum(result["scores"].values())
                max_score = len(result["scores"]) * 5
                print(f"JSON{json_ok} Schema{schema_ok} {latency}s 得分:{total_score}/{max_score}")

    # ── 汇总报告 ──
    print(f"\n\n{'='*80}")
    print("  模型评测汇总报告")
    print(f"{'='*80}")

    # 按模型汇总
    model_summary = {}
    for r in all_results:
        mk = r["model"]
        if mk not in model_summary:
            model_summary[mk] = {
                "json_pass": 0, "json_total": 0,
                "schema_pass": 0, "schema_total": 0,
                "total_score": 0, "max_score": 0,
                "avg_latency": [],
                "errors": 0,
            }
        s = model_summary[mk]
        s["json_total"] += 1
        s["schema_total"] += 1
        if r["json_valid"]:
            s["json_pass"] += 1
        if r["schema_match"]:
            s["schema_pass"] += 1
        if r["error"]:
            s["errors"] += 1
        else:
            s["total_score"] += sum(r["scores"].values())
            s["max_score"] += len(r["scores"]) * 5
            if r["latency_s"]:
                s["avg_latency"].append(r["latency_s"])

    # 打印表格
    print(f"\n{'模型':<25} {'JSON合规':>8} {'Schema匹配':>10} {'质量得分':>8} {'平均延迟':>8} {'错误':>4}")
    print("-" * 75)

    for mk, s in sorted(model_summary.items()):
        json_rate = f"{s['json_pass']}/{s['json_total']}"
        schema_rate = f"{s['schema_pass']}/{s['schema_total']}"
        quality = f"{s['total_score']}/{s['max_score']}" if s['max_score'] > 0 else "N/A"
        avg_lat = f"{sum(s['avg_latency'])/len(s['avg_latency']):.1f}s" if s['avg_latency'] else "N/A"
        print(f"{mk:<25} {json_rate:>8} {schema_rate:>10} {quality:>8} {avg_lat:>8} {s['errors']:>4}")

    # 保存详细结果
    output_path = "scripts/reports/model_benchmark.json"
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
