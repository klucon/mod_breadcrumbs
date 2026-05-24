from __future__ import annotations

import json
from html import escape

from sqlalchemy import text


def _settings(settings: str) -> dict[str, object]:
    raw = (settings or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"menu_alias": raw}
    return data if isinstance(data, dict) else {}


def _current_path(context: dict) -> str:
    request = context.get("request")
    url = getattr(request, "url", None)
    return str(getattr(url, "path", "") or "").rstrip("/") or "/"


def _is_active(item_url: str, current_path: str) -> bool:
    clean_url = item_url.split("?", 1)[0].rstrip("/") or "/"
    return clean_url == current_path


async def _menu_id(db: object, selected_menu: str) -> int | None:
    query = "SELECT id FROM com_menu_menus"
    params: dict[str, object] = {}
    if selected_menu:
        if selected_menu.isdigit():
            query += " WHERE id = :menu_id"
            params["menu_id"] = int(selected_menu)
        else:
            query += " WHERE alias = :alias"
            params["alias"] = selected_menu
    query += " ORDER BY id ASC LIMIT 1"
    row = (await db.execute(text(query), params)).mappings().first()
    return int(row["id"]) if row else None


def _active_chain(items: list[dict[str, object]], current_path: str) -> list[dict[str, object]]:
    by_id = {int(item["id"]): item for item in items}
    active = next((item for item in items if _is_active(str(item["url"] or "#"), current_path)), None)
    if active is None:
        return []
    chain = [active]
    parent_id = active.get("parent_id")
    while str(parent_id or "").isdigit():
        parent = by_id.get(int(parent_id))
        if parent is None:
            break
        chain.append(parent)
        parent_id = parent.get("parent_id")
    return list(reversed(chain))


async def render(context: dict | None = None) -> str:
    context = context or {}
    db = context.get("db")
    if db is None:
        return ""

    settings = _settings(str(context.get("settings") or ""))
    selected_menu = str(settings.get("menu_alias") or settings.get("menu_id") or "").strip()
    home_label = str(settings.get("home_label") or "Úvod").strip()
    current_path = _current_path(context)

    try:
        menu_id = await _menu_id(db, selected_menu)
        if menu_id is None:
            return ""
        rows = (
            await db.execute(
                text(
                    "SELECT id, parent_id, title, url FROM com_menu_items "
                    "WHERE menu_id = :menu_id AND status = 'published' "
                    "ORDER BY parent_id ASC, ordering ASC, title ASC, id ASC"
                ),
                {"menu_id": menu_id},
            )
        ).mappings().all()
    except Exception:
        return ""

    chain = _active_chain([dict(row) for row in rows], current_path)
    if not chain and current_path == "/":
        chain = [{"title": home_label, "url": "/"}]
    if not chain:
        return ""

    parts = ['<nav class="mod-breadcrumbs" aria-label="Breadcrumb"><ol class="breadcrumb">']
    last_index = len(chain) - 1
    for index, item in enumerate(chain):
        title = escape(str(item["title"] or ""))
        url = escape(str(item["url"] or "#"), quote=True)
        if index == last_index:
            parts.append(f'<li class="breadcrumb-item active" aria-current="page">{title}</li>')
        else:
            parts.append(f'<li class="breadcrumb-item"><a href="{url}">{title}</a></li>')
    parts.append("</ol></nav>")
    return "".join(parts)
