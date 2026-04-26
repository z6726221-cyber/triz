"""启动器：用 subprocess 独立运行两个端到端测试进程。"""

import subprocess
import sys
from pathlib import Path


def launch(mode: str):
    log_path = Path(__file__).parent / f"e2e_{mode}.log"
    err_path = Path(__file__).parent / f"e2e_{mode}.err"
    script = Path(__file__).parent / "e2e_test.py"

    with (
        open(log_path, "w", encoding="utf-8") as out,
        open(err_path, "w", encoding="utf-8") as err,
    ):
        proc = subprocess.Popen(
            [sys.executable, "-u", str(script), mode],
            stdout=out,
            stderr=err,
            cwd=str(Path(__file__).parent),
            creationflags=(
                subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            ),
        )

    print(f"已启动 {mode} 模式测试 (PID: {proc.pid})")
    print(f"  stdout -> {log_path}")
    print(f"  stderr -> {err_path}")
    return proc


def main():
    orch_proc = launch("orchestrator")
    agent_proc = launch("agent")

    print(f"\n两个测试进程已启动:")
    print(f"  Orchestrator PID: {orch_proc.pid}")
    print(f"  Agent PID: {agent_proc.pid}")
    print(f"\n查看日志:")
    print(f"  tail -f scripts/e2e_orchestrator.log")
    print(f"  tail -f scripts/e2e_agent.log")


if __name__ == "__main__":
    main()
