from lib.output_language import (
    DEFAULT_LANGUAGE_CODE,
    SUPPORTED_LANGUAGE_CODES,
    language_display_name,
    resolve_language_code,
)
from lib.speech_rate import SPEECH_RATE_UPS_BY_LANGUAGE, speech_rate_units_per_second
from lib.text_metrics import count_reading_units


def test_every_supported_language_has_a_speech_rate() -> None:
    """语速表缺了哪个语言，选中它的项目就会静默按中文语速估时长。"""
    for code in SUPPORTED_LANGUAGE_CODES:
        assert code in SPEECH_RATE_UPS_BY_LANGUAGE
        assert speech_rate_units_per_second(code, None) == SPEECH_RATE_UPS_BY_LANGUAGE[code]


def test_every_supported_language_has_a_display_name() -> None:
    """提示词里写的是语言名；缺名字就会退成默认语言，项目选的语言被无声忽略。"""
    names = {language_display_name(code) for code in SUPPORTED_LANGUAGE_CODES}
    assert len(names) == len(SUPPORTED_LANGUAGE_CODES)
    assert language_display_name("en") == "English"
    assert language_display_name("zh") == "中文"


def test_dirty_values_fall_back_instead_of_reaching_the_lookup_tables() -> None:
    """存量项目可能没有这个字段或带着脏值；下游的语速表只认三个语言码。"""
    for dirty in [None, "", "   ", 123, ["zh"], {}, "fr", False]:
        assert resolve_language_code(dirty) == DEFAULT_LANGUAGE_CODE


def test_supported_codes_pass_through_unchanged() -> None:
    for code in SUPPORTED_LANGUAGE_CODES:
        assert resolve_language_code(code) == code


def test_reading_units_differ_by_language() -> None:
    """英文按词、中文按字；语言码传错时长会差出数倍。"""
    assert count_reading_units("a lone clerk waits behind the counter", "en") == 7
    assert count_reading_units("值夜班的店员", "zh") == 6
