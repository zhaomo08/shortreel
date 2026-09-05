from lib.output_language import OUTPUT_LANGUAGE_CODE, OUTPUT_LANGUAGE_NAME
from lib.speech_rate import SPEECH_RATE_UPS_BY_LANGUAGE, speech_rate_units_per_second
from lib.text_metrics import count_reading_units


def test_code_is_a_language_the_speech_rate_table_knows() -> None:
    """存进 project.json 的值要能当语速表的键，否则时长估算会静默回退中文语速。"""
    assert OUTPUT_LANGUAGE_CODE in SPEECH_RATE_UPS_BY_LANGUAGE
    assert speech_rate_units_per_second(OUTPUT_LANGUAGE_CODE, None) == SPEECH_RATE_UPS_BY_LANGUAGE[OUTPUT_LANGUAGE_CODE]


def test_english_reading_units_are_words_not_characters() -> None:
    """英文按词计，中文按字计；语言码传错会让时长差出数倍。"""
    sentence = "a lone clerk waits behind the counter"
    assert count_reading_units(sentence, OUTPUT_LANGUAGE_CODE) == 7


def test_name_reads_as_an_instruction_not_a_code() -> None:
    """提示词里是「必须使用 {target_language}」，填语言码会读成「必须使用 en」。"""
    assert OUTPUT_LANGUAGE_NAME == "English"
    assert OUTPUT_LANGUAGE_NAME != OUTPUT_LANGUAGE_CODE
