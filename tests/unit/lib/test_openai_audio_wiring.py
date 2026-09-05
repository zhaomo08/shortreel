"""OpenAI 语音合成的接线：后端实现早就在，缺的是注册与模型登记。

两者缺任一，用户在设置页填了 OpenAI key 也配不出旁白配音——界面上不会出现语音通道，
或选中后在合成时才失败。这个分支只接 CPA 与国外供应商，OpenAI 是唯一的 TTS 来源。
"""

from lib.audio_backends import get_registered_backends
from lib.config.registry import PROVIDER_REGISTRY, ModelInfo
from lib.providers import PROVIDER_OPENAI


def _openai_audio_models() -> dict[str, ModelInfo]:
    return {
        model_id: info
        for model_id, info in PROVIDER_REGISTRY[PROVIDER_OPENAI].models.items()
        if info.media_type == "audio"
    }


def test_openai_audio_backend_is_registered() -> None:
    assert PROVIDER_OPENAI in get_registered_backends()


def test_openai_exposes_text_to_speech_models() -> None:
    models = _openai_audio_models()
    assert models, "registry 没有 audio 模型时，设置页不会显示 OpenAI 的语音通道"
    for info in models.values():
        assert "text_to_speech" in info.capabilities


def test_exactly_one_audio_default_so_the_channel_can_resolve() -> None:
    defaults = [mid for mid, info in _openai_audio_models().items() if info.default]
    assert len(defaults) == 1


def test_audio_concurrency_key_is_configurable() -> None:
    """登记了 audio 模型却不放开 audio_max_workers，语音任务会卡在默认并发上。"""
    assert "audio_max_workers" in PROVIDER_REGISTRY[PROVIDER_OPENAI].optional_keys


def test_audio_models_are_priced_so_cost_estimates_are_not_blank() -> None:
    for model_id, info in _openai_audio_models().items():
        pricing = info.pricing
        assert pricing is not None, f"{model_id} 缺定价，成本预估会显示空值"
        assert pricing.currency == "USD"
