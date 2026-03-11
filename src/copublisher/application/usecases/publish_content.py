"""
Application-level publish workflows used by CLI and GUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol


class PublishExecutorPort(Protocol):
    def load_episode_overview(self, *, episode_path: Path) -> tuple[str, str]: ...
    def close_wechat_browser(self) -> bool: ...
    def run_list_drafts(
        self, *, batch_dirs: list[Path], account: str | None
    ) -> tuple[str, list[tuple[str, str, str, str]], Path | None]: ...
    def run_wechat_batch(
        self, *, batch_dir: Path, pairs: list[tuple[Path, Path]], account: str | None
    ) -> list[tuple[bool, str]]: ...
    def run_legacy_script(
        self,
        *,
        video_path: Path,
        script_data: dict,
        platform: str,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]: ...
    def run_episode_adapter(
        self,
        *,
        episode_path: Path,
        platforms: list[str],
        video_path: Path | None,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]: ...


class PublishContentUseCase:
    def __init__(
        self,
        log_callback: Callable[[str], None] | None = None,
        executor: PublishExecutorPort | None = None,
    ):
        if executor is None:
            from copublisher.infrastructure.publishers.executor import LegacyPlatformExecutor

            executor = LegacyPlatformExecutor(log_callback=log_callback)
        self.executor = executor

    def close_wechat_browser(self) -> bool:
        return self.executor.close_wechat_browser()

    def load_episode_overview(self, *, episode_path: Path) -> tuple[str, str]:
        return self.executor.load_episode_overview(episode_path=episode_path)

    def run_list_drafts(
        self, *, batch_dirs: list[Path], account: str | None
    ) -> tuple[str, list[tuple[str, str, str, str]], Path | None]:
        return self.executor.run_list_drafts(batch_dirs=batch_dirs, account=account)

    def run_wechat_batch(
        self, *, batch_dir: Path, pairs: list[tuple[Path, Path]], account: str | None
    ) -> list[tuple[bool, str]]:
        return self.executor.run_wechat_batch(batch_dir=batch_dir, pairs=pairs, account=account)

    def run_legacy_script(
        self,
        *,
        video_path: Path,
        script_data: dict,
        platform: str,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]:
        return self.executor.run_legacy_script(
            video_path=video_path,
            script_data=script_data,
            platform=platform,
            privacy=privacy,
            account=account,
            keep_wechat_browser_open=keep_wechat_browser_open,
        )

    def run_episode_adapter(
        self,
        *,
        episode_path: Path,
        platforms: list[str],
        video_path: Path | None,
        privacy: str,
        account: str | None,
        keep_wechat_browser_open: bool = False,
    ) -> dict[str, tuple[bool, str]]:
        return self.executor.run_episode_adapter(
            episode_path=episode_path,
            platforms=platforms,
            video_path=video_path,
            privacy=privacy,
            account=account,
            keep_wechat_browser_open=keep_wechat_browser_open,
        )

