from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "src/modules/mod_breadcrumbs/module.py"
SPEC = importlib.util.spec_from_file_location("mod_breadcrumbs_module", MODULE_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
render = module.render


class _Result:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "_Result":
        return self

    def first(self) -> dict[str, object] | None:
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, object]]:
        return self._rows


class _Db:
    async def execute(self, statement: object, params: dict[str, object] | None = None) -> _Result:
        sql = str(statement)
        if "FROM com_menu_menus" in sql:
            return _Result([{"id": 1}])
        if "FROM com_menu_items" in sql:
            return _Result(
                [
                    {"id": 1, "parent_id": None, "title": "Články", "url": "/clanky"},
                    {"id": 2, "parent_id": 1, "title": "Novinka", "url": "/clanky/novinka"},
                ]
            )
        return _Result([])


@pytest.mark.asyncio
async def test_render_breadcrumb_chain() -> None:
    request = type("Request", (), {"url": type("Url", (), {"path": "/clanky/novinka"})()})()
    html = await render({"db": _Db(), "request": request})

    assert 'class="mod-breadcrumbs"' in html
    assert 'href="/clanky"' in html
    assert "Články" in html
    assert 'aria-current="page">Novinka' in html
