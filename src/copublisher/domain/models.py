"""
Domain models for job execution use cases.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from copublisher.shared.security import sanitize_identifier


SUPPORTED_JOB_MODES = {"legacy"}
VIDEO_PLATFORMS = {"wechat", "youtube", "tiktok", "instagram"}
ARTICLE_PLATFORMS = {"medium", "twitter", "devto"}


def _expand_platforms(platform_value: Any) -> list[str]:
    if isinstance(platform_value, list):
        raw_values = [str(p).strip().lower() for p in platform_value if str(p).strip()]
    else:
        normalized = str(platform_value or "wechat").strip().lower()
        if not normalized:
            normalized = "wechat"
        raw_values = [part.strip().lower() for part in normalized.split(",") if part.strip()]

    expanded: list[str] = []
    for item in raw_values:
        if item == "both":
            expanded.extend(["wechat", "youtube"])
        elif item == "all":
            expanded.extend(sorted(VIDEO_PLATFORMS | ARTICLE_PLATFORMS))
        elif item == "all-articles":
            expanded.extend(sorted(ARTICLE_PLATFORMS))
        elif item == "all-videos":
            expanded.extend(sorted(VIDEO_PLATFORMS))
        else:
            expanded.append(item)

    dedup: list[str] = []
    seen: set[str] = set()
    for platform in expanded:
        if platform not in seen:
            seen.add(platform)
            dedup.append(platform)
    return dedup


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    mode: str
    platforms: list[str]
    video_path: Path
    script_path: Path
    privacy: str
    account: str | None
    dry_run: bool
    raw: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        cli_dry_run: bool = False,
        supported_platforms: set[str] | None = None,
    ) -> "JobSpec":
        mode = str(payload.get("mode", "legacy")).strip().lower()
        if mode not in SUPPORTED_JOB_MODES:
            raise ValueError(f"不支持的 job mode: {mode}")

        platforms = _expand_platforms(payload.get("platforms", payload.get("platform", "wechat")))
        if not platforms:
            raise ValueError("platforms 不能为空")
        if supported_platforms is not None:
            invalid = [p for p in platforms if p not in supported_platforms]
            if invalid:
                raise ValueError(f"不支持的平台: {', '.join(invalid)}")

        job_id = sanitize_identifier(
            str(payload.get("job_id") or payload.get("id") or "job"),
            field_name="job_id",
        )
        if not job_id:
            raise ValueError("job_id 不能为空")

        account = sanitize_identifier(payload.get("account"), field_name="account")
        video_raw = str(payload.get("video") or "").strip()
        script_raw = str(payload.get("script") or "").strip()
        if not video_raw or not script_raw:
            raise ValueError("video 或 script 不能为空")

        video_path = Path(video_raw)
        script_path = Path(script_raw)
        if not video_path.is_file() or not script_path.is_file():
            raise ValueError("video 或 script 文件不存在")

        dry_run = bool(cli_dry_run or payload.get("dry_run", False))
        privacy = str(payload.get("privacy", "private")).strip().lower() or "private"

        return cls(
            job_id=job_id,
            mode=mode,
            platforms=platforms,
            video_path=video_path,
            script_path=script_path,
            privacy=privacy,
            account=account,
            dry_run=dry_run,
            raw=payload,
        )

    def load_script_data(self) -> dict[str, Any]:
        with self.script_path.open("r", encoding="utf-8") as f:
            return json.load(f)

