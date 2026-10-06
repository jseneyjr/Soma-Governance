"""Backward-compatibility facade for immune_system.verification -> soma_core.verification."""
from __future__ import annotations

import sys
import types
from typing import Any
import soma_core.verification as _impl

for _attr in dir(_impl):
    if not (_attr.startswith('__') and _attr.endswith('__')):
        globals()[_attr] = getattr(_impl, _attr)


class _FacadeModule(types.ModuleType):
    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        try:
            setattr(_impl, name, value)
        except Exception:
            pass


sys.modules[__name__].__class__ = _FacadeModule
