from __future__ import annotations

import logging
from typing import Any, Protocol, TYPE_CHECKING

from .tools import IdeaCLI, NovelCLI
from . import formatting

if TYPE_CHECKING:
    from .agent import Agent
    from .commit_queue import CommitQueue
    from .github import GitHubCLI

logger = logging.getLogger(__name__)


class ForestBackend(Protocol):
    async def search(self, query: str, limit: int = 5) -> dict[str, Any]: ...
    async def read(self, ref: str) -> dict[str, Any]: ...
    async def capture(self, title: str, body: str, tags: str | None = None) -> dict[str, Any]: ...
    async def update(self, ref: str, title: str | None = None, body: str | None = None, tags: str | None = None) -> dict[str, Any]: ...
    async def delete(self, ref: str) -> dict[str, Any]: ...
    async def link(self, ref1: str, ref2: str) -> dict[str, Any]: ...
    async def edges(self, ref: str | None = None) -> dict[str, Any]: ...
    async def stats(self) -> dict[str, Any]: ...
    async def tags(self) -> dict[str, Any]: ...
    async def synthesize(self, node_ids: list[str]) -> dict[str, Any]: ...


class Router:
    def __init__(
        self,
        forest: ForestBackend,
        ideas: IdeaCLI | None = None,
        novels: NovelCLI | None = None,
        agent: Agent | None = None,
        github: GitHubCLI | None = None,
        commit_queue: CommitQueue | None = None,
    ) -> None:
        self.forest = forest
        self.ideas = ideas
        self.novels = novels
        self.agent = agent
        self.github = github
        self.commit_queue = commit_queue

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

    async def handle_text(
        self,
        text: str,
        on_tool_call: Any = None,
        reply_context: str | None = None,
        memory_context: str | None = None,
    ) -> str:
        """Free text goes through the LLM agent if available, else plain search."""
        if self.agent is not None:
            try:
                from .prompt import SYSTEM_PROMPT

                # Build full user message with context layers
                parts: list[str] = []
                if memory_context:
                    parts.append(memory_context)
                if reply_context:
                    parts.append(f"[Replying to: {reply_context}]")
                parts.append(text)
                user_message = "\n\n".join(parts)

                return await self.agent.run(
                    user_message, SYSTEM_PROMPT, self.forest,
                    github=self.github, commit_queue=self.commit_queue,
                    on_tool_call=on_tool_call,
                )
            except Exception:
                logger.exception("Agent failed, falling back to search")

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
