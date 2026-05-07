"""
pipeline.py — Daily email marketing pipeline for Wodify gym outreach.

Flow:
    Scraper (UI → store) → Secretary (sync + summarize) → Data Scientist → Manager → Marketer

Engagement data is persisted in engagement_store.json after each run.
"""

import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

import store
from scraper import run as run_scraper
from secretary import run as run_secretary, run_recent as run_secretary_recent
from data_scientist import run as run_data_scientist
from manager import run as run_manager
from marketer import run as run_marketer


async def run_pipeline():
    print("\n" + "=" * 60)
    print("  MARKETING PIPELINE — STARTING")
    print("=" * 60)

    # 0. SCRAPER — pull fresh interaction data from Wodify UI into the store
    await run_scraper()

    # 1. SECRETARY — sync clients from Wodify and summarize engagement
    contact_data = await run_secretary(
        "Fetch all member contacts from Wodify, sync to the store, and summarize the engagement landscape."
    )

    # 2. DATA SCIENTIST — score and rank leads
    lead_scores = await run_data_scientist(
        f"Analyze this engagement summary and return a ranked list of leads to contact today:\n\n{contact_data}"
    )

    # 3. MANAGER — build today's outreach plan
    outreach_plan = await run_manager(
        f"Create today's outreach plan from these lead scores:\n\n{lead_scores}"
    )

    # 4. MARKETER — write and send personalized follow-ups
    marketer_output = await run_marketer(
        f"Execute this outreach plan. Write and send personalized emails to each lead.\n\n"
        f"Plan:\n{outreach_plan}\n\nLead data:\n{lead_scores}"
    )

    # Record each outreach as 'sent' in the engagement store
    top_leads = store.get_top_leads(50)
    contacted_ids = [
        lead["client_id"] for lead in top_leads
        if lead.get("score", 0) > 0 or lead.get("emails_sent", 0) == 0
    ]
    for client_id in contacted_ids[:20]:
        store.record_interaction(client_id, "sent", notes="Daily pipeline outreach")

    print(f"\n[Pipeline] Recorded {min(len(contacted_ids), 20)} outreach interactions in store.")
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60 + "\n")


async def run_recent_report(days: int = 2):
    """Print a report of clients who interacted with marketing emails recently."""
    print("\n" + "=" * 60)
    print(f"  RECENT INTERACTIONS — LAST {days} DAYS")
    print("=" * 60)
    report = await run_secretary_recent(days=days)
    print(report)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys
    if "--recent" in sys.argv:
        days = int(sys.argv[sys.argv.index("--recent") + 1]) if len(sys.argv) > sys.argv.index("--recent") + 1 else 2
        asyncio.run(run_recent_report(days=days))
    else:
        asyncio.run(run_pipeline())
