"""
top_clients.py — Ranks the top 30 clients by engagement.

Scoring: score = (clicks × 4) + (opens × 1)
Clicks are 4× more valuable than opens.
Ties broken by clicks first, then opens.

Output: top_30.json — a rolling history keyed by month (YYYY-MM).
Each run saves a snapshot for the current month so rankings can be
compared month to month.
"""

import json
import os
from datetime import datetime

STORE_PATH = os.path.join(os.path.dirname(__file__), "engagement_store.json")
OUT_PATH   = os.path.join(os.path.dirname(__file__), "top_30.json")


def main():
    with open(STORE_PATH) as f:
        data = json.load(f)

    scored = []
    for client_id, client in data["clients"].items():
        clicks = client.get("clicks", 0)
        opens  = client.get("opens", 0)
        score  = (clicks * 4) + (opens * 1)
        scored.append({
            "name":            client.get("name", "Unknown"),
            "email":           client.get("email", ""),
            "clicks":          clicks,
            "opens":           opens,
            "score":           score,
            "date_last_added": client.get("date_last_added", ""),
        })

    scored.sort(key=lambda x: (x["score"], x["clicks"], x["opens"]), reverse=True)
    top30 = [{"rank": rank, **client} for rank, client in enumerate(scored[:30], start=1)]

    # Load existing history or start fresh (migrate old list format if needed)
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            existing = json.load(f)
        history = existing if isinstance(existing, dict) else {}
    else:
        history = {}

    month_key = datetime.now().strftime("%Y-%m")
    history[month_key] = {
        "generated": datetime.now().isoformat(),
        "clients":   top30,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(history, f, indent=2)
    print(f"Wrote snapshot for {month_key} to {OUT_PATH}")

    print(f"\n{'Rank':<5} {'Name':<30} {'Email':<35} {'Clicks':>6} {'Opens':>5} {'Score':>6}")
    print("-" * 90)
    for entry in top30:
        print(
            f"{entry['rank']:<5} {entry['name']:<30} {entry['email']:<35} "
            f"{entry['clicks']:>6} {entry['opens']:>5} {entry['score']:>6}"
        )


if __name__ == "__main__":
    main()
