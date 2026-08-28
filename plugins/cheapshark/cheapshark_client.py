"""Thin HTTP wrapper around the CheapShark API. Standard library only - no
third-party dependencies, so the plugin needs no install step to run."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://www.cheapshark.com/api/1.0/"

# CheapShark rejects requests with a missing or generic User-Agent
# ({"error": "Missing or generic User-Agent header detected..."}), so this
# must be set on every request.
USER_AGENT = "cheapshark-mcp/0.1 (github.com/kozakq/Game-Deals-MCP)"

TIMEOUT = 10.0


class CheapSharkError(Exception):
    """Raised when the CheapShark API can't be reached or returns an error."""


def _get(path: str, params: dict | None = None) -> dict | list:
    query = urllib.parse.urlencode(
        {k: v for k, v in (params or {}).items() if v is not None}
    )
    url = f"{BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise CheapSharkError(f"CheapShark API returned an error: {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CheapSharkError(f"Could not reach CheapShark API: {exc}") from exc

    return json.loads(body)


def fetch_stores() -> list[dict]:
    return _get("stores")


def fetch_deals(**params) -> list[dict]:
    return _get("deals", params=params)


def fetch_games_by_title(title: str) -> list[dict]:
    return _get("games", params={"title": title})


def fetch_game_detail(game_id: str) -> dict:
    return _get("games", params={"id": game_id})
