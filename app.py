from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Brug roproxy-domaenen (kan ændres hvis din ven bruger en anden)
ROPROXY_BASE = "https://www.roproxy.com"

# Roblox asset type IDs:
# 34 = GamePass, 2 = T-Shirt, 11 = Shirt, 12 = Pants
ASSET_TYPES = {
    34: "gamepass",
    2: "tshirt",
    11: "shirt",
    12: "pants",
}

def fetch_inventory(user_id: int, asset_type_id: int):
    """
    Henter items for en given assetTypeId via inventory/list-json.
    Strukturen kan variere lidt, så vi prøver flere felter.
    """
    url = (
        f"{ROPROXY_BASE}/users/inventory/list-json"
        f"?assetTypeId={asset_type_id}&cursor=&itemsPerPage=100&pageNumber=1&userId={user_id}"
    )

    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("Error fetching inventory", asset_type_id, ":", e)
        return []

    # Forsøg at finde listen af items (den kan hedde Data / Items / data)
    items_raw = data.get("Data") or data.get("Items") or data.get("data") or []

    normalized = []
    for entry in items_raw:
        # Mange endpoints har Item + Product struktur
        item = entry.get("Item", entry)
        product = entry.get("Product", {}) or {}

        asset_id = item.get("AssetId") or item.get("Id") or item.get("id")
        name = item.get("Name") or item.get("name") or "Item"
        price = (
            product.get("PriceInRobux")
            or product.get("price")
            or entry.get("PriceInRobux")
            or entry.get("price")
        )

        if not asset_id or price is None:
            continue

        normalized.append(
            {
                "id": int(asset_id),
                "name": str(name),
                "price": int(price),
                "type": ASSET_TYPES.get(asset_type_id, "unknown"),
            }
        )

    return normalized


@app.route("/user/<int:user_id>/items")
def get_user_items(user_id: int):
    """
    Returnerer samlet liste af gamepasses + t-shirts + shirts + pants
    for den givne userId.
    """
    all_items = []

    for asset_type_id in ASSET_TYPES.keys():
        items = fetch_inventory(user_id, asset_type_id)
        all_items.extend(items)

    # Sorter efter pris (billigste først)
    all_items.sort(key=lambda x: x.get("price", 0))

    return jsonify({"userId": user_id, "items": all_items})


@app.route("/")
def root():
    return "PLS DONATE backend OK", 200


if __name__ == "__main__":
    # Til lokal test
    app.run(host="0.0.0.0", port=8000)
