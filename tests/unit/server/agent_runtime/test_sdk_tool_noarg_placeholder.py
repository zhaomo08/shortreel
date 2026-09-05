from dataclasses import dataclass, replace
from typing import Any

import pytest

from server.agent_runtime.sdk_tools import _drop_noarg_placeholder


@dataclass(frozen=True)
class _FakeSdkTool:
    name: str
    handler: Any


def _echo_tool() -> tuple[_FakeSdkTool, list[Any]]:
    seen: list[Any] = []

    async def _handler(args: Any) -> dict[str, Any]:
        seen.append(args)
        return {"ok": True}

    return _FakeSdkTool(name="echo", handler=_handler), seen


@pytest.mark.asyncio
async def test_bare_placeholder_is_dropped() -> None:
    tool, seen = _echo_tool()
    await _drop_noarg_placeholder(tool).handler({"_": True})
    assert seen == [{}]


@pytest.mark.asyncio
async def test_placeholder_dropped_alongside_real_arguments() -> None:
    tool, seen = _echo_tool()
    await _drop_noarg_placeholder(tool).handler({"_": False, "episode": 1})
    assert seen == [{"episode": 1}]


@pytest.mark.asyncio
async def test_non_boolean_underscore_is_preserved() -> None:
    tool, seen = _echo_tool()
    await _drop_noarg_placeholder(tool).handler({"_": "keep me"})
    assert seen == [{"_": "keep me"}]


@pytest.mark.asyncio
async def test_arguments_without_placeholder_pass_through_unchanged() -> None:
    tool, seen = _echo_tool()
    await _drop_noarg_placeholder(tool).handler({"episode": 2})
    assert seen == [{"episode": 2}]


@pytest.mark.asyncio
async def test_non_dict_arguments_reach_the_handler() -> None:
    tool, seen = _echo_tool()
    await _drop_noarg_placeholder(tool).handler(None)
    assert seen == [None]


def test_replace_keeps_tool_identity() -> None:
    tool, _ = _echo_tool()
    assert _drop_noarg_placeholder(tool).name == "echo"
    assert replace(tool, name="other").name == "other"
