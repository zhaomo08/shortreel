"""Fork 定制：内置 OpenAI 供应商的 TTS 模型（gpt-4o-mini-tts / tts-1 / tts-1-hd）。

上游目录没有收录它们，官方同步又会整份替换内置供应商清单，所以不写进出厂快照，而是在装入出厂快照与同步数据时
补进来：条目缺了才补，清单里缺了才补，官方日后收录同名模型时以官方为准。后端见 ``lib/backends/audio_backends/openai.py``。
价格沿用 fork 原注册表的估算：美元/百万字符 12、15、30，按目录的 characters 计量（每万字符）写成 0.12、0.15、0.30。
"""

from __future__ import annotations

from dataclasses import replace

from arcreel_catalog_core import BuiltinProviderListing, BuiltinProviderModel, CatalogData, parse_entry

_PROVIDER = "openai"
_DEFAULT_AUDIO = "gpt-4o-mini-tts"


def _entry(name: str, display_name: str, per_10k_chars: float) -> dict[str, object]:
    return {
        "maker": "openai",
        "name": name,
        "media_type": "audio",
        "display_name": display_name,
        "facts": {},
        "price": {
            "currency": "USD",
            "meters": [{"meter": "characters", "dims": [], "rows": [{"when": {}, "price": per_10k_chars}]}],
        },
    }


_ENTRIES = tuple(
    parse_entry(raw)
    for raw in (
        _entry("gpt-4o-mini-tts", "GPT-4o mini TTS", 0.12),
        _entry("tts-1", "TTS-1", 0.15),
        _entry("tts-1-hd", "TTS-1 HD", 0.30),
    )
)


def with_fork_additions(data: CatalogData) -> CatalogData:
    """补上 fork 的 OpenAI TTS 条目与供应商模型；``data`` 已全部包含时原样返回。"""
    keys = {entry.key for entry in data.entries}
    entries = data.entries + tuple(entry for entry in _ENTRIES if entry.key not in keys)
    listing = data.builtin_providers.get(_PROVIDER)
    if listing is None:
        return replace(data, entries=entries) if len(entries) != len(data.entries) else data
    listed = {model.api_model_name for model in listing.models}
    extra = tuple(
        BuiltinProviderModel(api_model_name=entry.name, entry=entry.key.ref)
        for entry in _ENTRIES
        if entry.name not in listed
    )
    defaults = listing.defaults if "audio" in listing.defaults else {**listing.defaults, "audio": _DEFAULT_AUDIO}
    if not extra and len(entries) == len(data.entries) and defaults is listing.defaults:
        return data
    providers = {
        **data.builtin_providers,
        _PROVIDER: BuiltinProviderListing(models=listing.models + extra, defaults=defaults),
    }
    return replace(data, entries=entries, builtin_providers=providers)
