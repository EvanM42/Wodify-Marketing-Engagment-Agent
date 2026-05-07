import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

import wodify_api
import store
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

SYSTEM_PROMPT = """
You are a secretary for a gym marketing team.
You are given raw client data fetched from the Wodify API and their historical engagement records.

Your job:
1. Identify clients with zero engagement history (never emailed or tracked).
2. Flag clients contacted before but with no opens, clicks, or replies.
3. Highlight clients showing consistent engagement (opens, clicks, replies > 0).
4. Return a clean structured summary: who is active, who is cold, who is new.
Do not score or plan outreach — only organize and describe the data.
"""


def _extract_clients(raw) -> list[dict]:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("data", "Data", "Clients", "clients", "Results", "results"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]
    return []


def _sync_clients():
    """Pull clients from Wodify API and upsert into the local store."""
    try:
        raw = wodify_api.get_clients()
        clients = _extract_clients(raw)
        for c in clients:
            client_id = str(c.get("Id") or c.get("id") or "")
            if not client_id:
                continue
            store.upsert_client(client_id, {
                "name": f"{c.get('FirstName', c.get('first_name', ''))} {c.get('LastName', c.get('last_name', ''))}".strip(),
                "email": c.get("Email") or c.get("email", ""),
                "phone": c.get("Phone") or c.get("PhoneNumber") or c.get("phone", ""),
            })
        store.sync_timestamp()
        print(f"[Secretary] Synced {len(clients)} clients to engagement store.")
    except Exception as e:
        print(f"[Secretary] Wodify API error: {e}")


async def _run_agent(task: str, data: list) -> str:
    summary = json.dumps(data, indent=2)
    result_text = ""
    async for message in query(
        prompt=f"{task}\n\nClient data:\n{summary}",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-6",
            allowed_tools=["Read"],
            system_prompt=SYSTEM_PROMPT,
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"[Tool: {block.name}]")
        elif isinstance(message, ResultMessage):
            result_text = message.result or ""
            print(f"\n[Secretary] Done (status: {message.subtype})")
    return result_text


async def run(task: str) -> str:
    """Full sync + summarize top 50 leads."""
    print("\n[Secretary] Fetching clients from Wodify API...")
    _sync_clients()
    return await _run_agent(task, store.get_top_leads(50))


async def run_recent(days: int = 2) -> str:
    """Return clients who interacted with marketing emails in the last `days` days."""
    print(f"\n[Secretary] Querying clients active in last {days} days...")
    _sync_clients()
    recent = store.get_recent_interactions(days=days)
    print(f"[Secretary] Found {len(recent)} clients with recent interactions.")
    return await _run_agent(
        f"Summarize these clients who interacted with marketing emails in the last {days} days. "
        "List each person's name, email, phone, and what they did (open/click/reply).",
        recent,
    )


if __name__ == "__main__":
    import sys
    if "--recent" in sys.argv:
        asyncio.run(run_recent(days=2))
    else:
        asyncio.run(run("Summarize the current client engagement landscape."))
