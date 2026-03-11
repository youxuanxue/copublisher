"""
CLI 子命令：微信公众号草稿发布（支持目录批量或单篇）。

用法:
  copublisher gzh-drafts <目录或单篇.md> [--skip N] [--account 账号] [--headless]
  copublisher gzh-drafts /path/to/article.md --account yiqichengzhang
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run_gzh_drafts_cli(argv: list[str], default_content_dir: Path | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="copublisher gzh-drafts",
        description="将 Markdown 发布为公众号图文草稿（目录批量或单篇）",
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=None,
        help="包含 .md 的目录路径，或单篇 .md 文件路径",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        metavar="N",
        help="仅目录模式：跳过前 N 篇",
    )
    parser.add_argument(
        "--account",
        default=None,
        metavar="NAME",
        help="公众号账号名，用于多账号登录状态（如 yiqichengzhang）",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行浏览器",
    )
    args = parser.parse_args(argv)

    path = args.path or default_content_dir
    if path is None:
        print("❌ 请指定目录或单篇 .md 文件，例如: copublisher gzh-drafts /path/to/md-folder")
        print("   单篇: copublisher gzh-drafts /path/to/article.md --account yiqichengzhang")
        sys.exit(1)

    path = Path(path)
    if not path.exists():
        print(f"❌ 路径不存在: {path}")
        sys.exit(1)

    article_path: Path | None = None
    content_dir: Path
    if path.is_file():
        if path.suffix.lower() != ".md":
            print("❌ 单篇模式请指定 .md 文件")
            sys.exit(1)
        article_path = path
        content_dir = path.parent
        total = 1
        print(f"单篇发布: {path.name}" + (f" [账号: {args.account}]" if args.account else ""))
    else:
        md_files = sorted(path.glob("*.md"))
        if not md_files:
            print("❌ 没有找到 .md 文件")
            sys.exit(1)
        content_dir = path
        files_to_run = md_files[args.skip:]
        total = len(files_to_run)
        print(f"找到 {len(md_files)} 个文件，跳过前 {args.skip} 篇，本次处理 {total} 篇\n")

    from copublisher.application.usecases.gzh_drafts import GzhDraftsUseCase

    usecase = GzhDraftsUseCase()
    try:
        usecase.run(
            content_dir=content_dir,
            skip=args.skip,
            headless=args.headless,
            progress_fn=lambda msg: print(msg),
            article_path=article_path,
            account=args.account or None,
        )
    except KeyboardInterrupt:
        print("\n⚠️  用户取消操作")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
