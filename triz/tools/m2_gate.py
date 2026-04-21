"""M2 门控 Tool：判断是否需要触发根因分析"""
from triz.context import WorkflowContext


def should_trigger_m2(ctx: WorkflowContext) -> bool:
    """默认触发，仅当无 SAO 或全为 Useful 功能时跳过。"""
    if not ctx.sao_list:
        return False

    for sao in ctx.sao_list:
        if sao.function_type in ("harmful", "excessive", "insufficient"):
            return True

    return False
