from __future__ import annotations

import json
import logging
import time
from typing import Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .router import ForestBackend

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "forest_search",
            "description": "Search the Forest knowledge base for nodes matching a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forest_read",
            "description": "Read a Forest node's full body by UUID prefix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "UUID prefix (4+ characters) of the node to read.",
                    },
                },
                "required": ["ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forest_capture",
            "description": "Capture a new note in the Forest knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short title (3-8 words).",
                    },
                    "body": {
                        "type": "string",
                        "description": "Full note body.",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated tags, e.g. '#project/foo,#pattern/bar'.",
                    },
                },
                "required": ["title", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forest_stats",
            "description": "Get Forest knowledge base statistics (node/edge counts, recent nodes).",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forest_synthesize",
            "description": "Synthesize a new article from 2+ existing nodes using GPT-5. Takes node UUID prefixes, calls the Forest server's LLM to produce a synthesis, and saves it as a new node. This is slow (30-90s).",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2+ node UUID prefixes to synthesize.",
                    },
                },
                "required": ["node_ids"],
            },
        },
    },
]

MAX_ROUNDS = 5
MAX_REPEAT = 3
TOTAL_TIMEOUT = 120.0


async def _dispatch_tool(
    name: str, args: dict[str, Any], forest: ForestBackend,
) -> str:
    """Call the appropriate ForestBackend method and return JSON result."""
    match name:
        case "forest_search":
            result = await forest.search(args["query"], limit=args.get("limit", 5))
        case "forest_read":
            result = await forest.read(args["ref"])
        case "forest_capture":
            result = await forest.capture(
                title=args["title"],
                body=args["body"],
                tags=args.get("tags"),
            )
        case "forest_stats":
            result = await forest.stats()
        case "forest_synthesize":
            result = await forest.synthesize(args["node_ids"])
        case _:
            return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(result, default=str)


class Agent:
    """LLM agent that chains Forest tool calls via OpenRouter."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    async def run(
        self,
        user_message: str,
        system_prompt: str,
        forest: ForestBackend,
    ) -> str:
        """Run the agent loop. Returns the final text response."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        call_history: list[str] = []
        start = time.monotonic()

        for _ in range(MAX_ROUNDS):
            elapsed = time.monotonic() - start
            remaining = TOTAL_TIMEOUT - elapsed
            if remaining <= 0:
                return "Timed out while thinking. Try a simpler question?"

            resp = await self._chat(messages, timeout=remaining)
            choice = resp["choices"][0]
            msg = choice["message"]

            # Append assistant message to history
            messages.append(msg)

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                # Final text response
                return msg.get("content") or ""

            # Execute tool calls
            for tc in tool_calls:
                fn = tc["function"]
                name = fn["name"]
                raw_args = fn.get("arguments", "{}")
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}

                # Repetitive call detection
                call_key = f"{name}:{raw_args}"
                call_history.append(call_key)
                repeat_count = call_history.count(call_key)
                if repeat_count >= MAX_REPEAT:
                    logger.warning("Agent repeated %s %dx, aborting", name, repeat_count)
                    return "I got stuck in a loop. Try rephrasing your question?"

                logger.info("Tool call: %s(%s)", name, raw_args)
                try:
                    result = await _dispatch_tool(name, args, forest)
                except Exception as e:
                    result = json.dumps({"error": str(e)})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        return "Reached the maximum number of steps. Here's what I found so far."

    async def _chat(
        self,
        messages: list[dict[str, Any]],
        timeout: float,
    ) -> dict[str, Any]:
        """Single non-streaming chat completion call to OpenRouter."""
        resp = await self._client.post(
            f"{self._base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": messages,
                "tools": TOOLS,
            },
            timeout=min(timeout, 45.0),
        )
        resp.raise_for_status()
        return resp.json()
