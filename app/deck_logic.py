CHARACTER_DPT_FACTORS = {
    "IRONCLAD": 0.50,
    "SILENT":   0.60,   # Neutralize 3 dmg, Weak, aggro style
    "DEFECT":   0.50,
    "REGENT":   0.50,
    "NECROBINDER": 0.45 # Summon-focused, slow Act 1 scaling
}

CHARACTER_BPT_FACTORS = {
    "IRONCLAD": 0.60,
    "SILENT":   0.75,   # Weak gives effective DR
    "DEFECT":   0.60,
    "REGENT":   0.60,
    "NECROBINDER": 0.65 # Minions reduce incoming damage indirectly
}

def compute_card_damage(card):
    dmg = card.get("damage") or 0
    hits = card.get("hit_count") or 1
    return dmg * hits

def compute_card_block(card):
    return card.get("block") or 0

def estimate_turn_damage(cards_data, energy_per_turn=3):
    ZERO_COST_VIRTUAL = 0.6

    items = []
    for c in cards_data:
        damage = compute_card_damage(c)
        cost = c.get("cost")

        if cost is None or cost < 0:
            continue

        if cost == 0:
            effective_cost = ZERO_COST_VIRTUAL
        else:
            effective_cost = cost

        items.append({
            "damage": damage,
            "cost": cost,
            "dpe": damage / effective_cost
        })

    # Greedy selection
    def simulate_turn():
        energy = energy_per_turn
        turn_damage = 0

        for card in sorted(items, key=lambda x: x["dpe"], reverse=True):
            if card["cost"] == 0:
                turn_damage += card["damage"]
                continue

            if card["cost"] <= energy:
                energy -= card["cost"]
                turn_damage += card["damage"]

        return turn_damage

    turn1 = simulate_turn()
    turn2 = simulate_turn()
    return (turn1 + turn2) / 2

def estimate_turn_block(cards_data, energy_per_turn=3):
    ZERO_COST_VIRTUAL = 0.6
    items = []

    for c in cards_data:
        block = compute_card_block(c)
        cost = c.get("cost")

        if cost is None or cost < 0:
            continue

        if cost == 0:
            effective_cost = ZERO_COST_VIRTUAL
        else:
            effective_cost = cost

        items.append({
            "block": block,
            "cost": cost,
            "bpe": block / effective_cost
        })

    energy = energy_per_turn
    total_block = 0

    for card in sorted(items, key=lambda x: x["bpe"], reverse=True):

        if card["cost"] == 0:
            total_block += card["block"]
            continue
        
        if card["cost"] <= energy:
            energy -= card["cost"]
            total_block += card["block"]

    return total_block

def compute_deck_stats(deck_ids, cards_index, character_id: str | None = None):
    cards_data = [cards_index[cid] for cid in deck_ids if cid in cards_index]

    total_damage = sum(compute_card_damage(c) for c in cards_data)
    total_block = sum(compute_card_block(c) for c in cards_data)

    dpt = estimate_turn_damage(cards_data)
    bpt = estimate_turn_block(cards_data)

    dpt_factor = CHARACTER_DPT_FACTORS.get(character_id, 0.50)
    bpt_factor = CHARACTER_BPT_FACTORS.get(character_id, 0.60)

    adjusted_dpt_normal = dpt * dpt_factor
    adjusted_dpt_vulnerable = dpt * 1.5 * dpt_factor

    adjusted_bpt_normal = bpt * bpt_factor

    return {
        "total_damage": total_damage,
        "total_block": total_block,

        # "dpt": {
        #     "normal": round(dpt, 2),
        #     "vulnerable": round(dpt * 1.5, 2)
        # },

        "adjusted_dpt": {
            "normal": round(adjusted_dpt_normal, 2),
            "vulnerable": round(adjusted_dpt_vulnerable, 2)
        },

        # "bpt": {
        #     "normal": round(bpt, 2)
        # },

        "adjusted_bpt": {
            "normal": round(adjusted_bpt_normal, 2)
        }
    }
    