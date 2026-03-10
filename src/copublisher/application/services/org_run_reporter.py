"""
Write organization run reports to reports/org-runs/<id>/.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from copublisher.shared.io import atomic_write_json
from copublisher.shared.security import sanitize_identifier


class OrgRunReporter:
    def __init__(self, root_dir: str | Path = "reports/org-runs"):
        self.root_dir = Path(root_dir)

    def write(
        self,
        *,
        org_run_id: str,
        action_payload: dict[str, Any] | None,
        job_payload: dict[str, Any],
        run_result: dict[str, Any],
        org_state: dict[str, Any],
    ) -> Path:
        safe_id = sanitize_identifier(org_run_id, field_name="org_run_id")
        if not safe_id:
            raise ValueError("org_run_id 不能为空")

        target_dir = self.root_dir / safe_id
        target_dir.mkdir(parents=True, exist_ok=True)

        atomic_write_json(target_dir / "job_payload.json", job_payload, ensure_ascii=False)
        atomic_write_json(target_dir / "run_result.json", run_result, ensure_ascii=False)
        atomic_write_json(target_dir / "org_state.json", org_state, ensure_ascii=False)
        if action_payload is not None:
            atomic_write_json(target_dir / "action_payload.json", action_payload, ensure_ascii=False)

        summary = self._build_summary(
            org_run_id=safe_id,
            job_payload=job_payload,
            run_result=run_result,
            org_state=org_state,
        )
        atomic_write_json(target_dir / "summary.json", summary, ensure_ascii=False)
        return target_dir

    def _build_summary(
        self,
        *,
        org_run_id: str,
        job_payload: dict[str, Any],
        run_result: dict[str, Any],
        org_state: dict[str, Any],
    ) -> dict[str, Any]:
        platform_statuses = (
            run_result.get("metrics", {}).get("platform_results", {})
            if isinstance(run_result, dict)
            else {}
        )
        retry_platforms = [
            p for p, item in platform_statuses.items()
            if (not item.get("success")) and item.get("retryable")
        ]
        manual_platforms = [
            p for p, item in platform_statuses.items()
            if item.get("manual_takeover_required")
        ]
        return {
            "org_run_id": org_run_id,
            "written_at": datetime.now(timezone.utc).isoformat(),
            "status": run_result.get("status"),
            "org_state": org_state.get("org_state"),
            "job_id": run_result.get("metrics", {}).get("job_id"),
            "trace_id": run_result.get("metrics", {}).get("trace_id"),
            "platform_statuses": platform_statuses,
            "retry_platforms": retry_platforms,
            "manual_takeover_platforms": manual_platforms,
            "retry_entry_hint": self._build_retry_hint(job_payload, retry_platforms),
            "manual_takeover_entry_hint": self._build_retry_hint(job_payload, manual_platforms),
        }

    def _build_retry_hint(self, job_payload: dict[str, Any], platforms: list[str]) -> str | None:
        if not platforms:
            return None
        job_id = job_payload.get("job_id", "<job_id>")
        video = job_payload.get("video", "<video>")
        script = job_payload.get("script", "<script>")
        platform_value = ",".join(platforms)
        return (
            "copublisher job run "
            f"--job-id {job_id} --platforms {platform_value} "
            f"--video {video} --script {script} --json"
        )

