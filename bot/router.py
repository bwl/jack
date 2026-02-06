from __future__ import annotations

from typing import Any, Protocol

from .tools import IdeaCLI, NovelCLI
from . import formatting


class ForestBackend(Protocol):
    async def search(self, query: str, limit: int = 5) -> dict[str, Any]: ...
    async def read(self, ref: str) -> dict[str, Any]: ...
    async def capture(self, title: str, body: str, tags: str | None = None) -> dict[str, Any]: ...
    async def stats(self) -> dict[str, Any]: ...


class Router:
    def __init__(
        self,
        forest: ForestBackend,
        ideas: IdeaCLI | None = None,
        novels: NovelCLI | None = None,
    ) -> None:
        self.forest = forest
        self.ideas = ideas
        self.novels = novels

    async def handle_command(self, command: str, args: str) -> str:
        try:
            match command:
                # --- Forest ---
                case "search" | "s":
                    if not args:
                        return "Usage: /search <query>"
                    data = await self.forest.search(args)
                    return formatting.format_search(data)

                case "read" | "r":
                    if not args:
                        return "Usage: /read <ref>"
                    data = await self.forest.read(args)
                    return formatting.format_read(data)

                case "capture" | "c":
                    if not args:
                        return "Usage: /capture Title | Body | #tags"
                    return await self._handle_capture(args)

                case "stats":
                    data = await self.forest.stats()
                    return formatting.format_stats(data)

                # --- Portfolio (icli) ---
                case "ideas" | "idea" | "projects" | "project" | "portfolio":
                    return await self._handle_portfolio(command, args)

                # --- Novels (ncli) ---
                case "novels" | "novel":
                    return await self._handle_novels(command, args)

                # --- Meta ---
                case "start" | "help":
                    return formatting.format_help(has_tools=self.ideas is not None)

                case _:
                    return formatting.format_help(has_tools=self.ideas is not None)

        except Exception as e:
            return formatting.format_error(str(e))

    async def handle_text(self, text: str) -> str:
        """Free-text messages default to search. Phase 2 growth seam."""
        try:
            data = await self.forest.search(text)
            return formatting.format_search(data)
        except Exception as e:
            return formatting.format_error(str(e))

    async def _handle_capture(self, raw: str) -> str:
        parts = [p.strip() for p in raw.split("|")]
        title = parts[0]
        body = parts[1] if len(parts) > 1 else title
        tags = parts[2] if len(parts) > 2 else None

        data = await self.forest.capture(title, body, tags)
        return formatting.format_capture(data)

    async def _handle_portfolio(self, command: str, args: str) -> str:
        if self.ideas is None:
            return "Portfolio commands are only available in local mode."

        match command:
            case "ideas":
                text = await self.ideas.ideas(args or None)
                return formatting.format_text("Ideas", text)
            case "idea":
                if not args:
                    return "Usage: /idea <name>"
                text = await self.ideas.idea_show(args)
                return formatting.format_text(f"Idea: {args}", text)
            case "projects":
                text = await self.ideas.projects(args or None)
                return formatting.format_text("Projects", text)
            case "project":
                if not args:
                    return "Usage: /project <name>"
                text = await self.ideas.project_summary(args)
                return formatting.format_text(f"Project: {args}", text)
            case "portfolio":
                if not args:
                    return "Usage: /portfolio <query>"
                text = await self.ideas.search(args)
                return formatting.format_text(f"Portfolio: {args}", text)
            case _:
                return "Unknown portfolio command."

    async def _handle_novels(self, command: str, args: str) -> str:
        if self.novels is None:
            return "Novel commands are only available in local mode."

        match command:
            case "novels":
                text = await self.novels.ls(args or None)
                return formatting.format_text("Novels", text)
            case "novel":
                if not args:
                    return "Usage: /novel <name>"
                text = await self.novels.show(args)
                return formatting.format_text(f"Novel: {args}", text)
            case _:
                return "Unknown novel command."
