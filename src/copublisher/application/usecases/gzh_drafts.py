"""
Application use case: 微信公众号草稿批量发布。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol


class GzhDraftsRunnerPort(Protocol):
    """公众号草稿发布执行器端口，由 infrastructure 实现。"""

    def run(
        self,
        *,
        content_dir: Path,
        skip: int = 0,
        headless: bool = False,
        progress_fn: Callable[[str], None] | None = None,
        article_path: Path | None = None,
        account: str | None = None,
    ) -> None: ...


class GzhDraftsUseCase:
    """批量或将单篇 Markdown 发布为公众号图文草稿。"""

    def __init__(self, runner: GzhDraftsRunnerPort | None = None):
        if runner is None:
            from copublisher.infrastructure.gzh_drafts_runner import GzhDraftsRunner

            runner = GzhDraftsRunner()
        self._runner = runner

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
        self._runner.run(
            content_dir=content_dir,
            skip=skip,
            headless=headless,
            progress_fn=progress_fn,
            article_path=article_path,
            account=account,
        )
