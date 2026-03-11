#!/usr/bin/env python3
"""
微信公众号草稿发布入口脚本（向后兼容）。

推荐用法:
  python -m copublisher gzh-drafts <目录或单篇.md> [--skip N] [--account 账号]
  python -m copublisher gzh-drafts /path/to/article.md --account yiqichengzhang

本脚本作为便捷入口保留：若不传参数则使用环境变量 COPUBLISHER_GZH_DEFAULT_DIR 或历史默认目录。
"""

import os
import sys
from pathlib import Path

# 向后兼容：无参数时使用环境变量或历史默认（可通过 env 覆盖）
_DEFAULT_CONTENT_DIR = os.environ.get(
    "COPUBLISHER_GZH_DEFAULT_DIR",
    "/Users/xuejiao/Desktop/History/inspur/cowork/transcript/ppt_gen/content-series",
)


def main():
    argv = sys.argv[1:]

    # 无参数或仅 --skip N 时，使用默认目录以保持向后兼容
    if not argv or (len(argv) == 2 and argv[0] == "--skip"):
        default_dir = Path(_DEFAULT_CONTENT_DIR)
        if not default_dir.exists():
            print(f"❌ 默认目录不存在: {default_dir}")
            print("   请设置 COPUBLISHER_GZH_DEFAULT_DIR 或显式指定: copublisher gzh-drafts <目录或单篇.md>")
            sys.exit(1)
        sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
        from copublisher.interfaces.cli.gzh_drafts_command import run_gzh_drafts_cli

        run_gzh_drafts_cli(argv, default_content_dir=default_dir)
        return

    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from copublisher.interfaces.cli.gzh_drafts_command import run_gzh_drafts_cli

    run_gzh_drafts_cli(argv)


if __name__ == "__main__":
    main()
