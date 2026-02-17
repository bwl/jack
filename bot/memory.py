"""Per-chat conversation memory for context continuity.

Stores recent message pairs (user + assistant) per chat so the LLM agent
can understand follow-ups like "tell me more about that" or "what else?".
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Turn:
    role: str  # "user" or "assistant"
    text: str
    timestamp: float


class ChatMemory:
    """Bounded per-chat message buffer with LRU eviction."""

    def __init__(
        self,
        max_turns_per_chat: int = 10,
        max_chats: int = 50,
        ttl_seconds: float = 3600.0,
    ) -> None:
        self._max_turns = max_turns_per_chat
        self._max_chats = max_chats
        self._ttl = ttl_seconds
        self._chats: OrderedDict[int, list[Turn]] = OrderedDict()

    def add(self, chat_id: int, role: str, text: str) -> None:
        """Append a turn to the chat's history."""
        if chat_id not in self._chats:
            # Evict oldest chat if at capacity
            if len(self._chats) >= self._max_chats:
                self._chats.popitem(last=False)
            self._chats[chat_id] = []
        else:
            # Move to end (most recently active)
            self._chats.move_to_end(chat_id)

        turns = self._chats[chat_id]
        turns.append(Turn(role=role, text=text, timestamp=time.monotonic()))

        # Trim oldest turns if over limit
        if len(turns) > self._max_turns:
            self._chats[chat_id] = turns[-self._max_turns :]

    def get_context(self, chat_id: int) -> list[Turn]:
        """Return recent turns for a chat, pruning stale entries."""
        turns = self._chats.get(chat_id, [])
        if not turns:
            return []

        now = time.monotonic()
        fresh = [t for t in turns if (now - t.timestamp) < self._ttl]
        self._chats[chat_id] = fresh
        return fresh

    def format_for_prompt(self, chat_id: int) -> str:
        """Format recent history as a context block for the LLM."""
        turns = self.get_context(chat_id)
        if not turns:
            return ""

        lines = ["[Conversation history]"]
        for t in turns:
            prefix = "User" if t.role == "user" else "Jack"
            # Truncate long messages in history to save tokens
            text = t.text[:500] + "..." if len(t.text) > 500 else t.text
            lines.append(f"{prefix}: {text}")
        lines.append("[End of history]")
        return "\n".join(lines)

    def clear(self, chat_id: int) -> None:
        """Clear history for a specific chat."""
        self._chats.pop(chat_id, None)
