"""
CLI adapter for job-file execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from copublisher.application.services.idempotency_service import IdempotencyService
from copublisher.application.usecases.run_job import RunJobInput, RunJobUseCase
from copublisher.infrastructure.registry import build_default_registry
from copublisher.infrastructure.state_store.json_store import ExecutionStateStore


def build_run_job_usecase(state_root: str | Path | None = None) -> RunJobUseCase:
    if state_root is None:
        state_root = Path.home() / ".copublisher" / "execution_state"
    store = ExecutionStateStore(state_root)
    return RunJobUseCase(
        registry=build_default_registry(),
        idempotency_service=IdempotencyService(store),
    )


def run_job_file(job_file: str, dry_run: bool = False) -> dict[str, Any]:
    usecase = build_run_job_usecase()
    return usecase.execute(RunJobInput(job_file=job_file, cli_dry_run=dry_run))


def run_job_payload(payload: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    usecase = build_run_job_usecase()
    return usecase.execute_payload(payload, cli_dry_run=dry_run)

