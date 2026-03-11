"""
Shared pytest fixtures for copublisher tests.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path


@pytest.fixture()
def tmp_json(tmp_path: Path):
    """Write a temporary JSON file and return the path.

    Usage::

        def test_foo(tmp_json):
            path = tmp_json({"key": "value"})
    """

    def _factory(data: dict, name: str = "data.json") -> Path:
        p = tmp_path / name
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    return _factory


@pytest.fixture()
def fake_publisher():
    """Return a fake ``PublisherPort``-compatible object.

    The stub records calls and returns configurable outcomes.
    """
    from copublisher.domain.result import PlatformRunOutcome

    class FakePublisher:
        def __init__(self, platform: str = "fake", success: bool = True, message: str = "ok"):
            self.platform = platform
            self._success = success
            self._message = message
            self.calls: list[dict] = []

        def publish(self, *, video_path, script_data, privacy, account) -> PlatformRunOutcome:
            self.calls.append({
                "video_path": video_path,
                "script_data": script_data,
                "privacy": privacy,
                "account": account,
            })
            return PlatformRunOutcome(
                platform=self.platform,
                success=self._success,
                message=self._message,
            )

    return FakePublisher
