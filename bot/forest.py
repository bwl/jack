from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any


def _normalize_search(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize CLI search output to the shape formatting.py expects."""
    nodes = raw.get("nodes", [])
    pagination = raw.get("pagination", {})
    return {
        "query": raw.get("query", ""),
        "results": nodes,
        "total": pagination.get("total", len(nodes)),
    }


def _normalize_capture(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize CLI capture output to the shape formatting.py expects."""
    linking = raw.get("linking", {})
    return {
        "node": raw.get("node", {}),
        "links": {"accepted": linking.get("edgesCreated", 0)},
    }


def _normalize_stats(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize CLI stats output to the shape formatting.py expects."""
    nodes = raw.get("nodes", {})
    edges = raw.get("edges", {})
    return {
        "counts": {
            "nodes": nodes.get("total", 0),
            "edges": edges.get("total", 0),
        },
        "degree": {},
        "recent": nodes.get("recent", []),
    }


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
        raw = await self._run("search", query, "--limit", str(limit))
        return _normalize_search(raw)

    async def read(self, ref: str) -> dict[str, Any]:
        return await self._run("read", ref)

    async def capture(self, title: str, body: str, tags: str | None = None) -> dict[str, Any]:
        args = ["capture", "--title", title, "--stdin"]
        if tags:
            args.extend(["--tags", tags])
        raw = await self._run(*args, stdin=body)
        return _normalize_capture(raw)

    async def stats(self) -> dict[str, Any]:
        raw = await self._run("stats")
        return _normalize_stats(raw)

    async def synthesize(self, node_ids: list[str]) -> dict[str, Any]:
        raise RuntimeError("synthesize is only available in API mode")
