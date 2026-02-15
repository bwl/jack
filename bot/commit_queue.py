"""Ambient commit queue — polls GitHub for new commits, no LLM involved."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .github import GitHubCLI

logger = logging.getLogger(__name__)


@dataclass
class CommitQueue:
    github: GitHubCLI
    repos: list[str]
    state_path: Path
    poll_interval: int = 300

    _cursors: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _pending: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._load()

    async def poll(self) -> None:
        """Fetch new commits for each repo since its cursor, append to pending."""
        for repo in self.repos:
            try:
                since = self._cursors.get(repo)
                raw = await self.github.recent_commits(repo, since=since, limit=30)
                if not raw.strip():
                    continue

                existing_shas = {c["sha"] for c in self._pending if c["repo"] == repo}
                newest_date = since

                for line in raw.strip().splitlines():
                    # Format: "sha date author: message"
                    parts = line.split(" ", 2)
                    if len(parts) < 3:
                        continue
                    sha, date, rest = parts
                    if sha in existing_shas:
                        continue

                    author_msg = rest.split(": ", 1)
                    author = author_msg[0] if len(author_msg) > 1 else ""
                    message = author_msg[1] if len(author_msg) > 1 else rest

                    self._pending.append({
                        "repo": repo,
                        "sha": sha,
                        "author": author,
                        "message": message,
                        "date": date,
                    })

                    if newest_date is None or date > newest_date:
                        newest_date = date

                if newest_date and newest_date != since:
                    self._cursors[repo] = newest_date

            except Exception:
                logger.warning("Failed to poll %s", repo, exc_info=True)

        self._save()

    def get_pending(self, repo: str | None = None) -> list[dict[str, Any]]:
        """Return outstanding commits, optionally filtered by repo."""
        if repo:
            return [c for c in self._pending if c["repo"] == repo]
        return list(self._pending)

    def ack(self, repo: str) -> int:
        """Mark all pending commits for a repo as processed. Returns count cleared."""
        before = len(self._pending)
        self._pending = [c for c in self._pending if c["repo"] != repo]
        cleared = before - len(self._pending)
        self._save()
        return cleared

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self._cursors = data.get("cursors", {})
                self._pending = data.get("pending", [])
            except (json.JSONDecodeError, KeyError):
                logger.warning("Corrupt commit queue state, starting fresh")
                self._cursors = {}
                self._pending = []

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps({
            "cursors": self._cursors,
            "pending": self._pending,
        }, indent=2) + "\n")
