import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

def load_json_list_as_dict(path: Path, id_field: str = "id"):
    """Load a JSON list and convert it into a dict keyed by the id field."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        return data  # This should not happen, but allow it.

    if not isinstance(data, list):
        raise ValueError(f"JSON data must be list or dict, got: {type(data)}")

    result = {}
    for item in data:
        if id_field not in item:
            raise ValueError(
                f"Object missing '{id_field}' field in {path}:\n{item}"
            )
        result[item[id_field]] = item

    return result

def load_cards():
    return load_json_list_as_dict(DATA_DIR / "cards.json", id_field="id")

def load_characters():
    return load_json_list_as_dict(DATA_DIR / "characters.json", id_field="id")
