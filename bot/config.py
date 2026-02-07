from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_users: frozenset[int]
    mode: str = "api"  # "api" or "cli"
    forest_bin: str = "forest"
    forest_url: str = "http://localhost:3000"
    forest_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "moonshotai/kimi-k2.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    @classmethod
    def from_env(cls) -> Config:
        token = os.environ.get("JACK_TELEGRAM_TOKEN", "").strip()
        if not token:
            print("JACK_TELEGRAM_TOKEN is required", file=sys.stderr)
            sys.exit(1)

        raw_users = os.environ.get("JACK_ALLOWED_USERS", "").strip()
        if not raw_users:
            print("JACK_ALLOWED_USERS is required", file=sys.stderr)
            sys.exit(1)

        try:
            allowed = frozenset(int(u.strip()) for u in raw_users.split(",") if u.strip())
        except ValueError:
            print("JACK_ALLOWED_USERS must be comma-separated integers", file=sys.stderr)
            sys.exit(1)

        mode = os.environ.get("JACK_MODE", "api").strip().lower()
        if mode not in ("api", "cli"):
            print("JACK_MODE must be 'api' or 'cli'", file=sys.stderr)
            sys.exit(1)

        forest_bin = os.environ.get("JACK_FOREST_BIN", "forest").strip()
        forest_url = os.environ.get("JACK_FOREST_URL", "http://localhost:3000").strip()
        forest_api_key = os.environ.get("JACK_FOREST_API_KEY", "").strip()

        if mode == "api" and not forest_api_key:
            print("JACK_FOREST_API_KEY is required when JACK_MODE=api", file=sys.stderr)
            sys.exit(1)

        openrouter_api_key = os.environ.get("JACK_OPENROUTER_API_KEY", "").strip()
        openrouter_model = os.environ.get(
            "JACK_OPENROUTER_MODEL", "moonshotai/kimi-k2.5",
        ).strip()
        openrouter_base_url = os.environ.get(
            "JACK_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1",
        ).strip()

        return cls(
            telegram_token=token,
            allowed_users=allowed,
            mode=mode,
            forest_bin=forest_bin,
            forest_url=forest_url,
            forest_api_key=forest_api_key,
            openrouter_api_key=openrouter_api_key,
            openrouter_model=openrouter_model,
            openrouter_base_url=openrouter_base_url,
        )
