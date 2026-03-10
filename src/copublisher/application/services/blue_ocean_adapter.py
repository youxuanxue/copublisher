"""
Blue-ocean adapter helpers (input mapping and decision mapping).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from copublisher.shared.security import sanitize_identifier

MAX_BLUE_OCEAN_INPUT_BYTES = 1024 * 1024


def load_blue_ocean_request(path: str | Path) -> dict[str, Any]:
    request_path = Path(path)
    if not request_path.exists():
        raise ValueError(f"输入文件不存在: {request_path}")
    size = request_path.stat().st_size
    if size > MAX_BLUE_OCEAN_INPUT_BYTES:
        raise ValueError(
            f"输入文件过大: {size} bytes (max {MAX_BLUE_OCEAN_INPUT_BYTES})"
        )
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    return payload


def build_job_payload_from_action(action: dict[str, Any]) -> dict[str, Any]:
    action_id = sanitize_identifier(action.get("action_id"), field_name="action_id")
    job_id = sanitize_identifier(
        action.get("job_id") or action.get("id"),
        field_name="job_id",
    )
    if not action_id:
        raise ValueError("action_id 不能为空")
    if not job_id:
        raise ValueError("job_id 不能为空")

    materials = action.get("materials") or {}
    video = str(materials.get("video") or action.get("video") or "").strip()
    script = str(materials.get("script") or action.get("script") or "").strip()
    if not video or not script:
        raise ValueError("materials.video 与 materials.script 不能为空")

    raw_platforms = action.get("platforms") or action.get("platform") or "wechat"
    if isinstance(raw_platforms, list):
        platform_value = ",".join(str(p).strip() for p in raw_platforms if str(p).strip())
    else:
        platform_value = str(raw_platforms).strip()
    if not platform_value:
        raise ValueError("platforms 不能为空")

    account = sanitize_identifier(action.get("account"), field_name="account")
    idempotency_key = sanitize_identifier(
        action.get("idempotency_key"),
        field_name="idempotency_key",
    )

    return {
        "action_id": action_id,
        "job_id": job_id,
        "mode": "legacy",
        "platform": platform_value,
        "video": video,
        "script": script,
        "account": account,
        "idempotency_key": idempotency_key,
        "trace_id": action.get("trace_id"),
    }


def map_run_result_to_org_state(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status")
    retryable = bool(result.get("retryable"))
    manual_takeover_required = bool(result.get("manual_takeover_required"))

    if status == "success":
        org_state = "SUCCESS"
    elif manual_takeover_required:
        org_state = "MANUAL_TAKEOVER"
    elif retryable:
        org_state = "RETRY_PENDING"
    else:
        org_state = "FAILED"

    platform_statuses = (
        result.get("metrics", {}).get("platform_results", {}) if isinstance(result, dict) else {}
    )
    retry_platforms = [
        platform
        for platform, status_obj in platform_statuses.items()
        if (not status_obj.get("success")) and status_obj.get("retryable")
    ]
    manual_takeover_platforms = [
        platform
        for platform, status_obj in platform_statuses.items()
        if status_obj.get("manual_takeover_required")
    ]

    return {
        "org_state": org_state,
        "status": status,
        "retryable": retryable,
        "manual_takeover_required": manual_takeover_required,
        "platform_statuses": platform_statuses,
        "retry_platforms": retry_platforms,
        "manual_takeover_platforms": manual_takeover_platforms,
        "feishu_card_payload": {
            "platform_statuses": platform_statuses,
            "retry_platforms": retry_platforms,
            "manual_takeover_platforms": manual_takeover_platforms,
        },
        "error": result.get("error"),
        "metrics": result.get("metrics"),
    }

