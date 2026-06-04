# main.py — Realdeet Twitter Scraper: FastAPI app + scheduled job

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from classifier import classify_batch
from config import SEARCH_QUERIES, SCRAPE_INTERVAL_MINUTES, TWEETS_PER_QUERY
from database import get_client, tweet_exists, save_lead, get_leads
from twitter_client import TwitterClient

load_dotenv()

# ── Singletons ────────────────────────────────────────────────────────────────
twitter = TwitterClient()
supabase = get_client()
scheduler = AsyncIOScheduler()

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")  # optional


# ── Core Scrape Job ───────────────────────────────────────────────────────────

async def send_slack_alert(tweet: dict, classification: dict):
    """Send a Slack notification for high-urgency leads."""
    if not SLACK_WEBHOOK:
        return
    urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
        classification["urgency"], "⚪"
    )
    message = {
        "text": (
            f"{urgency_icon} *New {classification['category']} requirement on Realdeet*\n"
            f"*@{tweet['profile']['handle']}* ({tweet['profile']['followers']:,} followers)\n"
            f"_{classification['summary']}_\n"
            f"<{tweet['url']}|View tweet>"
        )
    }
    async with httpx.AsyncClient() as client:
        await client.post(SLACK_WEBHOOK, json=message, timeout=5)


async def run_scrape_job():
    """
    Full scrape pipeline:
    1. Fetch tweets from all queries
    2. Skip already-seen tweets
    3. Classify new tweets with GPT-4o-mini
    4. Save genuine requirements to Supabase
    5. Alert on high-urgency leads via Slack
    """
    started_at = datetime.now()
    print(f"\n{'='*60}")
    print(f"🚀 Scrape job started at {started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    try:
        # Step 1: Fetch tweets
        all_tweets = await twitter.search_all_queries(SEARCH_QUERIES, count=TWEETS_PER_QUERY)

        # Step 2: Deduplicate against DB
        new_tweets = []
        for tweet in all_tweets:
            if not await tweet_exists(supabase, tweet["tweet_id"]):
                new_tweets.append(tweet)
        print(f"\n🆕 {len(new_tweets)} new tweets (not yet in DB)")

        if not new_tweets:
            print("Nothing new. Job complete.")
            return

        # Step 3: Classify
        print(f"\n🧠 Classifying {len(new_tweets)} tweets...")
        qualified = await classify_batch(new_tweets)

        # Step 4: Save + alert
        saved = 0
        for tweet, classification in qualified:
            await save_lead(supabase, tweet, classification)
            saved += 1
            if classification["urgency"] == "high":
                await send_slack_alert(tweet, classification)

        elapsed = (datetime.now() - started_at).seconds
        print(f"\n✅ Job done in {elapsed}s — {saved} leads saved")

    except Exception as e:
        print(f"\n❌ Scrape job error: {e}")
        raise


# ── App Lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Login to Twitter on startup
    await twitter.login()

    # Schedule the scrape job
    scheduler.add_job(
        run_scrape_job,
        "interval",
        minutes=SCRAPE_INTERVAL_MINUTES,
        id="scrape_job",
        next_run_time=datetime.now(),  # run immediately on startup
    )
    scheduler.start()
    print(f"⏰ Scheduler running — scraping every {SCRAPE_INTERVAL_MINUTES} minutes")

    yield

    scheduler.shutdown()
    print("Scheduler stopped.")


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Realdeet Twitter Scraper",
    description="Collects AI artist / video creator requirements from Twitter",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def health():
    return {
        "status": "running",
        "scrape_interval_minutes": SCRAPE_INTERVAL_MINUTES,
        "queries": len(SEARCH_QUERIES),
    }


@app.post("/scrape/trigger")
async def trigger_scrape(background_tasks: BackgroundTasks):
    """Manually trigger a scrape job (runs in background)."""
    background_tasks.add_task(run_scrape_job)
    return {"message": "Scrape job triggered — check logs for progress"}


@app.get("/leads")
async def list_leads(
    limit: int = Query(50, le=200),
    category: str = Query(None, description="ai_image | ai_video | video_edit | other"),
    urgency: str = Query(None, description="high | medium | low"),
    status: str = Query(None, description="new | contacted | converted | ignored"),
):
    """List captured leads with optional filters."""
    leads = await get_leads(supabase, limit=limit, category=category, urgency=urgency, status=status)
    return {"count": len(leads), "leads": leads}


@app.patch("/leads/{post_id}/status")
async def update_lead_status(post_id: str, status: str, notes: str = None):
    """Update a lead's status (for BD team use)."""
    data = {"status": status}
    if notes:
        data["notes"] = notes
    supabase.table("posts").update(data).eq("id", post_id).execute()
    return {"message": f"Lead {post_id} updated to '{status}'"}
