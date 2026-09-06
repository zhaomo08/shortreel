"""模型给 ``complete_asset_inventory`` 附说明时，不该把整份资产清单一起拒掉。

实际遇到的错误是 ``entries contains unsupported buckets: ['reason']``——一次调用里
角色、场景、道具全在，只因为多了一句说明就整批不落盘。
"""

import pytest

from lib.asset_inventory import AssetInventoryInvalidRequest, _prepare_entries


def test_narration_bucket_is_dropped_and_real_buckets_survive() -> None:
    prepared = _prepare_entries(
        {
            "characters": {"林岸": {"description": "值夜班的店员"}},
            "reason": "extracted from the source text",
        }
    )
    assert set(prepared) == {"characters"}
    assert "林岸" in prepared["characters"]


def test_known_buckets_alone_are_untouched() -> None:
    prepared = _prepare_entries({"scenes": {"便利店": {"description": "深夜的便利店"}}})
    assert set(prepared) == {"scenes"}


def test_no_known_bucket_still_fails_loudly() -> None:
    """全是未知键时不是说明混入——静默返回空会让 Agent 以为写入成功了。"""
    with pytest.raises(AssetInventoryInvalidRequest, match="no known bucket"):
        _prepare_entries({"reason": "nothing else"})


def test_empty_entries_stay_empty() -> None:
    assert _prepare_entries({}) == {}
    assert _prepare_entries(None) == {}
