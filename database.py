# # database.py — Supabase client for Realdeet scraper

# import os
# from supabase import create_client, Client


# def get_client() -> Client:
#     url = os.getenv("SUPABASE_URL")
#     key = os.getenv("SUPABASE_SERVICE_KEY")
#     if not url or not key:
#         raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
#     return create_client(url, key)


# async def tweet_exists(supabase: Client, tweet_id: str) -> bool:
#     result = supabase.table("posts").select("id").eq("tweet_id", tweet_id).execute()
#     return len(result.data) > 0


# async def upsert_profile(supabase: Client, profile: dict) -> str:
#     """Upsert a Twitter profile, return the profile row id."""
#     data = {
#         "twitter_id": profile["twitter_id"],
#         "handle": profile["handle"],
#         "display_name": profile["display_name"],
#         "bio": profile.get("bio", ""),
#         "followers": profile.get("followers", 0),
#         "following": profile.get("following", 0),
#         "tweet_count": profile.get("tweet_count", 0),
#         "account_created_at": profile.get("account_created_at"),
#         "website": profile.get("website"),
#         "verified": profile.get("verified", False),
#         "profile_image_url": profile.get("profile_image_url"),
#     }
#     result = (
#         supabase.table("profiles")
#         .upsert(data, on_conflict="twitter_id")
#         .execute()
#     )
#     return result.data[0]["id"]


# async def save_lead(supabase: Client, tweet: dict, classification: dict) -> None:
#     """Save a classified tweet as a lead in the DB."""
#     # 1. Upsert profile first
#     profile_id = await upsert_profile(supabase, tweet["profile"])

#     # 2. Insert post
#     post_data = {
#         "tweet_id": tweet["tweet_id"],
#         "profile_id": profile_id,
#         "text": tweet["text"],
#         "posted_at": tweet["created_at"],
#         "url": tweet["url"],
#         "likes": tweet.get("likes", 0),
#         "retweets": tweet.get("retweets", 0),
#         "replies": tweet.get("replies", 0),
#         "category": classification["category"],
#         "urgency": classification["urgency"],
#         "has_budget_signal": classification["has_budget_signal"],
#         "is_brand_or_business": classification["is_brand_or_business"],
#         "summary": classification["summary"],
#         "status": "new",
#     }
#     supabase.table("posts").insert(post_data).execute()
#     print(f"  💾 Saved lead: @{tweet['profile']['handle']} — {classification['summary'][:60]}")


# async def get_leads(
#     supabase: Client,
#     limit: int = 50,
#     category: str = None,
#     urgency: str = None,
#     status: str = None,
# ) -> list[dict]:
#     """Fetch leads with optional filters."""
#     query = (
#         supabase.table("posts")
#         .select("*, profiles(*)")
#         .order("posted_at", desc=True)
#         .limit(limit)
#     )
#     if category:
#         query = query.eq("category", category)
#     if urgency:
#         query = query.eq("urgency", urgency)
#     if status:
#         query = query.eq("status", status)

#     result = query.execute()
#     return result.data

# database.py — Local CSV file storage / Supabase database for Realdeet scraper
# ==================================================================================================================================================================================================================================================================================================================================================
import os
import csv
from typing import Optional, Any

# --- SUPABASE IMPORTS (Uncomment to switch back to Supabase) ---
# from supabase import create_client, Client
# --------------------------------------------------------------


LEADS_FILE = "leads.csv"

# Global cache of seen tweet IDs to make deduplication check fast
_seen_ids_cache = None


def get_client() -> str:
    """Returns the filepath of the CSV file instead of a Supabase client."""
    return LEADS_FILE


def reset_db_cache() -> None:
    """Clear the local cache of seen IDs to force reloading from CSV."""
    global _seen_ids_cache
    _seen_ids_cache = None


async def tweet_exists(csv_path: str, tweet_id: str) -> bool:
    """Check if a tweet ID already exists in the CSV file."""
    global _seen_ids_cache
    if _seen_ids_cache is None:
        _seen_ids_cache = set()
        if os.path.exists(csv_path):
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        tid = row.get("tweet_id")
                        if tid:
                            _seen_ids_cache.add(tid)
            except Exception as e:
                print(f"⚠️  Error reading CSV file for deduplication: {e}")
    
    return tweet_id in _seen_ids_cache


async def save_lead(csv_path: str, tweet: dict, classification: dict) -> None:
    """Save a classified tweet as a lead in the CSV file."""
    global _seen_ids_cache
    
    file_exists = os.path.exists(csv_path)
    
    headers = [
        "tweet_id", "posted_at", "handle", "display_name", "text", "url", 
        "category", "urgency", "has_budget_signal", "is_brand_or_business", 
        "summary", "followers", "likes", "retweets", "replies", "status", "notes"
    ]
    
    row = {
        "tweet_id": tweet["tweet_id"],
        "posted_at": tweet["created_at"],
        "handle": tweet["profile"]["handle"],
        "display_name": tweet["profile"]["display_name"],
        "text": tweet["text"],
        "url": tweet["url"],
        "category": classification["category"],
        "urgency": classification["urgency"],
        "has_budget_signal": str(classification["has_budget_signal"]),
        "is_brand_or_business": str(classification["is_brand_or_business"]),
        "summary": classification["summary"],
        "followers": str(tweet["profile"].get("followers", 0)),
        "likes": str(tweet.get("likes", 0)),
        "retweets": str(tweet.get("retweets", 0)),
        "replies": str(tweet.get("replies", 0)),
        "status": "new",
        "notes": ""
    }
    
    try:
        # Append row to CSV
        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
            
        # Add to local cache so we don't pick it up again this run
        if _seen_ids_cache is not None:
            _seen_ids_cache.add(tweet["tweet_id"])
            
        print(f"  💾 Saved lead to CSV: @{tweet['profile']['handle']} — {classification['summary'][:60]}")
    except Exception as e:
        print(f"  ❌ Error saving lead to CSV: {e}")
        raise


async def get_leads(
    csv_path: str,
    limit: int = 50,
    category: str = None,
    urgency: str = None,
    status: str = None,
) -> list[dict]:
    """Fetch leads from the CSV file with optional filters."""
    leads = []
    if not os.path.exists(csv_path):
        return leads
        
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Apply filters
                if category and row.get("category") != category:
                    continue
                if urgency and row.get("urgency") != urgency:
                    continue
                if status and row.get("status") != status:
                    continue
                    
                # Reconstruct structured dict matching the original Supabase schema
                # for compatibility with the FastAPI response
                lead = {
                    "id": row.get("tweet_id"),  # Using tweet_id as the primary key ID
                    "tweet_id": row.get("tweet_id"),
                    "text": row.get("text"),
                    "posted_at": row.get("posted_at"),
                    "url": row.get("url"),
                    "likes": int(row.get("likes", 0) or 0),
                    "retweets": int(row.get("retweets", 0) or 0),
                    "replies": int(row.get("replies", 0) or 0),
                    "category": row.get("category"),
                    "urgency": row.get("urgency"),
                    "has_budget_signal": row.get("has_budget_signal") == "True",
                    "is_brand_or_business": row.get("is_brand_or_business") == "True",
                    "summary": row.get("summary"),
                    "status": row.get("status", "new"),
                    "notes": row.get("notes", ""),
                    "profiles": {
                        "handle": row.get("handle"),
                        "display_name": row.get("display_name"),
                        "followers": int(row.get("followers", 0) or 0)
                    }
                }
                leads.append(lead)
    except Exception as e:
        print(f"⚠️  Error reading leads from CSV: {e}")
        
    # Reverse to show latest first (newest posted_at)
    leads.reverse()
    return leads[:limit]


async def update_lead_status(csv_path: str, tweet_id: str, status: str, notes: str = None) -> bool:
    """Updates a lead's status and notes in the CSV file."""
    if not os.path.exists(csv_path):
        return False
        
    rows = []
    updated = False
    headers = [
        "tweet_id", "posted_at", "handle", "display_name", "text", "url", 
        "category", "urgency", "has_budget_signal", "is_brand_or_business", 
        "summary", "followers", "likes", "retweets", "replies", "status", "notes"
    ]
    
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("tweet_id") == tweet_id:
                    row["status"] = status
                    if notes is not None:
                        row["notes"] = notes
                    updated = True
                rows.append(row)
                
        if updated:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            return True
    except Exception as e:
        print(f"⚠️  Error updating lead status in CSV: {e}")
        
    return False


# ==============================================================================
# ── SUPABASE DATABASE IMPLEMENTATION (COMMENTED OUT FOR FUTURE USE) ───────────
# ==============================================================================
#
# def get_client() -> Client:
#     """Returns a Supabase client."""
#     url = os.getenv("SUPABASE_URL")
#     key = os.getenv("SUPABASE_SERVICE_KEY")
#     if not url or not key:
#         raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
#     return create_client(url, key)
#
#
# async def tweet_exists(supabase: Client, tweet_id: str) -> bool:
#     """Check if a tweet ID already exists in the Supabase table."""
#     result = supabase.table("posts").select("id").eq("tweet_id", tweet_id).execute()
#     return len(result.data) > 0
#
#
# async def upsert_profile(supabase: Client, profile: dict) -> str:
#     """Upsert a Twitter profile, return the profile row id."""
#     data = {
#         "twitter_id": profile["twitter_id"],
#         "handle": profile["handle"],
#         "display_name": profile["display_name"],
#         "bio": profile.get("bio", ""),
#         "followers": profile.get("followers", 0),
#         "following": profile.get("following", 0),
#         "tweet_count": profile.get("tweet_count", 0),
#         "account_created_at": profile.get("account_created_at"),
#         "website": profile.get("website"),
#         "verified": profile.get("verified", False),
#         "profile_image_url": profile.get("profile_image_url"),
#     }
#     result = (
#         supabase.table("profiles")
#         .upsert(data, on_conflict="twitter_id")
#         .execute()
#     )
#     return result.data[0]["id"]
#
#
# async def save_lead(supabase: Client, tweet: dict, classification: dict) -> None:
#     """Save a classified tweet as a lead in the Supabase database."""
#     profile_id = await upsert_profile(supabase, tweet["profile"])
#     post_data = {
#         "tweet_id": tweet["tweet_id"],
#         "profile_id": profile_id,
#         "text": tweet["text"],
#         "posted_at": tweet["created_at"],
#         "url": tweet["url"],
#         "likes": tweet.get("likes", 0),
#         "retweets": tweet.get("retweets", 0),
#         "replies": tweet.get("replies", 0),
#         "category": classification["category"],
#         "urgency": classification["urgency"],
#         "has_budget_signal": classification["has_budget_signal"],
#         "is_brand_or_business": classification["is_brand_or_business"],
#         "summary": classification["summary"],
#         "status": "new",
#     }
#     supabase.table("posts").insert(post_data).execute()
#     print(f"  💾 Saved lead to Supabase: @{tweet['profile']['handle']} — {classification['summary'][:60]}")
#
#
# async def get_leads(
#     supabase: Client,
#     limit: int = 50,
#     category: str = None,
#     urgency: str = None,
#     status: str = None,
# ) -> list[dict]:
#     """Fetch leads from Supabase with optional filters."""
#     query = (
#         supabase.table("posts")
#         .select("*, profiles(*)")
#         .order("posted_at", desc=True)
#         .limit(limit)
#     )
#     if category:
#         query = query.eq("category", category)
#     if urgency:
#         query = query.eq("urgency", urgency)
#     if status:
#         query = query.eq("status", status)
#     result = query.execute()
#     return result.data
#
#
# async def update_lead_status(supabase: Client, tweet_id: str, status: str, notes: str = None) -> bool:
#     """Update a lead's status and notes in the Supabase table."""
#     data = {"status": status}
#     if notes is not None:
#         data["notes"] = notes
#     # We use tweet_id here to match the CSV implementation signature
#     result = supabase.table("posts").update(data).eq("tweet_id", tweet_id).execute()
#     return len(result.data) > 0


