"""MCP server exposing Game Speedrun Data via Speedrun.com.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from urllib import parse, request, error


class SpeedrunError(Exception):
    """Raised when the speedrun.com API can't be reached or returns an error."""


BASE_URL = "https://www.speedrun.com/api/v1"
TIMEOUT = 10.0

SERVER_NAME = "speedrun-mcp"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"

def _fetch_games_by_name(name: str) -> list[dict]:
    url = f"{BASE_URL}/games?{parse.urlencode({'name': name})}"
    try:
        with request.urlopen(url, timeout=TIMEOUT) as response:
            body = json.load(response)
    except error.HTTPError as exc:
        raise SpeedrunError(f"speedrun.com API returned an error: {exc.code}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise SpeedrunError(f"Could not reach speedrun.com API: {exc}") from exc
    return body["data"]


def search_game(title: str) -> dict:
    try:
        matches = _fetch_games_by_name(title)
    except SpeedrunError as exc:
        return {"error": str(exc)}

    if not matches:
        return {"error": f"No games found matching '{title}'."}

    exact = [g for g in matches if g["names"]["international"].lower() == title.lower()]
    best = exact[0] if exact else matches[0]
    others = [g["names"]["international"] for g in matches if g is not best][:5]

    result = {
        "id": best["id"],
        "name": best["names"]["international"],
        "abbreviation": best["abbreviation"],
        "weblink": best["weblink"],
    }
    if others:
        result["other_matches"] = others
    return result


def _fetch_categories(game_id: str) -> list[dict]:
    url = f"{BASE_URL}/games/{game_id}/categories"
    try:
        with request.urlopen(url, timeout=TIMEOUT) as response:
            body = json.load(response)
    except error.HTTPError as exc:
        raise SpeedrunError(f"speedrun.com API returned an error: {exc.code}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise SpeedrunError(f"Could not reach speedrun.com API: {exc}") from exc
    return body["data"]


def get_categories(game_id: str) -> dict:
    try:
        categories = _fetch_categories(game_id)
    except SpeedrunError as exc:
        return {"error": str(exc)}

    if not categories:
        return {"error": f"No categories found for game ID '{game_id}'."}

    result = {
        "game_id": game_id,
        "categories": [
            {
                "id": c["id"],
                "name": c["name"],
                "weblink": c["weblink"],
                "type": c["type"],
                "miscellaneous": c["miscellaneous"],
            }
            for c in categories
        ],
    }
    return result


def _fetch_leaderboard(game_id: str, category_id: str, top: int = 10) -> dict:
    query = parse.urlencode({"top": top, "embed": "players"})
    url = f"{BASE_URL}/leaderboards/{game_id}/category/{category_id}?{query}"
    try:
        with request.urlopen(url, timeout=TIMEOUT) as response:
            body = json.load(response)
    except error.HTTPError as exc:
        raise SpeedrunError(f"speedrun.com API returned an error: {exc.code}") from exc
    except (error.URLError, TimeoutError, OSError) as exc:
        raise SpeedrunError(f"Could not reach speedrun.com API: {exc}") from exc
    return body["data"]


def get_leaderboard(game_id: str, category_id: str, top: int = 10) -> dict:
    try:
        leaderboard = _fetch_leaderboard(game_id, category_id, top)
    except SpeedrunError as exc:
        return {"error": str(exc)}

    if not leaderboard.get("runs"):
        return {"error": f"No runs found for game ID '{game_id}' and category ID '{category_id}'."}

    # id -> display name, built once from the embedded flat players list
    player_names = {
        p["id"]: p["names"]["international"]
        for p in leaderboard["players"]["data"]
    }

    runs = []
    for entry in leaderboard["runs"]:
        run = entry["run"]
        players = [
            player_names.get(p.get("id"), p.get("name", "unknown"))
            for p in run["players"]
        ]
        videos = run.get("videos")
        video_url = videos["links"][0]["uri"] if videos and videos.get("links") else None

        runs.append({
            "place": entry["place"],
            "players": players,
            "time_seconds": run["times"]["primary_t"],
            "video": video_url,
            "weblink": run["weblink"],
        })

    return {"game_id": game_id, "category_id": category_id, "runs": runs}



TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_leaderboard",
        "description": (
            "Retrieve the leaderboard for a specific game and category by their IDs. "
            "Returns {\"error\": ...} if the leaderboard is not found or if an error occurs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {
                    "type": "string",
                    "description": 'The ID of the game (e.g. "o1y9wo6q").',
                },
                "category_id": {
                    "type": "string",
                    "description": 'The ID of the category (e.g. "4d4e1e1e").',
                },
                "top": {
                    "type": "integer",
                    "description": "The number of top leaderboard entries to retrieve.",
                },
            },
            "required": ["game_id", "category_id"],
        },
        "handler": lambda args: get_leaderboard(args["game_id"], args["category_id"], args.get("top", 10)),
    },
    {
        "name": "get_categories",
        "description": (
            "Retrieve the categories for a game by its ID. Returns {\"error\": ...} "
            "if the game has no categories or if an error occurs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "game_id": {
                    "type": "string",
                    "description": 'The ID of the game (e.g. "o1y9wo6q").',
                },
            },
            "required": ["game_id"],
        },
        "handler": lambda args: get_categories(args["game_id"]),
    },
    {
    "name": "search_game",
    "description": (
        "Search speedrun.com for a game by title and resolve it to the game ID "
        "needed by get_categories and get_leaderboard. Returns {\"error\": ...} "
        "if nothing matched."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": 'The game title to search for (e.g. "Hades").',
            },
        },
        "required": ["title"],
    },
    "handler": lambda args: search_game(args["title"]),
}
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
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        try:
            method = message.get("method")
            params = message.get("params") or {}
            request_id = message.get("id")
            if method and request_id is not None:
                _handle_request(method, params, request_id)
        except Exception as exc:
            request_id = message.get("id")
            if request_id is not None:
                _respond(request_id, error={"code": -32603, "message": f"Internal error: {exc}"})


if __name__ == "__main__":
    main()
