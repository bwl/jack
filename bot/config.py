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

        return cls(
            telegram_token=token,
            allowed_users=allowed,
            mode=mode,
            forest_bin=forest_bin,
            forest_url=forest_url,
            forest_api_key=forest_api_key,
        )
