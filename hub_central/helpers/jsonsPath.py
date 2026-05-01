import json
from pathlib import Path

BASE_DIR     = Path(__file__).resolve().parent.parent
servers_path = BASE_DIR / "jsons" / "connections.json"

_EMPTY = {"servidores": {}}


def obtener_json_path() -> dict:
    try:
        with open(servers_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return _EMPTY.copy()
    except json.JSONDecodeError:
        return _EMPTY.copy()
