"""Shared utility modules (lazy-loaded to avoid eager imports)."""

from importlib import import_module

_EXPORTS = {
    "atomic_write_json": (".io", "atomic_write_json"),
    "atomic_write_text": (".io", "atomic_write_text"),
    "sanitize_identifier": (".security", "sanitize_identifier"),
    "find_config_file": (".config", "find_config_file"),
}


def __getattr__(name: str):
    if name in _EXPORTS:
        rel_module, symbol = _EXPORTS[name]
        module = import_module(rel_module, __name__)
        value = getattr(module, symbol)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_EXPORTS)
