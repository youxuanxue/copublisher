"""
Infrastructure: 微信公众号草稿发布执行器，封装 core.GzhDraftPublisher。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from copublisher.core.gzh_drafts import GzhDraftPublisher, parse_md_article


class GzhDraftsRunner:
    """公众号草稿批量发布执行器，委托给 core.GzhDraftPublisher。"""

    def run(
        self,
        *,
        content_dir: Path,
        skip: int = 0,
        headless: bool = False,
        progress_fn: Callable[[str], None] | None = None,
        article_path: Path | None = None,
        account: str | None = None,
    ) -> None:
        if article_path is not None:
            if not article_path.is_file():
                raise FileNotFoundError(f"不是文件: {article_path}")
            files_to_run = [article_path]
        else:
            md_files = sorted(content_dir.glob("*.md"))
            if not md_files:
                raise FileNotFoundError(f"没有找到 .md 文件: {content_dir}")
            files_to_run = md_files[skip:]

        pub = GzhDraftPublisher(headless=headless, account=account)
        try:
            pub.authenticate()
            for i, md_file in enumerate(files_to_run, 1):
                if progress_fn:
                    progress_fn(f"\n[{i}/{len(files_to_run)}] {md_file.name}")
                content = md_file.read_text(encoding="utf-8")
                title, body = parse_md_article(content, default_title=md_file.stem)
                pub.create_draft(title=title, markdown_content=body)
                if i < len(files_to_run):
                    time.sleep(4)
        finally:
            pub.close()
