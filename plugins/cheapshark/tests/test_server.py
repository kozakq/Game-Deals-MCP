import httpx
import pytest
import respx

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


@respx.mock
def test_resolve_store_is_case_insensitive_and_rejects_unknown():
    respx.get(STORES_URL).mock(return_value=httpx.Response(200, json=FAKE_STORES))

    assert server.resolve_store("steam") == ("1", None)
    assert server.resolve_store("STEAM") == ("1", None)
    assert server.resolve_store("Steam") == ("1", None)
    assert server.resolve_store(1) == ("1", None)

    store_id, error = server.resolve_store("Epik")
    assert store_id is None
    assert "No store matching 'Epik'" in error
    assert "Steam" in error


@respx.mock
def test_search_deals_with_no_results_returns_empty_list_not_error():
    respx.get(STORES_URL).mock(return_value=httpx.Response(200, json=FAKE_STORES))
    respx.get(DEALS_URL).mock(return_value=httpx.Response(200, json=[]))

    result = server.search_deals(title="a game that definitely does not exist", store="Steam")

    assert result == []


@respx.mock
def test_search_deals_with_unknown_store_returns_error_dict():
    respx.get(STORES_URL).mock(return_value=httpx.Response(200, json=FAKE_STORES))

    result = server.search_deals(store="NotARealStore")

    assert "error" in result


@respx.mock
def test_get_game_with_no_matches_returns_error_dict():
    respx.get(GAMES_URL).mock(return_value=httpx.Response(200, json=[]))

    result = server.get_game("a game that definitely does not exist")

    assert "error" in result
