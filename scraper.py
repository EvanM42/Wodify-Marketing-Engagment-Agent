"""
scraper.py — Scrapes Wodify marketing email interaction data (opens, clicks, bounces).

First-time setup (handles MFA):
    python scraper.py --setup

Every subsequent run (headless, reuses saved session):
    python scraper.py

Watch it run with a visible browser:
    python scraper.py --debug
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

import store

EMAIL = os.getenv("WODIFY_EMAIL", "")
PASSWORD = os.getenv("WODIFY_PASSWORD", "")
SESSION_FILE = os.path.join(os.path.dirname(__file__), "session.json")
HEADLESS = "--debug" not in sys.argv and "--setup" not in sys.argv
SETUP_MODE = "--setup" in sys.argv

LOGIN_URL = "https://app.wodify.com/SignIn/Home"
MARKETING_EMAIL_URL = "https://app.wodify.com/Admin/Main?q=MarketingEmails"


# ---------------------------------------------------------------------------
# SETUP — one-time MFA login to save session
# ---------------------------------------------------------------------------

async def setup_session():
    print("[Scraper] SETUP MODE — browser opening. Complete MFA. Session saves automatically.")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(LOGIN_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        await page.locator("#Input_UserName2").fill(EMAIL)
        await page.get_by_role("button", name="CONTINUE").click()
        await page.wait_for_timeout(2500)
        await page.locator("#Input_Password").fill(PASSWORD)
        await page.get_by_role("button", name="SIGN IN TO WODIFY").click()

        print("[Scraper] Waiting for MFA and login to complete...")
        for _ in range(180):
            await asyncio.sleep(1)
            if "SignIn" not in page.url and "Login" not in page.url:
                break
        else:
            print("[Scraper] Timed out. Try again.")
            await browser.close()
            return

        await page.wait_for_timeout(2000)
        await context.storage_state(path=SESSION_FILE)
        print(f"[Scraper] Session saved to {SESSION_FILE}")
        await browser.close()


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime | None:
    """Parse Wodify date strings like 'May 04' or 'Apr 30' into a datetime."""
    year = datetime.now().year
    for fmt, s in [(f"%b %d %Y", f"{date_str.strip()} {year}"), ("%b %d, %Y", date_str.strip())]:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_recent(date_str: str, days: int = 30) -> bool:
    """Return True if the email was sent within the last `days` days."""
    d = _parse_date(date_str)
    if d is None:
        return True  # include if unparseable
    return d >= datetime.now(timezone.utc) - timedelta(days=days)


# ---------------------------------------------------------------------------
# SCRAPING
# ---------------------------------------------------------------------------

async def _wait_for_table(page, timeout: int = 20000):
    """Wait for the email list table to have real rows (not skeleton)."""
    try:
        await page.wait_for_selector("img[src*='table_skeleton']", state="hidden", timeout=timeout)
    except PlaywrightTimeout:
        pass
    # Also wait for at least one real row
    try:
        await page.wait_for_selector("table tbody tr td", timeout=timeout)
    except PlaywrightTimeout:
        pass
    await page.wait_for_timeout(1000)


async def _get_sent_emails(page) -> list[dict]:
    """Navigate to Marketing Emails, click Sent, return list of {name, date, index}."""
    await page.goto(MARKETING_EMAIL_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)
    await _wait_for_table(page)

    await page.get_by_text("Sent", exact=True).first.click()
    await page.wait_for_timeout(3000)
    await _wait_for_table(page)

    rows = await page.locator("table tbody tr").all()
    emails = []
    for i, row in enumerate(rows):
        cells = await row.locator("td").all_text_contents()
        if len(cells) < 5:
            continue
        name = cells[2].strip()
        date_str = cells[5].strip()
        emails.append({"name": name, "date": date_str, "row_index": i})

    print(f"[Scraper] Found {len(emails)} sent emails.")
    return emails


async def _scrape_email_stats(page, row_index: int) -> dict:
    """
    Click into a sent email by row index and capture the stats API response.
    Returns dict with RecipientsWithOpens, RecipientsWithClicks, RecipientsWithBounces.
    """
    captured = {}

    async def on_response(response):
        if "DataActionGet_MarketingEmail_Stats" in response.url:
            try:
                captured["data"] = await response.body()
            except Exception:
                pass

    page.on("response", on_response)

    # Re-navigate to sent list and click the right row
    await page.goto(MARKETING_EMAIL_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)
    await _wait_for_table(page)

    await page.get_by_text("Sent", exact=True).first.click()
    await page.wait_for_timeout(3000)
    await _wait_for_table(page)

    rows = await page.locator("table tbody tr").all()
    if row_index >= len(rows):
        return {}

    name_cell = rows[row_index].locator("td").nth(2)
    await name_cell.click()
    await page.wait_for_timeout(4000)

    page.remove_listener("response", on_response)

    if "data" not in captured:
        return {}

    parsed = json.loads(captured["data"])
    return parsed.get("data", {}).get("ResponseMarketingEmailStats", {})


# ---------------------------------------------------------------------------
# MAIN RUN
# ---------------------------------------------------------------------------

async def run():
    if SETUP_MODE:
        await setup_session()
        return []

    if not os.path.exists(SESSION_FILE):
        print("[Scraper] No session found. Run: python scraper.py --setup")
        return []

    all_interactions = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(storage_state=SESSION_FILE)
        page = await context.new_page()

        # Quick auth check
        await page.goto("https://app.wodify.com/Admin/Main", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        if "SignIn" in page.url or "Login" in page.url:
            print("[Scraper] Session expired. Run: python scraper.py --setup")
            await browser.close()
            return []

        try:
            sent_emails = await _get_sent_emails(page)
            # Only process emails from the last 30 days
            recent_emails = [e for e in sent_emails if _is_recent(e["date"], days=30)]
            print(f"[Scraper] Processing {len(recent_emails)} emails from the last 30 days.")

            for email_meta in recent_emails:
                print(f"[Scraper] Scraping: {email_meta['name']} ({email_meta['date']})")
                try:
                    stats = await _scrape_email_stats(page, email_meta["row_index"])
                    if not stats:
                        continue

                    interaction_map = {
                        "open":   stats.get("RecipientsWithOpens", {}).get("List", []),
                        "click":  stats.get("RecipientsWithClicks", {}).get("List", []),
                        "bounce": stats.get("RecipientsWithBounces", {}).get("List", []),
                    }

                    for interaction_type, recipients in interaction_map.items():
                        for person in recipients:
                            entry = {
                                "name":     person.get("Name", ""),
                                "email":    person.get("Email", ""),
                                "object_id": person.get("ObjectId", ""),
                                "type":     interaction_type,
                                "campaign": email_meta["name"],
                            }
                            all_interactions.append(entry)

                    opens  = len(interaction_map["open"])
                    clicks = len(interaction_map["click"])
                    print(f"  -> {opens} opens, {clicks} clicks")

                except Exception as e:
                    print(f"[Scraper] Error on '{email_meta['name']}': {e}")

        finally:
            # Refresh session
            await context.storage_state(path=SESSION_FILE)
            await browser.close()

    # Write into engagement store
    recorded = 0
    for entry in all_interactions:
        data = store.load()
        # Match by Wodify ObjectId first, then fall back to email
        client_id = next(
            (cid for cid, c in data["clients"].items()
             if cid == entry["object_id"] or c.get("email") == entry["email"]),
            None,
        )
        if client_id is None:
            client_id = entry["object_id"] or entry["email"]
            store.upsert_client(client_id, {
                "name":  entry["name"],
                "email": entry["email"],
                "phone": "",
            })

        if entry["type"] in ("open", "click", "bounce"):
            store.record_interaction(
                client_id,
                entry["type"],
                notes=f"Campaign: {entry['campaign']}",
            )
            recorded += 1

    print(f"\n[Scraper] Done — {recorded} interactions written to engagement_store.json.")
    return all_interactions


if __name__ == "__main__":
    asyncio.run(run())
