from flask import Flask, jsonify, request
import requests
import urllib.parse

app = Flask(__name__)

# Roproxy baser
RO_GAMES = "https://games.roproxy.com"
RO_CATALOG = "https://catalog.roproxy.com"
RO_USERS = "https://users.roproxy.com"

# ---------- helpers ----------

def safe_get_json(url, params=None, timeout=8):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("HTTP error:", url, "->", e)
        return None

def fetch_username(user_id: int) -> str | None:
    url = f"{RO_USERS}/v1/users/{user_id}"
    data = safe_get_json(url)
    if not data:
        return None
    return data.get("name")

# ---------- catalog items (tshirts, shirts, pants osv.) ----------

def fetch_catalog_items_for_creator(username: str):
    all_items = []
    cursor = None

    # hård cap så vi ikke spammer (30 per call, max ~300)
    MAX_CALLS = 10
    calls = 0

    while calls < MAX_CALLS:
        params = {
            "CreatorName": username,
            "Limit": 30,
        }
        if cursor:
            params["Cursor"] = cursor

        url = f"{RO_CATALOG}/v1/search/items/details"
        data = safe_get_json(url, params=params)
        calls += 1

        if not data:
            break

        items = data.get("data") or []
        for entry in items:
            asset_id = entry.get("id")
            name = entry.get("name") or "Item"
            price = entry.get("price")  # kan være None
            item_type = entry.get("itemType") or "AvatarItem"

            if asset_id is None or price is None:
                continue

            all_items.append(
                {
                    "id": int(asset_id),
                    "name": str(name),
                    "price": int(price),
                    "type": str(item_type).lower(),  # fx "tshirt", "shirt", "pants"
                }
            )

        cursor = data.get("nextPageCursor")
        if not cursor:
            break

    return all_items

# ---------- gamepasses (fra alle brugerens spil) ----------

def fetch_gamepasses_for_user(user_id: int):
    gamepasses = []

    # 1) hent brugerens universer (games)
    url_games = f"{RO_GAMES}/v2/users/{user_id}/games"
    params = {
        "accessFilter": 2,  # 2 = public games
        "limit": 50,
        "sortOrder": "Asc",
    }
    data_games = safe_get_json(url_games, params=params)
    if not data_games:
        return gamepasses

    games = data_games.get("data") or []
    for g in games:
        universe_id = g.get("id")
        if not universe_id:
            continue

        url_gp = f"{RO_GAMES}/v1/games/{universe_id}/game-passes"
        params_gp = {
            "limit": 100,
            "sortOrder": "Asc",
        }
        data_gp = safe_get_json(url_gp, params=params_gp)
        if not data_gp:
            continue

        for gp in data_gp.get("data", []):
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

            gamepasses.append(
                {
                    "id": int(gp_id),
                    "name": str(name),
                    "price": int(price),
                    "type": "gamepass",
                }
            )

    return gamepasses

# ---------- main route ----------

@app.route("/user/<int:user_id>/items")
def get_user_items(user_id: int):
    # prøv at få username fra query, ellers hent den via users.roproxy
    username = request.args.get("username")
    if not username:
        username = fetch_username(user_id)

    all_items = []

    # avatar items (tshirts, shirts, pants, osv.) baseret på creator name
    if username:
        avatar_items = fetch_catalog_items_for_creator(username)
        all_items.extend(avatar_items)

    # gamepasses fra alle brugerens spil
    gp_items = fetch_gamepasses_for_user(user_id)
    all_items.extend(gp_items)

    # sorter efter pris (billigste først)
    all_items.sort(key=lambda x: x.get("price", 0))

    return jsonify(
        {
            "userId": user_id,
            "username": username,
            "items": all_items,
        }
    )

@app.route("/")
def root():
    return "PLS DONATE backend OK (new endpoint version)", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
