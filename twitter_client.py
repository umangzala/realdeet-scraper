# twitter_client.py — Twitter session via twikit (internal API, no key needed)

import asyncio
import os
from typing import Optional
from twikit import Client
from config import COOKIES_FILE, MIN_FOLLOWER_COUNT, REQUEST_DELAY_SECONDS


class TwitterClient:
    def __init__(self):
        self.client = Client("en-US")
        self._logged_in = False

    async def login(self):
        """
        Login with cookie persistence.
        First run: authenticates and saves cookies.
        Subsequent runs: loads saved cookies (skips login entirely).
        """
        if os.path.exists(COOKIES_FILE):
            print("🍪 Loading saved session cookies...")
            self.client.load_cookies(COOKIES_FILE)
            self._logged_in = True
            print("✅ Session restored from cookies")
            return

        handle = os.getenv("TWITTER_HANDLE")
        email = os.getenv("TWITTER_EMAIL")
        password = os.getenv("TWITTER_PASSWORD")

        if not all([handle, email, password]):
            raise ValueError(
                "TWITTER_HANDLE, TWITTER_EMAIL, and TWITTER_PASSWORD must be set in .env"
            )

        print(f"🔐 Logging in as @{handle}...")
        await self.client.login(
            auth_info_1=handle,
            auth_info_2=email,
            password=password,
        )
        self.client.save_cookies(COOKIES_FILE)
        self._logged_in = True
        print("✅ Login successful, cookies saved")

    def _extract_tweet(self, tweet) -> Optional[dict]:
        """
        Extract a clean dict from a twikit Tweet object.
        Returns None if the tweet doesn't pass basic quality filters.
        """
        try:
            user = tweet.user

            # Filter out low-follower accounts (likely bots)
            followers = getattr(user, "followers_count", 0) or 0
            if followers < MIN_FOLLOWER_COUNT:
                return None

            # Skip if the account bio looks like an artist self-promoting
            # (we want buyers, not sellers)
            bio = getattr(user, "description", "") or ""
            artist_self_promo_signals = [
                "commissions open",
                "available for commissions",
                "hire me",
                "my portfolio",
                "digital artist",
                "ai artist",
            ]
            if any(signal in bio.lower() for signal in artist_self_promo_signals):
                return None

            return {
                "tweet_id": str(tweet.id),
                "text": tweet.text,
                "created_at": str(tweet.created_at),
                "url": f"https://twitter.com/{user.screen_name}/status/{tweet.id}",
                "likes": getattr(tweet, "favorite_count", 0) or 0,
                "retweets": getattr(tweet, "retweet_count", 0) or 0,
                "replies": getattr(tweet, "reply_count", 0) or 0,
                "lang": getattr(tweet, "lang", "en"),
                "profile": {
                    "twitter_id": str(user.id),
                    "handle": user.screen_name,
                    "display_name": user.name,
                    "bio": bio,
                    "followers": followers,
                    "following": getattr(user, "friends_count", 0) or 0,
                    "tweet_count": getattr(user, "statuses_count", 0) or 0,
                    "account_created_at": str(getattr(user, "created_at", "")),
                    "website": getattr(user, "url", None),
                    "verified": getattr(user, "verified", False),
                    "profile_image_url": getattr(user, "profile_image_url", None),
                },
            }
        except Exception as e:
            print(f"  ⚠️  Error extracting tweet {getattr(tweet, 'id', '?')}: {e}")
            return None

    async def search(self, query: str, count: int = 20) -> list[dict]:
        """
        Search Twitter for tweets matching a query.
        Returns a list of clean tweet dicts that pass quality filters.
        """
        if not self._logged_in:
            await self.login()

        print(f"  🔍 Searching: {query[:80]}...")
        tweets = await self.client.search_tweet(query, product="Latest", count=count)

        results = []
        for tweet in tweets:
            extracted = self._extract_tweet(tweet)
            if extracted:
                results.append(extracted)

        print(f"  📥 Got {len(results)} quality tweets (filtered from {len(tweets)} raw)")
        return results

    async def search_all_queries(self, queries: list[str], count: int = 20) -> list[dict]:
        """
        Run all queries with a delay between each to respect rate limits.
        Deduplicates by tweet_id across queries.
        """
        seen_ids = set()
        all_results = []

        for i, query in enumerate(queries):
            try:
                results = await self.search(query, count)
                for tweet in results:
                    if tweet["tweet_id"] not in seen_ids:
                        seen_ids.add(tweet["tweet_id"])
                        all_results.append(tweet)
            except Exception as e:
                print(f"  ❌ Query {i+1} failed: {e}")

            # Rate limit safety: wait between queries
            if i < len(queries) - 1:
                await asyncio.sleep(REQUEST_DELAY_SECONDS)

        print(f"\n📊 Total unique tweets across all queries: {len(all_results)}")
        return all_results
