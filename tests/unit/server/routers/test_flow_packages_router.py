"""Google Flow 任务包：分镜图生视频走路由端到端，参考生视频替身掉供应商投影。"""

import asyncio
import json
import zipfile
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient

from lib.project.project_manager import ProjectManager
from server.auth import CurrentUserInfo, get_current_user
from server.error_handlers import register_error_handlers
from server.routers import flow_packages
from server.services.project import flow_package
from tests.auth_deps import AUTH_DEPENDENCIES


def _segment(segment_id: str, video_prompt, storyboard_image):
    return {
        "segment_id": segment_id,
        "novel_text": "t",
        "duration_seconds": 6,
        "characters_in_segment": [],
        "scenes": [],
        "props": [],
        "image_prompt": "a room",
        "video_prompt": video_prompt,
        "generated_assets": {"storyboard_image": storyboard_image, "video_clip": None, "status": "pending"},
    }


def _client(monkeypatch, tmp_path):
    pm = ProjectManager(tmp_path / "projects")
    pm.create_project("demo")
    pm.create_project_metadata("demo", "Demo", "Anime", "narration")
    pm.save_script(
        "demo",
        {
            "episode": 1,
            "title": "E1",
            "content_mode": "narration",
            "segments": [
                _segment("E1S01", "Slow push-in on the window", "storyboards/scene_E1S01.png"),
                _segment("E1S02", None, None),
            ],
        },
        "episode_1.json",
        validate=False,
    )
    storyboard = pm.get_project_path("demo") / "storyboards" / "scene_E1S01.png"
    storyboard.parent.mkdir(parents=True, exist_ok=True)
    storyboard.write_bytes(b"png-bytes")
    monkeypatch.setattr(flow_packages, "get_project_manager", lambda: pm)

    app = FastAPI()
    register_error_handlers(app)
    app.dependency_overrides[get_current_user] = lambda: CurrentUserInfo(id="default", sub="testuser", role="admin")
    app.include_router(flow_packages.router, prefix="/api/v1", dependencies=AUTH_DEPENDENCIES)
    return TestClient(app)


def test_storyboard_episode_exports_prompt_and_start_frame_per_shot(monkeypatch, tmp_path):
    response = _client(monkeypatch, tmp_path).get("/api/v1/projects/demo/episodes/1/flow-package")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(BytesIO(response.content))
    root = "demo_ep1_flow"
    assert zf.read(f"{root}/01_E1S01/start_frame.png") == b"png-bytes"
    assert "Slow push-in on the window" in zf.read(f"{root}/01_E1S01/prompt.txt").decode()
    manifest = json.loads(zf.read(f"{root}/manifest.json"))
    assert manifest["mode"] == "storyboard"
    first, second = manifest["shots"]
    assert (first["id"], first["folder"], first["duration_seconds"]) == ("E1S01", "01_E1S01", 6)
    assert first["files"] == ["prompt.txt", "start_frame.png"]
    assert first["notes"] == []
    # 没有提示词也没有分镜图的镜头照样占位，备注说明缺什么
    assert second["files"] == ["prompt.txt"]
    assert second["notes"] == ["该镜头还没有视频提示词"]
    assert f"{root}/README.txt" in zf.namelist()


def test_unknown_episode_is_404(monkeypatch, tmp_path):
    response = _client(monkeypatch, tmp_path).get("/api/v1/projects/demo/episodes/9/flow-package")
    assert response.status_code == 404


def test_reference_units_number_refs_in_request_order_and_fall_back_to_unit_text(monkeypatch, tmp_path):
    async def _projection(**kwargs):
        return kwargs["unit"]["unit_id"]

    def _preview(*, unit, **_kwargs):
        if unit["unit_id"] == "E1U01":
            return {
                "text": "<林夏>@图片1 走进 @图片2",
                "unavailable": None,
                "references": [
                    {"type": "character", "name": "林 夏", "path": "characters/linxia.png"},
                    {"type": "scene", "name": "咖啡/馆", "path": "scenes/cafe.jpg"},
                ],
            }
        return {"text": None, "unavailable": "未配置视频供应商", "references": []}

    monkeypatch.setattr(flow_package, "project_reference_unit_request", _projection)
    monkeypatch.setattr(flow_package, "render_reference_prompt_preview", _preview)
    script = {
        "video_units": [
            {"unit_id": "E1U01", "text": "raw", "duration_seconds": 8},
            {"unit_id": "E1U02", "text": "林夏坐下", "duration_seconds": 5},
        ]
    }

    shots = asyncio.run(
        flow_package.collect_reference_units({}, tmp_path, script, translate=lambda *a, **k: "", names=None)
    )

    first, second = shots
    assert first.prompt == "<林夏>@图片1 走进 @图片2"
    assert [name for name, _ in first.images] == ["ref_1_林_夏.png", "ref_2_咖啡_馆.jpg"]
    assert first.images[0][1] == tmp_path / "characters/linxia.png"
    assert (second.prompt, second.note) == ("林夏坐下", "导出的是单元正文：未配置视频供应商")


def test_missing_image_is_noted_not_fatal(tmp_path):
    zip_path = tmp_path / "out.zip"
    shot = flow_package.FlowShot("E1U01", 8, "p", None, (("ref_1_a.png", tmp_path / "gone.png"),))

    flow_package.write_flow_package(zip_path, root="r", mode="reference_video", aspect_ratio="9:16", shots=[shot])

    manifest = json.loads(zipfile.ZipFile(zip_path).read("r/manifest.json"))
    assert manifest["shots"][0]["files"] == ["prompt.txt"]
    assert manifest["shots"][0]["notes"] == ["缺少图片 ref_1_a.png"]
