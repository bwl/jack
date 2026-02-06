from __future__ import annotations

import httpx
from typing import Any


class ForestAPIError(RuntimeError):
    pass


class ForestAPI:
    """Async HTTP client for the Forest REST API.

    Same public interface as ForestCLI — search, read, capture, stats —
    returning the same normalized dicts that formatting.py expects.
    """

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/") + "/api/v1"
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        resp = await self._client.get(f"{self._base}{path}", params=params)
        return self._unwrap(resp)

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._base}{path}", json=body)
        return self._unwrap(resp)

    @staticmethod
    def _unwrap(resp: httpx.Response) -> dict[str, Any]:
        payload = resp.json()
        if not payload.get("success"):
            err = payload.get("error", {})
            msg = err.get("message", f"HTTP {resp.status_code}")
            raise ForestAPIError(msg)
        return payload.get("data", {})

    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        data = await self._get("/search/semantic", q=query, limit=limit)
        nodes = data.get("nodes", [])
        pagination = data.get("pagination", {})
        return {
            "query": query,
            "results": nodes,
            "total": pagination.get("total", len(nodes)),
        }

    async def read(self, ref: str) -> dict[str, Any]:
        data = await self._get(f"/nodes/{ref}", includeBody="true", includeEdges="false")
        node = data.get("node", {})
        return {
            "node": node,
            "body": node.get("body", ""),
        }

    async def capture(self, title: str, body: str, tags: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": title, "body": body}
        if tags:
            payload["tags"] = [t.strip().lstrip("#") for t in tags.split(",")]
        data = await self._post("/nodes", payload)
        linking = data.get("linking", {})
        return {
            "node": data.get("node", {}),
            "links": {"accepted": linking.get("autoLinked", linking.get("edgesCreated", 0))},
        }

    async def stats(self) -> dict[str, Any]:
        data = await self._get("/stats")
        nodes = data.get("nodes", {})
        edges = data.get("edges", {})
        return {
            "counts": {
                "nodes": nodes.get("total", 0),
                "edges": edges.get("total", 0),
            },
            "degree": {},
            "recent": nodes.get("recent", []),
        }
