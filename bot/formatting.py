from __future__ import annotations

from html import escape
from typing import Any

TELEGRAM_MAX = 4096


_TRUNCATION_SUFFIX = "\n\n<i>[truncated]</i>"


def _truncate(text: str, max_len: int = TELEGRAM_MAX) -> str:
    if len(text) <= max_len:
        return text
    # Truncate, then close any open <pre> tags so Telegram can parse the HTML
    cut = text[: max_len - len(_TRUNCATION_SUFFIX) - 10]
    open_pre = cut.count("<pre>") - cut.count("</pre>")
    suffix = "</pre>" * open_pre + _TRUNCATION_SUFFIX
    return cut + suffix


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


def format_help(has_tools: bool = True) -> str:
    lines = [
        "<b>Jack — Forest Telegram Bot</b>\n",
        "<b>Forest:</b>",
        "/search <i>query</i>  — search the Forest",
        "/s <i>query</i>  — alias for /search",
        "/read <i>ref</i>  — read a node (UUID prefix)",
        "/r <i>ref</i>  — alias for /read",
        "/capture <i>Title | Body | #tags</i>  — capture a note",
        "/c <i>Title | Body | #tags</i>  — alias for /capture",
        "/stats  — node/edge counts &amp; degree stats",
    ]

    if has_tools:
        lines += [
            "",
            "<b>Portfolio:</b>",
            "/ideas <i>query</i>  — search ideas",
            "/idea <i>name</i>  — show idea details",
            "/projects <i>query</i>  — search projects",
            "/project <i>name</i>  — show project summary",
            "/portfolio  — search across all sources",
            "",
            "<b>Novels:</b>",
            "/novels <i>query</i>  — list/search novels",
            "/novel <i>name</i>  — show novel details",
        ]

    lines += [
        "",
        "/help  — this message",
        "",
        "<i>Any other text → forest search</i>",
    ]

    return "\n".join(lines)


def format_error(err: str) -> str:
    return f"Error: <code>{escape(err)}</code>"
