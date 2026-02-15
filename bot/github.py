"""Async wrapper for the GitHub CLI (gh)."""

from __future__ import annotations

from .tools import ToolCLI


class GitHubCLI(ToolCLI):
    def __init__(self) -> None:
        super().__init__(bin="gh")

    async def recent_commits(
        self, repo: str, since: str | None = None, limit: int = 10,
    ) -> str:
        """List recent commits on the default branch."""
        jq = r'.[] | "\(.sha[0:8]) \(.commit.author.date[0:10]) \(.commit.author.name): \(.commit.message | split("\n") | .[0])"'
        qs = f"per_page={limit}"
        if since:
            qs += f"&since={since}"
        return await self._run(
            "api", f"repos/{repo}/commits?{qs}", "--jq", jq,
        )

    async def compare(self, repo: str, base: str, head: str) -> str:
        """Compare two refs — commit list + diffstat summary."""
        jq = (
            r'"Commits: \(.total_commits)\n"'
            r' + (.commits | map("  \(.sha[0:8]) \(.commit.message | split("\n") | .[0])") | join("\n"))'
            r' + "\n\nFiles changed: \(.files | length)\n"'
            r' + (.files | map("  \(.status) \(.filename) (+\(.additions)/-\(.deletions))") | join("\n"))'
        )
        return await self._run(
            "api", f"repos/{repo}/compare/{base}...{head}", "--jq", jq,
        )

    async def pr_list(self, repo: str, state: str = "open") -> str:
        """List recent pull requests."""
        jq = r'.[] | "#\(.number) [\(.state)] \(.title) (\(.user.login), \(.updated_at[0:10]))"'
        return await self._run(
            "api", f"repos/{repo}/pulls?state={state}&per_page=10",
            "--jq", jq,
        )
