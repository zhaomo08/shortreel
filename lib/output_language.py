"""这个分支只产出英文成片，语言不再从源文推断。

上游按源文语言决定输出语言：``generate_overview`` 把 LLM 识别出的语言写进
``project.json`` 的 ``source_language``，剧本、口播、字幕与视觉提示词都跟着它走。
本分支面向海外投放，梗概可以用中文写，成片一律英文，所以输出语言是固定的，不是
从素材里读出来的。

两个常量分工不同，不能互换：

* :data:`OUTPUT_LANGUAGE_CODE` 是存进 ``project.json`` 的值。语速表
  （``lib.speech_rate``）、阅读单位（``lib.text_metrics``）与工具入参校验
  （``server.tool_runtime``）都拿它当键，只接受 ``zh`` / ``en`` / ``vi``。
* :data:`OUTPUT_LANGUAGE_NAME` 是写进提示词的名字。提示词里是「所有字符串值必须
  使用 {target_language}」这样的句子，填语言码会读成「必须使用 en」，填全名才是
  给模型的清晰指令。
"""

from __future__ import annotations

#: 存进 ``project.json`` 的 ``source_language``；须是 speech_rate / text_metrics 认得的语言码。
OUTPUT_LANGUAGE_CODE = "en"

#: 注入提示词 ``target_language`` 的语言名。
OUTPUT_LANGUAGE_NAME = "English"
