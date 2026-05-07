import json
import os
from datetime import datetime, timedelta, timezone

STORE_PATH = os.path.join(os.path.dirname(__file__), "engagement_store.json")


def load() -> dict:
    if not os.path.exists(STORE_PATH):
        return {"clients": {}, "last_sync": None}
    with open(STORE_PATH) as f:
        return json.load(f)


def save(data: dict):
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def upsert_client(client_id: str, info: dict):
    store = load()
    today = datetime.now().strftime("%m-%d-%Y")
    if client_id not in store["clients"]:
        store["clients"][client_id] = {
            "name": info.get("name", ""),
            "email": info.get("email", ""),
            "phone": info.get("phone", ""),
            "opens": 0,
            "clicks": 0,
            "replies": 0,
            "emails_sent": 0,
            "last_contacted": None,
            "date_last_added": today,
            "history": [],
        }
    else:
        existing = store["clients"][client_id]
        existing["name"] = info.get("name", existing["name"])
        existing["email"] = info.get("email", existing["email"])
        existing["phone"] = info.get("phone", existing["phone"])
        existing["date_last_added"] = today
    save(store)


def record_interaction(client_id: str, interaction_type: str, notes: str = ""):
    """Record an interaction. Types: 'sent', 'open', 'click', 'reply'."""
    store = load()
    if client_id not in store["clients"]:
        return
    client = store["clients"][client_id]

    client["date_last_added"] = datetime.now().strftime("%m-%d-%Y")

    if interaction_type == "open":
        client["opens"] += 1
    elif interaction_type == "click":
        client["clicks"] += 1
    elif interaction_type == "reply":
        client["replies"] += 1
    elif interaction_type == "sent":
        client["emails_sent"] += 1
        client["last_contacted"] = datetime.now().isoformat()

    client["history"].append({
        "type": interaction_type,
        "timestamp": datetime.now().isoformat(),
        "notes": notes,
    })
    save(store)


def get_engagement_score(client: dict) -> int:
    return (
        client["opens"] * 1 +
        client["clicks"] * 3 +
        client["replies"] * 5
    )


def get_top_leads(n: int = 20) -> list[dict]:
    store = load()
    scored = [
        {**c, "client_id": cid, "score": get_engagement_score(c)}
        for cid, c in store["clients"].items()
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:n]


def get_recent_interactions(days: int = 2) -> list[dict]:
    """Return clients who had an open, click, or reply within the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    data = load()
    results = []
    for cid, client in data["clients"].items():
        recent = [
            h for h in client.get("history", [])
            if h["type"] in ("open", "click", "reply")
            and datetime.fromisoformat(h["timestamp"]).replace(tzinfo=timezone.utc) >= cutoff
        ]
        if recent:
            results.append({
                **client,
                "client_id": cid,
                "score": get_engagement_score(client),
                "recent_interactions": recent,
            })
    results.sort(key=lambda x: len(x["recent_interactions"]), reverse=True)
    return results


def sync_timestamp():
    store = load()
    store["last_sync"] = datetime.now().isoformat()
    save(store)
