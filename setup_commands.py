r"""安装命令行入口：在 .venv/Scripts/ 中创建 triz / triz_agent / triz_pipeline 命令。

用法：
    .venv\Scripts\activate
    python setup_commands.py

之后即可直接使用 triz、triz_agent、triz_pipeline 命令。
"""
import os
import sys
import shutil


def main():
    if sys.platform != "win32":
        print("此脚本仅适用于 Windows。Linux/macOS 可直接使用 python -m 命令。")
        return

    venv_scripts = os.path.join(sys.prefix, "Scripts")
    if not os.path.isdir(venv_scripts):
        print(f"[错误] 未找到 {venv_scripts}")
        sys.exit(1)

    commands = {
        "triz.cmd": "triz_wrapper",
        "triz_agent.cmd": "triz_agent_wrapper",
        "triz_pipeline.cmd": "triz_pipeline_wrapper",
    }

    project_root = os.path.dirname(os.path.abspath(__file__))

    for filename, module in commands.items():
        cmd_path = os.path.join(venv_scripts, filename)
        # %~dp0 = .cmd 文件所在目录（.venv/Scripts/）
        # 设置 PYTHONPATH 确保项目根目录在 sys.path 中
        content = (
            f'@echo off\r\n'
            f'set "PYTHONPATH={project_root}"\r\n'
            f'"%~dp0python.exe" -m {module} %*\r\n'
        )
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] {filename} -> python -m {module}")

    print(f"\n安装完成！共 {len(commands)} 个命令已创建在 {venv_scripts}")
    print("现在可以直接使用：triz、triz_agent、triz_pipeline")


if __name__ == "__main__":
    main()
