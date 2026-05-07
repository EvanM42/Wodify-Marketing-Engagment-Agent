# Wodify Email Marketing Agent

An automated marketing tool that reads your Wodify email campaign data, figures out which members are most engaged, and can send them personalized follow-up emails — all without you having to do it manually.

It works in two main ways:
- **Scrape + Report**: Pull who opened and clicked your emails and rank the top 30 most engaged members.
- **Full Pipeline**: Do all of the above, then automatically write and send personalized follow-up emails to your top leads.

---

## Where the Data Comes From

The data comes from two sources depending on what is being collected:

- **Client list** (names, emails, phone numbers) — pulled directly from the **Wodify REST API** using your API key. This is a standard API call that Wodify officially supports.
- **Email engagement data** (who opened, who clicked, who bounced) — scraped from the **Wodify web UI** using a browser automation tool called Playwright. Wodify does not expose this data through their API, so the scraper logs in as you, navigates to Marketing Emails → Sent, clicks into each campaign, and captures the engagement stats directly from the page. This is why the one-time login setup step is required.

---

## What is Playwright?

**What is it?**
Playwright is an open-source tool made by Microsoft that lets you control a web browser through code. You write a script and it drives the browser exactly like a human would — clicking buttons, filling forms, navigating pages.

**How secure is it?**
Playwright itself is secure and widely used in professional software testing. The security risk isn't Playwright — it's that your Wodify credentials are stored in the `.env` file and the session is saved to `session.json`, so you want to make sure those files never get shared or uploaded anywhere.

**What does it do here?**
It logs into your Wodify account, navigates to the Marketing Emails page, clicks into each sent campaign, and reads the engagement stats (opens, clicks, bounces) that Wodify only shows in the UI. It then hands that data off to the rest of the pipeline.

**How does it do it?**
Playwright launches a real Chromium browser (the same engine as Google Chrome) either visibly or invisibly in the background. It interacts with the page the same way you would, and it can also intercept the network responses the page receives — which is how it captures the engagement data without having to scrape the raw HTML.

---

## What You Need Before Starting

- **Python 3.10 or higher** — download at https://www.python.org/downloads/
- **A Wodify account** with access to Marketing Emails
- **Your Wodify login email and password**
- **Your Wodify Public API key** (see below for how to find it)
- **An Anthropic API key** — needed to run the AI agents (secretary, data scientist, manager, marketer). Sign up at https://console.anthropic.com

### How to find your Wodify API key
1. Log into Wodify
2. Click your gym name in the top right
3. Go to **Settings** → **Integrations** → **API**
4. Copy the **Public API Key**

---

## Installation

### 1. Install Python dependencies
Open a terminal in this folder and run:
```bash
pip install playwright python-dotenv requests claude-agent-sdk
```

### 2. Install the browser the scraper uses
```bash
playwright install chromium
```

### 3. Set up your credentials
Copy `example.env` to a new file called `.env`:
```bash
cp example.env .env
```
Then open `.env` and fill in your three values:
```
WODIFY_PUBLIC_API_KEY=your_api_key_here
WODIFY_EMAIL=your_wodify_login_email@example.com
WODIFY_PASSWORD=your_wodify_password
```
The `.env` file is ignored by git and will never be uploaded anywhere.

### 4. Set your Anthropic API key
The AI agents need an Anthropic API key to run. Set it as an environment variable:

**Mac / Linux:**
```bash
export ANTHROPIC_API_KEY=your_anthropic_key_here
```

**Windows (Command Prompt):**
```
set ANTHROPIC_API_KEY=your_anthropic_key_here
```

**Windows (PowerShell):**
```
$env:ANTHROPIC_API_KEY="your_anthropic_key_here"
```

### 5. Log in once to save your session (handles MFA)
Wodify uses two-factor authentication, so you need to log in manually one time. This saves a session file so every future run is fully automatic.
```bash
python scraper.py --setup
```
A browser window will open with your email pre-filled. Enter your password, complete the MFA step (text code, authenticator app, etc.), and once you land on the Wodify dashboard, go back to your terminal and press **Enter**. A `session.json` file will be saved. You only need to do this once — or again if your session expires.

---

## How to Run Each Part

### Pull fresh email engagement data from Wodify
This opens a browser in the background, logs into your Wodify account, reads your sent email campaigns from the last 30 days, and saves who opened and clicked each one.
```bash
python scraper.py
```
To watch the browser while it runs (useful for troubleshooting):
```bash
python scraper.py --debug
```

---

### Get the top 30 most engaged members
After running the scraper, this ranks your members by engagement and saves the results. It scores each person using: **(clicks × 4) + (opens × 1)** — clicks count more because they show stronger interest.
```bash
python top_clients.py
```
Results are saved to `top_30.json`. Each time you run this in a new month, a new snapshot is added so you can track changes over time.

---

### Export the top 30 to Excel
After running `top_clients.py`, this creates a `top_30.csv` file you can open directly in Excel:
```bash
python export_top30.py
```
Double-click `top_30.csv` and it opens straight in Excel — no import steps needed.

---

### Run the full pipeline (scrape + AI follow-ups)
This runs all five steps in sequence: scrape Wodify → sync your client list → score leads → build an outreach plan → write and send personalized emails.
```bash
python pipeline.py
```
**Note:** This will actually send emails to your members. Make sure you've reviewed your top leads before running this in production.

---

### Check who engaged with emails recently
To see a quick report of members who opened or clicked an email in the last 2 days:
```bash
python pipeline.py --recent
```
You can change the number of days:
```bash
python pipeline.py --recent 7
```

---

### Run individual agents manually
Each agent can also be run on its own for testing or one-off tasks.

**Secretary** — Syncs your client list from the Wodify API and summarizes who is active, cold, or new:
```bash
python secretary.py
```

**Data Scientist** — Scores and ranks your leads by engagement:
```bash
python data_scientist.py
```

**Manager** — Builds a prioritized outreach plan from the lead scores:
```bash
python manager.py
```

**Marketer** — Writes and sends personalized follow-up emails:
```bash
python marketer.py
```

---

## If Your Session Expires
If you run the scraper and see `Session expired`, just run the setup step again:
```bash
python scraper.py --setup
```

---

## Where Your Data Is Stored

All of your gym's data stays on your own computer — nothing is uploaded anywhere.

| File | What it contains |
|---|---|
| `engagement_store.json` | Every member's opens, clicks, replies, and full interaction history. Grows over time as you run the pipeline. |
| `top_30.json` | Monthly snapshots of your top 30 most engaged members. A new entry is added each month so you can compare over time. |
| `top_30.csv` | The most recent top 30 exported as a spreadsheet. Regenerated each time you run `export_top30.py`. |
| `session.json` | Your saved Wodify login session. Never share this file. |
| `.env` | Your API keys and password. Never share this file. |

The engagement store scores each member: `(opens × 1) + (clicks × 3) + (replies × 5)`. This score is used by the AI agents to decide who to prioritize. The top 30 report uses a different formula that weights clicks more heavily: `(clicks × 4) + (opens × 1)`.

---

## Scheduling (Run the Pipeline Automatically Every Day)

### Windows Task Scheduler
1. Open **Task Scheduler** (search for it in the Start menu)
2. Click **Create Basic Task** on the right
3. Give it a name like "Wodify Marketing Pipeline" and click Next
4. Set the trigger to **Daily**, pick a time (e.g., 8:00 AM), click Next
5. Set the action to **Start a Program**
6. Program: `python`
7. Arguments: `pipeline.py`
8. Start in: the full path to this folder (e.g., `C:\Users\YourName\Marketing_Agent`)
9. Click Finish — it will run automatically every day at that time

### Mac / Linux (cron)
Run `crontab -e` and add this line (change the path to match where this folder is):
```
0 8 * * * cd /path/to/Marketing_Agent && python pipeline.py
```
This runs the pipeline every day at 8:00 AM.

---

## File Reference

| File | What it does |
|---|---|
| `pipeline.py` | Runs all five agents in sequence as one daily job |
| `scraper.py` | Logs into Wodify and pulls email open/click data for the last 30 days |
| `secretary.py` | Syncs your member list from the Wodify API and summarizes engagement |
| `data_scientist.py` | Scores and ranks members by how engaged they are |
| `manager.py` | Builds a prioritized outreach plan from the scores |
| `marketer.py` | Writes and sends personalized follow-up emails |
| `top_clients.py` | Ranks the top 30 members and saves a monthly snapshot to `top_30.json` |
| `export_top30.py` | Exports the latest top 30 to `top_30.csv` for Excel |
| `wodify_api.py` | Handles all calls to the Wodify REST API |
| `store.py` | Reads and writes `engagement_store.json` |
| `example.env` | Template for your credentials — copy this to `.env` and fill it in |
