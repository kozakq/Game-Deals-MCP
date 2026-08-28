"""MCP server exposing PC game deal search and price-history lookups via CheapShark.

Hand-written against the MCP stdio JSON-RPC protocol (spec 2025-06-18) instead of
a framework. Claude Desktop/Cowork plugin installs run .mcp.json's command/args
directly with no install step, and this server's original dependencies (fastmcp,
httpx) pulled in several platform-specific compiled packages (pydantic-core,
cryptography, rpds-py, ...) that can't be vendored portably. Standard library
only sidesteps that entirely - nothing to install, ever, on any platform.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

import cheapshark_client as cs

SERVER_NAME = "cheapshark-mcp"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"

_store_cache: dict | None = None


def get_store_cache() -> dict:
    """Fetch the store list once and cache it in memory for the life of the process."""
    global _store_cache
    if _store_cache is None:
        stores = cs.fetch_stores()
        _store_cache = {
            "by_id": {s["storeID"]: s["storeName"] for s in stores},
            "by_name": {s["storeName"].lower(): s["storeID"] for s in stores},
            "active": [
                {"store_id": s["storeID"], "name": s["storeName"]}
                for s in stores
                if int(s["isActive"]) == 1
            ],
        }
    return _store_cache


def resolve_store(store: str | int | None) -> tuple[str | None, str | None]:
    """Translate a store name or numeric ID into a CheapShark storeID.

    Returns (store_id, error_message) - exactly one will be None.
    """
    if store is None:
        return None, None

    cache = get_store_cache()
    store_str = str(store).strip()

    if store_str.isdigit():
        return store_str, None

    store_id = cache["by_name"].get(store_str.lower())
    if store_id is not None:
        return store_id, None

    known = ", ".join(sorted(s["name"] for s in cache["active"]))
    return None, f"No store matching '{store}' (matching is case-insensitive). Known stores: {known}"


def _deal_url(deal_id: str) -> str:
    return f"https://www.cheapshark.com/redirect?dealID={deal_id}"


def list_stores() -> list[dict]:
    return get_store_cache()["active"]


def search_deals(
    title: str | None = None,
    store: str | int | None = None,
    on_sale_only: bool = True,
    min_price: float | None = None,
    max_price: float | None = None,
    min_metacritic: int | None = None,
    min_steam_rating: int | None = None,
    sort_by: str = "Deal Rating",
    limit: int = 20,
) -> list[dict] | dict:
    store_id, error = resolve_store(store)
    if error:
        return {"error": error}

    try:
        raw_deals = cs.fetch_deals(
            title=title,
            storeID=store_id,
            onSale=1 if on_sale_only else None,
            lowerPrice=min_price,
            upperPrice=max_price,
            metacritic=min_metacritic,
            steamRating=min_steam_rating,
            sortBy=sort_by,
            pageSize=limit,
        )
    except cs.CheapSharkError as exc:
        return {"error": str(exc)}

    cache = get_store_cache()
    return [
        {
            "title": d["title"],
            "store": cache["by_id"].get(d["storeID"], d["storeID"]),
            "sale_price": float(d["salePrice"]),
            "normal_price": float(d["normalPrice"]),
            "savings_percent": round(float(d["savings"]), 1),
            "metacritic_score": int(d["metacriticScore"]) or None,
            "steam_rating": d["steamRatingText"] or None,
            "deal_url": _deal_url(d["dealID"]),
        }
        for d in raw_deals
    ]


def get_game(title: str) -> dict:
    try:
        matches = cs.fetch_games_by_title(title)
    except cs.CheapSharkError as exc:
        return {"error": str(exc)}

    if not matches:
        return {"error": f"No games found matching '{title}'."}

    exact = [m for m in matches if m["external"].lower() == title.lower()]
    best = exact[0] if exact else matches[0]
    others = [m["external"] for m in matches if m is not best][:5]

    try:
        detail = cs.fetch_game_detail(best["gameID"])
    except cs.CheapSharkError as exc:
        return {"error": str(exc)}

    cache = get_store_cache()
    current_deals = sorted(
        (
            {
                "store": cache["by_id"].get(d["storeID"], d["storeID"]),
                "price": float(d["price"]),
                "retail_price": float(d["retailPrice"]),
                "savings_percent": round(float(d["savings"]), 1),
                "deal_url": _deal_url(d["dealID"]),
            }
            for d in detail["deals"]
        ),
        key=lambda d: d["price"],
    )

    result = {
        "title": detail["info"]["title"],
        "current_deals": current_deals,
        "cheapest_current_price": current_deals[0]["price"] if current_deals else None,
        "historical_low_price": float(detail["cheapestPriceEver"]["price"]),
        "historical_low_date": datetime.fromtimestamp(
            detail["cheapestPriceEver"]["date"], tz=timezone.utc
        ).date().isoformat(),
    }
    if others:
        result["other_matches"] = others
    return result


TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_stores",
        "description": (
            "List the active PC game storefronts CheapShark tracks (Steam, GOG, Epic, "
            "Humble, etc.), including the numeric store IDs used internally. You "
            "generally don't need the IDs - search_deals accepts store names directly."
        ),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: list_stores(),
    },
    {
        "name": "search_deals",
        "description": (
            'Search current game deals across storefronts, with filters. Returns a '
            "list of deals (empty list if nothing matches - that's not an error), or "
            'a dict with an "error" key if the store name could not be matched or '
            "the API is unavailable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": 'Filter by game title (partial match, e.g. "witcher").',
                },
                "store": {
                    "type": ["string", "integer"],
                    "description": (
                        'A storefront name (e.g. "Steam", "GOG", "Epic Games Store", '
                        '"Humble Store") - matching is case-insensitive - or a numeric '
                        "CheapShark store ID. See list_stores for the full set of names."
                    ),
                },
                "on_sale_only": {
                    "type": "boolean",
                    "description": "If true (default), only return deals currently on sale.",
                    "default": True,
                },
                "min_price": {"type": "number", "description": "Minimum sale price in USD."},
                "max_price": {"type": "number", "description": "Maximum sale price in USD."},
                "min_metacritic": {
                    "type": "integer",
                    "description": "Minimum Metacritic score (0-100).",
                },
                "min_steam_rating": {
                    "type": "integer",
                    "description": "Minimum Steam user rating percent (0-100).",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["Deal Rating", "Price", "Savings", "Recent", "Metacritic", "Reviews"],
                    "description": 'Sort order. Default "Deal Rating" (best deals first).',
                    "default": "Deal Rating",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of results to return (default 20).",
                    "default": 20,
                },
            },
        },
        "handler": lambda args: search_deals(
            title=args.get("title"),
            store=args.get("store"),
            on_sale_only=args.get("on_sale_only", True),
            min_price=args.get("min_price"),
            max_price=args.get("max_price"),
            min_metacritic=args.get("min_metacritic"),
            min_steam_rating=args.get("min_steam_rating"),
            sort_by=args.get("sort_by", "Deal Rating"),
            limit=args.get("limit", 20),
        ),
    },
    {
        "name": "get_game",
        "description": (
            "Look up a game's current prices across every storefront plus its "
            "all-time historical low price - the data needed to judge whether a "
            "current deal is actually good, or whether to wait for a better one. "
            'Returns {"error": ...} if no game matched the title or the API is '
            "unavailable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": (
                        'The game title to look up (e.g. "Hades"). Matching prefers '
                        "an exact (case-insensitive) title match; if none is found, "
                        "uses the closest search result and lists other candidates "
                        'under "other_matches" in case the wrong game was picked.'
                    ),
                },
            },
            "required": ["title"],
        },
        "handler": lambda args: get_game(args["title"]),
    },
]

_TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}


def _send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def _respond(request_id, result: dict | None = None, error: dict | None = None) -> None:
    message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        message["error"] = error
    else:
        message["result"] = result
    _send(message)


def _handle_request(method: str, params: dict, request_id) -> None:
    if method == "initialize":
        _respond(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    elif method == "ping":
        _respond(request_id, {})
    elif method == "tools/list":
        _respond(request_id, {
            "tools": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": t["inputSchema"],
                }
                for t in TOOLS
            ]
        })
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        tool = _TOOLS_BY_NAME.get(name)
        if tool is None:
            _respond(request_id, error={"code": -32602, "message": f"Unknown tool: {name}"})
            return
        try:
            result = tool["handler"](arguments)
            _respond(request_id, {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": False,
            })
        except Exception as exc:
            _respond(request_id, {
                "content": [{"type": "text", "text": f"Tool execution failed: {exc}"}],
                "isError": True,
            })
    else:
        _respond(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = message.get("method")
        request_id = message.get("id")

        if method is None or request_id is None:
            continue  # a notification (no id) or a response we don't care about

        _handle_request(method, message.get("params") or {}, request_id)


if __name__ == "__main__":
    main()
