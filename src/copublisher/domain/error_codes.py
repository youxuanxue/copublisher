"""
Domain error codes and retry/manual-takeover policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    MP_INPUT_INVALID = "MP_INPUT_INVALID"
    MP_AUTH_REQUIRED = "MP_AUTH_REQUIRED"
    MP_PLATFORM_TIMEOUT = "MP_PLATFORM_TIMEOUT"
    MP_PLATFORM_CHANGED = "MP_PLATFORM_CHANGED"
    MP_RATE_LIMIT = "MP_RATE_LIMIT"
    MP_PLATFORM_ERROR = "MP_PLATFORM_ERROR"
    MP_INTERNAL_ERROR = "MP_INTERNAL_ERROR"


@dataclass(frozen=True)
class ErrorPolicy:
    retryable: bool
    manual_takeover_required: bool


_POLICIES: dict[ErrorCode, ErrorPolicy] = {
    ErrorCode.MP_INPUT_INVALID: ErrorPolicy(False, False),
    ErrorCode.MP_AUTH_REQUIRED: ErrorPolicy(False, True),
    ErrorCode.MP_PLATFORM_TIMEOUT: ErrorPolicy(True, False),
    ErrorCode.MP_PLATFORM_CHANGED: ErrorPolicy(False, True),
    ErrorCode.MP_RATE_LIMIT: ErrorPolicy(True, False),
    ErrorCode.MP_PLATFORM_ERROR: ErrorPolicy(True, False),
    ErrorCode.MP_INTERNAL_ERROR: ErrorPolicy(True, False),
}


def get_policy(code: ErrorCode | str) -> ErrorPolicy:
    normalized = ErrorCode(code)
    return _POLICIES[normalized]


def map_exception_to_error_code(exc: Exception) -> ErrorCode:
    if isinstance(exc, ValueError):
        return ErrorCode.MP_INPUT_INVALID
    if isinstance(exc, PermissionError):
        return ErrorCode.MP_AUTH_REQUIRED
    if isinstance(exc, TimeoutError):
        return ErrorCode.MP_PLATFORM_TIMEOUT

    message = str(exc).lower()
    if "rate limit" in message or "too many requests" in message:
        return ErrorCode.MP_RATE_LIMIT
    if "auth" in message or "login" in message or "credential" in message:
        return ErrorCode.MP_AUTH_REQUIRED
    if "timeout" in message:
        return ErrorCode.MP_PLATFORM_TIMEOUT
    if "ui changed" in message or "selector" in message:
        return ErrorCode.MP_PLATFORM_CHANGED
    return ErrorCode.MP_PLATFORM_ERROR


def build_error_payload(
    *,
    code: ErrorCode | str,
    message: str,
    platform: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "code": str(ErrorCode(code).value),
        "message": message,
        "platform": platform,
        "details": details or {},
    }
