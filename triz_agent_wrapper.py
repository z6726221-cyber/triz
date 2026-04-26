"""triz_agent 命令入口：确保 editable install 的包可被找到。"""
import sys
import os

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
for _sub in ("triz_agent", "triz_pipeline"):
    _path = os.path.join(_PROJECT_ROOT, _sub)
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from triz_agent.cli import main

if __name__ == "__main__":
    main()
