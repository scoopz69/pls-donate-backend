import requests
from flask import Flask, jsonify

app = Flask(__name__)

# Roproxy V2 base
ROPROXY_V2 = "https://games.roproxy.com"

def safe_get_json(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"HTTP error: {url} -> {e}")
        return None

# 1. Get universes owned by user
def get_user_universes(user_id: int):
    url = f"{ROPROXY_V2}/v2/users/{user_id}/games"
    params = {
        "accessFilter": 2,
        "limit": 50,
        "sortOrder": "Asc"
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    universes = []
    for g in data.get("data", []):
        if "id" in g:
            universes.append(g["id"])

    return universes

# 2. Get gamepasses for a universe
def get_gamepasses(universe_id: int):
    url = f"{ROPROXY_V2}/v1/games/{universe_id}/game-passes"
    params = {
        "limit": 100,
        "sortOrder": "Asc"
    }

    data = safe_get_json(url, params=params)
    if not data:
        return []

    passes = []
    for p in data.get("data", []):
        gp_id = p.get("id")
        name = p.get("name") or "Gamepass"
        product = p.get("product") or {}

        price = product.get("price") or product.get("PriceInRobux") or 0
        if not gp_id or price <= 0:
            continue

        passes.append({
            "id": gp_id,
            "name": name,
            "price": price,
            "type": "gamepass"
        })

    return passes

# 3. Combined endpoint
@app.route("/user/<int:user_id>/items")
def get_items(user_id: int):
    universes = get_user_universes(user_id)

    all_passes = []
    for univ in universes:
        gp = get_gamepasses(univ)
        all_passes.extend(gp)

    all_passes.sort(key=lambda x: x["price"])

    return jsonify({
        "userId": user_id,
        "items": all_passes
    })

@app.route("/")
def root():
    return "PLS Donate Backend OK (Roproxy v2 Gamepass API)"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
