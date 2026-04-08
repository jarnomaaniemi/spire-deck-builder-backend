from app.loader import load_cards, load_characters

def test_cards_loaded():
    cards = load_cards()
    assert isinstance(cards, dict)
    assert len(cards) > 0, "cards.json should not be empty"

def test_characters_loaded():
    chars = load_characters()
    assert isinstance(chars, dict)
    assert len(chars) > 0, "characters.json should not be empty"

def test_character_fields():
    chars = load_characters()
    for cid, char in chars.items():
        assert "name" in char
        assert "starting_deck" in char
        assert isinstance(char["starting_deck"], list)