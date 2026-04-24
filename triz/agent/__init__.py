"""约束式自主 Agent：状态机 + LLM 决策的 TRIZ 工作流编排。"""
from triz.agent.agent import TrizAgent
from triz.agent.state_machine import STATE_MACHINE, is_valid_transition

__all__ = ["TrizAgent", "STATE_MACHINE", "is_valid_transition"]