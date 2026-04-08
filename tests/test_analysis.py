from app.deck_logic import compute_deck_stats
from app.loader import load_cards

cards = load_cards()

def test_analysis_basic_damage():
    # Use two well-known cards.
    deck = ["STRIKE_IRONCLAD", "BASH"]

    stats = compute_deck_stats(deck, cards)

    assert "total_damage" in stats
    assert stats["total_damage"] >= 10  # Strike+hit_count + Bash damage
    assert "adjusted_dpt" in stats
    assert stats["adjusted_dpt"]["normal"] > 0


def test_analysis_block():
    # Ironclad's defend card provides block.
    deck = ["DEFEND_IRONCLAD"]

    stats = compute_deck_stats(deck, cards)

    assert "total_block" in stats
    assert stats["total_block"] > 0
    assert "adjusted_bpt" in stats
    assert stats["adjusted_bpt"]["normal"] > 0


def test_analysis_vulnerable_multiplier():
    deck = ["STRIKE_IRONCLAD"]
    stats = compute_deck_stats(deck, cards)

    normal = stats["adjusted_dpt"]["normal"]
    vuln = stats["adjusted_dpt"]["vulnerable"]

    assert vuln == round(normal * 1.5, 2)