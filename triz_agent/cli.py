"""TRIZ Agent CLI：交互式 TUI。"""

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

from triz_agent.agent import TrizAgent
from triz_agent.tools.registry import register_default_tools
from triz_agent.database.init_db import init_database

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

WELCOME = """TRIZ Agent — 交互模式
输入问题开始分析，或 /help 查看命令"""

# ── 配色方案 ────────────────────────────────────────────
STYLE_SKILL = Style(color="cyan", bold=True)
STYLE_TOOL = Style(color="green", bold=True)
STYLE_ERROR = Style(color="red", bold=True)
STYLE_SUCCESS = Style(color="bright_green", bold=True)
STYLE_INFO = Style(color="bright_black")


class TRIZAgentConsole:
    """TRIZ Agent 交互式控制台。"""

    def __init__(self):
        self.console = Console()
        self.session = None
        self.agent = None
        self.session_history = []
        self.last_report = ""
        self._nodes = []
        self._live = None  # Rich Live 组件用于实时更新
        self._panel = None  # 当前显示的 Panel
        self._refresh_thread = None  # 后台刷新线程
        self._refresh_running = False  # 刷新线程运行标志
        self._spinner_frame = 0  # 当前 spinner 动画帧

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

            self._run_analysis(user_input)

    def _handle_command(self, cmd: str) -> bool:
        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action in ("/exit", "/quit", "/q"):
            self.console.print("再见！", style=STYLE_INFO)
            return True

        elif action == "/new":
            self.agent = None
            self.session_history = []
            self.console.print("[系统] 已重置上下文", style=STYLE_INFO)

        elif action == "/save":
            self._save_report(arg)

        elif action == "/show":
            self._show_node(arg)

        elif action == "/list":
            self._list_nodes()

        elif action in ("/help", "/?"):
            self._show_help()

        else:
            self.console.print(
                f"[错误] 未知命令: {action}，输入 /help 查看列表", style=STYLE_ERROR
            )

        return False

    def _show_help(self):
        help_text = """
[bold]可用命令[/bold]
  [cyan]/new[/cyan]              开始新对话，重置上下文
  [cyan]/save [文件名][/cyan]      保存最终报告（默认: report.md）
  [cyan]/list[/cyan]              列出所有节点
  [cyan]/show all[/cyan]          显示所有节点及完整输出
  [cyan]/show <节点名>[/cyan]      查看指定节点详情
  [cyan]/help, /?[/cyan]          显示此帮助
  [cyan]/exit, /quit[/cyan]       退出程序

[dim]直接输入问题即可执行 TRIZ 分析[/dim]
"""
        self.console.print(help_text)

    def _save_report(self, filename: str):
        if not self.last_report:
            self.console.print(
                "[错误] 暂无报告可保存，先执行一次分析", style=STYLE_ERROR
            )
            return

        filename = filename or "report.md"
        if not filename.endswith(".md"):
            filename += ".md"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.last_report)
            self.console.print(
                f"[系统] 报告已保存: {os.path.abspath(filename)}", style=STYLE_SUCCESS
            )
        except Exception as e:
            self.console.print(f"[错误] 保存失败: {e}", style=STYLE_ERROR)

    def _list_nodes(self):
        """列出所有可用节点。"""
        if not self._nodes:
            self.console.print("[系统] 当前无节点记录", style=STYLE_INFO)
            return
        self.console.print("\n[bold]可用节点：[/bold]")
        for i, node in enumerate(self._nodes, 1):
            name = node.get("node_name", "未知")
            steps = node.get("steps", [])
            status = node.get("status", "running")
            done = sum(1 for s in steps if s.get("status") == "done")
            self.console.print(f"  [cyan]{i}.[/cyan] {name} ({done}/{len(steps)} 步骤完成, {status})")
        self.console.print()

    def _show_node(self, node_name: str):
        if not self._nodes:
            self.console.print("[系统] 当前无节点记录", style=STYLE_INFO)
            return

        node_name = node_name.strip().lower()
        if node_name == "all":
            for node in self._nodes:
                self._render_node_full(node)
            return

        found = False
        for node in self._nodes:
            if node.get("node_name", "").lower() == node_name:
                self._render_node_full(node)
                found = True
        if not found:
            available = ", ".join(n.get("node_name", "") for n in self._nodes)
            self.console.print(
                f"[错误] 未找到节点 '{node_name}'。可用: {available}", style=STYLE_ERROR
            )

    def _render_node_full(self, node: dict):
        """完整展示节点的所有步骤和输出。"""
        from rich.markdown import Markdown

        name = node.get("node_name", "未知")
        steps = node.get("steps", [])
        status = node.get("status", "running")

        self.console.print(f"\n[bold cyan]━━━ {name} ━━━[/bold cyan]")
        for i, step in enumerate(steps, 1):
            sname = step.get("step_name", "")
            stype = step.get("step_type", "")
            sstatus = step.get("status", "")
            thought = step.get("thought", "")
            result = step.get("result", {})

            if stype == "Skill":
                tag = "Skill"
            elif stype == "Tool":
                tag = "Tool"
            else:
                tag = stype

            self.console.print()
            if sstatus == "done":
                if step.get("skipped"):
                    self.console.print(f"[yellow]⏭[{i}] [{tag}] {sname} [跳过][/yellow]")
                else:
                    self.console.print(f"[green]✓[{i}] [{tag}] {sname}[/green]")
                    if result:
                        content = self._get_result_full_content(result)
                        if content:
                            self.console.print(Markdown(content))
            elif sstatus == "error":
                err = step.get("error", "")
                self.console.print(f"[red]✗[{i}] [{tag}] {sname} [错误: {err}][/red]")
            elif sstatus == "running":
                self.console.print(f"[yellow]◐[{i}] [{tag}] 正在执行: {sname}[/yellow]")
                if thought:
                    self.console.print(f"  思考: {thought}")
            else:
                self.console.print(f"●[{i}] [{tag}] {sname}")

        if status == "done":
            self.console.print(f"\n[cyan]✓ 完成[/cyan]")
        self.console.print()

    def _get_result_full_content(self, result):
        """从 result 中提取完整的文本内容。"""
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict):
            for key in ("content", "text", "output", "markdown", "report"):
                if key in result and result[key]:
                    return str(result[key]).strip()
            for v in result.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, list) and v:
                    first = v[0]
                    if isinstance(first, str):
                        return first.strip()
                    return str(first)[:200]
        return ""

    def _render_node_plain(self, node: dict):
        # 确保 Live 已清理
        if self._live:
            self._live.stop()
            self._live = None

        self._nodes = []
        self.last_report = ""

        if self.agent is None:
            self.agent = TrizAgent(
                tool_registry=register_default_tools(), callback=self._on_event
            )
            self.console.print("[模式] Agent 自主决策", style=STYLE_INFO)

        self.console.print()
        self.console.print(
            f"[分析开始] {datetime.now().strftime('%H:%M:%S')}", style=STYLE_INFO
        )
        self.console.print()

        try:
            report = self.agent.run(question, self.session_history)
            self.last_report = report
        except Exception as e:
            self.console.print(f"\n[错误] 执行失败: {e}", style=STYLE_ERROR)

        self.session_history.append({"question": question})

    def _on_event(self, event_type: str, data: dict):
        if event_type == "node_start":
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
            # 如果还没有 node，初始化一个默认 node
            if not self._nodes:
                self._nodes.append({
                    "node_name": "TRIZ 分析",
                    "current": 1,
                    "total": 1,
                    "steps": [],
                    "status": "running",
                })

            if self._nodes:
                step_info = {
                    "step_name": data["step_name"],
                    "step_type": data["step_type"],
                    "status": "running",
                }
                if "agent_thought" in data:
                    step_info["thought"] = data["agent_thought"]
                self._nodes[-1]["steps"].append(step_info)
                # 更新当前步骤编号
                self._nodes[-1]["current"] = len(self._nodes[-1]["steps"])
                self._render_node(self._nodes[-1])
                # 启动刷新线程让 Spinner 动画持续
                self._start_refresh_thread()

        elif event_type == "step_complete":
            # 停止刷新线程
            self._stop_refresh_thread()
            if self._nodes and self._nodes[-1]["steps"]:
                step = self._nodes[-1]["steps"][-1]
                step["status"] = "done"
                step["result"] = data.get("result", {})
                result = data.get("result", {})
                if isinstance(result, dict) and result.get("skipped"):
                    step["skipped"] = True
            if self._nodes:
                self._render_node(self._nodes[-1])

        elif event_type == "step_error":
            if self._nodes and self._nodes[-1]["steps"]:
                step = self._nodes[-1]["steps"][-1]
                step["status"] = "error"
                step["error"] = data.get("error", "未知错误")
            if self._nodes:
                self._render_node(self._nodes[-1])

        elif event_type == "node_complete":
            if self._nodes:
                self._nodes[-1]["status"] = "done"
                self._nodes[-1]["ctx"] = data.get("ctx")
                self._render_node(self._nodes[-1])

        elif event_type == "report":
            # 停止 Live
            if self._live:
                self._live.stop()
                self._live = None
            self._render_report(data["content"])

    def _render_node_plain(self, node: dict):
        """直接打印节点内容（用于历史记录），不通过 Rich Live。"""
        name = node.get("node_name", "未知")
        steps = node.get("steps", [])
        status = node.get("status", "running")

        self.console.print(f"\n[bold cyan]━━━ {name} ━━━[/bold cyan]")
        for step in steps:
            sname = step.get("step_name", "")
            stype = step.get("step_type", "")
            sstatus = step.get("status", "")
            thought = step.get("thought", "")
            result = step.get("result", {})

            if stype == "Skill":
                tag = "Skill"
            elif stype == "Tool":
                tag = "Tool"
            else:
                tag = stype

            if sstatus == "done":
                if step.get("skipped"):
                    self.console.print(f"  ⏭ [{tag}] {sname} [跳过]")
                else:
                    self.console.print(f"  ✓ [{tag}] {sname}")
                    # 显示输出摘要
                    if result:
                        content = self._get_result_content(result)
                        if content:
                            self.console.print(f"    输出: {content[:200]}...")
                if thought:
                    thought_preview = thought[:80] + "..." if len(thought) > 80 else thought
                    self.console.print(f"    思考: {thought_preview}")
            elif sstatus == "error":
                err = step.get("error", "")
                self.console.print(f"  ✗ [{tag}] {sname} [错误: {err}]")
            elif sstatus == "running":
                self.console.print(f"  ◐ [{tag}] 正在执行: {sname}")
                if thought:
                    thought_preview = thought[:80] + "..." if len(thought) > 80 else thought
                    self.console.print(f"    → {thought_preview}")
            else:
                self.console.print(f"  ● [{tag}] {sname}")

        if status == "done":
            self.console.print(f"[cyan]✓ 完成[/cyan]")
        self.console.print()

    def _get_result_content(self, result):
        """从 result 中提取文本内容。"""
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict):
            # 尝试常见字段
            for key in ("content", "text", "output", "markdown", "report"):
                if key in result and result[key]:
                    return str(result[key]).strip()
            # 返回第一个非空字符串值
            for v in result.values():
                if isinstance(v, str) and v.strip():
                    return v.strip()
                if isinstance(v, list) and v:
                    return str(v[0])[:100]
        return ""

    def _render_node(self, node: dict, compact: bool = False):
        """渲染节点状态，使用 Live 实现实时更新。"""
        from rich.live import Live
        from rich.panel import Panel

        name = node.get("node_name", "未知")
        current = node.get("current", 0)
        total = node.get("total", 0)
        steps = node.get("steps", [])
        status = node.get("status", "running")

        step_lines = []
        for step in steps:
            sname = step.get("step_name", "")
            stype = step.get("step_type", "")
            sstatus = step.get("status", "")
            thought = step.get("thought", "")

            if stype == "Skill":
                tag = "[cyan]Skill[/cyan]"
            elif stype == "Tool":
                tag = "[green]Tool[/green]"
            else:
                tag = stype

            if sstatus == "running":
                # 运行中：使用旋转字符动画
                spinner = ["◐", "◒", "◓", "◑"][self._spinner_frame]
                line = f"[yellow]{spinner}[/yellow] {tag} 正在执行: {sname}"
                step_lines.append(line)
                if thought:
                    thought_preview = thought[:100] + "..." if len(thought) > 100 else thought
                    step_lines.append(f"  [dim]→ {thought_preview}[/dim]")
            elif sstatus == "error":
                err = step.get("error", "")
                line = f"[red]✗[/red] {tag} {sname} [red]错误: {err}[/red]"
                step_lines.append(line)
            elif sstatus == "done":
                if step.get("skipped"):
                    line = f"[yellow]⏭[/yellow] {tag} {sname} [yellow]跳过[/yellow]"
                else:
                    line = f"[green]✓[/green] {tag} {sname}"
                step_lines.append(line)
            else:
                line = f"● {tag} {sname}"
                step_lines.append(line)

        content = "\n".join(step_lines) if step_lines else "[dim]分析中...[/dim]"

        border_style = "cyan" if status == "done" else "yellow"
        title = f"[bold]{name}[/bold]"

        new_panel = Panel(
            content,
            title=title,
            border_style=border_style,
            box=box.ROUNDED,
        )

        # 初始化 Live 或更新显示
        if self._live is None:
            self._live = Live(new_panel, console=self.console, refresh_per_second=4)
            self._live.start()
            self._panel = new_panel
        else:
            self._panel = new_panel
            self._live.update(new_panel)

    def _start_refresh_thread(self):
        """启动后台刷新线程，让 Spinner 动画持续更新。"""
        import threading
        from rich.console import group
        from rich.text import Text

        def refresh_loop():
            while self._refresh_running:
                if self._live and self._nodes:
                    # 递增 spinner 帧
                    self._spinner_frame = (self._spinner_frame + 1) % 4
                    # 直接修改 Panel 内容来实现动画
                    try:
                        # 重新构建带新 spinner 的内容
                        node = self._nodes[-1]
                        name = node.get("node_name", "未知")
                        steps = node.get("steps", [])
                        status = node.get("status", "running")

                        step_lines = []
                        for step in steps:
                            sname = step.get("step_name", "")
                            stype = step.get("step_type", "")
                            sstatus = step.get("status", "")
                            thought = step.get("thought", "")

                            if stype == "Skill":
                                tag = "[cyan]Skill[/cyan]"
                            elif stype == "Tool":
                                tag = "[green]Tool[/green]"
                            else:
                                tag = stype

                            if sstatus == "running":
                                spinner = ["◐", "◒", "◓", "◑"][self._spinner_frame]
                                line = f"[yellow]{spinner}[/yellow] {tag} 正在执行: {sname}"
                                step_lines.append(line)
                                if thought:
                                    thought_preview = thought[:100] + "..." if len(thought) > 100 else thought
                                    step_lines.append(f"  [dim]→ {thought_preview}[/dim]")
                            elif sstatus == "error":
                                err = step.get("error", "")
                                line = f"[red]✗[/red] {tag} {sname} [red]错误: {err}[/red]"
                                step_lines.append(line)
                            elif sstatus == "done":
                                if step.get("skipped"):
                                    line = f"[yellow]⏭[/yellow] {tag} {sname} [yellow]跳过[/yellow]"
                                else:
                                    line = f"[green]✓[/green] {tag} {sname}"
                                step_lines.append(line)
                            else:
                                line = f"● {tag} {sname}"
                                step_lines.append(line)

                        content = "\n".join(step_lines) if step_lines else "[dim]分析中...[/dim]"
                        border_style = "cyan" if status == "done" else "yellow"

                        new_panel = Panel(
                            content,
                            title=f"[bold]{name}[/bold]",
                            border_style=border_style,
                            box=box.ROUNDED,
                        )
                        self._panel = new_panel
                        self._live.update(new_panel)
                    except Exception:
                        pass
                import time
                time.sleep(0.2)  # 每 0.2 秒刷新一次

        self._refresh_running = True
        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _stop_refresh_thread(self):
        """停止后台刷新线程。"""
        self._refresh_running = False
        if self._refresh_thread:
            self._refresh_thread.join(timeout=0.5)
            self._refresh_thread = None

    def _render_report(self, content: str):
        self.console.print()
        self.console.print(Markdown(content))
        self.console.print()
        self.console.print("─" * 50, style="dim")
        self.console.print(
            "分析完成。输入新问题继续，或 /save 保存报告。", style=STYLE_INFO
        )
        self.console.print()


def _make_detail_callback(console: Console):
    """创建一个详细的 callback，输出 Agent 每一步的思考和执行结果。"""
    from rich.panel import Panel
    from rich.text import Text

    def _on_detail_event(event_type: str, data: dict):
        if event_type == "step_start":
            step_name = data.get("step_name", "未知")
            step_type = data.get("step_type", "")
            thought = data.get("agent_thought", "")

            # 用不同颜色区分 Skill 和 Tool
            if step_type == "Skill":
                tag = "[bold cyan][Skill][/bold cyan]"
            elif step_type == "Tool":
                tag = "[bold green][Tool][/bold green]"
            else:
                tag = f"[{step_type}]"

            console.print(f"\n{tag} 开始执行: {step_name}")
            if thought:
                # 显示思考过程（截断过长内容）
                thought_short = thought[:300] + ("..." if len(thought) > 300 else "")
                console.print(f"  [dim]思考: {thought_short}[/dim]")

        elif event_type == "step_complete":
            step_name = data.get("step_name", "")
            step_type = data.get("step_type", "")
            result = data.get("result", "")

            # 显示执行结果摘要
            if isinstance(result, str):
                summary = result[:200].replace("\n", " ").strip()
                if len(result) > 200:
                    summary += "..."
                console.print(f"  [dim]输出: {summary}[/dim]")
            elif isinstance(result, dict):
                if result.get("skipped"):
                    console.print(f"  [yellow]⏭ 已跳过[/yellow]")
                else:
                    # 尝试提取关键信息
                    keys = list(result.keys())[:3]
                    summary = ", ".join(f"{k}={str(result[k])[:50]}" for k in keys)
                    console.print(f"  [dim]结果: {summary}[/dim]")
            console.print(f"  [green]✓ 完成[/green]")

        elif event_type == "step_error":
            step_name = data.get("step_name", "")
            error = data.get("error", "未知错误")
            console.print(f"  [red]✗ 错误: {error}[/red]")

        elif event_type == "report":
            console.print()  # 报告前空行

    return _on_detail_event


def _run_single(question: str):
    """单次执行模式（非交互）。"""
    if not question or not question.strip():
        Console().print(
            "[错误] 问题不能为空，使用 -q 指定问题或直接进入交互模式", style=STYLE_ERROR
        )
        sys.exit(1)

    console = Console()
    init_database()
    console.print(LOGO, style="bold bright_cyan")
    console.print()

    console.print("[模式] Agent 自主决策", style=STYLE_INFO)
    console.print()

    # 使用详细 callback 输出每一步信息
    callback = _make_detail_callback(console)
    runner = TrizAgent(
        tool_registry=register_default_tools(),
        callback=callback,
    )

    try:
        report = runner.run(question)
        console.print(Markdown(report))
    except Exception as e:
        console.print(f"[错误] 执行失败: {e}", style=STYLE_ERROR)


def main():
    parser = argparse.ArgumentParser(
        description="TRIZ Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-q", "--query", help="单次模式：直接输入问题并输出报告")
    parser.add_argument("-f", "--file", help="从文件读取问题（单次模式）")

    args = parser.parse_args()

    if not sys.stdin.isatty():
        try:
            pipe_input = sys.stdin.read().strip()
        except (OSError, IOError):
            pipe_input = ""
        if pipe_input:
            _run_single(pipe_input)
            return

    if args.query:
        _run_single(args.query)
    elif args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                question = f.read().strip()
            _run_single(question)
        except FileNotFoundError:
            Console().print(f"[错误] 文件不存在: {args.file}", style=STYLE_ERROR)
            sys.exit(1)
        except Exception as e:
            Console().print(f"[错误] 读取文件失败: {e}", style=STYLE_ERROR)
            sys.exit(1)
    else:
        console_app = TRIZAgentConsole()
        console_app.run()


if __name__ == "__main__":
    main()
