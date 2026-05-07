"""
export_top30.py — Exports the most recent top 30 snapshot to top_30.csv.
Open top_30.csv directly in Excel.
"""

import csv
import json
import os

TOP30_PATH = os.path.join(os.path.dirname(__file__), "top_30.json")
CSV_PATH   = os.path.join(os.path.dirname(__file__), "top_30.csv")

with open(TOP30_PATH) as f:
    history = json.load(f)

latest_month = sorted(history.keys())[-1]
clients = history[latest_month]["clients"]
generated = history[latest_month]["generated"]

with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["rank", "name", "email", "clicks", "opens", "score", "date_last_added"])
    writer.writeheader()
    writer.writerows(clients)

print(f"Exported {len(clients)} clients from {latest_month} (generated {generated})")
print(f"File ready: {CSV_PATH}")
