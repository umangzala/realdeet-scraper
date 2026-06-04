# Realdeet Twitter Scraper — Setup Guide

Collects AI artist / video creator hiring requirements from Twitter.
Stack: twikit (Twitter internal API) + GPT-4o-mini + Supabase + FastAPI

---

## Step 1: Prerequisites

- Python 3.11+
- A Supabase project (free tier works)
- An OpenAI API key
- A dedicated Twitter account for scraping (don't use your personal one)

---

## Step 2: Install dependencies

```bash
cd realdeet-scraper
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 3: Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your values
```

---

## Step 4: Set up Supabase tables

1. Go to your Supabase project → SQL Editor
2. Paste the contents of `schema.sql` and run it
3. Tables `profiles` and `posts` will be created

---

## Step 5: Run the scraper

```bash
uvicorn main:app --reload --port 8000
```

On first run it will:
1. Log in to Twitter and save cookies to `cookies.json`
2. Immediately trigger a scrape job
3. Schedule a scrape every 30 minutes

Watch the terminal — you'll see tweets being fetched, classified, and saved.

---

## Step 6: View leads

Open your browser: http://localhost:8000/leads

Filter by category or urgency:
```
GET /leads?category=ai_video&urgency=high
GET /leads?status=new&limit=20
```

Manually trigger a scrape without waiting:
```
POST /leads/trigger
```

---

## Deployment (optional)

To run 24/7 on a cheap VPS ($6/month DigitalOcean):

```bash
# Install screen or use systemd
screen -S realdeet-scraper
uvicorn main:app --host 0.0.0.0 --port 8000
# Ctrl+A, D to detach
```

---

## Troubleshooting

**Login fails:** Twitter sometimes requires email verification on first login.
Check your Twitter email inbox and complete verification, then retry.

**Cookies expire:** Delete `cookies.json` and restart — it will re-login.

**twikit attribute errors:** twikit is actively maintained and attribute names
can change between versions. Check https://github.com/d60/twikit for the latest
Tweet and User object attributes if you see AttributeError.

**Rate limit errors:** Increase `REQUEST_DELAY_SECONDS` in config.py (try 10–15s).
