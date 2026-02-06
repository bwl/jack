from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ForestCLI:
    bin: str = "forest"
    timeout: float = 30.0

    async def _run(self, *args: str, stdin: str | None = None) -> dict[str, Any]:
        proc = await asyncio.create_subprocess_exec(
            self.bin, *args, "--json",
            stdin=asyncio.subprocess.PIPE if stdin else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(stdin.encode() if stdin else None),
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            err = stderr.decode().strip() or stdout.decode().strip()
            raise RuntimeError(f"forest exited {proc.returncode}: {err}")
        return json.loads(stdout.decode())

    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        return await self._run("search", query, "--limit", str(limit))

    async def read(self, ref: str) -> dict[str, Any]:
        return await self._run("read", ref)

    async def capture(self, title: str, body: str, tags: str | None = None) -> dict[str, Any]:
        args = ["capture", "--title", title, "--stdin"]
        if tags:
            args.extend(["--tags", tags])
        return await self._run(*args, stdin=body)

    async def stats(self) -> dict[str, Any]:
        return await self._run("stats")
