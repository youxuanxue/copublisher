"""
验证 copublisher 模块安装和导入（向后兼容入口）。

推荐用法: python -m copublisher verify

本脚本作为便捷入口保留，内部委托给 copublisher verify 子命令。
"""

import sys
from pathlib import Path


def main():
    # 确保能导入 copublisher（开发模式下 src 可能不在 path 中）
    src = Path(__file__).resolve().parent / "src"
    if src.exists() and str(src) not in sys.path:
        sys.path.insert(0, str(src))

    # 委托给统一 CLI
    from copublisher.interfaces.cli.verify_command import run_verify_cli

    run_verify_cli([])


if __name__ == "__main__":
    main()
