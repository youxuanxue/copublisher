"""
Infrastructure: 微信公众号草稿发布执行器，封装 core.GzhDraftPublisher。
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Callable


class GzhDraftsRunner:
    """公众号草稿批量发布执行器，委托给 core.GzhDraftPublisher。"""

    def run(
        self,
        *,
        content_dir: Path,
        skip: int = 0,
        headless: bool = False,
        progress_fn: Callable[[str], None] | None = None,
    ) -> None:
        from copublisher.core.gzh_drafts import GzhDraftPublisher

        md_files = sorted(content_dir.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"没有找到 .md 文件: {content_dir}")
        files_to_run = md_files[skip:]

        pub = GzhDraftPublisher(headless=headless)
        try:
            pub.authenticate()
            for i, md_file in enumerate(files_to_run, 1):
                if progress_fn:
                    progress_fn(f"\n[{i}/{len(files_to_run)}] {md_file.name}")
                content = md_file.read_text(encoding="utf-8")
                title = md_file.stem
                m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if m:
                    title = m.group(1).strip()
                    content = content.replace(m.group(0), "", 1).strip()
                pub.create_draft(title=title, markdown_content=content)
                if i < len(files_to_run):
                    time.sleep(4)
        finally:
            pub.close()
