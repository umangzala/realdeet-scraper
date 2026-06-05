# classifier.py — GPT-4o-mini intent classifier for Realdeet

import os
import json
from openai import AsyncOpenAI

_client = None
_no_key_warned = False

def _get_client():
    """Lazy-init the OpenAI client. Returns None if no API key is configured."""
    global _client, _no_key_warned
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-..."):
        if not _no_key_warned:
            print("⚠️  OPENAI_API_KEY not set — classifier will skip (all tweets treated as non-requirements)")
            _no_key_warned = True
        return None
    if _client is None:
        _client = AsyncOpenAI(api_key=api_key)
    return _client

SYSTEM_PROMPT = """You are a classifier for Realdeet, a marketplace platform connecting brands with AI artists, AI image generators, AI video creators, and video editors.

Your job: determine if a tweet author is expressing intent to HIRE or COMMISSION creative talent.

Rules:
- Return ONLY valid JSON, no extra text
- is_requirement = true only if the author wants to hire/commission someone (not self-promo, not commentary)
- Ignore tweets where the author IS the artist advertising their own services
- Consider urgency signals: words like "asap", "urgent", "deadline", "this week"
- Consider budget signals: any mention of price, rate, pay, budget, $, USD, per hour
"""

USER_PROMPT = """Classify this tweet:

Tweet: {tweet_text}
Author bio: {bio}
Likes: {likes} | Retweets: {retweets}

Return JSON with exactly these fields:
{{
  "is_requirement": <bool>,
  "category": "<ai_image|ai_video|video_edit|other>",
  "urgency": "<high|medium|low>",
  "has_budget_signal": <bool>,
  "is_brand_or_business": <bool>,
  "summary": "<one-line summary of what they need, or empty string if not a requirement>"
}}"""


async def classify_tweet(tweet: dict) -> dict:
    """
    Classify a single tweet using GPT-4o-mini.
    Returns a classification dict. Falls back to safe defaults on error.
    """
    try:
        openai_client = _get_client()
        if openai_client is None:
            # Fallback to local heuristic classifier when API key is missing
            text = tweet["text"].lower()
            is_req = any(kw in text for kw in ["looking for", "need a", "hiring", "seeking", "commission", "want to buy", "looking to buy"])
            
            if is_req:
                category = "video_edit" if "edit" in text else ("ai_video" if "video" in text else ("ai_image" if any(x in text for x in ["art", "image", "draw", "illustrat", "artist"]) else "other"))
                urgency = "high" if any(kw in text for kw in ["asap", "urgent", "today", "immediately", "deadline", "fast"]) else "medium"
                has_budget = any(kw in text for kw in ["budget", "$", "usd", "pay", "paying", "rate"])
                
                # Create a clean summary
                summary = tweet["text"].replace("\n", " ")[:80]
                if len(tweet["text"]) > 80:
                    summary += "..."
                
                return {
                    "is_requirement": True,
                    "category": category,
                    "urgency": urgency,
                    "has_budget_signal": has_budget,
                    "is_brand_or_business": False,
                    "summary": f"[Heuristic] {summary}",
                }
            return {
                "is_requirement": False,
                "category": "other",
                "urgency": "low",
                "has_budget_signal": False,
                "is_brand_or_business": False,
                "summary": "",
            }

        prompt = USER_PROMPT.format(
            tweet_text=tweet["text"],
            bio=tweet["profile"].get("bio", ""),
            likes=tweet.get("likes", 0),
            retweets=tweet.get("retweets", 0),
        )

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=200,
        )

        result = json.loads(response.choices[0].message.content)

        # Ensure all expected keys exist (defensive)
        return {
            "is_requirement": bool(result.get("is_requirement", False)),
            "category": result.get("category", "other"),
            "urgency": result.get("urgency", "low"),
            "has_budget_signal": bool(result.get("has_budget_signal", False)),
            "is_brand_or_business": bool(result.get("is_brand_or_business", False)),
            "summary": result.get("summary", ""),
        }

    except Exception as e:
        print(f"  ⚠️  Classifier error for tweet {tweet.get('tweet_id')}: {e}")
        # Return safe default — will be treated as not a requirement
        return {
            "is_requirement": False,
            "category": "other",
            "urgency": "low",
            "has_budget_signal": False,
            "is_brand_or_business": False,
            "summary": "",
        }


async def classify_batch(tweets: list[dict]) -> list[tuple[dict, dict]]:
    """
    Classify a list of tweets. Returns list of (tweet, classification) pairs
    where is_requirement is True.
    """
    import asyncio

    results = []
    tasks = [classify_tweet(t) for t in tweets]
    classifications = await asyncio.gather(*tasks)

    for tweet, classification in zip(tweets, classifications):
        if classification["is_requirement"]:
            results.append((tweet, classification))
            urgency_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                classification["urgency"], "⚪"
            )
            print(
                f"  {urgency_icon} [{classification['category']}] {tweet['profile']['handle']}: "
                f"{classification['summary'][:80]}"
            )

    print(f"\n✅ {len(results)}/{len(tweets)} tweets classified as genuine requirements")
    return results
