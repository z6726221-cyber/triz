"""triz 命令入口：默认启动 Agent 模式，加 --pipeline 切换到 Pipeline 模式。"""
import sys
import os

# 确保 editable install 的子包可被找到（.exe zipapp 不处理 .pth 文件）
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for _sub in ("triz_agent", "triz_pipeline"):
    _path = os.path.join(_PROJECT_ROOT, _sub)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    if "--pipeline" in sys.argv:
        sys.argv.remove("--pipeline")
        from triz_pipeline.cli import main as pipeline_main
        pipeline_main()
    else:
        from triz_agent.cli import main as agent_main
        agent_main()

if __name__ == "__main__":
    main()
