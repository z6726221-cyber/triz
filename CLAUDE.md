# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TRIZ Intelligent System — Python monorepo with two independent approaches to automated TRIZ (Theory of Inventive Problem Solving) analysis. Accepts engineering problems in Chinese, produces structured TRIZ solution reports.

## Commands

### Running
```bash
triz                          # Agent mode (default) interactive TUI
triz --pipeline               # Pipeline mode interactive TUI
triz -q "问题描述"              # Single-shot
triz -f problem.txt           # From file

# Or via python -m (works from any directory)
python -m triz_agent          # Agent
python -m triz_pipeline       # Pipeline
python -m triz_agent -q "..." # Agent single-shot
```

### Testing
```bash
cd triz_agent && python -m pytest tests/ -v
cd triz_pipeline && python -m pytest tests/ -v
python -m pytest tests/test_tools.py -v  # Single file

# Pipeline e2e (in triz_pipeline/scripts/)
python e2e_test.py orchestrator
python normal_test.py
```

### Setup (after venv rebuild)
```bash
.venv\Scripts\activate
pip install -e triz_agent -e triz_pipeline -e .
python setup_commands.py  # Creates triz/triz_agent/triz_pipeline .cmd files
```

## Architecture

Two independent packages implementing the same TRIZ workflow (M1→M2→M3→M4→M5→M6) with different execution strategies:

### triz_agent — ReAct Autonomous Agent
- LLM decides next action at each step via `TrizAgent` (agent/agent.py)
- Skills return **Markdown strings**, accumulated in agent memory
- Flexible: can skip steps, retry, make autonomous decisions
- State machine governs valid transitions (agent/state_machine.py)

### triz_pipeline — Deterministic Orchestrator
- Fixed 4-node workflow via `Orchestrator` (orchestrator/orchestrator.py)
- Skills return **Pydantic models**, merged into `WorkflowContext`
- Convergence control loop with 7-threshold termination (tools/m7_convergence.py)
- More deterministic, structured output, easier to debug

### Duplicated Components (independent copies, no cross-dependencies)
- `WorkflowContext` (context.py) — Identical Pydantic model in both packages
- `tools/` — Same tool implementations (solve_contradiction, query_parameters, query_matrix, query_separation, fos_search, input_classifier)
- `database/` — SQLite with 39 TRIZ parameters, 40 principles, contradiction matrix, separation rules
- `cli.py` — Rich TUI with `/new`, `/save`, `/history`, `/show`, `/help`, `/exit`
- Skills load prompts from `SKILL.md` files (YAML frontmatter + Markdown body), with progressive disclosure via `references/` subdirectories

### Key Pattern: Skill Auto-Discovery
Both registries use `importlib` to find `handler.py` in skill subdirectories. Each skill has a `SKILL.md` prompt file. Agent skills return Markdown; Pipeline skills return Pydantic models.

### Key Pattern: Per-Skill Model Routing
Each skill (m1-m6) can use a different LLM model via `MODEL_M*` env vars in `.env`.

## Configuration

Both packages use `.env` files with:
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` — LLM API (uses SDU proxy)
- `MODEL_NAME` — Main model
- `MODEL_M1` through `MODEL_M6` — Per-skill model overrides
- `SERP_API_KEY` — Google Patents search
- `AGENT_*` vars — Agent-specific config (optional, fallback to OPENAI_*)

Database auto-created at `triz_*/data/triz_knowledge.db` on first run.

## Important Notes

- **Chinese-first**: All user-facing text, SKILL.md prompts, and TRIZ data are in Chinese
- **Windows-focused**: setup_commands.py creates .cmd files, CLI handles Windows encoding
- **No linter/formatter configured** in the project
- **sentence-transformers** is lazy-loaded (~100MB model: paraphrase-multilingual-MiniLM-L12-v2)
- **triz_agent and triz_pipeline are completely independent** — no cross-dependencies between them
- `triz_wrapper.py` at root provides unified `triz` command (defaults to Agent, `--pipeline` switches)
