"""
CLI 子命令：微信公众号草稿批量发布。

用法: copublisher gzh-drafts <content_dir> [--skip N] [--headless]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def run_gzh_drafts_cli(argv: list[str], default_content_dir: Path | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="copublisher gzh-drafts",
        description="批量将 Markdown 文件发布为公众号图文草稿",
    )
    parser.add_argument(
        "content_dir",
        type=Path,
        nargs="?",
        default=None,
        help="包含 .md 文件的目录路径",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        metavar="N",
        help="跳过前 N 篇",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行浏览器",
    )
    args = parser.parse_args(argv)

    content_dir = args.content_dir or default_content_dir
    if content_dir is None:
        print("❌ 请指定 content_dir，例如: copublisher gzh-drafts /path/to/md-folder")
        print("   提示: 或使用 python publish_gzh_drafts.py <content_dir> [--skip N]（向后兼容）")
        sys.exit(1)

    content_dir = Path(content_dir)
    if not content_dir.exists():
        print(f"❌ 目录不存在: {content_dir}")
        sys.exit(1)

    md_files = sorted(content_dir.glob("*.md"))
    if not md_files:
        print("❌ 没有找到 .md 文件")
        sys.exit(1)

    skip = args.skip
    files_to_run = md_files[skip:]
    total = len(files_to_run)
    print(f"找到 {len(md_files)} 个文件，跳过前 {skip} 篇，本次处理 {total} 篇\n")

    from copublisher.application.usecases.gzh_drafts import GzhDraftsUseCase

    usecase = GzhDraftsUseCase()
    try:
        usecase.run(
            content_dir=content_dir,
            skip=skip,
            headless=args.headless,
            progress_fn=lambda msg: print(msg),
        )
    except KeyboardInterrupt:
        print("\n⚠️  用户取消操作")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
