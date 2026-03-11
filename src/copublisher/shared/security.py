"""
Security helpers for untrusted external identifiers.

sanitize_identifier: 用于路径拼接的标识符校验。
拒绝 ``..``、``/``、``\\`` 等路径穿越字符；最大长度 64 字符。
**有意允许非 ASCII 字符**（如中文账号名「奶奶讲故事」），不限于 ASCII letters/digits/_/-。
"""

from __future__ import annotations


def sanitize_identifier(value: str | None, field_name: str = "identifier") -> str | None:
    """
    Validate identifier used in file-path composition.

    Rules applied:
    - reject path traversal markers (``..``) and separators (``/``, ``\\``)
    - max length 64 characters
    - reject literal dot-path markers (``.``, ``..``)

    Non-ASCII characters (e.g. Chinese account names like "奶奶讲故事")
    are intentionally allowed — not restricted to ASCII letters/digits/_/-.
    """
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if ".." in normalized or "/" in normalized or "\\" in normalized:
        raise ValueError(f"{field_name} contains forbidden path characters")

    if len(normalized) > 64:
        raise ValueError(f"{field_name} is too long (max 64 chars)")

    if normalized in {".", ".."}:
        raise ValueError(
            f"{field_name} must be a normal name (not dot-path markers)"
        )

    return normalized
