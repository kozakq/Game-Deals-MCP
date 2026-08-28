"""MCP server exposing PC game deal search and price-history lookups via CheapShark."""

from __future__ import annotations

from datetime import datetime, timezone

from fastmcp import FastMCP

import cheapshark_client as cs

mcp = FastMCP("CheapShark Game Deals")

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


@mcp.tool
def list_stores() -> list[dict]:
    """List the active PC game storefronts CheapShark tracks (Steam, GOG, Epic, Humble, etc.),
    including the numeric store IDs used internally. You generally don't need the IDs -
    search_deals accepts store names directly."""
    return get_store_cache()["active"]


@mcp.tool
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
    """Search current game deals across storefronts, with filters.

    Args:
        title: Filter by game title (partial match, e.g. "witcher").
        store: A storefront name (e.g. "Steam", "GOG", "Epic Games Store", "Humble Store") -
            matching is case-insensitive - or a numeric CheapShark store ID. See list_stores
            for the full set of names.
        on_sale_only: If True (default), only return deals currently on sale.
        min_price: Minimum sale price in USD.
        max_price: Maximum sale price in USD.
        min_metacritic: Minimum Metacritic score (0-100).
        min_steam_rating: Minimum Steam user rating percent (0-100).
        sort_by: One of "Deal Rating" (default, best deals first), "Price", "Savings",
            "Recent", "Metacritic", "Reviews".
        limit: Max number of results to return (default 20).

    Returns a list of deals (empty list if nothing matches - that's not an error), or a
    dict with an "error" key if the store name couldn't be matched or the API is unavailable.
    """
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


@mcp.tool
def get_game(title: str) -> dict:
    """Look up a game's current prices across every storefront plus its all-time historical
    low price - the data needed to judge whether a current deal is actually good, or whether
    to wait for a better one.

    Args:
        title: The game title to look up (e.g. "Hades"). Matching prefers an exact
            (case-insensitive) title match; if none is found, uses the closest search
            result and lists other candidates under "other_matches" in case the wrong
            game was picked.

    Returns a dict with current_deals (sorted cheapest first), cheapest_current_price,
    historical_low_price, and historical_low_date. Returns {"error": ...} if no game
    matched the title or the API is unavailable.
    """
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


if __name__ == "__main__":
    mcp.run()
