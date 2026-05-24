from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.registry import ComponentRegistry


def setup(registry: "ComponentRegistry") -> None:
    from src.modules.mod_breadcrumbs.module import render

    registry.register_module("breadcrumbs", render)
