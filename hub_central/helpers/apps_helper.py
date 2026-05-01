import json
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent.parent
apps_path = BASE_DIR / "jsons" / "apps.json"

_EMPTY = {"apps": []}


def obtener_apps() -> dict:
    try:
        with open(apps_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _EMPTY.copy()


def guardar_apps(data: dict) -> None:
    apps_path.parent.mkdir(parents=True, exist_ok=True)
    with open(apps_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def buscar_app(nombre: str) -> tuple[dict | None, int]:
    """Devuelve (app, índice) o (None, -1) si no existe."""
    data = obtener_apps()
    for i, app in enumerate(data["apps"]):
        if app["name"].lower() == nombre.lower():
            return app, i
    return None, -1
