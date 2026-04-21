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
            print("[系统] 历史查看功能在当前版本中暂不可用")
            continue

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
