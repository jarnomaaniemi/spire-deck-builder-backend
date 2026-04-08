import pytest
from fastapi.testclient import TestClient

from main import app
client = TestClient(app)


@pytest.fixture(scope="function")
def api_key():
    """Register a test user and return the API key."""
    resp = client.post("/auth/register")
    assert resp.status_code == 200
    return resp.json()["api_key"]


@pytest.fixture(scope="function")
def deck_pack_id(api_key):
    """Create a deck and return its pack_id."""
    resp = client.post(
        "/deck/create",
        json={"character": "IRONCLAD"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    return resp.json()["pack_id"]


# ---------------------------
# PUBLIC ENDPOINT TESTS
# ---------------------------

def test_list_characters():
    resp = client.get("/characters")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert "IRONCLAD" in data


def test_character_deck():
    resp = client.get("/characters/IRONCLAD/deck")
    assert resp.status_code == 200
    data = resp.json()
    assert "character" in data
    assert "deck" in data
    assert "stats" in data


def test_character_deck_not_found():
    resp = client.get("/characters/DOES_NOT_EXIST/deck")
    assert resp.status_code == 404


def test_search_cards_by_name():
    resp = client.get("/search/cards?name=bash")
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    for card in data["cards"]:
        assert "bash" in card["name"].lower()


# ---------------------------
# PROTECTED ENDPOINT TESTS
# ---------------------------

def test_deck_create(api_key):
    resp = client.post(
        "/deck/create",
        json={"character": "IRONCLAD"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "pack_id" in data
    assert "deck" in data
    assert "stats" in data


def test_list_user_decks(api_key, deck_pack_id):
    resp = client.get("/decks", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    decks = resp.json()["decks"]
    assert len(decks) >= 1
    assert any(d["pack_id"] == deck_pack_id for d in decks)


def test_get_deck(api_key, deck_pack_id):
    resp = client.get(
        f"/deck/{deck_pack_id}",
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pack_id"] == deck_pack_id


def test_add_card(api_key, deck_pack_id):
    resp = client.post(
        "/deck/add",
        json={"pack_id": deck_pack_id, "add_card": "Bash"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "BASH" in data["deck"]


def test_wrong_api_key_cannot_access(api_key, deck_pack_id):
    wrong_key = "totally_wrong_key"

    resp = client.get(
        f"/deck/{deck_pack_id}",
        headers={"X-API-Key": wrong_key}
    )
    assert resp.status_code == 403


def test_missing_api_key_cannot_access():
    resp = client.get("/decks")
    assert resp.status_code == 401


def test_auth_me(api_key):
    resp = client.get("/auth/me", headers={"X-API-Key": api_key})
    assert resp.status_code == 200
    assert resp.json().get("api_key") == api_key


def test_create_deck_invalid_character(api_key):
    resp = client.post(
        "/deck/create",
        json={"character": "UNKNOWN"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 404


def test_add_card_invalid_card(api_key, deck_pack_id):
    resp = client.post(
        "/deck/add",
        json={"pack_id": deck_pack_id, "add_card": "NO_SUCH_CARD"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 404


def test_remove_card_success(api_key, deck_pack_id):
    # First add a card to ensure we have something to remove
    resp = client.post(
        "/deck/add",
        json={"pack_id": deck_pack_id, "add_card": "Bash"},
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    added_deck = resp.json()["deck"]
    count_after_add = added_deck.count("BASH")

    # Now remove the same card
    resp = client.delete(
        f"/deck/{deck_pack_id}/card/Bash",
        headers={"X-API-Key": api_key}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["deck"].count("BASH") == count_after_add - 1

