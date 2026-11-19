"""OpenAI 语音合成的接线：后端实现早就在，缺的是注册、装配与模型目录收录（fork 定制）。

三者缺任一，用户在设置页填了 OpenAI key 也配不出旁白配音——界面上不会出现语音通道，
或选中后在合成时才失败。上游目录没收录 OpenAI TTS，由 lib/catalog/fork_additions.py 补进来。
"""

from arcreel_catalog_core import BuiltinProviderListing, CatalogData
from lib.backends.audio_backends import get_registered_backends
from lib.backends.backend_assembly.specs import PROVIDER_SPEC_REGISTRY
from lib.backends.providers import PROVIDER_OPENAI
from lib.catalog import query as catalog
from lib.catalog.fork_additions import with_fork_additions
from lib.config.registry import PROVIDER_REGISTRY

_TTS_MODELS = ("gpt-4o-mini-tts", "tts-1", "tts-1-hd")


def test_openai_audio_backend_is_registered_and_assembled() -> None:
    assert PROVIDER_OPENAI in get_registered_backends()
    assert (PROVIDER_OPENAI, "audio") in PROVIDER_SPEC_REGISTRY


def test_openai_exposes_text_to_speech_models() -> None:
    models = catalog.list_models(PROVIDER_OPENAI)
    for model_id in _TTS_MODELS:
        assert models[model_id].media_type == "audio"
        assert "text_to_speech" in models[model_id].capabilities


def test_audio_default_resolves() -> None:
    assert catalog.default_model(PROVIDER_OPENAI, "audio") == "gpt-4o-mini-tts"


def test_audio_concurrency_key_is_configurable() -> None:
    """登记了 audio 模型却不放开 audio_max_workers，语音任务会卡在默认并发上。"""
    assert "audio_max_workers" in PROVIDER_REGISTRY[PROVIDER_OPENAI].optional_keys


def test_audio_models_are_priced_so_cost_estimates_are_not_blank() -> None:
    for model_id in _TTS_MODELS:
        price = catalog.provider_model_price(PROVIDER_OPENAI, model_id, "audio")
        assert price is not None, f"{model_id} 缺定价，费用会记为未定价"
        assert price.price is not None, f"{model_id} 缺定价，费用会记为未定价"
        assert price.price.currency == "USD"


def test_survives_official_sync_replacing_the_provider_listing() -> None:
    """官方同步整份替换内置供应商清单；同步数据装入时同样要补回 TTS。"""
    synced = CatalogData(
        dataset_version="2099-01-01T00:00:00Z",
        entries=(),
        builtin_providers={PROVIDER_OPENAI: BuiltinProviderListing(models=(), defaults={})},
    )
    patched = with_fork_additions(synced)
    names = {m.api_model_name for m in patched.builtin_providers[PROVIDER_OPENAI].models}
    assert set(_TTS_MODELS) <= names
    assert patched.builtin_providers[PROVIDER_OPENAI].defaults["audio"] == "gpt-4o-mini-tts"
    assert with_fork_additions(patched) is patched
