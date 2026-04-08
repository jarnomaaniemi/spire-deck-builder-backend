from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def execute_graphql(query: str, variables: dict | None = None, headers: dict | None = None):
    response = client.post(
        "/graphql",
        json={"query": query, "variables": variables},
        headers=headers or {},
    )
    assert response.status_code == 200
    return response.json()


def register_api_key() -> str:
    data = execute_graphql("mutation { register { api_key } }")
    return data["data"]["register"]["api_key"]


def create_deck(api_key: str) -> str:
    data = execute_graphql(
        """
        mutation CreateDeck($character: String!) {
          create_deck(character: $character) {
            pack_id
            character
            deck
          }
        }
        """,
        variables={"character": "IRONCLAD"},
        headers={"X-API-Key": api_key},
    )
    return data["data"]["create_deck"]["pack_id"]


def test_graphql_characters_and_search():
    characters = execute_graphql("query { characters }")
    assert "IRONCLAD" in characters["data"]["characters"]

    search = execute_graphql(
        """
        query SearchCards($name: String) {
          search_cards(name: $name) {
            count
            cards {
              id
              name
            }
          }
        }
        """,
        variables={"name": "bash"},
    )
    cards = search["data"]["search_cards"]["cards"]
    assert search["data"]["search_cards"]["count"] >= 1
    assert any("bash" in card["name"].lower() for card in cards)


def test_graphql_protected_deck_mutations():
    api_key = register_api_key()
    pack_id = create_deck(api_key)

    deck_data = execute_graphql(
        """
        query Deck($packId: String!) {
          deck(pack_id: $packId) {
            pack_id
            character
            deck
          }
        }
        """,
        variables={"packId": pack_id},
        headers={"X-API-Key": api_key},
    )
    assert deck_data["data"]["deck"]["pack_id"] == pack_id

    add_data = execute_graphql(
        """
        mutation AddCard($packId: String!, $addCard: String!) {
          add_card_to_deck(pack_id: $packId, add_card: $addCard) {
            deck
          }
        }
        """,
        variables={"packId": pack_id, "addCard": "Bash"},
        headers={"X-API-Key": api_key},
    )
    deck_after_add = add_data["data"]["add_card_to_deck"]["deck"]
    count_after_add = deck_after_add.count("BASH")
    assert count_after_add >= 1

    remove_data = execute_graphql(
        """
        mutation RemoveCard($packId: String!, $cardId: String!) {
          remove_card_from_deck(pack_id: $packId, card_id: $cardId) {
            deck
          }
        }
        """,
        variables={"packId": pack_id, "cardId": "Bash"},
        headers={"X-API-Key": api_key},
    )
    deck_after_remove = remove_data["data"]["remove_card_from_deck"]["deck"]
    assert deck_after_remove.count("BASH") == count_after_add - 1


def test_graphql_protected_mutation_requires_api_key():
    data = execute_graphql(
        """
        mutation {
          create_deck(character: "IRONCLAD") {
            pack_id
          }
        }
        """
    )
    assert data["data"] is None
    assert data["errors"]


def test_graphql_invalid_api_key_rejected():
    data = execute_graphql(
        """
        mutation {
          create_deck(character: "IRONCLAD") {
            pack_id
          }
        }
        """,
        headers={"X-API-Key": "totally_wrong_key"},
    )
    assert data["data"] is None
    assert data["errors"]