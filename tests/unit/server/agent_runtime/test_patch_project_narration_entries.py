"""``entries`` 里混进说明文本时，不该把整批资产一起拒掉。

实际遇到的调用：``{"table": "props", "entries": {"手机": {...}, "奶茶": {...},
"笔记本电脑": {...}, "reason": "Add missing props from source text"}}``。三个道具一个
都没写进去，模型收到的是「props 'reason' 的内容必须是对象」。
"""

from server.agent_runtime.sdk_tools.patch_project import _without_narration_entries


def test_narration_string_is_dropped_and_assets_survive() -> None:
    args = {
        "table": "props",
        "entries": {
            "手机": {"description": "一部智能手机"},
            "奶茶": {"description": "一杯奶茶"},
            "reason": "Add missing props from source text",
        },
    }
    assert _without_narration_entries(args)["entries"] == {
        "手机": {"description": "一部智能手机"},
        "奶茶": {"description": "一杯奶茶"},
    }


def test_an_asset_actually_named_reason_is_kept() -> None:
    """判据是值的形状不是键名：资产名由用户自由命名，按名字剥会误伤。"""
    args = {"table": "props", "entries": {"reason": {"description": "一块写着 reason 的牌子"}}}
    assert _without_narration_entries(args) == args


def test_untouched_when_nothing_looks_like_narration() -> None:
    args = {"table": "props", "entries": {"手机": {"description": "一部智能手机"}}}
    assert _without_narration_entries(args) == args


def test_all_non_objects_go_downstream_for_the_real_error() -> None:
    """整个 entries 都不是对象时不是说明混入，剥成空反而把真错误藏了。"""
    args = {"table": "props", "entries": {"手机": "一部智能手机"}}
    assert _without_narration_entries(args) == args


def test_other_branches_pass_through() -> None:
    """settings / overview 分支不带 entries，不该被这层碰到。"""
    args = {"settings": {"source_language": "zh"}}
    assert _without_narration_entries(args) == args
