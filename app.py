from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Roproxy v2 host (din vens stil)
ROXY_BASE = "https://roxytheproxy.com"


def safe_get_json(url: str, timeout: int = 8):
    """GET + JSON med simpel fejl-håndtering."""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("HTTP error:", url, "->", e)
        return None


def fetch_gamepasses_for_user(user_id: int):
    """
    Henter ALLE gamepasses for alle offentlige games som brugeren ejer.
    Kun gamepasses, ingen tøj.
    """
    gamepasses = []

    # 1) Hent alle public games for user
    games_url = (
        f"{ROXY_BASE}/games.roblox.com/v2/users/{user_id}/games"
        "?accessFilter=2&limit=50&sortOrder=Asc"
    )
    games_data = safe_get_json(games_url)
    if not games_data:
        return gamepasses

    games = games_data.get("data") or []
    for g in games:
        universe_id = g.get("id")
        if not universe_id:
            continue

        # 2) Hent gamepasses for hvert universe
        gp_url = (
            f"{ROXY_BASE}/games.roblox.com/v1/games/{universe_id}/game-passes"
            "?limit=100&sortOrder=Asc"
        )
        gp_data = safe_get_json(gp_url)
        if not gp_data:
            continue

        for gp in gp_data.get("data", []):
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

            # Kun gamepasses med pris > 0
            if int(price) <= 0:
                continue

            gamepasses.append(
                {
                    "id": int(gp_id),
                    "name": str(name),
                    "price": int(price),
                    "type": "gamepass",
                }
            )

    # Sorter efter pris
    gamepasses.sort(key=lambda x: x["price"])
    return gamepasses


@app.route("/user/<int:user_id>/items")
def get_user_items(user_id: int):
    """
    Simpelt endpoint:
    /user/<id>/items  ->  { userId, items[] }
    items = KUN gamepasses (id, name, price, type="gamepass")
    """
    items = fetch_gamepasses_for_user(user_id)
    return jsonify(
        {
            "userId": user_id,
            "items": items,
        }
    )


@app.route("/")
def root():
    return "PLS DONATE backend OK (gamepasses only via roxytheproxy.com)", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
