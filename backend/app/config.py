from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MODEL_ALLOWLIST = {"gemini-3.5-flash-lite"}


def _dotenv_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _cors_origins(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return ()
    origins: list[str] = []
    for item in raw.split(","):
        origin = item.strip()
        try:
            parsed = urlsplit(origin)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain valid HTTP(S) origins") from exc
        if (
            not origin
            or any(char.isspace() for char in origin)
            or parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or port == 0
            or "*" in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS_ALLOWED_ORIGINS must contain valid HTTP(S) origins")
        origins.append(origin)
    return tuple(dict.fromkeys(origins))


@dataclass(frozen=True, slots=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    gemini_free_tier_confirmed: bool
    demo_now: str
    cors_allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> Settings:
        file_values = _dotenv_values(ROOT / ".env")

        def value(name: str, default: str = "") -> str:
            return os.environ.get(name, file_values.get(name, default)).strip()

        confirmation = value("GEMINI_FREE_TIER_CONFIRMED", "false").lower()
        if confirmation not in {"true", "false"}:
            raise ValueError("GEMINI_FREE_TIER_CONFIRMED must be true or false")
        model = value("GEMINI_MODEL", "gemini-3.5-flash-lite")
        demo_now = value("DEMO_NOW", "2026-10-10T07:00:00Z")
        try:
            from datetime import datetime

            parsed = datetime.fromisoformat(demo_now)
        except ValueError as exc:
            raise ValueError("DEMO_NOW must be an ISO-8601 timestamp with timezone") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("DEMO_NOW must include a timezone")
        origins = _cors_origins(value("CORS_ALLOWED_ORIGINS"))
        return cls(
            gemini_api_key=value("GEMINI_API_KEY"),
            gemini_model=model,
            gemini_free_tier_confirmed=confirmation == "true",
            demo_now=demo_now,
            cors_allowed_origins=origins,
        )

    @property
    def gemini_status(self) -> str:
        if not self.gemini_free_tier_confirmed:
            return "disabled"
        if self.gemini_model not in MODEL_ALLOWLIST:
            return "unavailable"
        if not self.gemini_api_key:
            return "not_configured"
        return "configured"
