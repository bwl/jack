from __future__ import annotations

from html import escape
from typing import Any

TELEGRAM_MAX = 4096


def _truncate(text: str, max_len: int = TELEGRAM_MAX) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 20] + "\n\n<i>[truncated]</i>"


def search_buttons(data: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (label, callback_data) pairs for search result buttons."""
    results = data.get("results", [])
    buttons = []
    for r in results:
        rid = r["id"][:8]
        title = r.get("title", "untitled")[:30]
        buttons.append((f"{title}", f"read:{rid}"))
    return buttons


def format_search(data: dict[str, Any]) -> str:
    results = data.get("results", [])
    if not results:
        return "No results found."

    query = escape(data.get("query", ""))
    lines = [f"<b>Search:</b> {query}  ({data.get('total', 0)} total)\n"]

    for r in results:
        rid = r["id"][:8]
        title = escape(r.get("title", "untitled"))
        score = r.get("similarity", 0)
        tags = " ".join(escape(t) for t in r.get("tags", [])[:4])
        preview = escape(r.get("bodyPreview", "")[:100])

        lines.append(
            f"<b>{title}</b>  <code>{rid}</code>  ({score:.2f})\n"
            f"{tags}\n"
            f"<i>{preview}</i>\n"
        )

    return _truncate("\n".join(lines))


def format_read(data: dict[str, Any]) -> str:
    node = data.get("node", {})
    title = escape(node.get("title", "untitled"))
    rid = node.get("id", "")[:8]
    tags = " ".join(escape(t) for t in node.get("tags", []))
    body = escape(data.get("body", ""))

    text = (
        f"<b>{title}</b>  <code>{rid}</code>\n"
        f"{tags}\n\n"
        f"<pre>{body}</pre>"
    )
    return _truncate(text)


def format_capture(data: dict[str, Any]) -> str:
    node = data.get("node", {})
    title = escape(node.get("title", "untitled"))
    rid = node.get("id", "")[:8]
    links = data.get("links", {})
    accepted = links.get("accepted", 0)

    return (
        f"Captured: <b>{title}</b>  <code>{rid}</code>\n"
        f"Auto-linked to {accepted} nodes."
    )


def format_stats(data: dict[str, Any]) -> str:
    counts = data.get("counts", {})
    degree = data.get("degree", {})
    recent = data.get("recent", [])[:5]

    lines = [
        "<b>Forest Stats</b>\n",
        f"Nodes: <b>{counts.get('nodes', 0)}</b>  "
        f"Edges: <b>{counts.get('edges', 0)}</b>\n",
        f"Degree — avg: {degree.get('avg', 0):.1f}  "
        f"median: {degree.get('median', 0)}  "
        f"p90: {degree.get('p90', 0)}  "
        f"max: {degree.get('max', 0)}\n",
    ]

    if recent:
        lines.append("\n<b>Recent:</b>")
        for r in recent:
            rid = r["id"][:8]
            title = escape(r.get("title", "untitled"))
            lines.append(f"  <code>{rid}</code>  {title}")

    return _truncate("\n".join(lines))


def format_text(label: str, text: str) -> str:
    """Wrap plain CLI text output for Telegram."""
    return _truncate(f"<b>{escape(label)}</b>\n\n<pre>{escape(text)}</pre>")


def format_help() -> str:
    return (
        "<b>Jack — Forest Telegram Bot</b>\n\n"
        "<b>Forest:</b>\n"
        "/search <i>query</i>  — search the Forest\n"
        "/s <i>query</i>  — alias for /search\n"
        "/read <i>ref</i>  — read a node (UUID prefix)\n"
        "/r <i>ref</i>  — alias for /read\n"
        "/capture <i>Title | Body | #tags</i>  — capture a note\n"
        "/c <i>Title | Body | #tags</i>  — alias for /capture\n"
        "/stats  — node/edge counts &amp; degree stats\n\n"
        "<b>Portfolio:</b>\n"
        "/ideas <i>query</i>  — search ideas\n"
        "/idea <i>name</i>  — show idea details\n"
        "/projects <i>query</i>  — search projects\n"
        "/project <i>name</i>  — show project summary\n"
        "/portfolio  — search across all sources\n\n"
        "<b>Novels:</b>\n"
        "/novels <i>query</i>  — list/search novels\n"
        "/novel <i>name</i>  — show novel details\n\n"
        "/help  — this message\n\n"
        "<i>Any other text → forest search</i>"
    )


def format_error(err: str) -> str:
    return f"Error: <code>{escape(err)}</code>"
