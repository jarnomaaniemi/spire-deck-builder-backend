from fastapi import APIRouter, HTTPException, Query, Security
from .loader import load_cards, load_characters
from .deck_logic import compute_deck_stats, compute_card_damage, compute_card_block
from .db import init_db, get_db
from uuid import uuid4
import json
from datetime import datetime, UTC
from pydantic import BaseModel

# API key dependency
from .dependencies import require_api_key

# Database Initialization
init_db()

# JSON Data Loading
cards = load_cards()
characters = load_characters()

# -----------------
# Helper functions
# -----------------

def remove_nulls(obj: dict) -> dict:
    return {key: value for key, value in obj.items() if value is not None}

def compute_dpe_from_entry(entry: dict) -> float:
    ZERO_COST_VIRTUAL = 0.6

    # Read cost from the entry or from raw data.
    if "cost" in entry:
        cost = entry.get("cost")
    else:
        cost = entry["raw"].get("cost")

    # Normalize cost.
    if cost is None or cost < 0:
        # Unplayable or cursed cards.
        return 0.0

    if cost == 0:
        effective_cost = ZERO_COST_VIRTUAL
    else:
        effective_cost = cost

    dmg = entry.get("total_damage") or 0

    return dmg / effective_cost

def compute_bpe_from_entry(entry: dict) -> float:
    ZERO_COST_VIRTUAL = 0.6

    # Read cost from the entry or from raw data.
    if "cost" in entry:
        cost = entry.get("cost")
    else:
        cost = entry["raw"].get("cost")

    # Negative cost means the card is unplayable.
    if cost is None or cost < 0:
        return 0.0

    # Zero-energy cards use a virtual cost.
    if cost == 0:
        effective_cost = ZERO_COST_VIRTUAL
    else:
        effective_cost = cost

    block = entry.get("total_block") or 0

    return block / effective_cost

def build_card_alias_index(cards: dict):
    alias_map = {}
    for real_id in cards.keys():
        parts = real_id.split("_")
        camel = "".join(p.capitalize() for p in parts)
        alias_map[camel] = real_id
    return alias_map

card_aliases = build_card_alias_index(cards)

def resolve_card_id(alias: str):
    if alias in card_aliases:
        return card_aliases[alias]
    if alias.upper() in cards:
        return alias.upper()
    return None

# --------
# ROUTERS
# --------

# PUBLIC (no API key required)
public_router = APIRouter()

# PROTECTED (requires API key)
protected_router = APIRouter(dependencies=[Security(require_api_key)])

# -----------------
# PUBLIC ENDPOINTS 
# -----------------

@public_router.post("/auth/register", tags=["Auth"])
def register():
    api_key = str(uuid4())
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (api_key, created_at)
        VALUES (?, ?)
    """, (api_key, datetime.now(UTC).isoformat()))
    conn.commit()
    conn.close()
    return {"api_key": api_key}


@public_router.get("/auth/me", tags=["Auth"])
def auth_me(api_key: str = Security(require_api_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT api_key, created_at FROM users WHERE api_key = ?", (api_key,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Invalid api_key")

    return {
        "api_key": row["api_key"],
        "created_at": row["created_at"]
    }

@public_router.get("/characters", tags=["Characters"])
def list_characters():
    return list(characters.keys())


@public_router.get("/characters/{char_id}/deck", tags=["Characters"])
def get_character_deck(char_id: str):
    char = characters.get(char_id.upper())
    if not char:
        raise HTTPException(status_code=404, detail="Unknown character")

    deck_aliases = char.get("starting_deck", [])
    resolved_ids = []
    for alias in deck_aliases:
        real = resolve_card_id(alias)
        resolved_ids.append(real or f"UNKNOWN:{alias}")

    stats = compute_deck_stats(resolved_ids, cards, character_id=char_id.upper())

    return {
        "character": char.get("name"),
        "deck": resolved_ids,
        "stats": stats
    }


# @protected_router.get("/cards")
# def list_cards():
#     return [
#         {
#             "id": cid,
#             "name": c.get("name"),
#             "type": c.get("type"),
#             "rarity": c.get("rarity"),
#             "color": c.get("color"),
#             "cost": c.get("cost"),
#         }
#         for cid, c in cards.items()
#     ]


# @protected_router.get("/cards/{card_id}")
# def get_card(card_id: str):
#     cid = card_id.upper()
#     card = cards.get(cid)
#     if not card:
#         raise HTTPException(status_code=404, detail="Card not found")
#     return {"id": cid, **card}


@public_router.get("/search/cards", tags=["Search"])
def search_cards(
    name: str | None = None,
    color: str | None = None,
    type: str | None = None,
    rarity: str | None = None,
    raw: bool = Query(default=False),
    sort: str | None = None
):
    results = []

    for cid, c in cards.items():

        if name and name.lower() not in c.get("name", "").lower():
            continue
        if color and color.lower() != c.get("color", "").lower():
            continue
        if type and type.lower() != c.get("type", "").lower():
            continue
        if rarity and rarity.lower() != c.get("rarity", "").lower():
            continue

        total_damage = compute_card_damage(c)
        total_block = compute_card_block(c)

        if raw:
            results.append({
                "id": cid,
                "raw": remove_nulls(c)
            })
            continue

        light_card = {
            "id": cid,
            "name": c.get("name"),
            "type": c.get("type"),
            "rarity": c.get("rarity"),
            "cost": c.get("cost"),
            "damage": c.get("damage"),
            "hit_count": c.get("hit_count"),
            "total_damage": total_damage,
            "block": c.get("block"),
            "total_block": total_block,
            "description": c.get("description"),
            "cards_draw": c.get("cards_draw"),
            "upgrade": c.get("upgrade"),
        }

        results.append(remove_nulls(light_card))

    if sort == "dpe":
        results.sort(key=lambda c: compute_dpe_from_entry(c), reverse=True)
    elif sort == "bpe":
        results.sort(key=lambda c: compute_bpe_from_entry(c), reverse=True)
    elif sort == "damage":
        results.sort(key=lambda c: c.get("total_damage", 0), reverse=True)
    elif sort == "block":
        results.sort(key=lambda c: c.get("total_block", 0), reverse=True)

    return {"count": len(results), "cards": results}

# ----------------
# PYDANTIC MODELS
# ----------------

class DeckCreateRequest(BaseModel):
    character: str
    
class DeckAddRequest(BaseModel):
    pack_id: str
    add_card: str
    
# ---------------------------------------
# PROTECTED ENDPOINTS (requires API KEY)
# ---------------------------------------

@protected_router.post("/deck/create", tags=["Decks"])
def create_deck(req: DeckCreateRequest, api_key: str = Security(require_api_key)):
    char_id = req.character.upper()

    conn = get_db()
    cursor = conn.cursor()

    char = characters.get(char_id)
    if not char:
        conn.close()
        raise HTTPException(404, "Unknown character")

    pack_id = str(uuid4())
    deck_aliases = char.get("starting_deck", [])
    resolved = [
        resolve_card_id(alias) or f"UNKNOWN:{alias}"
        for alias in deck_aliases
    ]

    cursor.execute("""
        INSERT INTO decks (pack_id, api_key, character, deck_json)
        VALUES (?, ?, ?, ?)
    """, (pack_id, api_key, char_id, json.dumps(resolved)))

    conn.commit()
    conn.close()

    stats = compute_deck_stats(resolved, cards, character_id=char_id)

    return {
        "pack_id": pack_id,
        "character": char_id,
        "deck": resolved,
        "stats": stats
    }


@protected_router.get("/decks", tags=["Decks"])
def list_user_decks(api_key: str = Security(require_api_key)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT pack_id, character, deck_json
        FROM decks
        WHERE api_key = ?
    """, (api_key,))

    rows = cursor.fetchall()
    conn.close()

    decks = []
    for r in rows:
        deck_list = json.loads(r["deck_json"])
        decks.append({
            "pack_id": r["pack_id"],
            "character": r["character"],
            "size": len(deck_list)
        })

    return {"decks": decks}


@protected_router.get("/deck/{pack_id}", tags=["Decks"])
def get_deck(pack_id: str, api_key: str = Security(require_api_key)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT character, deck_json
        FROM decks
        WHERE pack_id = ? AND api_key = ?
    """, (pack_id, api_key))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Pack not found")

    deck = json.loads(row["deck_json"])
    stats = compute_deck_stats(deck, cards, character_id=row["character"])

    return {
        "pack_id": pack_id,
        "character": row["character"],
        "deck": deck,
        "stats": stats
    }

@protected_router.post("/deck/add", tags=["Decks"])
def add_card_to_deck(req: DeckAddRequest, api_key: str = Security(require_api_key)):
    pack_id = req.pack_id

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT character, deck_json
        FROM decks
        WHERE pack_id = ? AND api_key = ?
    """, (pack_id, api_key))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pack not found")

    character_id = row["character"]
    deck = json.loads(row["deck_json"])

    card_id = resolve_card_id(req.add_card)
    if not card_id:
        conn.close()
        raise HTTPException(404, f"Unknown card: {req.add_card}")

    deck.append(card_id)

    cursor.execute("""
        UPDATE decks
        SET deck_json = ?
        WHERE pack_id = ? AND api_key = ?
    """, (json.dumps(deck), pack_id, api_key))

    conn.commit()
    conn.close()

    stats = compute_deck_stats(deck, cards, character_id=character_id)

    return {
        "pack_id": pack_id,
        "character": character_id,
        "deck": deck,
        "stats": stats
    }


@protected_router.delete("/deck/{pack_id}/card/{card_id}", tags=["Decks"])
def remove_card_from_deck(pack_id: str, card_id: str, api_key: str = Security(require_api_key)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT character, deck_json
        FROM decks
        WHERE pack_id = ? AND api_key = ?
    """, (pack_id, api_key))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Pack not found")

    character_id = row["character"]
    deck = json.loads(row["deck_json"])

    resolved_card_id = resolve_card_id(card_id)
    if not resolved_card_id:
        conn.close()
        raise HTTPException(404, f"Unknown card: {card_id}")

    if resolved_card_id not in deck:
        conn.close()
        raise HTTPException(404, f"Card {resolved_card_id} not in deck")

    deck.remove(resolved_card_id)

    cursor.execute("""
        UPDATE decks
        SET deck_json = ?
        WHERE pack_id = ? AND api_key = ?
    """, (json.dumps(deck), pack_id, api_key))

    conn.commit()
    conn.close()

    stats = compute_deck_stats(deck, cards, character_id=character_id)

    return {
        "pack_id": pack_id,
        "character": character_id,
        "deck": deck,
        "stats": stats
    }
    
# -------------------
# ROUTE REGISTRATION
# -------------------

router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)