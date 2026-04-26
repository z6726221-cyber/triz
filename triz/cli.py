"""CLI 入口：rich + prompt_toolkit 交互式 TUI。"""
import sys
import os
import argparse
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style
from rich import box
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import radiolist_dialog

from triz.orchestrator import Orchestrator
from triz.tools.registry import register_default_tools
from triz.agent import TrizAgent
from triz.database.init_db import init_database

# 修复 Windows 终端中文编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── ASCII Logo ──────────────────────────────────────────
LOGO = """
████████╗██████╗ ██╗███████╗
╚══██╔══╝██╔══██╗██║╚══███╔╝
   ██║   ██████╔╝██║  ███╔╝
   ██║   ██╔══██╗██║ ███╔╝
   ██║   ██║  ██║██║███████╗
   ╚═╝   ╚═╝  ╚═╝╚═╝╚══════╝
""".strip()

WELCOME = """TRIZ 智能系统 — 交互模式
输入问题开始分析，或 /help 查看命令"""

# ── 配色方案 ────────────────────────────────────────────
STYLE_SKILL = Style(color="cyan", bold=True)
STYLE_TOOL = Style(color="green", bold=True)
STYLE_ORCHESTRATOR = Style(color="yellow", bold=True)
STYLE_ERROR = Style(color="red", bold=True)
STYLE_SUCCESS = Style(color="bright_green", bold=True)
STYLE_INFO = Style(color="bright_black")


class TRIZConsole:
    """TRIZ 交互式控制台。"""

    def __init__(self, use_agent: bool = False):
        self.console = Console()
        self.session = None  # 延迟初始化
        self.orch = None
        self.use_agent = use_agent
        self.session_history = []
        self.last_report = ""
        self._nodes = []  # 当前轮次的节点输出缓存

    def _get_session(self):
        if self.session is None:
            self.session = PromptSession(
                message="> ",
                multiline=False,
            )
        return self.session

    def show_welcome(self):
        self.console.print(LOGO, style="bold bright_cyan")
        self.console.print(WELCOME, style=STYLE_INFO)
        self.console.print()

    def run(self):
        init_database()
        self.show_welcome()

        # 检测终端是否支持 prompt_toolkit
        use_prompt_toolkit = sys.stdin.isatty()
        if use_prompt_toolkit:
            try:
                self._get_session()
            except Exception:
                use_prompt_toolkit = False
                self.console.print(
                    "[提示] 当前终端不支持高级交互，已回退到基础输入模式",
                    style=STYLE_INFO,
                )

        while True:
            try:
                if use_prompt_toolkit:
                    try:
                        with patch_stdout():
                            user_input = self._get_session().prompt().strip()
                    except Exception:
                        user_input = self._get_session().prompt().strip()
                else:
                    user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n再见！", style=STYLE_INFO)
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                should_exit = self._handle_command(user_input)
                if should_exit:
                    break
                continue

            # 执行 TRIZ 分析
            self._run_analysis(user_input)

    def _handle_command(self, cmd: str) -> bool:
        """处理 /cmd 命令。返回 True 表示退出程序。"""
        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action in ("/exit", "/quit", "/q"):
            self.console.print("再见！", style=STYLE_INFO)
            return True

        elif action == "/new":
            self.orch = None
            self.session_history = []
            self.console.print("[系统] 已重置上下文", style=STYLE_INFO)

        elif action == "/switch":
            self._switch_mode()

        elif action == "/save":
            self._save_report(arg)

        elif action == "/history":
            self._show_history()

        elif action == "/show":
            self._show_node(arg)

        elif action in ("/help", "/?"):
            self._show_help()

        else:
            self.console.print(f"[错误] 未知命令: {action}，输入 /help 查看列表", style=STYLE_ERROR)

        return False

    def _show_help(self):
        help_text = """
[bold]可用命令[/bold]
  [cyan]/new[/cyan]              开始新对话，重置上下文
  [cyan]/switch[/cyan]            切换编排模式（弹出选择框）
  [cyan]/save [文件名][/cyan]      保存最终报告（默认: report.md）
  [cyan]/history[/cyan]           显示本轮所有节点输出
  [cyan]/show <节点名>[/cyan]      查看指定节点详情（如 /show M1）
  [cyan]/help, /?[/cyan]          显示此帮助
  [cyan]/exit, /quit[/cyan]       退出程序

[dim]直接输入问题即可执行 TRIZ 分析[/dim]
"""
        self.console.print(help_text)

    def _switch_mode(self):
        """通过 RadioList 对话框切换编排模式。"""
        try:
            result = radiolist_dialog(
                title="选择编排模式",
                text="切换后下次分析生效",
                values=[
                    (False, "标准流程（Orchestrator 硬编码）"),
                    (True,  "自主决策（Agent 自主调用）"),
                ],
                default=self.use_agent,
            ).run()

            if result is not None:
                self.use_agent = result
                self.orch = None
                mode = "自主决策" if self.use_agent else "标准流程"
                self.console.print(f"[系统] 已切换到 {mode} 模式", style=STYLE_SUCCESS)
        except Exception as e:
            # RadioList 在不支持 TUI 的终端会报错，回退到简单切换
            self.use_agent = not self.use_agent
            self.orch = None
            mode = "自主决策" if self.use_agent else "标准流程"
            self.console.print(f"[系统] 已切换到 {mode} 模式", style=STYLE_SUCCESS)

    def _save_report(self, filename: str):
        if not self.last_report:
            self.console.print("[错误] 暂无报告可保存，先执行一次分析", style=STYLE_ERROR)
            return

        filename = filename or "report.md"
        if not filename.endswith(".md"):
            filename += ".md"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.last_report)
            self.console.print(f"[系统] 报告已保存: {os.path.abspath(filename)}", style=STYLE_SUCCESS)
        except Exception as e:
            self.console.print(f"[错误] 保存失败: {e}", style=STYLE_ERROR)

    def _show_history(self):
        if not self._nodes:
            self.console.print("[系统] 当前无节点记录", style=STYLE_INFO)
            return

        for node in self._nodes:
            self._render_node(node, compact=True)

    def _show_node(self, node_name: str):
        node_name = node_name.strip().lower()
        found = False
        for node in self._nodes:
            if node.get("node_name", "").lower() == node_name:
                self._render_node(node, compact=False)
                found = True
        if not found:
            available = ", ".join(n.get("node_name", "") for n in self._nodes)
            self.console.print(f"[错误] 未找到节点 '{node_name}'。可用: {available}", style=STYLE_ERROR)

    def _run_analysis(self, question: str):
        """执行 TRIZ 分析，通过回调实时更新 UI。"""
        self._nodes = []
        self.last_report = ""

        if self.orch is None:
            if self.use_agent:
                self.orch = TrizAgent(tool_registry=register_default_tools(), callback=self._on_event)
                mode = "Agent 自主决策"
            else:
                self.orch = Orchestrator(callback=self._on_event)
                mode = "Orchestrator 硬编码"
            self.console.print(f"[模式] {mode}", style=STYLE_INFO)

        self.console.print()
        self.console.print(f"[分析开始] {datetime.now().strftime('%H:%M:%S')}", style=STYLE_INFO)
        self.console.print()

        try:
            if self.use_agent:
                report = self.orch.run(question, self.session_history)
            else:
                report = self.orch.run_workflow(question, self.session_history)
            self.last_report = report
        except Exception as e:
            self.console.print(f"\n[错误] 执行失败: {e}", style=STYLE_ERROR)

        self.session_history.append({"question": question})

    def _on_event(self, event_type: str, data: dict):
        """Orchestrator/Agent 回调：根据事件类型更新 UI。"""
        if event_type == "node_start":
            # Orchestrator 用 current/total，Agent 用 from_state/to_state
            node = {
                "node_name": data.get("node_name", data.get("to_state", "未知")),
                "current": data.get("current", 0),
                "total": data.get("total", 0),
                "steps": [],
                "status": "running",
            }
            self._nodes.append(node)
            self._render_node(node)

        elif event_type == "step_start":
            if self._nodes:
                step_info = {
                    "step_name": data["step_name"],
                    "step_type": data["step_type"],
                    "status": "running",
                }
                # Agent 模式下有 thought
                if "agent_thought" in data:
                    step_info["thought"] = data["agent_thought"]
                self._nodes[-1]["steps"].append(step_info)
                self._render_node(self._nodes[-1])

        elif event_type == "step_complete":
            if self._nodes and self._nodes[-1]["steps"]:
                step = self._nodes[-1]["steps"][-1]
                step["status"] = "done"
                step["result"] = data.get("result", {})
                # Gate skip 标记
                result = data.get("result", {})
                if isinstance(result, dict) and result.get("skipped"):
                    step["skipped"] = True
            self._render_node(self._nodes[-1])

        elif event_type == "step_error":
            if self._nodes and self._nodes[-1]["steps"]:
                step = self._nodes[-1]["steps"][-1]
                step["status"] = "error"
                step["error"] = data.get("error", "未知错误")
            self._render_node(self._nodes[-1])

        elif event_type == "node_complete":
            if self._nodes:
                self._nodes[-1]["status"] = "done"
                self._nodes[-1]["ctx"] = data.get("ctx")
            self._render_node(self._nodes[-1])

        elif event_type == "decision":
            self._render_decision(data)

        elif event_type == "report":
            # 最终报告单独渲染
            self._render_report(data["content"])

    def _render_node(self, node: dict, compact: bool = False):
        """渲染单个节点 Panel。"""
        name = node.get("node_name", "未知")
        current = node.get("current", 0)
        total = node.get("total", 0)
        steps = node.get("steps", [])
        status = node.get("status", "running")

        # 构建步骤列表
        step_lines = []
        for step in steps:
            sname = step.get("step_name", "")
            stype = step.get("step_type", "")
            sstatus = step.get("status", "")

            if stype == "Skill":
                icon = "[cyan]●[/cyan]"
            elif stype == "Tool":
                icon = "[green]●[/green]"
            elif stype == "Gate":
                icon = "[yellow]●[/yellow]"
            else:
                icon = "●"

            if sstatus == "running":
                line = f"{icon} {sname} [dim]...[/dim]"
            elif sstatus == "error":
                err = step.get("error", "")
                line = f"{icon} {sname} [red]✗ {err}[/red]"
            elif sstatus == "done":
                result = step.get("result", {})
                if step.get("skipped"):
                    line = f"{icon} {sname} [yellow]⏭ 跳过[/yellow]"
                else:
                    line = f"{icon} {sname} [green]✓[/green]"
            else:
                line = f"{icon} {sname}"

            step_lines.append(line)

        # 如果节点完成且不是紧凑模式，添加节点输出摘要
        if status == "done" and not compact:
            ctx = node.get("ctx")
            if ctx:
                summary = self._node_summary(node["node_name"], ctx)
                if summary:
                    step_lines.append("")
                    step_lines.append(summary)

        content = "\n".join(step_lines) if step_lines else "[dim]分析中...[/dim]"

        border_style = "cyan" if status == "done" else "yellow"
        title = f"[bold]节点 {current}/{total}[/bold] {name}"

        panel = Panel(
            content,
            title=title,
            border_style=border_style,
            box=box.ROUNDED,
        )

        # 清除之前的渲染（简化：每次都重新打印）
        # 实际 TUI 应该用 Live，但为了简单起见，直接打印
        self.console.print(panel)

    def _node_summary(self, node_name: str, ctx) -> str:
        """生成节点完成后的摘要。"""
        lines = []

        if node_name == "问题建模":
            if ctx.sao_list:
                lines.append("[bold]功能建模[/bold]")
                for sao in ctx.sao_list:
                    lines.append(f"  [{sao.subject}] → [{sao.action}] → [{sao.object}] ({sao.function_type})")
            if ctx.ifr:
                lines.append(f"  IFR: {ctx.ifr}")
            if ctx.root_param:
                lines.append(f"\n[bold]根因[/bold]: {ctx.root_param}")
            if ctx.contradiction_desc:
                lines.append(f"\n[bold]矛盾[/bold]: {ctx.contradiction_desc}")

        elif node_name == "矛盾求解":
            if ctx.improve_param_id:
                lines.append(f"改善参数: #{ctx.improve_param_id}")
            if ctx.worsen_param_id:
                lines.append(f"恶化参数: #{ctx.worsen_param_id}")
            if ctx.sep_type:
                lines.append(f"分离类型: {ctx.sep_type}")
            if ctx.principles:
                lines.append(f"发明原理: {ctx.principles}")

        elif node_name == "跨界检索":
            if ctx.cases:
                lines.append(f"召回 {len(ctx.cases)} 条案例")
                for case in ctx.cases[:3]:
                    lines.append(f"  [{case.source}] {case.title}")

        elif node_name == "方案生成":
            if ctx.solution_drafts:
                lines.append(f"生成 {len(ctx.solution_drafts)} 个方案")
                for draft in ctx.solution_drafts:
                    lines.append(f"  • {draft.title}")

        elif node_name == "方案评估":
            if ctx.ranked_solutions:
                top = ctx.ranked_solutions[0]
                lines.append(f"最高理想度: {top.ideality_score:.2f}")
                lines.append(f"最佳方案: {top.draft.title}")

        return "\n".join(lines) if lines else ""

    def _render_decision(self, data: dict):
        action = data.get("action", "")
        reason = data.get("reason", "")

        if action == "TERMINATE":
            style = "green"
            icon = "✓"
        elif action == "CONTINUE":
            style = "yellow"
            icon = "↻"
        else:
            style = "red"
            icon = "?"

        self.console.print()
        self.console.print(
            f"[{style}]{icon} 编排器决策: {action} — {reason}[/{style}]",
            style=f"bold {style}"
        )
        self.console.print()

    def _render_report(self, content: str):
        """渲染最终报告。"""
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()
        self.console.print("─" * 50, style="dim")
        self.console.print("分析完成。输入新问题继续，或 /save 保存报告。", style=STYLE_INFO)
        self.console.print()


def _run_single(question: str, use_agent: bool = False):
    """单次执行模式（非交互）。"""
    if not question or not question.strip():
        Console().print("[错误] 问题不能为空，使用 -q 指定问题或直接进入交互模式", style=STYLE_ERROR)
        sys.exit(1)

    console = Console()
    init_database()
    console.print(LOGO, style="bold bright_cyan")
    console.print()

    if use_agent:
        console.print("[模式] Agent 自主决策", style=STYLE_INFO)
        runner = TrizAgent(tool_registry=register_default_tools())
        run_method = runner.run
    else:
        console.print("[模式] Orchestrator 硬编码", style=STYLE_INFO)
        runner = Orchestrator()
        run_method = runner.run_workflow

    try:
        report = run_method(question)
        console.print(Markdown(report))
    except Exception as e:
        console.print(f"[错误] 执行失败: {e}", style=STYLE_ERROR)


def main():
    parser = argparse.ArgumentParser(
        description="TRIZ 智能系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-q", "--query", help="单次模式：直接输入问题并输出报告")
    parser.add_argument("-f", "--file", help="从文件读取问题（单次模式）")
    parser.add_argument("--agent", action="store_true", help="使用 Agent 自主决策模式（默认使用 Orchestrator）")

    args = parser.parse_args()

    # 管道输入检测
    if not sys.stdin.isatty():
        try:
            pipe_input = sys.stdin.read().strip()
        except (OSError, IOError):
            pipe_input = ""
        if pipe_input:
            _run_single(pipe_input, use_agent=args.agent)
            return

    # 单次模式：-q 或 -f
    if args.query:
        _run_single(args.query, use_agent=args.agent)
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                question = f.read().strip()
            _run_single(question, use_agent=args.agent)
        except FileNotFoundError:
            Console().print(f"[错误] 文件不存在: {args.file}", style=STYLE_ERROR)
            sys.exit(1)
        except Exception as e:
            Console().print(f"[错误] 读取文件失败: {e}", style=STYLE_ERROR)
            sys.exit(1)
    else:
        # 默认进入交互模式
        triz = TRIZConsole(use_agent=args.agent)
        triz.run()


if __name__ == "__main__":
    main()
