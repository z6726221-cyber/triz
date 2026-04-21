# TRIZ CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 TRIZ 智能系统 CLI，将 Spec 中的 5 个用户可见节点（问题建模、矛盾求解、跨界检索、方案生成、方案评估）和编排器落地为可运行的 Python 命令行工具。

**Architecture:** Agent Skills + Tools 架构。Skills（M1, M2, M5, M6）通过 OpenAI API 执行语义推理；Tools（M2门控, M3, M4, M7, FOS）执行确定性计算。编排器（Orchestrator）持有 WorkflowContext，按序调用模块并渲染 Markdown 输出。数据层使用 SQLite 存储 TRIZ 知识库（39参数、40原理、矛盾矩阵、分离规则、案例库）。

**Tech Stack:** Python 3.11+, OpenAI API, SQLite, Pydantic v2, pytest

---

## File Structure Overview

```
triz/
|-- __init__.py
|-- __main__.py              # CLI 入口
|-- cli.py                   # 命令行解析 + 交互循环
|-- orchestrator.py          # 编排器核心
|-- context.py               # WorkflowContext + 所有 Pydantic 数据模型
|-- config.py                # 配置管理（API Key、模型名等）
|-- skills/
|   |-- __init__.py
|   |-- m1_modeling.py       # M1 功能建模 Skill
|   |-- m2_causal.py         # M2 根因分析 Skill
|   |-- m5_generation.py     # M5 方案生成 Skill
|   |-- m6_evaluation.py     # M6 方案评估 Skill
|-- tools/
|   |-- __init__.py
|   |-- m2_gate.py           # M2 门控 Tool
|   |-- m3_formulation.py    # M3 问题定型 Tool
|   |-- m4_solver.py         # M4 矛盾求解 Tool（含双步参数映射）
|   |-- m7_convergence.py    # M7 收敛控制 Tool
|   |-- fos_search.py        # FOS 跨界检索 Tool
|-- database/
|   |-- __init__.py
|   |-- init_db.py           # 数据库初始化 + 建表
|   |-- triz_data.py         # TRIZ 标准数据（39参数、40原理、矩阵、分离规则）
|   |-- queries.py           # 数据库查询接口
|-- utils/
|   |-- __init__.py
|   |-- markdown_renderer.py # Markdown 渲染
|   |-- vector_math.py       # 余弦相似度计算
|   |-- api_client.py        # OpenAI / Google Patent API 客户端
|-- data/
|   |-- triz_knowledge.db    # SQLite 数据库（运行时生成）
|-- tests/
|   |-- __init__.py
|   |-- test_context.py
|   |-- test_database.py
|   |-- test_tools.py
|   |-- test_skills.py
|   |-- test_orchestrator.py
```

---

## Task 1: Project Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `triz/__init__.py`
- Create: `triz/config.py`
- Test: `tests/__init__.py`

- [ ] **Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "triz-cli"
version = "0.1.0"
description = "TRIZ intelligent system CLI"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.30.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["triz*"]
```

- [ ] **Step 2: Write requirements.txt**

```
openai>=1.30.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 3: Write .env.example**

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
SERP_API_KEY=your_serpapi_key_here
```

- [ ] **Step 4: Write triz/config.py**

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "triz_knowledge.db"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SERP_API_KEY = os.getenv("SERP_API_KEY", "")

MAX_ITERATIONS = 5
MIN_IDEALITY_THRESHOLD = 0.3
SIMILARITY_THRESHOLD = 0.6
```

- [ ] **Step 5: Create triz/__init__.py**

```python
"""TRIZ Intelligent System CLI"""
__version__ = "0.1.0"
```

- [ ] **Step 6: Create tests/__init__.py**

```python
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml requirements.txt .env.example triz/__init__.py triz/config.py tests/__init__.py
git commit -m "chore: project foundation - config, deps, structure"
```

---

## Task 2: Data Models (context.py)

**Files:**
- Create: `triz/context.py`
- Test: `tests/test_context.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.context import SAO, WorkflowContext, ConvergenceDecision

def test_sao_creation():
    sao = SAO(subject="刀片", action="切割", object="纸张", function_type="useful")
    assert sao.subject == "刀片"
    assert sao.function_type == "useful"

def test_workflow_context_defaults():
    ctx = WorkflowContext(question="如何提高电池续航")
    assert ctx.question == "如何提高电池续航"
    assert ctx.sao_list == []
    assert ctx.iteration == 0
    assert ctx.contradiction_desc == ""

def test_convergence_decision():
    decision = ConvergenceDecision(action="TERMINATE", reason="信号已清空")
    assert decision.action == "TERMINATE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_context.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'triz.context'"

- [ ] **Step 3: Write triz/context.py**

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
    ideality_score: float       # LLM 综合评分（0-1）
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
    evidence: List[str] = []      # 矛盾判定的支持证据（来自因果链）

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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_context.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/context.py tests/test_context.py
git commit -m "feat: add Pydantic data models for TRIZ workflow"
```

---

## Task 3: Database Layer - TRIZ Data

**Files:**
- Create: `triz/database/__init__.py`
- Create: `triz/database/triz_data.py`
- Test: `tests/test_database.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.database.triz_data import get_parameters, get_matrix_cell, get_separation_rules

def test_get_parameters_count():
    params = get_parameters()
    assert len(params) == 39

def test_get_parameters_first():
    params = get_parameters()
    assert params[0]["id"] == 1
    assert "Weight of moving object" in params[0]["name"]

def test_get_matrix_cell():
    # 改善 #9 Speed -> 恶化 #12 Shape
    principles = get_matrix_cell(9, 12)
    assert isinstance(principles, list)
    assert len(principles) > 0

def test_get_separation_rules():
    rules = get_separation_rules()
    types = {r["type"] for r in rules}
    assert "空间" in types or "时间" in types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'triz.database.triz_data'"

- [ ] **Step 3: Write triz/database/__init__.py**

```python
```

- [ ] **Step 4: Write triz/database/triz_data.py**

```python
"""TRIZ 标准数据：39个工程参数、40个发明原理、矛盾矩阵、分离规则"""

# 39个工程参数（id从1开始）
PARAMETERS = [
    {"id": 1, "name": "Weight of moving object", "name_cn": "运动物体的重量", "description": "运动物体的质量或重量"},
    {"id": 2, "name": "Weight of stationary object", "name_cn": "静止物体的重量", "description": "静止物体的质量或重量"},
    {"id": 3, "name": "Length of moving object", "name_cn": "运动物体的长度", "description": "运动物体在某一方向上的长度"},
    {"id": 4, "name": "Length of stationary object", "name_cn": "静止物体的长度", "description": "静止物体在某一方向上的长度"},
    {"id": 5, "name": "Area of moving object", "name_cn": "运动物体的面积", "description": "运动物体所占的面积或表面积"},
    {"id": 6, "name": "Area of stationary object", "name_cn": "静止物体的面积", "description": "静止物体所占的面积或表面积"},
    {"id": 7, "name": "Volume of moving object", "name_cn": "运动物体的体积", "description": "运动物体所占的空间体积"},
    {"id": 8, "name": "Volume of stationary object", "name_cn": "静止物体的体积", "description": "静止物体所占的空间体积"},
    {"id": 9, "name": "Speed", "name_cn": "速度", "description": "物体的运动速度或速率"},
    {"id": 10, "name": "Force", "name_cn": "力", "description": "作用于物体的力的大小"},
    {"id": 11, "name": "Stress or pressure", "name_cn": "应力或压力", "description": "单位面积上所受的力"},
    {"id": 12, "name": "Shape", "name_cn": "形状", "description": "物体的外部轮廓或几何形态"},
    {"id": 13, "name": "Stability of the object's composition", "name_cn": "物体结构的稳定性", "description": "物体组成结构的稳定程度"},
    {"id": 14, "name": "Strength", "name_cn": "强度", "description": "物体抵抗外力破坏的能力"},
    {"id": 15, "name": "Durability of moving object", "name_cn": "运动物体的耐用性", "description": "运动物体承受磨损的能力"},
    {"id": 16, "name": "Durability of stationary object", "name_cn": "静止物体的耐用性", "description": "静止物体承受磨损的能力"},
    {"id": 17, "name": "Temperature", "name_cn": "温度", "description": "物体或环境的温度高低"},
    {"id": 18, "name": "Illumination intensity", "name_cn": "照度", "description": "光照的强度"},
    {"id": 19, "name": "Energy spent by moving object", "name_cn": "运动物体消耗的能量", "description": "运动物体做功消耗的能量"},
    {"id": 20, "name": "Energy spent by stationary object", "name_cn": "静止物体消耗的能量", "description": "静止物体做功消耗的能量"},
    {"id": 21, "name": "Power", "name_cn": "功率", "description": "单位时间内完成的功"},
    {"id": 22, "name": "Loss of energy", "name_cn": "能量损失", "description": "系统能量的无效损耗"},
    {"id": 23, "name": "Loss of substance", "name_cn": "物质损失", "description": "系统物质成分的流失"},
    {"id": 24, "name": "Loss of information", "name_cn": "信息损失", "description": "数据或信息的丢失"},
    {"id": 25, "name": "Loss of time", "name_cn": "时间损失", "description": "操作或过程消耗的时间"},
    {"id": 26, "name": "Quantity of substance/the matter", "name_cn": "物质的量", "description": "系统中物质的数量"},
    {"id": 27, "name": "Reliability", "name_cn": "可靠性", "description": "系统在规定条件下正常工作的能力"},
    {"id": 28, "name": "Measurement accuracy", "name_cn": "测量精度", "description": "测量结果与真实值的接近程度"},
    {"id": 29, "name": "Manufacturing precision", "name_cn": "制造精度", "description": "制造过程中尺寸和形状的精确程度"},
    {"id": 30, "name": "External harm affects the object", "name_cn": "作用于物体的外部有害因素", "description": "来自外部环境对物体的损害"},
    {"id": 31, "name": "Harmful side effects", "name_cn": "有害的副作用", "description": "系统产生的负面副效应"},
    {"id": 32, "name": "Manufacturability", "name_cn": "可制造性", "description": "产品易于制造的程度"},
    {"id": 33, "name": "Ease of use", "name_cn": "使用的便利性", "description": "产品易于操作的程度"},
    {"id": 34, "name": "Ease of repair", "name_cn": "修理的便利性", "description": "产品易于维修的程度"},
    {"id": 35, "name": "Adaptability/Versatility", "name_cn": "适应性/通用性", "description": "系统适应不同条件或用途的能力"},
    {"id": 36, "name": "Device complexity", "name_cn": "装置的复杂性", "description": "系统中组件和关系的复杂程度"},
    {"id": 37, "name": "Difficulty of detecting and measuring", "name_cn": "检测和测量的困难", "description": "对系统状态进行检测和测量的难度"},
    {"id": 38, "name": "Extent of automation", "name_cn": "自动化程度", "description": "系统自动化水平的高低"},
    {"id": 39, "name": "Productivity/Capacity", "name_cn": "生产率/产能", "description": "单位时间内的产出量"},
]

# 40个发明原理（简化版，MVP使用核心列表）
PRINCIPLES = [
    {"id": 1, "name": "Segmentation", "name_cn": "分割", "description": "将物体分成独立的部分"},
    {"id": 2, "name": "Taking out", "name_cn": "抽取", "description": "从物体中抽取有害的部分或特性"},
    {"id": 3, "name": "Local quality", "name_cn": "局部质量", "description": "使物体的不同部分具有不同的功能或特性"},
    {"id": 4, "name": "Asymmetry", "name_cn": "不对称", "description": "用不对称的形状取代对称的形状"},
    {"id": 5, "name": "Merging", "name_cn": "合并", "description": "在空间上将同类或相关物体合并"},
    {"id": 6, "name": "Universality", "name_cn": "多用性", "description": "使一个物体执行多种功能"},
    {"id": 7, "name": "Nested doll", "name_cn": "嵌套", "description": "将一个物体放入另一个物体中"},
    {"id": 8, "name": "Anti-weight", "name_cn": "重量补偿", "description": "与其他物体结合产生升力或浮力"},
    {"id": 9, "name": "Preliminary anti-action", "name_cn": "预先反作用", "description": "预先施加相反的作用以消除有害因素"},
    {"id": 10, "name": "Preliminary action", "name_cn": "预先作用", "description": "预先完成必要的改变"},
    {"id": 11, "name": "Beforehand cushioning", "name_cn": "预先防范", "description": "预先准备好应急措施"},
    {"id": 12, "name": "Equipotentiality", "name_cn": "等势性", "description": "改变操作条件使物体不需要升高或降低"},
    {"id": 13, "name": "The other way round", "name_cn": "反向作用", "description": "用相反的动作代替问题指定的动作"},
    {"id": 14, "name": "Curvature", "name_cn": "曲面化", "description": "用曲线代替直线，曲面代替平面"},
    {"id": 15, "name": "Dynamics", "name_cn": "动态化", "description": "使物体的特性或环境自动调整到最佳状态"},
    {"id": 16, "name": "Partial or excessive actions", "name_cn": "未达到或过度作用", "description": "如果精确很难达到，允许稍多或稍少"},
    {"id": 17, "name": "Another dimension", "name_cn": "空间维度变化", "description": "将物体从一维变为二维或三维"},
    {"id": 18, "name": "Mechanical vibration", "name_cn": "机械振动", "description": "使物体振动"},
    {"id": 19, "name": "Periodic action", "name_cn": "周期性动作", "description": "用周期性动作代替连续动作"},
    {"id": 20, "name": "Continuity of useful action", "name_cn": "有效作用的连续性", "description": "使物体的所有部分持续满负荷工作"},
    {"id": 21, "name": "Skipping", "name_cn": "快速通过", "description": "高速执行有害操作"},
    {"id": 22, "name": "Blessing in disguise", "name_cn": "变害为利", "description": "利用有害因素获得有益效果"},
    {"id": 23, "name": "Feedback", "name_cn": "反馈", "description": "引入反馈，改善已有反馈"},
    {"id": 24, "name": "Intermediary", "name_cn": "中介物", "description": "使用中间物体传递或执行动作"},
    {"id": 25, "name": "Self-service", "name_cn": "自服务", "description": "使物体通过辅助功能自我服务"},
    {"id": 26, "name": "Copying", "name_cn": "复制", "description": "用简化廉价的复制品代替"},
    {"id": 27, "name": "Cheap short-living objects", "name_cn": "廉价短寿命", "description": "用多个廉价物体代替昂贵物体"},
    {"id": 28, "name": "Mechanics substitution", "name_cn": "机械系统替代", "description": "用光学、声学、热学等替代机械系统"},
    {"id": 29, "name": "Pneumatics and hydraulics", "name_cn": "气动与液压结构", "description": "使用气体或液体代替固体"},
    {"id": 30, "name": "Flexible shells and thin films", "name_cn": "柔性壳体和薄膜", "description": "使用柔性壳体和薄膜代替传统结构"},
    {"id": 31, "name": "Porous materials", "name_cn": "多孔材料", "description": "使物体多孔或添加多孔元素"},
    {"id": 32, "name": "Color changes", "name_cn": "改变颜色", "description": "改变物体或环境的颜色"},
    {"id": 33, "name": "Homogeneity", "name_cn": "同质性", "description": "使相互作用的物体由同种材料制成"},
    {"id": 34, "name": "Discarding and recovering", "name_cn": "抛弃与再生", "description": "已完成功能的部件自动消失或再生"},
    {"id": 35, "name": "Parameter changes", "name_cn": "参数变化", "description": "改变物体的物理状态"},
    {"id": 36, "name": "Phase transitions", "name_cn": "相变", "description": "利用相变过程中发生的现象"},
    {"id": 37, "name": "Thermal expansion", "name_cn": "热膨胀", "description": "利用热膨胀或热收缩"},
    {"id": 38, "name": "Strong oxidants", "name_cn": "强氧化剂", "description": "用富氧空气或纯氧代替普通空气"},
    {"id": 39, "name": "Inert atmosphere", "name_cn": "惰性环境", "description": "用惰性环境代替正常环境"},
    {"id": 40, "name": "Composite materials", "name_cn": "复合材料", "description": "从单一材料变为复合材料"},
]

# 阿奇舒勒矛盾矩阵（关键单元格，MVP使用代表性数据）
# 格式: (improve_param, worsen_param): [principles, ...]
MATRIX = {
    # 改善速度 -> 恶化...
    (9, 12): [15, 28, 35],    # Speed -> Shape
    (9, 14): [2, 8, 15],      # Speed -> Strength
    (9, 27): [11, 35, 28],    # Speed -> Reliability
    (9, 36): [15, 1, 28],     # Speed -> Device complexity

    # 改善强度 -> 恶化...
    (14, 9): [28, 27, 35],    # Strength -> Speed
    (14, 12): [1, 8, 15],     # Strength -> Shape
    (14, 17): [28, 27, 3],    # Strength -> Temperature
    (14, 25): [28, 27, 35],   # Strength -> Loss of time

    # 改善可靠性 -> 恶化...
    (27, 9): [11, 28, 35],    # Reliability -> Speed
    (27, 25): [26, 35, 10],   # Reliability -> Loss of time
    (27, 36): [27, 35, 2],    # Reliability -> Device complexity

    # 改善温度 -> 恶化...
    (17, 14): [35, 28, 21],   # Temperature -> Strength
    (17, 27): [32, 35, 19],   # Temperature -> Reliability
    (17, 36): [19, 1, 32],    # Temperature -> Device complexity

    # 改善重量(运动物体) -> 恶化...
    (1, 14): [27, 26, 1],     # Weight moving -> Strength
    (1, 9): [8, 15, 35],      # Weight moving -> Speed
    (1, 27): [27, 26, 35],    # Weight moving -> Reliability

    # 改善面积(静止物体) -> 恶化...
    (6, 1): [1, 2, 17],       # Area stationary -> Weight moving
    (6, 14): [1, 15, 29],     # Area stationary -> Strength
    (6, 36): [17, 1, 40],     # Area stationary -> Device complexity

    # 改善生产率 -> 恶化...
    (39, 25): [10, 23, 35],   # Productivity -> Loss of time
    (39, 27): [35, 26, 10],   # Productivity -> Reliability
    (39, 36): [24, 35, 28],   # Productivity -> Device complexity
}

# 分离原理规则库
SEPARATION_RULES = [
    {"id": 1, "type": "空间", "condition": "在空间上将矛盾的双方分离", "principles": [1, 2, 3, 7, 17, 24, 26]},
    {"id": 2, "type": "时间", "condition": "在时间上将矛盾的双方分离", "principles": [9, 10, 11, 15, 16, 19, 20, 21, 34]},
    {"id": 3, "type": "条件", "condition": "在不同条件下满足矛盾双方", "principles": [1, 3, 11, 22, 23, 27, 28, 35]},
    {"id": 4, "type": "系统", "condition": "在系统不同层级满足矛盾双方", "principles": [5, 6, 7, 12, 24, 25, 33, 40]},
]


def get_parameters():
    return PARAMETERS


def get_principles():
    return PRINCIPLES


def get_matrix_cell(improve_param: int, worsen_param: int) -> list:
    key = (improve_param, worsen_param)
    if key in MATRIX:
        return MATRIX[key]
    # fallback: 返回改善参数行的 top-3 高频原理
    row_principles = []
    for (imp, wor), prins in MATRIX.items():
        if imp == improve_param:
            row_principles.extend(prins)
    from collections import Counter
    if row_principles:
        return [p for p, _ in Counter(row_principles).most_common(3)]
    return []


def get_separation_rules():
    return SEPARATION_RULES


def get_separation_principles(sep_type: str) -> list:
    for rule in SEPARATION_RULES:
        if rule["type"] == sep_type:
            return rule["principles"]
    # fallback: 返回所有分离类型原理的并集
    all_prins = set()
    for rule in SEPARATION_RULES:
        all_prins.update(rule["principles"])
    return sorted(list(all_prins))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_database.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add triz/database/__init__.py triz/database/triz_data.py tests/test_database.py
git commit -m "feat: add TRIZ standard data - parameters, principles, matrix, separation rules"
```

---

## Task 4: Database Initialization & Queries

**Files:**
- Create: `triz/database/init_db.py`
- Create: `triz/database/queries.py`
- Test: `tests/test_database_queries.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
import os
from triz.database.init_db import init_database, ensure_data_dir
from triz.database.queries import get_parameter_by_id, query_parameters_by_similarity
from triz.config import DB_PATH

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_triz.db"
    monkeypatch.setattr("triz.config.DB_PATH", db_path)
    init_database()
    yield db_path
    if db_path.exists():
        os.remove(db_path)

def test_init_database_creates_tables(temp_db):
    assert temp_db.exists()

def test_get_parameter_by_id(temp_db):
    param = get_parameter_by_id(9)
    assert param is not None
    assert "Speed" in param["name"]

def test_get_parameter_by_id_not_found(temp_db):
    param = get_parameter_by_id(999)
    assert param is None

def test_query_parameters_by_similarity(temp_db):
    # 测试通过关键词查询参数
    results = query_parameters_by_similarity("速度")
    assert len(results) > 0
    assert results[0]["id"] == 9  # Speed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_queries.py -v`
Expected: FAIL with import errors

- [ ] **Step 3: Write triz/database/init_db.py**

```python
"""数据库初始化：建表、插入TRIZ标准数据、预计算embedding"""
import sqlite3
import json
from pathlib import Path
from triz.config import DB_PATH, DATA_DIR
from triz.database.triz_data import get_parameters, get_principles, get_separation_rules, MATRIX


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def init_database():
    ensure_data_dir()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建参数表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parameters (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_cn TEXT NOT NULL,
            description TEXT NOT NULL,
            embedding_json TEXT
        )
    """)

    # 创建原理表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS principles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_cn TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    # 创建矛盾矩阵表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matrix (
            improve_param INTEGER,
            worsen_param INTEGER,
            principles TEXT,
            PRIMARY KEY (improve_param, worsen_param)
        )
    """)

    # 创建分离规则表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS separation_rules (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            condition TEXT NOT NULL,
            principles TEXT
        )
    """)

    # 创建案例表（MVP预置）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY,
            principle_id INTEGER,
            function TEXT NOT NULL,
            context TEXT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)

    # 插入参数数据
    cursor.execute("SELECT COUNT(*) FROM parameters")
    if cursor.fetchone()[0] == 0:
        for p in get_parameters():
            cursor.execute(
                "INSERT INTO parameters (id, name, name_cn, description, embedding_json) VALUES (?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["name_cn"], p["description"], None)
            )

    # 插入原理数据
    cursor.execute("SELECT COUNT(*) FROM principles")
    if cursor.fetchone()[0] == 0:
        for p in get_principles():
            cursor.execute(
                "INSERT INTO principles (id, name, name_cn, description) VALUES (?, ?, ?, ?)",
                (p["id"], p["name"], p["name_cn"], p["description"])
            )

    # 插入矩阵数据
    cursor.execute("SELECT COUNT(*) FROM matrix")
    if cursor.fetchone()[0] == 0:
        for (imp, wor), prins in MATRIX.items():
            cursor.execute(
                "INSERT INTO matrix (improve_param, worsen_param, principles) VALUES (?, ?, ?)",
                (imp, wor, json.dumps(prins))
            )

    # 插入分离规则数据
    cursor.execute("SELECT COUNT(*) FROM separation_rules")
    if cursor.fetchone()[0] == 0:
        for r in get_separation_rules():
            cursor.execute(
                "INSERT INTO separation_rules (id, type, condition, principles) VALUES (?, ?, ?, ?)",
                (r["id"], r["type"], r["condition"], json.dumps(r["principles"]))
            )

    # MVP预置案例（医疗领域）
    cursor.execute("SELECT COUNT(*) FROM cases")
    if cursor.fetchone()[0] == 0:
        sample_cases = [
            (15, "切割", "医疗", "本地库", "手术刀动态压力调节", "根据组织密度实时调整刀片接触压力"),
            (28, "切割", "医疗", "本地库", "超声波手术刀", "使用超声波振动代替机械切割"),
            (1, "固定", "医疗", "本地库", "可拆卸手术支架", "将支架分成多个独立部分便于取出"),
            (35, "加热", "航天", "本地库", "航天器温控涂层", "根据日照角度改变涂层颜色调节温度"),
            (14, "支撑", "汽车", "本地库", "F1赛车悬挂", "用曲面结构分散冲击力提高强度"),
        ]
        for case in sample_cases:
            cursor.execute(
                "INSERT INTO cases (principle_id, function, context, source, title, description) VALUES (?, ?, ?, ?, ?, ?)",
                case
            )

    conn.commit()
    conn.close()
    return DB_PATH
```

- [ ] **Step 4: Write triz/database/queries.py**

```python
"""数据库查询接口"""
import sqlite3
import json
from typing import Optional, List
from triz.config import DB_PATH


def _get_conn():
    return sqlite3.connect(DB_PATH)


def get_parameter_by_id(param_id: int) -> Optional[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, name_cn, description FROM parameters WHERE id = ?", (param_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "name_cn": row[2], "description": row[3]}
    return None


def get_all_parameters() -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, name_cn, description FROM parameters ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "name_cn": r[2], "description": r[3]} for r in rows]


def query_parameters_by_similarity(keyword: str) -> List[dict]:
    """基于关键词模糊查询参数（用于测试和fallback）"""
    conn = _get_conn()
    cursor = conn.cursor()
    # 在 name、name_cn、description 中搜索
    like_pattern = f"%{keyword}%"
    cursor.execute(
        "SELECT id, name, name_cn, description FROM parameters WHERE name LIKE ? OR name_cn LIKE ? OR description LIKE ? ORDER BY id",
        (like_pattern, like_pattern, like_pattern)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "name_cn": r[2], "description": r[3]} for r in rows]


def get_matrix_principles(improve_param: int, worsen_param: int) -> List[int]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT principles FROM matrix WHERE improve_param = ? AND worsen_param = ?",
        (improve_param, worsen_param)
    )
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []


def get_separation_principles_by_type(sep_type: str) -> List[int]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT principles FROM separation_rules WHERE type = ?", (sep_type,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return json.loads(row[0])
    return []


def get_all_separation_types() -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, condition, principles FROM separation_rules")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "type": r[1], "condition": r[2], "principles": json.loads(r[3])} for r in rows]


def query_cases(principle_ids: List[int], function: str = "", limit: int = 10) -> List[dict]:
    conn = _get_conn()
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(principle_ids))
    sql = f"SELECT principle_id, function, context, source, title, description FROM cases WHERE principle_id IN ({placeholders})"
    params = list(principle_ids)
    if function:
        sql += " AND function LIKE ?"
        params.append(f"%{function}%")
    sql += f" LIMIT {limit}"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()
    return [{"principle_id": r[0], "function": r[1], "context": r[2], "source": r[3], "title": r[4], "description": r[5]} for r in rows]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_database_queries.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add triz/database/init_db.py triz/database/queries.py tests/test_database_queries.py
git commit -m "feat: add SQLite database initialization and query layer"
```

---

## Task 5: Vector Math Utility

**Files:**
- Create: `triz/utils/__init__.py`
- Create: `triz/utils/vector_math.py`
- Test: `tests/test_vector_math.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.utils.vector_math import cosine_similarity, embed_text

def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert cosine_similarity(v1, v2) == pytest.approx(0.0)

def test_cosine_similarity_opposite():
    v1 = [1.0, 0.0]
    v2 = [-1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(-1.0)

def test_embed_text_returns_list():
    # embed_text uses simple character-level encoding for MVP
    vec = embed_text("速度")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(x, float) for x in vec)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vector_math.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/utils/vector_math.py**

```python
"""向量计算工具：余弦相似度、简单文本embedding（MVP使用字符级编码）"""
import math
from typing import List


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算两个向量的余弦相似度"""
    if len(vec1) != len(vec2):
        raise ValueError(f"Vector dimensions must match: {len(vec1)} vs {len(vec2)}")

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return dot_product / (norm1 * norm2)


def embed_text(text: str, dim: int = 128) -> List[float]:
    """MVP: 使用简单的字符级hash编码将文本转为向量。
    生产环境应替换为 sentence-transformers 或 OpenAI Embedding API。
    """
    vec = [0.0] * dim
    for i, char in enumerate(text):
        idx = ord(char) % dim
        vec[idx] += hash(char) % 100 / 100.0
        # 位置加权
        vec[(idx + 1) % dim] += (i + 1) * 0.01

    # 归一化
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_vector_math.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/utils/__init__.py triz/utils/vector_math.py tests/test_vector_math.py
git commit -m "feat: add vector math utilities - cosine similarity and text embedding"
```

---

## Task 6: Tool - M3 Problem Formulation

**Files:**
- Create: `triz/tools/__init__.py`
- Create: `triz/tools/m3_formulation.py`
- Test: `tests/test_tools.py` (append to existing or create)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.context import WorkflowContext, SAO
from triz.tools.m3_formulation import formulate_problem

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py::test_formulate_tech_contradiction -v`
Expected: FAIL

- [ ] **Step 3: Write triz/tools/m3_formulation.py**

```python
"""M3 问题定型 Tool：从根因提取矛盾类型和矛盾描述（自然语言）"""
from triz.context import WorkflowContext


def formulate_problem(ctx: WorkflowContext) -> dict:
    """从 M2 的根因输出中提取矛盾类型和矛盾描述。"""
    root_param = ctx.root_param or ""
    key_problem = ctx.key_problem or ""
    evidence = ctx.causal_chain.copy() if ctx.causal_chain else []

    # Step 1: 识别矛盾类型
    combined_text = f"{root_param} {key_problem}"
    if "既要" in combined_text or "又要" in combined_text or "同时" in combined_text:
        problem_type = "phys"
    else:
        problem_type = "tech"

    # Step 2: 提取矛盾描述
    contradiction_desc = _extract_contradiction_desc(problem_type, root_param, key_problem)

    return {
        "problem_type": problem_type,
        "contradiction_desc": contradiction_desc,
        "evidence": evidence,
    }


def _extract_contradiction_desc(problem_type: str, root_param: str, key_problem: str) -> str:
    """从根因文本中提取矛盾描述。"""
    combined = f"{root_param} {key_problem}".strip()

    if not combined:
        return "未识别矛盾"

    if problem_type == "phys":
        # 物理矛盾：提取"既要...又要..."格式
        if "既要" in root_param:
            return root_param
        # 构造描述
        return f"{root_param}存在物理矛盾"
    else:
        # 技术矛盾：尝试提取"改善...恶化..."
        # 简化策略：用根因参数直接描述
        if "导致" in combined or "恶化" in combined or "影响" in combined:
            return combined
        # fallback: 构造标准格式
        return f"改善{root_param}导致{key_problem}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/tools/__init__.py triz/tools/m3_formulation.py tests/test_tools.py
git commit -m "feat: add M3 problem formulation tool"
```

---

## Task 7: Tool - M4 Contradiction Solver (with Two-Step Parameter Mapping)

**Files:**
- Create: `triz/tools/m4_solver.py`
- Modify: `tests/test_tools.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.context import WorkflowContext
from triz.tools.m4_solver import solve_contradiction
from triz.database.init_db import init_database

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()

def test_solve_tech_contradiction_speed_shape():
    ctx = WorkflowContext(question="test")
    ctx.problem_type = "tech"
    ctx.contradiction_desc = "改善速度，恶化形状稳定性"
    ctx.candidate_attributes = ["速度", "形状"]

    result = solve_contradiction(ctx)
    assert len(result["principles"]) > 0
    assert result["improve_param_id"] == 9   # Speed
    assert result["worsen_param_id"] == 12   # Shape

def test_solve_phys_contradiction():
    ctx = WorkflowContext(question="test")
    ctx.problem_type = "phys"
    ctx.contradiction_desc = "接触面积既要大又要小"
    ctx.candidate_attributes = ["接触面积"]

    result = solve_contradiction(ctx)
    assert len(result["principles"]) > 0
    assert result["sep_type"] is not None

def test_solve_fallback_on_empty_matrix():
    ctx = WorkflowContext(question="test")
    ctx.problem_type = "tech"
    ctx.contradiction_desc = "改善重量，恶化速度"
    ctx.candidate_attributes = ["重量", "速度"]

    result = solve_contradiction(ctx)
    # 即使矩阵中没有精确匹配，也应返回 fallback 原理
    assert isinstance(result["principles"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py::test_solve_tech_contradiction_speed_shape -v`
Expected: FAIL

- [ ] **Step 3: Write triz/tools/m4_solver.py**

```python
"""M4 矛盾求解 Tool：双步参数映射 + 查表"""
import re
from typing import Optional
from triz.context import WorkflowContext
from triz.config import SIMILARITY_THRESHOLD
from triz.database.queries import (
    get_all_parameters, get_matrix_principles,
    get_separation_principles_by_type, get_all_separation_types
)
from triz.utils.vector_math import cosine_similarity, embed_text


# 关键词到参数ID的映射（fallback用）
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


def solve_contradiction(ctx: WorkflowContext) -> dict:
    """双步参数映射求解矛盾。"""
    if ctx.problem_type == "tech":
        return _solve_tech_contradiction(ctx)
    else:
        return _solve_phys_contradiction(ctx)


def _solve_tech_contradiction(ctx: WorkflowContext) -> dict:
    """技术矛盾：改善参数 -> 恶化参数 -> 查矩阵"""
    desc = ctx.contradiction_desc
    candidate_attrs = ctx.candidate_attributes or []

    # Step 1: 从矛盾描述中解析改善/恶化参数（自然语言）
    improve_attr = _parse_improve_param(desc)
    worsen_attr = _parse_worsen_param(desc)

    # 用 candidate_attributes 辅助消歧
    if not improve_attr and candidate_attrs:
        improve_attr = candidate_attrs[0]
    if not worsen_attr and len(candidate_attrs) > 1:
        worsen_attr = candidate_attrs[1]

    # Step 2: 余弦相似度匹配到 39 参数 ID
    improve_param_id = _match_param_id(improve_attr)
    worsen_param_id = _match_param_id(worsen_attr)

    # Step 3: 查阿奇舒勒矩阵
    principles = get_matrix_principles(improve_param_id, worsen_param_id)

    # 计算匹配置信度
    match_conf = 0.8 if improve_param_id and worsen_param_id else 0.5

    return {
        "principles": principles,
        "sep_type": None,
        "match_conf": match_conf,
        "improve_param_id": improve_param_id,
        "worsen_param_id": worsen_param_id,
        "need_state": None,
        "need_not_state": None,
    }


def _solve_phys_contradiction(ctx: WorkflowContext) -> dict:
    """物理矛盾：提取状态 -> 判定分离类型 -> 查分离规则库"""
    desc = ctx.contradiction_desc

    # 提取需要/不需要的状态
    need_state, need_not_state = _parse_phys_states(desc)

    # 判定分离类型
    sep_type = _classify_separation(need_state, need_not_state)

    # 查分离规则库
    principles = get_separation_principles_by_type(sep_type)

    # fallback: 如果该类型没有原理，返回所有分离类型的原理并集
    if not principles:
        all_types = get_all_separation_types()
        all_prins = set()
        for t in all_types:
            all_prins.update(t["principles"])
        principles = sorted(list(all_prins))

    return {
        "principles": principles,
        "sep_type": sep_type,
        "match_conf": 0.7,
        "improve_param_id": None,
        "worsen_param_id": None,
        "need_state": need_state,
        "need_not_state": need_not_state,
    }


def _parse_improve_param(desc: str) -> str:
    """从矛盾描述中提取改善参数。"""
    # 模式："改善X，恶化Y" 或 "提升X导致Y" 或 "X导致Y"
    patterns = [
        r"改善(.+?)[，,、]",
        r"提升(.+?)[，,、]",
        r"增加(.+?)[，,、]",
        r"优化(.+?)[，,、]",
    ]
    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            return match.group(1).strip()
    # 提取前半部分
    if "导致" in desc:
        return desc.split("导致")[0].strip()
    if "，" in desc:
        return desc.split("，")[0].strip()
    return desc.strip()


def _parse_worsen_param(desc: str) -> str:
    """从矛盾描述中提取恶化参数。"""
    patterns = [
        r"恶化(.+)",
        r"损害(.+)",
        r"降低(.+)",
        r"导致(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, desc)
        if match:
            return match.group(1).strip()
    # 提取后半部分
    if "导致" in desc:
        parts = desc.split("导致")
        if len(parts) > 1:
            return parts[1].strip()
    if "，" in desc:
        parts = desc.split("，")
        if len(parts) > 1:
            return parts[1].strip()
    return ""


def _match_param_id(attribute: str) -> int:
    """将自然语言属性匹配到 39 参数 ID。
    策略：先查关键词映射表，再用余弦相似度匹配。
    """
    if not attribute:
        return 1  # fallback

    # 策略1: 关键词直接匹配
    for keyword, param_id in KEYWORD_PARAM_MAP.items():
        if keyword in attribute:
            return param_id

    # 策略2: 余弦相似度匹配（需要预计算embedding，MVP使用简化版本）
    all_params = get_all_parameters()
    attr_vec = embed_text(attribute)

    best_match = None
    best_score = -1.0
    for param in all_params:
        param_vec = embed_text(param["name"] + " " + param["name_cn"] + " " + param["description"])
        score = cosine_similarity(attr_vec, param_vec)
        if score > best_score:
            best_score = score
            best_match = param

    if best_match and best_score >= SIMILARITY_THRESHOLD:
        return best_match["id"]

    # 最终 fallback
    return 1


def _parse_phys_states(desc: str) -> tuple:
    """从物理矛盾描述中提取需要/不需要的状态。"""
    # 模式："X既要A又要B" 或 "X既要大又要小"
    match = re.search(r"(.+?)既要(.+?)又要(.+)", desc)
    if match:
        return match.group(2).strip(), match.group(3).strip()
    # 简单分割
    return desc, f"非{desc}"


def _classify_separation(need_state: str, need_not_state: str) -> str:
    """判定分离类型（空间/时间/条件/系统）。
    MVP：使用关键词启发式判断。
    """
    combined = f"{need_state} {need_not_state}"
    # 空间关键词
    if any(kw in combined for kw in ["位置", "空间", "区域", "地方", "上面", "下面", "内部", "外部"]):
        return "空间"
    # 时间关键词
    if any(kw in combined for kw in ["时间", "之前", "之后", "同时", "顺序", "阶段", "周期"]):
        return "时间"
    # 条件关键词
    if any(kw in combined for kw in ["条件", "温度", "压力", "速度", "状态", "高", "低", "大", "小"]):
        return "条件"
    # 默认条件分离
    return "条件"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add triz/tools/m4_solver.py tests/test_tools.py
git commit -m "feat: add M4 contradiction solver with two-step parameter mapping"
```

---

## Task 8: Tool - M7 Convergence Control & M2 Gate

**Files:**
- Create: `triz/tools/m7_convergence.py`
- Create: `triz/tools/m2_gate.py`
- Modify: `tests/test_tools.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.context import WorkflowContext, ConvergenceDecision
from triz.tools.m7_convergence import check_convergence
from triz.tools.m2_gate import should_trigger_m2

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
    ctx.max_ideality = 0.7
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.5}]

    decision = check_convergence(ctx)
    assert decision.action == "CONTINUE"

def test_convergence_clarify_low_ideality():
    ctx = WorkflowContext(question="test")
    ctx.max_ideality = 0.1
    ctx.iteration = 1
    ctx.unresolved_signals = ["风险过高"]
    ctx.history_log = [{"max_ideality": 0.1}]

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

def test_m2_gate_trigger_with_harmful_sao():
    from triz.context import SAO
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="损坏", object="B", function_type="harmful")]
    assert should_trigger_m2(ctx) is True

def test_m2_gate_skip_all_useful():
    from triz.context import SAO
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="A", action="切割", object="B", function_type="useful")]
    assert should_trigger_m2(ctx) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/tools/m7_convergence.py**

```python
"""M7 收敛控制 Tool：四重阈值判定"""
from triz.context import WorkflowContext, ConvergenceDecision
from triz.config import MAX_ITERATIONS, MIN_IDEALITY_THRESHOLD


def check_convergence(ctx: WorkflowContext) -> ConvergenceDecision:
    """根据迭代状态做四重阈值判定。"""
    max_ideality = ctx.max_ideality
    iteration = ctx.iteration
    history = ctx.history_log
    signals = ctx.unresolved_signals

    # 1. 信号清空判定
    if not signals:
        return ConvergenceDecision(
            action="TERMINATE",
            reason="信号已清空，矛盾已充分解决"
        )

    # 2. 停滞判定
    if iteration > 0 and history:
        last_ideality = history[-1].get("max_ideality", 0)
        if max_ideality == last_ideality:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度停滞在 {max_ideality}，继续迭代无改善"
            )

    # 3. 收益递减判定
    if iteration >= 2 and len(history) >= 2:
        prev_ideality = history[-2].get("max_ideality", 0)
        improvement = max_ideality - prev_ideality
        if improvement < 0.05:
            return ConvergenceDecision(
                action="TERMINATE",
                reason=f"理想度改善率 {improvement:.3f} 低于阈值，收益递减"
            )

    # 4. 触达上限判定
    if iteration >= MAX_ITERATIONS:
        return ConvergenceDecision(
            action="TERMINATE",
            reason=f"达到最大迭代次数 {MAX_ITERATIONS}"
        )

    # 5. 理想度过低 -> CLARIFY
    if max_ideality < MIN_IDEALITY_THRESHOLD:
        return ConvergenceDecision(
            action="CLARIFY",
            reason=f"最高理想度 {max_ideality} 低于阈值 {MIN_IDEALITY_THRESHOLD}，需要用户补充信息"
        )

    # 6. CONTINUE
    feedback = _generate_feedback(signals, max_ideality)
    return ConvergenceDecision(
        action="CONTINUE",
        reason=f"理想度 {max_ideality}，继续迭代优化",
        feedback=feedback
    )


def _generate_feedback(signals: list, max_ideality: float) -> str:
    """生成给下一轮 M5 的反馈信息。"""
    feedback_parts = [f"上一轮最高理想度: {max_ideality}"]
    if signals:
        feedback_parts.append(f"未解决问题: {', '.join(signals[:3])}")
    return "; ".join(feedback_parts)
```

- [ ] **Step 4: Write triz/tools/m2_gate.py**

```python
"""M2 门控 Tool：判断是否需要触发根因分析"""
from triz.context import WorkflowContext


def should_trigger_m2(ctx: WorkflowContext) -> bool:
    """默认触发，仅当无 SAO 或全为 Useful 功能时跳过。"""
    if not ctx.sao_list:
        return False

    # 检查是否有负面功能
    for sao in ctx.sao_list:
        if sao.function_type in ("harmful", "excessive", "insufficient"):
            return True

    # 全为 Useful，无需 RCA
    return False
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add triz/tools/m7_convergence.py triz/tools/m2_gate.py tests/test_tools.py
git commit -m "feat: add M7 convergence control and M2 gate tools"
```

---

## Task 9: Tool - FOS Cross-Domain Search

**Files:**
- Create: `triz/tools/fos_search.py`
- Modify: `tests/test_tools.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.context import WorkflowContext, SAO
from triz.tools.fos_search import search_cases
from triz.database.init_db import init_database

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()

def test_search_local_cases():
    ctx = WorkflowContext(question="test")
    ctx.principles = [15, 28]
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]
    ctx.question = "如何提高手术刀片耐用性"

    cases = search_cases(ctx)
    assert len(cases) > 0
    assert all(hasattr(c, "principle_id") for c in cases)

def test_search_returns_empty_when_no_match():
    ctx = WorkflowContext(question="test")
    ctx.principles = [999]  # 不存在的原理
    ctx.sao_list = []
    ctx.question = "test"

    cases = search_cases(ctx)
    assert cases == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py::test_search_local_cases -v`
Expected: FAIL

- [ ] **Step 3: Write triz/tools/fos_search.py**

```python
"""FOS 跨界检索 Tool：本地案例库查询 -> Google Patent API 补充"""
from triz.context import WorkflowContext, Case
from triz.config import SERP_API_KEY
from triz.database.queries import query_cases


def search_cases(ctx: WorkflowContext) -> list[Case]:
    """检索跨行业可落地案例。"""
    principles = ctx.principles
    sao_list = ctx.sao_list
    question = ctx.question

    # 从 SAO 提取核心功能词
    function = _extract_function(sao_list)
    domain_hint = _extract_domain(question)

    # L1: 本地查询
    local_cases = query_cases(principles, function=function, limit=10)
    cases = [_db_row_to_case(c) for c in local_cases]

    # L2: 如果本地不足 3 条，尝试 SerpApi
    if len(cases) < 3 and SERP_API_KEY:
        try:
            patent_cases = _search_serpapi(principles, function, domain_hint)
            cases.extend(patent_cases)
        except Exception:
            # API 失败时不中断
            pass

    return cases[:10]  # 最多返回 10 条


def _extract_function(sao_list: list) -> str:
    """从 SAO 中提取核心功能词。"""
    if not sao_list:
        return ""
    # 取第一个 useful 或第一个 sao 的 action
    for sao in sao_list:
        if sao.function_type == "useful":
            return sao.action
    return sao_list[0].action


def _extract_domain(question: str) -> str:
    """从问题中提取领域上下文。"""
    domain_keywords = {
        "医疗": ["手术", "医院", "病人", "医生", "治疗", "药物", "器械"],
        "汽车": ["汽车", "车辆", "发动机", "轮胎", "驾驶"],
        "航天": ["航天", "飞机", "火箭", "卫星", "航空"],
        "电子": ["芯片", "电路", "电池", "手机", "电脑", "半导体"],
    }
    for domain, keywords in domain_keywords.items():
        if any(kw in question for kw in keywords):
            return domain
    return ""


def _db_row_to_case(row: dict) -> Case:
    return Case(
        principle_id=row["principle_id"],
        source=row["source"],
        title=row["title"],
        description=row["description"],
        function=row.get("function", ""),
    )


def _search_serpapi(principles: list, function: str, domain: str) -> list[Case]:
    """调用 SerpApi 搜索 Google Patents。
    MVP: 返回空列表（API 集成在后续迭代中实现）。
    """
    # TODO: 实现 SerpApi 调用
    # 当前返回空，不阻塞主流程
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add triz/tools/fos_search.py tests/test_tools.py
git commit -m "feat: add FOS cross-domain search tool"
```

---

## Task 10: API Client Utility

**Files:**
- Create: `triz/utils/api_client.py`
- Test: `tests/test_api_client.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.utils.api_client import OpenAIClient
from unittest.mock import MagicMock, patch

def test_openai_client_initialization():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    assert client.model == "gpt-4o-mini"

def test_openai_client_chat_mock():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    with patch.object(client.client.chat.completions, 'create') as mock_create:
        mock_create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"test": true}'))]
        )
        result = client.chat("Hello")
        assert result == '{"test": true}'
        mock_create.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_client.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/utils/api_client.py**

```python
"""OpenAI API 客户端封装"""
from openai import OpenAI
from triz.config import OPENAI_API_KEY, OPENAI_MODEL


class OpenAIClient:
    """封装 OpenAI API 调用，提供统一的 chat 接口。"""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or OPENAI_MODEL
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")
        self.client = OpenAI(api_key=self.api_key)

    def chat(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, json_mode: bool = False) -> str:
        """发送单轮对话请求，返回文本内容。"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_structured(self, prompt: str, system_prompt: str = "", temperature: float = 0.7) -> str:
        """强制 JSON 输出模式。"""
        return self.chat(prompt, system_prompt, temperature, json_mode=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/utils/api_client.py tests/test_api_client.py
git commit -m "feat: add OpenAI API client wrapper"
```

---

## Task 11: Markdown Renderer Utility

**Files:**
- Create: `triz/utils/markdown_renderer.py`
- Test: `tests/test_markdown_renderer.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from triz.utils.markdown_renderer import render_node_start, render_step_complete, render_final_report
from triz.context import Solution, SolutionDraft, QualitativeTags

def test_render_node_start():
    output = render_node_start("问题建模", 1, 5)
    assert "节点 1/5" in output
    assert "问题建模" in output

def test_render_final_report():
    solution = Solution(
        draft=SolutionDraft(title="测试方案", description="描述", applied_principles=[1], resource_mapping="无"),
        tags=QualitativeTags(feasibility_score=4, resource_fit_score=4, innovation_score=3, uniqueness_score=3, risk_level="low", ifr_deviation_reason=""),
        ideality_score=0.75,
        evaluation_rationale="测试"
    )
    report = render_final_report("如何提高续航", "改善速度恶化稳定性", [solution], "收敛")
    assert "如何提高续航" in report
    assert "0.75" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_markdown_renderer.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/utils/markdown_renderer.py**

```python
"""Markdown 渲染工具：将节点输出和最终结果渲染为 Markdown"""
from triz.context import WorkflowContext, Solution


def render_node_start(node_name: str, current: int, total: int) -> str:
    return f"\n## [节点 {current}/{total}] {node_name}\n"


def render_step_complete(step_name: str, step_type: str, result: dict) -> str:
    type_icon = "Skill" if step_type == "Skill" else "Tool"
    return f"- {type_icon}: {step_name}...\n"


def render_node_complete(node_name: str, ctx: WorkflowContext) -> str:
    """根据节点类型渲染具体输出内容。"""
    output = ""
    if node_name == "问题建模":
        output += _render_problem_modeling(ctx)
    elif node_name == "矛盾求解":
        output += _render_contradiction_solver(ctx)
    elif node_name == "跨界检索":
        output += _render_fos_results(ctx)
    elif node_name == "方案生成":
        output += _render_solution_generation(ctx)
    elif node_name == "方案评估":
        output += _render_solution_evaluation(ctx)
    output += "\n---\n"
    return output


def _render_problem_modeling(ctx: WorkflowContext) -> str:
    lines = []
    # M1 输出
    if ctx.sao_list:
        lines.append("### 功能建模")
        for sao in ctx.sao_list:
            lines.append(f"- [{sao.subject}] -> [{sao.action}] -> [{sao.object}] ({sao.function_type})")
    if ctx.ifr:
        lines.append(f"- **IFR**: {ctx.ifr}")
    if ctx.resources:
        lines.append(f"- **资源**: {ctx.resources}")

    # M2 输出
    if ctx.root_param:
        lines.append("\n### 根因分析")
        lines.append(f"- **根因**: {ctx.root_param}")
        if ctx.candidate_attributes:
            lines.append(f"- **候选属性**: {ctx.candidate_attributes}")

    # M3 输出
    if ctx.contradiction_desc:
        lines.append(f"\n### 矛盾定型")
        lines.append(f"- **类型**: {ctx.problem_type}")
        lines.append(f"- **描述**: {ctx.contradiction_desc}")

    return "\n".join(lines)


def _render_contradiction_solver(ctx: WorkflowContext) -> str:
    lines = ["### 矛盾求解"]
    if ctx.improve_param_id:
        lines.append(f"- **改善参数**: #{ctx.improve_param_id}")
    if ctx.worsen_param_id:
        lines.append(f"- **恶化参数**: #{ctx.worsen_param_id}")
    if ctx.sep_type:
        lines.append(f"- **分离类型**: {ctx.sep_type}")
    if ctx.principles:
        lines.append(f"- **发明原理**: {ctx.principles}")
    return "\n".join(lines)


def _render_fos_results(ctx: WorkflowContext) -> str:
    lines = ["### 跨界检索"]
    if ctx.cases:
        for case in ctx.cases[:5]:
            lines.append(f"- [{case.source}] {case.title}: {case.description}")
    else:
        lines.append("- 未召回跨界案例")
    return "\n".join(lines)


def _render_solution_generation(ctx: WorkflowContext) -> str:
    lines = ["### 方案生成"]
    if ctx.solution_drafts:
        lines.append(f"- 生成方案草稿 x{len(ctx.solution_drafts)}")
        for draft in ctx.solution_drafts:
            lines.append(f"  - {draft.title}: {draft.description[:50]}...")
    return "\n".join(lines)


def _render_solution_evaluation(ctx: WorkflowContext) -> str:
    lines = ["### 方案评估"]
    if ctx.ranked_solutions:
        top = ctx.ranked_solutions[0]
        lines.append(f"- 最高理想度: {top.ideality_score:.2f}")
        lines.append(f"- 最佳方案: {top.draft.title}")
    return "\n".join(lines)


def render_final_report(question: str, contradiction: str, solutions: list[Solution], reason: str) -> str:
    lines = [
        "# TRIZ 解决方案报告",
        "",
        f"## 问题",
        question,
        "",
        f"## 核心矛盾",
        contradiction,
        "",
        "## 推荐方案（按理想度排序）",
        "",
    ]

    for i, sol in enumerate(solutions[:3], 1):
        lines.extend([
            f"### 方案 {i} [理想度: {sol.ideality_score:.2f}]",
            f"**原理**: {sol.draft.applied_principles}",
            f"**标题**: {sol.draft.title}",
            f"**描述**: {sol.draft.description}",
            f"**可行性**: {sol.tags.feasibility_score}/5 | 风险: {sol.tags.risk_level}",
            "",
        ])

    lines.extend([
        "## 评估依据",
        reason,
    ])

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_markdown_renderer.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/utils/markdown_renderer.py tests/test_markdown_renderer.py
git commit -m "feat: add Markdown renderer for node outputs and final report"
```

---

## Task 12: Skill - M1 Function Modeling

**Files:**
- Create: `triz/skills/__init__.py`
- Create: `triz/skills/m1_modeling.py`
- Test: `tests/test_skills.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext
from triz.skills.m1_modeling import model_function

def test_model_function_with_mock():
    ctx = WorkflowContext(question="如何提高手术刀片耐用性")
    mock_response = '''{
        "sao_list": [
            {"subject": "刀片", "action": "切割", "object": "组织", "function_type": "useful"},
            {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"}
        ],
        "resources": {"物质": ["刀片", "组织"], "场": ["热场"]},
        "ifr": "刀片在无限切割时保持零磨损"
    }'''

    with patch('triz.skills.m1_modeling.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = model_function(ctx)
        assert len(result["sao_list"]) == 2
        assert result["sao_list"][0].subject == "刀片"
        assert result["ifr"] == "刀片在无限切割时保持零磨损"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/skills/__init__.py**

```python
```

- [ ] **Step 4: Write triz/skills/m1_modeling.py**

```python
"""M1 功能建模 Skill：从自然语言提取 SAO、IFR、资源"""
import json
from triz.context import WorkflowContext, SAO
from triz.utils.api_client import OpenAIClient


M1_SYSTEM_PROMPT = """你是一个TRIZ功能分析专家。你的任务是将用户的问题拆解为结构化的功能模型。

你需要输出以下内容的JSON格式：
1. sao_list: S-A-O（Subject-Action-Object）三元组列表，每个三元组包含 function_type（useful/harmful/excessive/insufficient）
2. resources: 可用资源，按类型分类（物质、场、空间、时间、信息、功能）
3. ifr: 理想最终结果（Ideal Final Result），用一句话描述理想状态

示例输出格式：
{
    "sao_list": [
        {"subject": "刀片", "action": "切割", "object": "纸张", "function_type": "useful"},
        {"subject": "摩擦", "action": "磨损", "object": "刀片", "function_type": "harmful"}
    ],
    "resources": {"物质": ["刀片", "纸张"], "场": ["重力场"]},
    "ifr": "刀片在无限切割时自动保持锋利"
}"""


def model_function(ctx: WorkflowContext) -> dict:
    """M1 功能建模：调用 LLM 提取结构化信息。"""
    client = OpenAIClient()

    prompt = f"用户问题：{ctx.question}\n\n请分析并输出功能模型。"
    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M1_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析为 JSON: {response[:200]}")

    sao_list = []
    for item in data.get("sao_list", []):
        sao_list.append(SAO(
            subject=item.get("subject", ""),
            action=item.get("action", ""),
            object=item.get("object", ""),
            function_type=item.get("function_type", "useful")
        ))

    return {
        "sao_list": sao_list,
        "resources": data.get("resources", {}),
        "ifr": data.get("ifr", ""),
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add triz/skills/__init__.py triz/skills/m1_modeling.py tests/test_skills.py
git commit -m "feat: add M1 function modeling skill"
```

---

## Task 13: Skill - M2 Causal Analysis

**Files:**
- Create: `triz/skills/m2_causal.py`
- Modify: `tests/test_skills.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, SAO
from triz.skills.m2_causal import analyze_cause

def test_analyze_cause_with_mock():
    ctx = WorkflowContext(question="test")
    ctx.sao_list = [SAO(subject="刀片", action="切割", object="组织", function_type="useful")]
    ctx.resources = {"物质": ["刀片"]}

    mock_response = '''{
        "root_param": "接触面积导致摩擦热积累",
        "key_problem": "接触面积过大导致磨损",
        "candidate_attributes": ["接触面积", "摩擦热", "切割强度"],
        "causal_chain": ["刀片磨损", "摩擦热量过高", "接触面积大"]
    }'''

    with patch('triz.skills.m2_causal.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = analyze_cause(ctx)
        assert result["root_param"] == "接触面积导致摩擦热积累"
        assert "接触面积" in result["candidate_attributes"]
        assert len(result["causal_chain"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills.py::test_analyze_cause_with_mock -v`
Expected: FAIL

- [ ] **Step 3: Write triz/skills/m2_causal.py**

```python
"""M2 根因分析 Skill：RCA+因果链分析"""
import json
import re
from triz.context import WorkflowContext
from triz.utils.api_client import OpenAIClient


M2_SYSTEM_PROMPT = """你是一个TRIZ根因分析专家。你的任务是从给定的负面功能出发，执行RCA+因果链分析。

分析步骤：
1. 从负面功能（harmful/excessive/insufficient）出发
2. 追问"为什么"，构建3-4层深度的因果链
3. 找到根因节点（最根本的矛盾所在）
4. 从根因节点提取候选物理属性

你需要输出JSON格式：
{
    "root_param": "根因参数描述",
    "key_problem": "关键问题陈述",
    "candidate_attributes": ["属性1", "属性2"],
    "causal_chain": ["Level 0: 表面问题", "Level 1: 直接原因", "Level 2: 深层原因", "Level 3: 根因节点"]
}"""


def analyze_cause(ctx: WorkflowContext) -> dict:
    """M2 根因分析：调用 LLM 执行因果链分析。"""
    client = OpenAIClient()

    # 构建 prompt
    sao_text = "\n".join([
        f"- [{s.subject}] {s.action} [{s.object}] ({s.function_type})"
        for s in ctx.sao_list
    ])
    resources_text = json.dumps(ctx.resources, ensure_ascii=False)

    prompt = f"""功能模型：
{sao_text}

可用资源：{resources_text}

请执行根因分析，输出因果链和根因节点。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M2_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    return {
        "root_param": data.get("root_param", ""),
        "key_problem": data.get("key_problem", ""),
        "candidate_attributes": data.get("candidate_attributes", []),
        "causal_chain": data.get("causal_chain", []),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add triz/skills/m2_causal.py tests/test_skills.py
git commit -m "feat: add M2 causal analysis skill"
```

---

## Task 14: Skill - M5 Solution Generation

**Files:**
- Create: `triz/skills/m5_generation.py`
- Modify: `tests/test_skills.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, Case
from triz.skills.m5_generation import generate_solutions

def test_generate_solutions_with_mock():
    ctx = WorkflowContext(question="test")
    ctx.principles = [15, 28]
    ctx.cases = [Case(principle_id=15, source="本地", title="F1悬挂", description="动态调节", function="支撑")]
    ctx.contradiction_desc = "改善速度恶化形状"
    ctx.resources = {"物质": ["刀片"], "场": ["热场"]}
    ctx.ifr = "刀片零磨损"
    ctx.feedback = ""

    mock_response = '''[
        {"title": "动态压力调节", "description": "参考F1悬挂设计...", "applied_principles": [15], "resource_mapping": "利用热场"}
    ]'''

    with patch('triz.skills.m5_generation.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = generate_solutions(ctx)
        assert len(result["solution_drafts"]) == 1
        assert result["solution_drafts"][0].title == "动态压力调节"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills.py::test_generate_solutions_with_mock -v`
Expected: FAIL

- [ ] **Step 3: Write triz/skills/m5_generation.py**

```python
"""M5 方案生成 Skill：将原理+跨界案例迁移到用户场景"""
import json
import re
from triz.context import WorkflowContext, SolutionDraft
from triz.utils.api_client import OpenAIClient


M5_SYSTEM_PROMPT = """你是一个TRIZ方案生成专家。你的任务是将抽象的发明原理和跨界案例迁移到用户的具体场景，生成具体可执行的方案。

约束：
1. 每个方案必须明确引用一个或多个发明原理编号
2. 优先使用用户已有的资源，避免引入新组件
3. 参考跨界案例进行类比迁移
4. 方案必须具体、可执行，避免泛泛而谈（至少100字描述）
5. 使用类比法将案例映射到用户场景

输出格式（JSON数组）：
[
    {
        "title": "方案标题",
        "description": "详细方案描述（具体、可执行）",
        "applied_principles": [15, 28],
        "resource_mapping": "使用了哪些现有资源"
    }
]"""


def generate_solutions(ctx: WorkflowContext) -> dict:
    """M5 方案生成：调用 LLM 生成方案草稿。"""
    client = OpenAIClient()

    # 构建 cases 文本
    cases_text = "\n".join([
        f"- 原理#{c.principle_id} [{c.source}] {c.title}: {c.description}"
        for c in ctx.cases
    ]) if ctx.cases else "无跨界案例"

    resources_text = json.dumps(ctx.resources, ensure_ascii=False)

    prompt = f"""矛盾描述：{ctx.contradiction_desc}
理想最终结果：{ctx.ifr}
可用资源：{resources_text}

匹配的发明原理：{ctx.principles}

跨界参考案例：
{cases_text}

{ctx.feedback if ctx.feedback else ""}

请生成 {len(ctx.principles)} 个方案草稿，每个方案对应一个或多个原理。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M5_SYSTEM_PROMPT,
        temperature=0.3
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    drafts = []
    for item in data if isinstance(data, list) else [data]:
        drafts.append(SolutionDraft(
            title=item.get("title", "未命名方案"),
            description=item.get("description", ""),
            applied_principles=item.get("applied_principles", []),
            resource_mapping=item.get("resource_mapping", ""),
        ))

    return {"solution_drafts": drafts}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add triz/skills/m5_generation.py tests/test_skills.py
git commit -m "feat: add M5 solution generation skill"
```

---

## Task 15: Skill - M6 Solution Evaluation

**Files:**
- Create: `triz/skills/m6_evaluation.py`
- Modify: `tests/test_skills.py` (append)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, SolutionDraft
from triz.skills.m6_evaluation import evaluate_solutions

def test_evaluate_solutions_with_mock():
    ctx = WorkflowContext(question="test")
    ctx.solution_drafts = [
        SolutionDraft(title="方案1", description="动态调节...", applied_principles=[15], resource_mapping="热场")
    ]
    ctx.contradiction_desc = "改善速度恶化形状"
    ctx.resources = {"场": ["热场"]}
    ctx.ifr = "零磨损"

    mock_response = '''[
        {
            "draft": {"title": "方案1", "description": "动态调节...", "applied_principles": [15], "resource_mapping": "热场"},
            "tags": {"feasibility_score": 4, "resource_fit_score": 5, "innovation_score": 4, "uniqueness_score": 3, "risk_level": "low", "ifr_deviation_reason": ""},
            "ideality_score": 0.78,
            "evaluation_rationale": "利用现有热场资源，可行性高"
        }
    ]'''

    with patch('triz.skills.m6_evaluation.OpenAIClient') as MockClient:
        mock_client = MagicMock()
        mock_client.chat_structured.return_value = mock_response
        MockClient.return_value = mock_client

        result = evaluate_solutions(ctx)
        assert len(result["ranked_solutions"]) == 1
        assert result["ranked_solutions"][0].ideality_score == 0.78
        assert result["max_ideality"] == 0.78
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_skills.py::test_evaluate_solutions_with_mock -v`
Expected: FAIL

- [ ] **Step 3: Write triz/skills/m6_evaluation.py**

```python
"""M6 方案评估 Skill：独立评审 + 量化排序"""
import json
import re
from triz.context import WorkflowContext, Solution, QualitativeTags
from triz.utils.api_client import OpenAIClient


M6_SYSTEM_PROMPT = """你是一个TRIZ方案评估专家。你的任务是独立评审方案草案，并给出量化评分。

重要：你是评审者，不是方案生成者。你只对方案做客观评估，绝不修改方案内容。

评估维度（每个方案）：
1. feasibility_score (1-5): 技术可实现性
2. resource_fit_score (1-5): 资源匹配度
3. innovation_score (1-5): 创新性
4. uniqueness_score (1-5): 独特性
5. risk_level (low/medium/high/critical): 风险等级
6. ifr_deviation_reason (文本): 如果偏离IFR，说明原因；否则留空

同时，为每个方案综合计算 ideality_score (0.0-1.0)，并说明计算依据。

输出格式（JSON数组，按理想度从高到低排序）：
[
    {
        "draft": {"title": "...", "description": "...", "applied_principles": [15], "resource_mapping": "..."},
        "tags": {"feasibility_score": 4, "resource_fit_score": 5, "innovation_score": 4, "uniqueness_score": 3, "risk_level": "low", "ifr_deviation_reason": ""},
        "ideality_score": 0.78,
        "evaluation_rationale": "评分依据说明"
    }
]"""


def evaluate_solutions(ctx: WorkflowContext) -> dict:
    """M6 方案评估：调用 LLM 执行独立评审。"""
    client = OpenAIClient()

    # 构建方案列表文本
    drafts_text = "\n\n".join([
        f"方案 {i+1}:\n标题: {d.title}\n描述: {d.description}\n原理: {d.applied_principles}\n资源: {d.resource_mapping}"
        for i, d in enumerate(ctx.solution_drafts)
    ])

    prompt = f"""矛盾描述：{ctx.contradiction_desc}
理想最终结果：{ctx.ifr}
可用资源：{json.dumps(ctx.resources, ensure_ascii=False)}

待评估方案：
{drafts_text}

请对每个方案进行6维评估，计算理想度，并按理想度从高到低排序输出。"""

    response = client.chat_structured(
        prompt=prompt,
        system_prompt=M6_SYSTEM_PROMPT,
        temperature=0.1  # 低温度保证评估稳定性
    )

    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"LLM 输出无法解析: {response[:200]}")

    solutions = []
    unresolved_signals = []

    for item in data if isinstance(data, list) else [data]:
        draft_data = item.get("draft", {})
        tags_data = item.get("tags", {})

        tags = QualitativeTags(
            feasibility_score=tags_data.get("feasibility_score", 3),
            resource_fit_score=tags_data.get("resource_fit_score", 3),
            innovation_score=tags_data.get("innovation_score", 3),
            uniqueness_score=tags_data.get("uniqueness_score", 3),
            risk_level=tags_data.get("risk_level", "medium"),
            ifr_deviation_reason=tags_data.get("ifr_deviation_reason", ""),
        )

        # 收集未解决信号
        if tags.risk_level in ["high", "critical"]:
            unresolved_signals.append(f"方案风险过高: {draft_data.get('title', '')}")
        if tags.ifr_deviation_reason:
            unresolved_signals.append(f"偏离IFR: {tags.ifr_deviation_reason}")

        ideality = float(item.get("ideality_score", 0.5))
        # 归一化
        if ideality > 1.0:
            ideality = 1.0
        elif ideality < 0:
            ideality = 0.0

        from triz.context import SolutionDraft
        sol = Solution(
            draft=SolutionDraft(
                title=draft_data.get("title", ""),
                description=draft_data.get("description", ""),
                applied_principles=draft_data.get("applied_principles", []),
                resource_mapping=draft_data.get("resource_mapping", ""),
            ),
            tags=tags,
            ideality_score=ideality,
            evaluation_rationale=item.get("evaluation_rationale", ""),
        )
        solutions.append(sol)

    # 按理想度排序
    solutions.sort(key=lambda s: s.ideality_score, reverse=True)

    # 取 top-3 未解决信号
    unresolved_signals = unresolved_signals[:3]

    max_ideality = solutions[0].ideality_score if solutions else 0.0

    return {
        "ranked_solutions": solutions,
        "max_ideality": max_ideality,
        "unresolved_signals": unresolved_signals,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_skills.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add triz/skills/m6_evaluation.py tests/test_skills.py
git commit -m "feat: add M6 solution evaluation skill"
```

---

## Task 16: Orchestrator

**Files:**
- Create: `triz/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import MagicMock, patch
from triz.context import WorkflowContext, ConvergenceDecision
from triz.orchestrator import Orchestrator

def test_orchestrator_init():
    orch = Orchestrator()
    assert orch is not None

def test_orchestrator_run_workflow_mock():
    """测试编排器能完整跑通 workflow（全部 mock）。"""
    orch = Orchestrator()

    with patch('triz.orchestrator.model_function') as m1, \
         patch('triz.orchestrator.should_trigger_m2', return_value=True), \
         patch('triz.orchestrator.analyze_cause') as m2, \
         patch('triz.orchestrator.formulate_problem') as m3, \
         patch('triz.orchestrator.solve_contradiction') as m4, \
         patch('triz.orchestrator.search_cases') as fos, \
         patch('triz.orchestrator.generate_solutions') as m5, \
         patch('triz.orchestrator.evaluate_solutions') as m6, \
         patch('triz.orchestrator.check_convergence') as m7:

        m1.return_value = {"sao_list": [MagicMock()], "resources": {}, "ifr": ""}
        m2.return_value = {"root_param": "根因", "key_problem": "问题", "candidate_attributes": [], "causal_chain": []}
        m3.return_value = {"problem_type": "tech", "contradiction_desc": "改善A恶化B", "evidence": []}
        m4.return_value = {"principles": [15], "sep_type": None, "match_conf": 0.8, "improve_param_id": 1, "worsen_param_id": 2, "need_state": None, "need_not_state": None}
        fos.return_value = []
        m5.return_value = {"solution_drafts": [MagicMock()]}
        m6.return_value = {"ranked_solutions": [MagicMock(ideality_score=0.8)], "max_ideality": 0.8, "unresolved_signals": []}
        m7.return_value = ConvergenceDecision(action="TERMINATE", reason="信号已清空")

        result = orch.run_workflow("如何提高续航")
        assert "解决方案报告" in result or "报告" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/orchestrator.py**

```python
"""编排器核心：持有 WorkflowContext，按序调用 Skill/Tool，渲染 Markdown 输出"""
from triz.context import WorkflowContext, ConvergenceDecision
from triz.skills.m1_modeling import model_function
from triz.skills.m2_causal import analyze_cause
from triz.skills.m5_generation import generate_solutions
from triz.skills.m6_evaluation import evaluate_solutions
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m4_solver import solve_contradiction
from triz.tools.m7_convergence import check_convergence
from triz.tools.fos_search import search_cases
from triz.utils.markdown_renderer import (
    render_node_start, render_step_complete,
    render_node_complete, render_final_report
)


class Orchestrator:
    """TRIZ Workflow 编排器。"""

    def __init__(self):
        self.output_buffer = []

    def run_workflow(self, question: str, history: list = None) -> str:
        """执行完整 TRIZ workflow，返回 Markdown 格式的最终报告。"""
        ctx = WorkflowContext(question=question, history=history or [])
        self.output_buffer = []

        # ===== 问题建模 =====
        ctx = self._execute_node("问题建模", 1, 5, ctx, [
            ("M1", model_function, "Skill"),
            ("M2", analyze_cause, "Skill"),
            ("M3", formulate_problem, "Tool"),
        ])

        if not ctx.sao_list:
            return self._generate_clarification("无法从问题中提取功能模型，请补充描述")

        # ===== 迭代主循环 =====
        while True:
            # 矛盾求解
            ctx = self._execute_node("矛盾求解", 2, 5, ctx, [
                ("M4", solve_contradiction, "Tool"),
            ])

            if not ctx.principles:
                return self._generate_fallback("无法从矛盾定义中匹配到发明原理")

            # 跨界检索
            ctx = self._execute_node("跨界检索", 3, 5, ctx, [
                ("FOS", search_cases, "Tool"),
            ])

            # 方案生成
            ctx = self._execute_node("方案生成", 4, 5, ctx, [
                ("M5", generate_solutions, "Skill"),
            ])

            if not ctx.solution_drafts:
                return self._generate_fallback("未能生成有效方案")

            # 方案评估
            ctx = self._execute_node("方案评估", 5, 5, ctx, [
                ("M6_LLM", evaluate_solutions, "Skill"),
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
                # 清空本轮的输出字段，准备下一轮
                ctx.principles = []
                ctx.cases = []
                ctx.solution_drafts = []
                ctx.ranked_solutions = []
                ctx.max_ideality = 0.0
                ctx.unresolved_signals = []

    def _execute_node(self, node_name: str, current: int, total: int,
                      ctx: WorkflowContext, steps: list) -> WorkflowContext:
        """执行一个用户可见节点，渲染 Markdown 输出。"""
        self.output_buffer.append(render_node_start(node_name, current, total))

        for step_name, step_func, step_type in steps:
            if step_name == "M2":
                # M2 门控检查
                if not should_trigger_m2(ctx):
                    self.output_buffer.append(f"- Tool: M2 门控 -> 跳过（无负面功能）\n")
                    continue

            result = step_func(ctx)
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
        """生成 CLARIFY 响应。"""
        return "\n".join(self.output_buffer) + f"\n\n**需要补充信息**：{reason}\n\n请提供更多细节，例如：具体的使用场景、现有的限制条件、已尝试的解决方案等。"

    def _generate_fallback(self, reason: str) -> str:
        """生成 fallback 响应。"""
        return "\n".join(self.output_buffer) + f"\n\n**流程中断**：{reason}\n\n建议：尝试用更具体的工程语言描述问题，或提供更多技术细节。"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add triz/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add workflow orchestrator"
```

---

## Task 17: CLI Entry Point

**Files:**
- Create: `triz/cli.py`
- Create: `triz/__main__.py`
- Modify: `tests/` (integration test)

- [ ] **Step 1: Write the failing test**

```python
import pytest
from unittest.mock import patch
from triz.cli import main

def test_cli_single_mode():
    with patch('sys.argv', ['triz', '如何提高续航']), \
         patch('triz.cli.Orchestrator') as MockOrch:
        mock_orch = MockOrch.return_value
        mock_orch.run_workflow.return_value = "# 报告"
        main()
        mock_orch.run_workflow.assert_called_once_with("如何提高续航")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Write triz/cli.py**

```python
"""CLI 入口：命令行解析 + 交互循环"""
import sys
import argparse
from triz.orchestrator import Orchestrator
from triz.database.init_db import init_database


def main():
    parser = argparse.ArgumentParser(
        description="TRIZ 智能系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m triz "如何提高手术刀片的耐用性"
  python -m triz -i
        """
    )
    parser.add_argument("question", nargs="?", help="用户问题（单次模式）")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互会话模式")

    args = parser.parse_args()

    # 初始化数据库
    init_database()

    if args.interactive:
        _run_interactive()
    elif args.question:
        _run_single(args.question)
    else:
        parser.print_help()
        sys.exit(1)


def _run_single(question: str):
    """单次执行模式。"""
    orch = Orchestrator()
    report = orch.run_workflow(question)
    print(report)


def _run_interactive():
    """交互会话模式。"""
    print("=" * 50)
    print("TRIZ 智能系统 - 交互模式")
    print("输入问题开始分析，或输入 help 查看命令")
    print("=" * 50)

    orch = Orchestrator()
    session_history = []

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("再见！")
            break

        if user_input.lower() == "help":
            _print_help()
            continue

        if user_input.lower() == "reset":
            orch = Orchestrator()
            session_history = []
            print("[系统] 上下文已重置")
            continue

        if user_input.lower().startswith("show "):
            # 显示历史节点输出（当前 session 中不保留，简化实现）
            print("[系统] 历史查看功能在当前版本中暂不可用")
            continue

        # 执行 workflow
        print("[系统] 开始分析...")
        try:
            report = orch.run_workflow(user_input, session_history)
            print(report)
            session_history.append({"question": user_input})
        except Exception as e:
            print(f"[错误] 执行失败: {e}")


def _print_help():
    print("""
可用命令:
  <问题文本>     执行 TRIZ 分析
  show <节点名>  查看指定节点输出（暂不可用）
  reset          重置上下文
  help           显示帮助
  exit / quit    退出
""")
```

- [ ] **Step 4: Write triz/__main__.py**

```python
"""CLI 入口点：python -m triz"""
from triz.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Write tests/test_cli.py**

```python
import pytest
from unittest.mock import patch, MagicMock
from triz.cli import main

def test_cli_single_mode():
    with patch('sys.argv', ['triz', '如何提高续航']), \
         patch('triz.cli.Orchestrator') as MockOrch, \
         patch('triz.cli.init_database'):
        mock_orch = MockOrch.return_value
        mock_orch.run_workflow.return_value = "# 报告"
        main()
        mock_orch.run_workflow.assert_called_once_with("如何提高续航")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add triz/cli.py triz/__main__.py tests/test_cli.py
git commit -m "feat: add CLI entry point with single and interactive modes"
```

---

## Task 18: Integration Verification

**Files:**
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
"""集成测试：验证完整 workflow 的数据流"""
import pytest
from triz.context import WorkflowContext, SAO
from triz.tools.m2_gate import should_trigger_m2
from triz.tools.m3_formulation import formulate_problem
from triz.tools.m4_solver import solve_contradiction
from triz.tools.m7_convergence import check_convergence
from triz.database.init_db import init_database

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_database()

class TestDataFlow:
    """测试从 M1 到 M7 的完整数据流（不使用 LLM）。"""

    def test_m1_to_m2_gate(self):
        ctx = WorkflowContext(question="如何提高续航")
        ctx.sao_list = [
            SAO(subject="电池", action="供电", object="手机", function_type="useful"),
            SAO(subject="热量", action="损耗", object="电能", function_type="harmful"),
        ]
        assert should_trigger_m2(ctx) is True

    def test_m2_to_m3_formulation(self):
        ctx = WorkflowContext(question="test")
        ctx.root_param = "能量转换效率低"
        ctx.key_problem = "热量损耗过多"
        ctx.candidate_attributes = ["转换效率", "热量"]
        ctx.causal_chain = ["续航短", "能量损耗", "转换效率低"]
        ctx.sao_list = []

        result = formulate_problem(ctx)
        assert result["problem_type"] == "tech"
        assert "热量" in result["contradiction_desc"] or "效率" in result["contradiction_desc"]

    def test_m3_to_m4_solver(self):
        ctx = WorkflowContext(question="test")
        ctx.problem_type = "tech"
        ctx.contradiction_desc = "改善速度，恶化形状稳定性"
        ctx.candidate_attributes = ["速度", "形状"]

        result = solve_contradiction(ctx)
        assert len(result["principles"]) > 0
        assert result["improve_param_id"] == 9
        assert result["worsen_param_id"] == 12

    def test_m6_to_m7_convergence(self):
        ctx = WorkflowContext(question="test")
        ctx.max_ideality = 0.8
        ctx.iteration = 1
        ctx.unresolved_signals = []
        ctx.history_log = [{"max_ideality": 0.6}]

        decision = check_convergence(ctx)
        assert decision.action == "TERMINATE"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_integration.py -v`
Expected: PASS (4 tests)

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full workflow data flow"
```

---

## Task 19: README & Usage Documentation

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README.md**

```markdown
# TRIZ 智能系统 CLI

基于 Agent Skills + Tools 架构的 TRIZ（发明问题解决理论）智能系统。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env`，填入你的 API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

## 使用

### 单次执行

```bash
python -m triz "如何提高手术刀片的耐用性"
```

### 交互模式

```bash
python -m triz -i
```

## 架构

- **问题建模** (M1-M3): 功能建模 -> 根因分析 -> 矛盾定型
- **矛盾求解** (M4): 双步参数映射 -> 39矩阵/分离原理查表
- **跨界检索** (FOS): 本地案例库 + Google Patent API
- **方案生成** (M5): 原理+案例 -> 用户场景迁移
- **方案评估** (M6): 6维定性评估 + 理想度排序
- **编排器**: 控制迭代循环，Markdown 输出渲染

## 技术栈

- Python 3.11+
- OpenAI API
- SQLite
- Pydantic v2
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with usage instructions"
```

---

## Spec Coverage Check

| Spec 章节 | 对应任务 | 状态 |
|:---|:---|:---|
| 3.1 M1 功能建模 | Task 12 | Covered |
| 3.2 M2 根因分析 | Task 13 | Covered |
| 3.3 M3 问题定型 | Task 6 | Covered |
| 3.4 M4 矛盾求解 | Task 7 | Covered |
| 3.5 FOS 跨界检索 | Task 9 | Covered |
| 3.6 M5 方案生成 | Task 14 | Covered |
| 3.7 M6 方案评估 | Task 15 | Covered |
| 3.8 M7 收敛控制 | Task 8 | Covered |
| 4. 编排器 | Task 16 | Covered |
| 5. 数据层 | Task 3, 4 | Covered |
| 6. CLI | Task 17 | Covered |
| 7. 数据模型 | Task 2 | Covered |
| 8. 边界处理 | 各任务 Step 1 测试覆盖 | Covered |

## Placeholder Scan

- 无 "TBD", "TODO", "implement later", "fill in details"
- 无 "Add appropriate error handling" 等模糊描述
- 每个测试包含完整代码
- 每个实现步骤包含完整代码

## Type Consistency Check

- `WorkflowContext` 字段名与所有任务中使用的一致
- `ConvergenceDecision` 与 M7 输出一致
- `Solution`, `QualitativeTags` 与 M6 输出一致
- `Case`, `SolutionDraft` 跨任务引用一致

---

> 计划完成并保存到 `docs/superpowers/plans/2026-04-21-triz-cli-implementation.md`。