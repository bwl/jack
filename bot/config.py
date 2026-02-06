from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    telegram_token: str
    allowed_users: frozenset[int]
    forest_bin: str = "forest"

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

        forest_bin = os.environ.get("JACK_FOREST_BIN", "forest").strip()
        return cls(telegram_token=token, allowed_users=allowed, forest_bin=forest_bin)
