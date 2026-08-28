import json
from unittest.mock import MagicMock, patch

import pytest

import server

STORES_URL = "https://www.cheapshark.com/api/1.0/stores"
DEALS_URL = "https://www.cheapshark.com/api/1.0/deals"
GAMES_URL = "https://www.cheapshark.com/api/1.0/games"

FAKE_STORES = [
    {"storeID": "1", "storeName": "Steam", "isActive": 1, "images": {}},
    {"storeID": "7", "storeName": "GOG", "isActive": 1, "images": {}},
    {"storeID": "99", "storeName": "Defunct Store", "isActive": 0, "images": {}},
]


@pytest.fixture(autouse=True)
def reset_store_cache():
    server._store_cache = None
    yield
    server._store_cache = None


def _fake_response(payload):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def _routed_urlopen(responses: dict[str, object]):
    """responses maps a URL prefix (before '?') to the JSON payload to return."""

    def fake_urlopen(request, timeout=None):
        url = request.full_url
        for prefix, payload in responses.items():
            if url.startswith(prefix):
                return _fake_response(payload)
        raise AssertionError(f"Unexpected URL requested: {url}")

    return fake_urlopen


def test_resolve_store_is_case_insensitive_and_rejects_unknown():
    with patch(
        "cheapshark_client.urllib.request.urlopen",
        side_effect=_routed_urlopen({STORES_URL: FAKE_STORES}),
    ):
        assert server.resolve_store("steam") == ("1", None)
        assert server.resolve_store("STEAM") == ("1", None)
        assert server.resolve_store("Steam") == ("1", None)
        assert server.resolve_store(1) == ("1", None)

        store_id, error = server.resolve_store("Epik")
        assert store_id is None
        assert "No store matching 'Epik'" in error
        assert "Steam" in error


def test_search_deals_with_no_results_returns_empty_list_not_error():
    with patch(
        "cheapshark_client.urllib.request.urlopen",
        side_effect=_routed_urlopen({STORES_URL: FAKE_STORES, DEALS_URL: []}),
    ):
        result = server.search_deals(title="a game that definitely does not exist", store="Steam")

    assert result == []


def test_search_deals_with_unknown_store_returns_error_dict():
    with patch(
        "cheapshark_client.urllib.request.urlopen",
        side_effect=_routed_urlopen({STORES_URL: FAKE_STORES}),
    ):
        result = server.search_deals(store="NotARealStore")

    assert "error" in result


def test_get_game_with_no_matches_returns_error_dict():
    with patch(
        "cheapshark_client.urllib.request.urlopen",
        side_effect=_routed_urlopen({GAMES_URL: []}),
    ):
        result = server.get_game("a game that definitely does not exist")

    assert "error" in result


def test_tools_call_dispatches_and_wraps_result(capsys):
    with patch(
        "cheapshark_client.urllib.request.urlopen",
        side_effect=_routed_urlopen({STORES_URL: FAKE_STORES}),
    ):
        server._handle_request("tools/call", {"name": "list_stores", "arguments": {}}, 1)

    out = json.loads(capsys.readouterr().out.strip())
    assert out["id"] == 1
    assert out["result"]["isError"] is False
    payload = json.loads(out["result"]["content"][0]["text"])
    assert {"store_id": "1", "name": "Steam"} in payload


def test_tools_call_unknown_tool_returns_protocol_error(capsys):
    server._handle_request("tools/call", {"name": "not_a_real_tool", "arguments": {}}, 2)

    out = json.loads(capsys.readouterr().out.strip())
    assert out["id"] == 2
    assert out["error"]["code"] == -32602
