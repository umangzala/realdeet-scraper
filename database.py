# database.py — Supabase client for Realdeet scraper

import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(url, key)


async def tweet_exists(supabase: Client, tweet_id: str) -> bool:
    result = supabase.table("posts").select("id").eq("tweet_id", tweet_id).execute()
    return len(result.data) > 0


async def upsert_profile(supabase: Client, profile: dict) -> str:
    """Upsert a Twitter profile, return the profile row id."""
    data = {
        "twitter_id": profile["twitter_id"],
        "handle": profile["handle"],
        "display_name": profile["display_name"],
        "bio": profile.get("bio", ""),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "tweet_count": profile.get("tweet_count", 0),
        "account_created_at": profile.get("account_created_at"),
        "website": profile.get("website"),
        "verified": profile.get("verified", False),
        "profile_image_url": profile.get("profile_image_url"),
    }
    result = (
        supabase.table("profiles")
        .upsert(data, on_conflict="twitter_id")
        .execute()
    )
    return result.data[0]["id"]


async def save_lead(supabase: Client, tweet: dict, classification: dict) -> None:
    """Save a classified tweet as a lead in the DB."""
    # 1. Upsert profile first
    profile_id = await upsert_profile(supabase, tweet["profile"])

    # 2. Insert post
    post_data = {
        "tweet_id": tweet["tweet_id"],
        "profile_id": profile_id,
        "text": tweet["text"],
        "posted_at": tweet["created_at"],
        "url": tweet["url"],
        "likes": tweet.get("likes", 0),
        "retweets": tweet.get("retweets", 0),
        "replies": tweet.get("replies", 0),
        "category": classification["category"],
        "urgency": classification["urgency"],
        "has_budget_signal": classification["has_budget_signal"],
        "is_brand_or_business": classification["is_brand_or_business"],
        "summary": classification["summary"],
        "status": "new",
    }
    supabase.table("posts").insert(post_data).execute()
    print(f"  💾 Saved lead: @{tweet['profile']['handle']} — {classification['summary'][:60]}")


async def get_leads(
    supabase: Client,
    limit: int = 50,
    category: str = None,
    urgency: str = None,
    status: str = None,
) -> list[dict]:
    """Fetch leads with optional filters."""
    query = (
        supabase.table("posts")
        .select("*, profiles(*)")
        .order("posted_at", desc=True)
        .limit(limit)
    )
    if category:
        query = query.eq("category", category)
    if urgency:
        query = query.eq("urgency", urgency)
    if status:
        query = query.eq("status", status)

    result = query.execute()
    return result.data
