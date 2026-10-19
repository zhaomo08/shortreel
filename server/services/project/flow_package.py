"""把一集导出成 Google Flow 任务包：视频在 Flow 网页里用订阅额度生成，再导回对应镜头。

Flow 没有 API，额度只能在网页里用，所以这里只负责「带出去」：每个镜头一个目录，
``prompt.txt`` 是这个镜头送进视频模型的最终提示词（与执行路径同一渲染出口），再附上
首帧/尾帧（分镜图生视频）或参考图（参考生视频）。导回不经本模块：前端按目录名或文件名
里的镜头 ID 匹配，逐个走既有的分镜视频上传接口，版本管理与元数据回写照旧。

只读：不向供应商发请求、不产生费用、不写项目。
"""

from __future__ import annotations

import json
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.i18n.display_names import DisplayNames
from lib.prompts.prompt_utils import render_storyboard_video_prompt
from lib.script.reference_video.request_projection import project_reference_unit_request
from lib.script.script_models import resolve_content_mode
from lib.script.storyboard_sequence import (
    StoryboardImageUnavailable,
    get_storyboard_items,
    resolve_storyboard_video_inputs,
)
from server.services.admission.reference_prompt_preview import render_reference_prompt_preview
from server.services.admission.video_batch_admission import resolve_voice_context

#: 包内文件名里不安全的字符（路径分隔符、Windows 保留字符、空白）。
_UNSAFE_NAME = re.compile(r'[\\/:*?"<>|\s]+')

README = """\
Google Flow 任务包
==================

每个镜头一个目录，目录名是「序号_镜头ID」。目录里：

- prompt.txt          这个镜头的视频提示词，整段粘贴到 Flow
- start_frame.*       首帧（分镜图），在 Flow 选「Frames to Video」后作为起始帧
- end_frame.*         尾帧（有才会出现），作为结束帧
- ref_N_<名字>.*      参考图（参考生视频），在 Flow 的「Ingredients」里按 N 的顺序添加；
                      提示词里的「@图片N」对应 ref_N

manifest.json 列出每个镜头的时长、画面比例和备注；prompts.md 是全部提示词的汇总，方便对照。

导回 ArcReel：
1. 把 Flow 下载的视频放进对应镜头的目录（文件名随意），或者放在任意位置但文件名里带上镜头 ID。
2. 回到这一集，点「导入 Flow 视频」，选择整个任务包目录。
3. 确认匹配结果后导入。导入的视频会作为该镜头的新版本，原来的版本可以在版本记录里恢复。
"""


@dataclass(frozen=True)
class FlowShot:
    shot_id: str
    duration_seconds: int | None
    prompt: str
    #: 提示词不是最终渲染结果时的原因（未就绪、渲染失败、供应商未配置等）；None 表示可直接用。
    note: str | None
    #: (包内文件名, 源文件绝对路径)
    images: tuple[tuple[str, Path], ...]


def _safe_name(name: str) -> str:
    return _UNSAFE_NAME.sub("_", name).strip("._") or "ref"


def _duration(item: dict[str, Any]) -> int | None:
    value = item.get("duration_seconds")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


async def collect_storyboard_shots(project: dict, project_path: Path, script: dict) -> list[FlowShot]:
    content_mode = resolve_content_mode(script, project)
    items, id_field, *_ = get_storyboard_items(script)
    voice_characters = await resolve_voice_context(project, content_mode)
    shots: list[FlowShot] = []
    for item in items:
        if not isinstance(item, dict) or not item.get(id_field):
            continue
        shot_id = str(item[id_field])
        raw = item.get("video_prompt")
        note: str | None = None
        if not raw:
            prompt, note = "", "该镜头还没有视频提示词"
        else:
            try:
                prompt = render_storyboard_video_prompt(
                    raw, item, content_mode=content_mode, voice_characters=voice_characters
                )
            except (ValueError, TypeError, KeyError):
                prompt = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False, indent=2)
                note = "提示词格式不合规，导出的是原始内容"
        images: list[tuple[str, Path]] = []
        try:
            start, end = resolve_storyboard_video_inputs(project_path=project_path, resource_id=shot_id, item=item)
        except (StoryboardImageUnavailable, ValueError):
            note = note or "还没有可用的分镜图，没有附首帧"
        else:
            images.append((f"start_frame{start.suffix}", start))
            if end is not None:
                images.append((f"end_frame{end.suffix}", end))
        shots.append(FlowShot(shot_id, _duration(item), prompt, note, tuple(images)))
    return shots


async def collect_reference_units(
    project: dict,
    project_path: Path,
    script: dict,
    *,
    translate: Callable[..., str],
    names: DisplayNames,
) -> list[FlowShot]:
    shots: list[FlowShot] = []
    for unit in script.get("video_units") or []:
        if not isinstance(unit, dict) or not unit.get("unit_id"):
            continue
        unit_id = str(unit["unit_id"])
        projection = await project_reference_unit_request(
            project=project, script=script, unit=unit, project_path=project_path
        )
        preview = render_reference_prompt_preview(
            project=project,
            unit=unit,
            project_path=project_path,
            projection=projection,
            translate=translate,
            names=names,
        )
        if preview["text"] is not None:
            prompt, note = preview["text"], None
        else:
            # 渲染依赖当前配置的视频供应商；只在 Flow 出片的项目可能没配，退回正文本身。
            prompt, note = str(unit.get("text") or ""), f"导出的是单元正文：{preview['unavailable']}"
        images = tuple(
            (f"ref_{index}_{_safe_name(ref['name'])}{Path(ref['path']).suffix}", project_path / ref["path"])
            for index, ref in enumerate(preview["references"], start=1)
        )
        shots.append(FlowShot(unit_id, _duration(unit), prompt, note, images))
    return shots


def shot_dir_name(index: int, shot_id: str) -> str:
    return f"{index:02d}_{_safe_name(shot_id)}"


def write_flow_package(zip_path: Path, *, root: str, mode: str, aspect_ratio: str, shots: list[FlowShot]) -> None:
    """写出任务包；读不到的图片记进备注并跳过，不让一张图挡住整包。"""
    manifest: list[dict[str, Any]] = []
    summary = [f"# {root}\n", f"画面比例：{aspect_ratio or '未设置'}\n"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{root}/README.txt", README)
        for index, shot in enumerate(shots, start=1):
            folder = shot_dir_name(index, shot.shot_id)
            notes = [shot.note] if shot.note else []
            files = ["prompt.txt"]
            zf.writestr(f"{root}/{folder}/prompt.txt", shot.prompt)
            for name, source in shot.images:
                if source.is_file():
                    zf.write(source, f"{root}/{folder}/{name}")
                    files.append(name)
                else:
                    notes.append(f"缺少图片 {name}")
            manifest.append(
                {
                    "index": index,
                    "id": shot.shot_id,
                    "folder": folder,
                    "duration_seconds": shot.duration_seconds,
                    "files": files,
                    "notes": notes,
                }
            )
            duration = f"{shot.duration_seconds}s" if shot.duration_seconds else "时长未设置"
            summary.append(f"\n## {folder}（{duration}）\n")
            summary.extend(f"\n> {note}\n" for note in notes)
            summary.append(f"\n```\n{shot.prompt}\n```\n")
        zf.writestr(
            f"{root}/manifest.json",
            json.dumps({"mode": mode, "aspect_ratio": aspect_ratio, "shots": manifest}, ensure_ascii=False, indent=2),
        )
        zf.writestr(f"{root}/prompts.md", "".join(summary))


__all__ = [
    "FlowShot",
    "collect_reference_units",
    "collect_storyboard_shots",
    "shot_dir_name",
    "write_flow_package",
]
