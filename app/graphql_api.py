from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request
from graphql import GraphQLError
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.schema.config import StrawberryConfig
from strawberry.scalars import JSON
from strawberry.types import Info

from .api import (
    cards,
    characters,
    compute_bpe_from_entry,
    compute_card_block,
    compute_card_damage,
    compute_deck_stats,
    compute_dpe_from_entry,
    remove_nulls,
    resolve_card_id,
)
from .db import get_db
from .dependencies import is_valid_api_key


@strawberry.type
class AdjustedDpt:
    normal: float
    vulnerable: float


@strawberry.type
class AdjustedBpt:
    normal: float


@strawberry.type
class DeckStats:
    total_damage: int
    total_block: int
    adjusted_dpt: AdjustedDpt
    adjusted_bpt: AdjustedBpt


@strawberry.type
class DeckResponse:
    pack_id: str
    character: str
    deck: list[str]
    stats: DeckStats


@strawberry.type
class ApiKeyResult:
    api_key: str


@strawberry.type
class MeResult:
    api_key: str
    created_at: str


@strawberry.type
class CharacterDeckResult:
    character: str
    deck: list[str]
    stats: DeckStats


@strawberry.type
class CardSearchResult:
    id: str
    name: str | None = None
    type: str | None = None
    rarity: str | None = None
    cost: int | None = None
    damage: int | None = None
    hit_count: int | None = None
    total_damage: int | None = None
    block: int | None = None
    total_block: int | None = None
    description: str | None = None
    cards_draw: JSON | None = None
    upgrade: JSON | None = None
    raw: JSON | None = None


@strawberry.type
class SearchCardsResult:
    count: int
    cards: list[CardSearchResult]


@strawberry.type
class DeckSummary:
    pack_id: str
    character: str
    size: int


@strawberry.type
class DeckListResult:
    decks: list[DeckSummary]


@strawberry.type
class Query:
    @strawberry.field
    def characters(self) -> list[str]:
        return list(characters.keys())

    @strawberry.field
    def character_deck(self, char_id: str) -> CharacterDeckResult:
        char = characters.get(char_id.upper())
        if not char:
            raise GraphQLError("Unknown character")

        deck_aliases = char.get("starting_deck", [])
        resolved_ids = [resolve_card_id(alias) or f"UNKNOWN:{alias}" for alias in deck_aliases]
        stats = compute_deck_stats(resolved_ids, cards, character_id=char_id.upper())

        return CharacterDeckResult(
            character=char.get("name"),
            deck=resolved_ids,
            stats=_build_deck_stats(stats),
        )

    @strawberry.field
    def search_cards(
        self,
        name: str | None = None,
        color: str | None = None,
        type: str | None = None,
        rarity: str | None = None,
        raw: bool = False,
        sort: str | None = None,
    ) -> SearchCardsResult:
        results: list[CardSearchResult] = []

        for cid, card in cards.items():
            if name and name.lower() not in card.get("name", "").lower():
                continue
            if color and color.lower() != card.get("color", "").lower():
                continue
            if type and type.lower() != card.get("type", "").lower():
                continue
            if rarity and rarity.lower() != card.get("rarity", "").lower():
                continue

            total_damage = compute_card_damage(card)
            total_block = compute_card_block(card)

            if raw:
                results.append(
                    CardSearchResult(
                        id=cid,
                        raw=remove_nulls(card),
                    )
                )
                continue

            results.append(
                CardSearchResult(
                    id=cid,
                    name=card.get("name"),
                    type=card.get("type"),
                    rarity=card.get("rarity"),
                    cost=card.get("cost"),
                    damage=card.get("damage"),
                    hit_count=card.get("hit_count"),
                    total_damage=total_damage,
                    block=card.get("block"),
                    total_block=total_block,
                    description=card.get("description"),
                    cards_draw=card.get("cards_draw"),
                    upgrade=card.get("upgrade"),
                )
            )

        if sort == "dpe":
            results.sort(key=lambda item: compute_dpe_from_entry(_entry_from_card_result(item)), reverse=True)
        elif sort == "bpe":
            results.sort(key=lambda item: compute_bpe_from_entry(_entry_from_card_result(item)), reverse=True)
        elif sort == "damage":
            results.sort(key=lambda item: item.total_damage or 0, reverse=True)
        elif sort == "block":
            results.sort(key=lambda item: item.total_block or 0, reverse=True)

        return SearchCardsResult(count=len(results), cards=results)

    @strawberry.field
    def me(self, info: Info) -> MeResult:
        api_key = _require_api_key(info)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT api_key, created_at FROM users WHERE api_key = ?", (api_key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise GraphQLError("Invalid api_key")

        return MeResult(api_key=row["api_key"], created_at=row["created_at"])

    @strawberry.field
    def decks(self, info: Info) -> DeckListResult:
        api_key = _require_api_key(info)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT pack_id, character, deck_json
            FROM decks
            WHERE api_key = ?
            """,
            (api_key,),
        )

        rows = cursor.fetchall()
        conn.close()

        decks = []
        for row in rows:
            deck_list = _json_loads(row["deck_json"])
            decks.append(
                DeckSummary(
                    pack_id=row["pack_id"],
                    character=row["character"],
                    size=len(deck_list),
                )
            )

        return DeckListResult(decks=decks)

    @strawberry.field
    def deck(self, info: Info, pack_id: str) -> DeckResponse:
        api_key = _require_api_key(info)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT character, deck_json
            FROM decks
            WHERE pack_id = ? AND api_key = ?
            """,
            (pack_id, api_key),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise GraphQLError("Pack not found")

        deck = _json_loads(row["deck_json"])
        stats = compute_deck_stats(deck, cards, character_id=row["character"])

        return DeckResponse(
            pack_id=pack_id,
            character=row["character"],
            deck=deck,
            stats=_build_deck_stats(stats),
        )


@strawberry.type
class Mutation:
    @strawberry.field
    def register(self) -> ApiKeyResult:
        api_key = str(uuid4())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (api_key, created_at)
            VALUES (?, ?)
            """,
            (api_key, datetime.now(UTC).isoformat()),
        )
        conn.commit()
        conn.close()
        return ApiKeyResult(api_key=api_key)

    @strawberry.field
    def create_deck(self, info: Info, character: str) -> DeckResponse:
        api_key = _require_api_key(info)
        char_id = character.upper()

        char = characters.get(char_id)
        if not char:
            raise GraphQLError("Unknown character")

        pack_id = str(uuid4())
        deck_aliases = char.get("starting_deck", [])
        resolved = [resolve_card_id(alias) or f"UNKNOWN:{alias}" for alias in deck_aliases]

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO decks (pack_id, api_key, character, deck_json)
            VALUES (?, ?, ?, ?)
            """,
            (pack_id, api_key, char_id, _json_dumps(resolved)),
        )
        conn.commit()
        conn.close()

        stats = compute_deck_stats(resolved, cards, character_id=char_id)

        return DeckResponse(
            pack_id=pack_id,
            character=char_id,
            deck=resolved,
            stats=_build_deck_stats(stats),
        )

    @strawberry.field
    def add_card_to_deck(self, info: Info, pack_id: str, add_card: str) -> DeckResponse:
        api_key = _require_api_key(info)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT character, deck_json
            FROM decks
            WHERE pack_id = ? AND api_key = ?
            """,
            (pack_id, api_key),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise GraphQLError("Pack not found")

        character_id = row["character"]
        deck = _json_loads(row["deck_json"])

        card_id = resolve_card_id(add_card)
        if not card_id:
            conn.close()
            raise GraphQLError(f"Unknown card: {add_card}")

        deck.append(card_id)
        cursor.execute(
            """
            UPDATE decks
            SET deck_json = ?
            WHERE pack_id = ? AND api_key = ?
            """,
            (_json_dumps(deck), pack_id, api_key),
        )
        conn.commit()
        conn.close()

        stats = compute_deck_stats(deck, cards, character_id=character_id)
        return DeckResponse(
            pack_id=pack_id,
            character=character_id,
            deck=deck,
            stats=_build_deck_stats(stats),
        )

    @strawberry.field
    def remove_card_from_deck(self, info: Info, pack_id: str, card_id: str) -> DeckResponse:
        api_key = _require_api_key(info)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT character, deck_json
            FROM decks
            WHERE pack_id = ? AND api_key = ?
            """,
            (pack_id, api_key),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise GraphQLError("Pack not found")

        character_id = row["character"]
        deck = _json_loads(row["deck_json"])

        resolved_card_id = resolve_card_id(card_id)
        if not resolved_card_id:
            conn.close()
            raise GraphQLError(f"Unknown card: {card_id}")

        if resolved_card_id not in deck:
            conn.close()
            raise GraphQLError(f"Card {resolved_card_id} not in deck")

        deck.remove(resolved_card_id)
        cursor.execute(
            """
            UPDATE decks
            SET deck_json = ?
            WHERE pack_id = ? AND api_key = ?
            """,
            (_json_dumps(deck), pack_id, api_key),
        )
        conn.commit()
        conn.close()

        stats = compute_deck_stats(deck, cards, character_id=character_id)
        return DeckResponse(
            pack_id=pack_id,
            character=character_id,
            deck=deck,
            stats=_build_deck_stats(stats),
        )


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    # GraphQL-kenttien nimet pysyvät snake_case-muodossa, eivätkä muutu camelCaseksi automaattisesti. 
    config=StrawberryConfig(auto_camel_case=False),
)

# FastAPI:n Request-objekti lisätään GraphQL:än kontekstiin, josta on luettavissa mm. HTTP-headerit, kuten API key.
def get_context(request: Request):
    return {"request": request}

graphql_router = GraphQLRouter(schema, context_getter=get_context)


def _require_api_key(info) -> str:
    # Strawberryn antama resolver-olion parametri, jonka kautta context luetaann. Contextiin on lisätty FastAPI:n Request-objekti, josta voidaan hakea headerit.
    request = info.context["request"]
    api_key = request.headers.get("X-API-Key")
    if not is_valid_api_key(api_key):
        raise GraphQLError("Invalid or missing API key")
    return api_key


def _build_deck_stats(stats: dict) -> DeckStats:
    return DeckStats(
        total_damage=stats["total_damage"],
        total_block=stats["total_block"],
        adjusted_dpt=AdjustedDpt(
            normal=stats["adjusted_dpt"]["normal"],
            vulnerable=stats["adjusted_dpt"]["vulnerable"],
        ),
        adjusted_bpt=AdjustedBpt(normal=stats["adjusted_bpt"]["normal"]),
    )


def _json_dumps(value) -> str:
    return json.dumps(value)


def _json_loads(value: str):
    return json.loads(value)


def _entry_from_card_result(card: CardSearchResult) -> dict:
    if card.raw is not None:
        raw_entry = card.raw
        if isinstance(raw_entry, dict):
            return raw_entry

    return {
        "id": card.id,
        "name": card.name,
        "type": card.type,
        "rarity": card.rarity,
        "cost": card.cost,
        "damage": card.damage,
        "hit_count": card.hit_count,
        "total_damage": card.total_damage,
        "block": card.block,
        "total_block": card.total_block,
        "description": card.description,
        "cards_draw": card.cards_draw,
        "upgrade": card.upgrade,
    }
