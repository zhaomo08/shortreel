"""SDK MCP tool for editing project.json assets by table + name 或顶层 settings 字段。

把 Agent 对 ``project.json`` 角色/场景/道具/商品的写入收归 ``patch_project``：按 table
（characters/scenes/props/products）+ name **upsert**（不存在则加、存在则改字段），经
``ProjectManager.upsert_assets`` 在单一文件锁内 read-modify-write，apply 后落盘前做结构
校验，非法则不写。取代脆弱的单行 CLI-JSON 脚本 ``add_assets.py``（且把「只能加」扩为「可改」）。

同一工具同时承担顶层 ``settings`` 字段写入（白名单驱动，见 ``_SETTINGS_WHITELIST``），
以及项目概述 ``overview``（synopsis/genre/theme/world_setting，merge 语义）的编辑。
``table + entries`` / ``settings`` / ``overview`` 三选一,在 ``update_project`` 锁内 RMW 同源。
"""

from __future__ import annotations

from typing import Any

from claude_agent_sdk import tool

from server.media_tools.context import ToolContext, tool_outcome_response, tool_services
from server.tool_runtime import (
    ASSET_TABLES as _TABLES,
)
from server.tool_runtime import (
    PROJECT_OVERVIEW_FIELDS as _OVERVIEW_FIELDS,
)
from server.tool_runtime import (
    PROJECT_SETTINGS as _SETTINGS_WHITELIST,
)
from server.tool_runtime import (
    PatchProjectRequest,
    ToolOutcome,
    ToolProblem,
    ToolRequest,
    patch_project,
)


# 顶层 settings 白名单。新增项 append 到 tuple,并在 _coerce_setting_value 加分支。
# source_language: overview 生成是非必经路径(generate_overview=false / overview 失败时
# 源语言不会落盘),需要给 Agent 在用户确认后写入的恢复通道,带 zh/en/vi enum 校验防乱填。
# planning_window_chars / planning_max_episodes: 分集规划工具的窗口字数与每批集数覆盖项,
# null 时回退工具内部默认。
# narration_voice / narration_speed: 项目级旁白音色与语速覆盖项,null 时回退全局配置。
# episode_target_duration: 单集目标时长(秒)软偏好,注入三条脚本规划提示词决定拆多少个单元;
# 区间校验取 lib.episode_target_duration 的同一把尺,ad 项目拒写。
def _without_narration_entries(args: dict[str, Any]) -> dict[str, Any]:
    """把模型混进 ``entries`` 的说明文本剔掉。

    ``entries`` 的键是资产名、值是该资产的字段对象。模型写入时习惯附一句说明，有时会把
    它当成同级条目塞进来——实际遇到的是 ``{"手机": {...}, "reason": "Add missing props"}``。
    整批因此被拒，三个道具一个都没写进去，模型收到的却是「'reason' 的内容必须是对象」。

    判据取值的形状而非键名：资产条目的值恒是对象，说明是字符串。按名字剥离会误伤真叫
    ``reason`` 的资产——资产名是用户自由命名的，而值不是对象的条目本来也不可能落盘。
    """
    entries = args.get("entries")
    if not isinstance(entries, dict):
        return args
    kept = {name: value for name, value in entries.items() if isinstance(value, dict)}
    if len(kept) == len(entries) or not kept:
        # 一个没剔，或者全是非对象——后者不是说明混入，交给下游报错，别把空 entries 递下去。
        return args
    return {**args, "entries": kept}


def patch_project_tool(ctx: ToolContext):
    @tool(
        "patch_project",
        "新增或修改 project.json:(1) 资产 upsert(传 table+entries),按 table+name upsert "
        "(name 不存在则新增、存在则合并改字段);(2) 顶层 settings 写入(传 settings),"
        f"白名单字段 {list(_SETTINGS_WHITELIST)},值为 null 时清除;(3) 项目概述编辑(传 overview),"
        f"白名单字段 {list(_OVERVIEW_FIELDS)},merge 语义只改传入字段、概述不存在时创建。"
        "三种形态三选一,同时给出多个或都不给会被拒。结构非法时不落盘并报错。",
        {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "enum": list(_TABLES),
                    "description": "(资产 upsert 分支)资产表:characters / scenes / props / products",
                },
                "entries": {
                    "type": "object",
                    "description": (
                        "(资产 upsert 分支){ 名称: { description, voice_style 等字段 } } 映射;至少一条。"
                        "角色条目可带 derivatives: { 衍生名: { description } },登记本体之外的另一套外观;"
                        "按衍生名合并(同名改描述、新名加入、未提及的保留),description 写相对本体的变化"
                    ),
                },
                "settings": {
                    "type": "object",
                    "description": (
                        "(settings 写入分支)顶层字段映射,key 必须在白名单内 "
                        f"{list(_SETTINGS_WHITELIST)},值为 null 时清除该字段"
                    ),
                },
                "overview": {
                    "type": "object",
                    "description": (
                        "(项目概述分支)概述字段映射,key 必须在白名单内 "
                        f"{list(_OVERVIEW_FIELDS)};merge 语义(只更新传入字段),概述不存在时创建"
                    ),
                },
            },
        },
    )
    async def _handler(args: dict[str, Any]) -> dict[str, Any]:
        args = _without_narration_entries(args)
        try:
            request = PatchProjectRequest.model_validate(args)
        except ValueError as exc:
            outcome = ToolOutcome(problem=ToolProblem("invalid_request", str(exc)))
        else:
            outcome = await patch_project(ToolRequest(request), ctx.scope, ctx.caller, tool_services(ctx))
        return tool_outcome_response("project_patch", outcome)

    return _handler


__all__ = ["patch_project_tool"]
