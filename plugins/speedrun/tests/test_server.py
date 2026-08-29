import json
from unittest.mock import MagicMock, patch

import pytest

import server

GAMES_URL = "https://www.speedrun.com/api/v1/games"
CATEGORIES_URL = "https://www.speedrun.com/api/v1/games/o1y9okr6/categories"
LEADERBOARD_URL = "https://www.speedrun.com/api/v1/leaderboards/o1y9okr6/category/zd3xmmvd"

FAKE_GAME_MATCHES = [
    {
        "id": "o1y9okr6",
        "names": {"international": "Hades"},
        "abbreviation": "hades",
        "weblink": "https://www.speedrun.com/hades",
    },
    {
        "id": "3dxy5vv6",
        "names": {"international": "Hades 2"},
        "abbreviation": "hades2",
        "weblink": "https://www.speedrun.com/hades2",
    },
]

FAKE_CATEGORIES = [
    {
        "id": "zd3xmmvd",
        "name": "Any Heat",
        "weblink": "https://www.speedrun.com/hades?h=Any_Heat",
        "type": "per-game",
        "miscellaneous": False,
    },
    {
        "id": "9d8e6j6d",
        "name": "Any Heat (Early Access)",
        "weblink": "https://www.speedrun.com/hades?h=Any_Heat_EA",
        "type": "per-game",
        "miscellaneous": True,
    },
]

FAKE_LEADERBOARD = {
    "runs": [
        {
            "place": 1,
            "run": {
                "players": [{"rel": "user", "id": "8e9k1yoj"}],
                "times": {"primary_t": 133},
                "videos": {"links": [{"uri": "https://youtu.be/EhYVNSnXJH4"}]},
                "weblink": "https://www.speedrun.com/hades/runs/men4r5qm",
            },
        },
        {
            "place": 2,
            "run": {
                # A guest runner - no registered id, just an inline name.
                "players": [{"rel": "guest", "name": "SomeGuest"}],
                "times": {"primary_t": 200},
                "videos": None,
                "weblink": "https://www.speedrun.com/hades/runs/guestrun1",
            },
        },
    ],
    "players": {
        "data": [
            {"id": "8e9k1yoj", "names": {"international": "Vorime"}},
        ]
    },
}


def _fake_response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _routed_urlopen(responses: dict[str, object]):
    """responses maps a URL prefix (before '?') to the JSON payload to return."""

    def fake_urlopen(url, timeout=None):
        for prefix, payload in responses.items():
            if url.startswith(prefix):
                return _fake_response({"data": payload})
        raise AssertionError(f"Unexpected URL requested: {url}")

    return fake_urlopen


def test_search_game_prefers_exact_match_and_lists_others():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({GAMES_URL: FAKE_GAME_MATCHES}),
    ):
        result = server.search_game("Hades")

    assert result["id"] == "o1y9okr6"
    assert result["name"] == "Hades"
    assert result["other_matches"] == ["Hades 2"]


def test_search_game_with_no_results_returns_error_dict():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({GAMES_URL: []}),
    ):
        result = server.search_game("a game that definitely does not exist")

    assert "error" in result


def test_get_categories_includes_type_and_miscellaneous_flag():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({CATEGORIES_URL: FAKE_CATEGORIES}),
    ):
        result = server.get_categories("o1y9okr6")

    names = {c["name"]: c for c in result["categories"]}
    assert names["Any Heat"]["miscellaneous"] is False
    assert names["Any Heat (Early Access)"]["miscellaneous"] is True
    assert all("type" in c for c in result["categories"])


def test_get_categories_with_none_found_returns_error_dict():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({CATEGORIES_URL: []}),
    ):
        result = server.get_categories("o1y9okr6")

    assert "error" in result


def test_get_leaderboard_resolves_registered_and_guest_players():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({LEADERBOARD_URL: FAKE_LEADERBOARD}),
    ):
        result = server.get_leaderboard("o1y9okr6", "zd3xmmvd", top=5)

    runs = result["runs"]
    assert runs[0]["players"] == ["Vorime"]
    assert runs[0]["time_seconds"] == 133
    assert runs[0]["video"] == "https://youtu.be/EhYVNSnXJH4"

    # Guest runner: no id to resolve, falls back to the inline name; missing
    # videos should come back as None instead of raising.
    assert runs[1]["players"] == ["SomeGuest"]
    assert runs[1]["video"] is None


def test_get_leaderboard_with_no_runs_returns_error_dict():
    with patch(
        "server.request.urlopen",
        side_effect=_routed_urlopen({LEADERBOARD_URL: {"runs": [], "players": {"data": []}}}),
    ):
        result = server.get_leaderboard("o1y9okr6", "zd3xmmvd")

    assert "error" in result
