"""一集的 Google Flow 任务包下载；打包逻辑见 ``server.services.project.flow_package``。"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

# fastapi 只 re-export 复数的 BackgroundTasks，单数版本只能取 starlette。
from starlette.background import BackgroundTask

from lib.infra.api_errors import NotFoundError
from lib.project.project_manager import get_project_manager, is_reference_video_project
from server.i18n import DisplayNamesCatalog, Translator
from server.services.project.flow_package import (
    collect_reference_units,
    collect_storyboard_shots,
    write_flow_package,
)

router = APIRouter()


def _load(project_name: str, episode: int) -> tuple[dict, Path, dict]:
    manager = get_project_manager()
    try:
        project = manager.load_project(project_name)
    except FileNotFoundError as exc:
        raise NotFoundError("project_not_found", name=project_name) from exc
    meta = next((e for e in project.get("episodes") or [] if e.get("episode") == episode), None)
    if meta is None or not meta.get("script_file"):
        raise NotFoundError("episode_not_found", episode=episode)
    try:
        script = manager.load_script(project_name, meta["script_file"])
    except FileNotFoundError as exc:
        raise NotFoundError("script_not_found", name=meta["script_file"]) from exc
    return project, manager.get_project_path(project_name), script


@router.get("/projects/{project_name}/episodes/{episode}/flow-package")
async def download_flow_package(project_name: str, episode: int, _t: Translator, names: DisplayNamesCatalog):
    project, project_path, script = await asyncio.to_thread(_load, project_name, episode)
    if is_reference_video_project(project):
        mode = "reference_video"
        shots = await collect_reference_units(project, project_path, script, translate=_t, names=names)
    else:
        mode = "storyboard"
        shots = await collect_storyboard_shots(project, project_path, script)
    root = f"{project_name}_ep{episode}_flow"
    raw_ratio = project.get("aspect_ratio")
    aspect_ratio = raw_ratio if isinstance(raw_ratio, str) else ""

    def _build() -> Path:
        workdir = Path(tempfile.mkdtemp(prefix="flow-package-"))
        try:
            write_flow_package(workdir / f"{root}.zip", root=root, mode=mode, aspect_ratio=aspect_ratio, shots=shots)
        except BaseException:
            shutil.rmtree(workdir, ignore_errors=True)
            raise
        return workdir / f"{root}.zip"

    zip_path = await asyncio.to_thread(_build)
    workdir = zip_path.parent
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=zip_path.name,
        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
    )


__all__ = ["router"]
