"""Thin HTTP wrapper around the CheapShark API. No business logic here."""

from __future__ import annotations

import httpx

BASE_URL = "https://www.cheapshark.com/api/1.0/"

# CheapShark rejects requests with a missing or generic User-Agent
# ({"error": "Missing or generic User-Agent header detected..."}), so this
# must be set on every request.
HEADERS = {"User-Agent": "cheapshark-mcp/0.1 (github.com/aqpickup/cheapshark-mcp)"}

client = httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10.0)


class CheapSharkError(Exception):
    """Raised when the CheapShark API can't be reached or returns an error."""


def _get(path: str, params: dict | None = None) -> dict | list:
    try:
        response = client.get(path, params=params)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise CheapSharkError("CheapShark API timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise CheapSharkError(
            f"CheapShark API returned an error: {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise CheapSharkError(f"Could not reach CheapShark API: {exc}") from exc
    return response.json()


def fetch_stores() -> list[dict]:
    return _get("stores")


def fetch_deals(**params) -> list[dict]:
    params = {k: v for k, v in params.items() if v is not None}
    return _get("deals", params=params)


def fetch_games_by_title(title: str) -> list[dict]:
    return _get("games", params={"title": title})


def fetch_game_detail(game_id: str) -> dict:
    return _get("games", params={"id": game_id})
