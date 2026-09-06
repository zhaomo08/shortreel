from dataclasses import dataclass, replace
from typing import Any

import pytest

from server.agent_runtime.sdk_tools import _drop_advisory_keys


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
    await _drop_advisory_keys(tool).handler({"_": True})
    assert seen == [{}]


@pytest.mark.asyncio
async def test_placeholder_dropped_alongside_real_arguments() -> None:
    tool, seen = _echo_tool()
    await _drop_advisory_keys(tool).handler({"_": False, "episode": 1})
    assert seen == [{"episode": 1}]


@pytest.mark.asyncio
async def test_arguments_without_placeholder_pass_through_unchanged() -> None:
    tool, seen = _echo_tool()
    await _drop_advisory_keys(tool).handler({"episode": 2})
    assert seen == [{"episode": 2}]


@pytest.mark.asyncio
async def test_non_dict_arguments_reach_the_handler() -> None:
    tool, seen = _echo_tool()
    await _drop_advisory_keys(tool).handler(None)
    assert seen == [None]


@pytest.mark.asyncio
async def test_placeholder_is_dropped_whatever_its_value() -> None:
    """占位符的值类型随模型与调用而变：{"_": true} 与 {"_": {}} 都出现过，认键不认值。"""
    for placeholder in (True, False, {}, [], 0, "", None, "x"):
        tool, seen = _echo_tool()
        await _drop_advisory_keys(tool).handler({"_": placeholder, "episode": 1})
        assert seen == [{"episode": 1}]


@pytest.mark.asyncio
async def test_narration_keys_are_dropped() -> None:
    """模型给写入调用附说明，extra=forbid 会因此拒掉整次写入。"""
    tool, seen = _echo_tool()
    await _drop_advisory_keys(tool).handler({"episode": 1, "reason": "补齐道具", "note": "from source text"})
    assert seen == [{"episode": 1}]


@pytest.mark.asyncio
async def test_real_arguments_survive() -> None:
    """只剥说明性键；业务字段与未知字段照旧交给下游校验。"""
    tool, seen = _echo_tool()
    await _drop_advisory_keys(tool).handler({"episode": 1, "typo_field": "x"})
    assert seen == [{"episode": 1, "typo_field": "x"}]


def test_replace_keeps_tool_identity() -> None:
    tool, _ = _echo_tool()
    assert _drop_advisory_keys(tool).name == "echo"
    assert replace(tool, name="other").name == "other"
