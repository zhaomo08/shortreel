"""成片语言由项目自己声明，不从源文推断。

上游按源文语言决定输出语言：``generate_overview`` 把 LLM 识别出的语言写进
``project.json`` 的 ``source_language``，剧本、口播、字幕与视觉提示词都跟着它走。
这个分支同时做中文与英文投放，梗概用哪种语言写和成片要哪种语言是两件事——中文梗概
做英文片是常态，所以语言由建项目时选定并存进项目，识别结果只作存档。

``source_language`` 存语言码：语速表（``lib.speech_rate``）、阅读单位
（``lib.text_metrics``）与工具入参校验（``server.tool_runtime``）都拿它当键。
提示词里要的是语言名——模板写作「所有字符串值必须使用 {target_language}」，填语言码
会读成「必须使用 en」——由 :func:`language_display_name` 换算。
"""

from __future__ import annotations

#: 合法的成片语言码，与 ``server.tool_runtime`` 的入参校验、``lib.speech_rate``
#: 的语速表同一套。
SUPPORTED_LANGUAGE_CODES: tuple[str, ...] = ("zh", "en", "vi")

#: 新项目未显式选择时的成片语言。
DEFAULT_LANGUAGE_CODE = "en"

#: 语言码 → 写进提示词的语言名。
_DISPLAY_NAMES: dict[str, str] = {
    "zh": "中文",
    "en": "English",
    "vi": "Tiếng Việt",
}

#: ``project.json`` 里标记「成片语言跟随源文」的布尔字段。缺失按 True，与上游行为一致。
LANGUAGE_FOLLOWS_SOURCE_FIELD = "language_follows_source"

#: 跟随源文时写进概述提示词的语言指令。此时还没有语言事实——识别正是这次调用要做的事，
#: 所以给的是相对指令而非某个具体语言名。
FOLLOW_SOURCE_INSTRUCTION = "与源文本相同的语言"


def language_follows_source(project: object) -> bool:
    """项目是否让成片语言跟随源文。

    缺字段按 True：这是上游行为，也是存量项目的既有预期。只有用户在建项目时显式选定
    某个语言，才会写 False 并锁住 ``source_language``。
    """
    if not isinstance(project, dict):
        return True
    value = project.get(LANGUAGE_FOLLOWS_SOURCE_FIELD)
    return True if value is None else bool(value)


def is_supported_language(value: object) -> bool:
    return isinstance(value, str) and value in SUPPORTED_LANGUAGE_CODES


def resolve_language_code(value: object) -> str:
    """把项目里存的值收敛成合法语言码。

    存量项目可能没有这个字段，或带着历史脏数据（非字符串、空串、未登记的语言码）。
    这里统一回退默认语言，让下游的语速表与阅读单位永远拿到认得的键。
    """
    if isinstance(value, str) and value in SUPPORTED_LANGUAGE_CODES:
        return value
    return DEFAULT_LANGUAGE_CODE


def language_display_name(value: object) -> str:
    """取写进提示词的语言名；未登记的值按默认语言处理。"""
    return _DISPLAY_NAMES[resolve_language_code(value)]
