import requests
from flask import Flask, jsonify

app = Flask(__name__)

# Brug Roblox direkte i stedet for roproxy
GAMES_BASE = "https://games.roblox.com"


def safe_get_json(url: str, params: dict | None = None, timeout: int = 10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"HTTP error: {url} -> {e}")
        return None


def get_user_universes(user_id: int) -> list[int]:
    """
    Henter public games (universes) for en user via:
    https://games.roblox.com/v2/users/{userId}/games
    """
    url = f"{GAMES_BASE}/v2/users/{user_id}/games"
    params = {
        "accessFilter": 2,   # public games
        "limit": 50,
        "sortOrder": "Asc",
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    universes: list[int] = []
    for g in data.get("data", []):
        uid = g.get("id")
        if uid is not None:
            universes.append(int(uid))

    return universes


def get_gamepasses_for_universe(universe_id: int) -> list[dict]:
    """
    Henter gamepasses for et universe via:
    https://games.roblox.com/v1/games/{universeId}/game-passes
    """
    url = f"{GAMES_BASE}/v1/games/{universe_id}/game-passes"
    params = {
        "limit": 100,
        "sortOrder": "Asc",
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    result: list[dict] = []
    for gp in data.get("data", []):
        gp_id = gp.get("id")
        name = gp.get("name") or "Gamepass"
        product = gp.get("product") or {}
        price = (
            product.get("price")
            or product.get("PriceInRobux")
            or 0
        )

        if gp_id is None or price is None:
            continue

        price = int(price)
        if price <= 0:
            continue

        result.append(
            {
                "id": int(gp_id),
                "name": str(name),
                "price": price,
                "type": "gamepass",
            }
        )

    return result


@app.route("/user/<int:user_id>/items")
def get_items(user_id: int):
    """
    /user/<id>/items -> { userId, items[] }
    items = alle gamepasses fra alle public universes, med:
      - id
      - name
      - price
      - type = "gamepass"
    """
    universes = get_user_universes(user_id)

    all_passes: list[dict] = []
    seen = set()

    for univ in universes:
        passes = get_gamepasses_for_universe(univ)
        for p in passes:
            key = (p["id"], p["price"])
            if key not in seen:
                seen.add(key)
                all_passes.append(p)

    all_passes.sort(key=lambda x: x["price"])

    return jsonify(
        {
            "userId": user_id,
            "items": all_passes,
        }
    )


@app.route("/")
def root():
    return "PLS DONATE backend OK (direct games.roblox.com)", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
