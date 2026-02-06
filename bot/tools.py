"""Async subprocess wrappers for icli and ncli (text output, no JSON)."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class ToolCLI:
    bin: str
    timeout: float = 30.0

    async def _run(self, *args: str) -> str:
        proc = await asyncio.create_subprocess_exec(
            self.bin, *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"{self.bin} exited {proc.returncode}: {err}")
        return stdout.decode().strip()


class IdeaCLI(ToolCLI):
    def __init__(self) -> None:
        super().__init__(bin="icli")

    async def search(self, query: str) -> str:
        return await self._run("search", query)

    async def ideas(self, query: str | None = None) -> str:
        args = ["ideas"]
        if query:
            args.extend(["-q", query])
        return await self._run(*args)

    async def idea_show(self, name: str) -> str:
        return await self._run("ideas", "show", name)

    async def projects(self, query: str | None = None) -> str:
        args = ["projects"]
        if query:
            args.extend(["-q", query])
        return await self._run(*args)

    async def project_summary(self, name: str) -> str:
        return await self._run("projects", "summary", name)

    async def status(self) -> str:
        return await self._run("status")

    async def stats(self) -> str:
        return await self._run("stats")


class NovelCLI(ToolCLI):
    def __init__(self) -> None:
        super().__init__(bin="ncli")

    async def ls(self, query: str | None = None) -> str:
        args = ["ls"]
        if query:
            args.extend(["-q", query])
        return await self._run(*args)

    async def show(self, name: str) -> str:
        return await self._run("show", name)
