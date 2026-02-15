from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .commit_queue import CommitQueue
    from .github import GitHubCLI
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
                        "description": "Comma-separated tags in namespace:value format, e.g. 'project:forest,topic:cli'.",
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
            "name": "forest_tags",
            "description": "List all existing tags in the Forest knowledge base. Call this before capturing to reuse existing tags and maintain consistency.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forest_update",
            "description": "Update an existing Forest node's title, body, or tags. Omitted fields are preserved. Use this to prepend content to changelogs or expand existing nodes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ref": {
                        "type": "string",
                        "description": "UUID prefix (4+ characters) of the node to update.",
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional — omit to keep current).",
                    },
                    "body": {
                        "type": "string",
                        "description": "New body content (optional — omit to keep current). Prepend new info to existing body.",
                    },
                    "tags": {
                        "type": "string",
                        "description": "Replacement tags in namespace:value format (optional — omit to keep current).",
                    },
                },
                "required": ["ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "commit_queue",
            "description": "Get outstanding commits from the ambient commit queue. These are commits that haven't been documented yet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "Filter by repo in owner/name format (optional — omit for all repos).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "commit_queue_ack",
            "description": "Mark a repo's commits as processed after documenting them. Call this after you've captured or updated a changelog node.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repo in owner/name format to acknowledge.",
                    },
                },
                "required": ["repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_compare",
            "description": "Compare two git refs on a GitHub repo — shows commit list and diff summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repo in owner/name format.",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base ref (tag, branch, or commit SHA).",
                    },
                    "head": {
                        "type": "string",
                        "description": "Head ref (tag, branch, or commit SHA).",
                    },
                },
                "required": ["repo", "base", "head"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_pr_list",
            "description": "List recent pull requests on a GitHub repo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {
                        "type": "string",
                        "description": "GitHub repo in owner/name format.",
                    },
                    "state": {
                        "type": "string",
                        "description": "PR state filter: 'open', 'closed', or 'all' (default 'open').",
                    },
                },
                "required": ["repo"],
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

MAX_ROUNDS = 10
MAX_REPEAT = 3
TOTAL_TIMEOUT = 120.0

ToolHook = Callable[[int, str, dict[str, Any]], Awaitable[None]]


def _tool_label(name: str, args: dict[str, Any]) -> str:
    match name:
        case "forest_search":
            return f"Searching: {args.get('query', '')}"
        case "forest_read":
            return f"Reading node {args.get('ref', '')}"
        case "forest_capture":
            return f"Capturing: {args.get('title', '')}"
        case "forest_stats":
            return "Checking stats"
        case "forest_tags":
            return "Listing tags"
        case "forest_update":
            return f"Updating node {args.get('ref', '')}"
        case "forest_synthesize":
            return "Synthesizing (this may take a moment)"
        case "commit_queue":
            repo = args.get("repo", "all repos")
            return f"Checking commit queue ({repo})"
        case "commit_queue_ack":
            return f"Acknowledging commits for {args.get('repo', '')}"
        case "github_compare":
            return f"Comparing {args.get('base', '')}...{args.get('head', '')} on {args.get('repo', '')}"
        case "github_pr_list":
            return f"Listing PRs on {args.get('repo', '')}"
        case _:
            return name


async def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    forest: ForestBackend,
    github: GitHubCLI | None = None,
    commit_queue: CommitQueue | None = None,
) -> str:
    """Call the appropriate backend method and return JSON result."""
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
        case "forest_update":
            result = await forest.update(
                ref=args["ref"],
                title=args.get("title"),
                body=args.get("body"),
                tags=args.get("tags"),
            )
        case "forest_tags":
            result = await forest.tags()
        case "forest_synthesize":
            result = await forest.synthesize(args["node_ids"])
        case "commit_queue":
            if commit_queue is None:
                return json.dumps({"error": "Commit queue not available"})
            pending = commit_queue.get_pending(repo=args.get("repo"))
            return json.dumps({"pending": pending, "count": len(pending)})
        case "commit_queue_ack":
            if commit_queue is None:
                return json.dumps({"error": "Commit queue not available"})
            cleared = commit_queue.ack(args["repo"])
            return json.dumps({"acknowledged": args["repo"], "cleared": cleared})
        case "github_compare":
            if github is None:
                return json.dumps({"error": "GitHub tools not available"})
            text = await github.compare(args["repo"], args["base"], args["head"])
            return json.dumps({"output": text})
        case "github_pr_list":
            if github is None:
                return json.dumps({"error": "GitHub tools not available"})
            text = await github.pr_list(args["repo"], state=args.get("state", "open"))
            return json.dumps({"output": text})
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
        github: GitHubCLI | None = None,
        commit_queue: CommitQueue | None = None,
        on_tool_call: ToolHook | None = None,
    ) -> str:
        """Run the agent loop. Returns the final text response."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        call_history: list[str] = []
        step = 0
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

                step += 1
                logger.info("Tool call: %s(%s)", name, raw_args)

                if on_tool_call:
                    try:
                        await on_tool_call(step, name, args)
                    except Exception:
                        logger.debug("on_tool_call hook failed", exc_info=True)

                try:
                    result = await _dispatch_tool(name, args, forest, github=github, commit_queue=commit_queue)
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
