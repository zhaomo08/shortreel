"""``entries`` 里混进说明文本时，不该把整批资产一起拒掉。

实际遇到的调用：``{"table": "props", "entries": {"手机": {...}, "奶茶": {...},
"笔记本电脑": {...}, "reason": "Add missing props from source text"}}``。三个道具一个
都没写进去，模型收到的是「props 'reason' 的内容必须是对象」。
"""

import pytest
from pydantic import ValidationError

from server.tool_runtime import PatchProjectRequest


def test_narration_string_is_dropped_and_assets_survive() -> None:
    request = PatchProjectRequest.model_validate(
        {
            "table": "props",
            "entries": {
                "手机": {"description": "一部智能手机"},
                "奶茶": {"description": "一杯奶茶"},
                "reason": "Add missing props from source text",
            },
        }
    )
    assert request.entries == {"手机": {"description": "一部智能手机"}, "奶茶": {"description": "一杯奶茶"}}


def test_an_asset_actually_named_reason_is_kept() -> None:
    """判据是值的形状不是键名：资产名由用户自由命名，按名字剥会误伤。"""
    entries = {"reason": {"description": "一块写着 reason 的牌子"}}
    assert PatchProjectRequest.model_validate({"table": "props", "entries": entries}).entries == entries


def test_untouched_when_nothing_looks_like_narration() -> None:
    entries = {"手机": {"description": "一部智能手机"}}
    assert PatchProjectRequest.model_validate({"table": "props", "entries": entries}).entries == entries


def test_all_non_objects_are_not_stripped_to_empty() -> None:
    """整个 entries 都不是对象时不是说明混入，剥成空反而把真错误藏了。"""
    request = PatchProjectRequest.model_validate({"table": "props", "entries": {"手机": "一部智能手机"}})
    assert request.entries == {"手机": "一部智能手机"}


def test_other_branches_pass_through() -> None:
    """settings / overview 分支不带 entries，不该被这层碰到。"""
    assert PatchProjectRequest.model_validate({"settings": {"source_language": "zh"}}).settings == {
        "source_language": "zh"
    }


def test_unknown_top_level_keys_still_rejected() -> None:
    with pytest.raises(ValidationError):
        PatchProjectRequest.model_validate({"settings": {"source_language": "zh"}, "typo": 1})
