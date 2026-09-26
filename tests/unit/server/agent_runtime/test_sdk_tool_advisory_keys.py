from server.agent_toolset.embedded import drop_advisory_keys


def test_bare_placeholder_is_dropped() -> None:
    assert drop_advisory_keys({"_": True}) == {}


def test_placeholder_dropped_alongside_real_arguments() -> None:
    assert drop_advisory_keys({"_": False, "episode": 1}) == {"episode": 1}


def test_arguments_without_placeholder_pass_through_unchanged() -> None:
    assert drop_advisory_keys({"episode": 2}) == {"episode": 2}


def test_non_dict_arguments_pass_through() -> None:
    assert drop_advisory_keys(None) is None


def test_placeholder_is_dropped_whatever_its_value() -> None:
    """占位符的值类型随模型与调用而变：{"_": true} 与 {"_": {}} 都出现过，认键不认值。"""
    for placeholder in (True, False, {}, [], 0, "", None, "x"):
        assert drop_advisory_keys({"_": placeholder, "episode": 1}) == {"episode": 1}


def test_narration_keys_are_dropped() -> None:
    """模型给写入调用附说明，extra=forbid 会因此拒掉整次写入。"""
    assert drop_advisory_keys({"episode": 1, "reason": "补齐道具", "note": "from source text"}) == {"episode": 1}


def test_real_arguments_survive() -> None:
    """只剥说明性键；业务字段与未知字段照旧交给下游校验。"""
    assert drop_advisory_keys({"episode": 1, "typo_field": "x"}) == {"episode": 1, "typo_field": "x"}
