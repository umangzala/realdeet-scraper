# twitter_client.py — Twitter session via twikit (internal API, no key needed)

from config import EXCLUDE_PATTERNS,MAX_TWEET_AGE_DAYS
import sys
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
import os
from typing import Optional
from twikit import Client
from config import COOKIES_FILE, MIN_FOLLOWER_COUNT, REQUEST_DELAY_SECONDS

# ProxyManager is optional — imported at runtime to avoid circular deps
try:
    from proxy_manager import ProxyManager
except ImportError:
    ProxyManager = None


class TwitterClient:
    def __init__(self, proxy_manager=None):
        self.proxy_manager = proxy_manager
        self._current_proxy = proxy_manager.get_proxy() if proxy_manager else None
        self.client = Client("en-US", proxy=self._current_proxy)
        self._logged_in = False
        self._patch_client_transaction()

        if self._current_proxy:
            from proxy_manager import ProxyManager
            print(f"🌐 TwitterClient using proxy: {ProxyManager._mask(self._current_proxy)}")
        else:
            print("🌐 TwitterClient using direct connection (no proxy)")

    def _patch_client_transaction(self):
        """
        Monkey-patch twikit's ClientTransaction class and User class to fix
        the regex patterns and parsing logic for the March 2026 X.com update
        and avoid KeyErrors on missing fields.
        """
        import re
        from twikit.x_client_transaction import ClientTransaction
        from twikit.user import User

        # 1. Patch ClientTransaction regexes and get_indices method
        ON_DEMAND_FILE_REGEX = re.compile(
            r""",(\d+):["']ondemand\.s["']""", flags=(re.VERBOSE | re.MULTILINE))
        ON_DEMAND_HASH_PATTERN = r',{}:\"([0-9a-f]+)\"'
        INDICES_REGEX = re.compile(
            r"""(\(\w{1,2}\[(\d{1,2})\],\s*16\))+""", flags=(re.VERBOSE | re.MULTILINE))

        async def get_indices(self_tx, home_page_response, session, headers):
            key_byte_indices = []
            response = self_tx.validate_response(
                home_page_response) or self_tx.home_page_response
            response_str = str(response)

            on_demand_file = ON_DEMAND_FILE_REGEX.search(response_str)
            if on_demand_file:
                on_demand_file_index = on_demand_file.group(1)
                hash_regex = re.compile(ON_DEMAND_HASH_PATTERN.format(on_demand_file_index))
                hash_match = hash_regex.search(response_str)
                if hash_match:
                    filename = hash_match.group(1)
                    on_demand_file_url = f"https://abs.twimg.com/responsive-web/client-web/ondemand.s.{filename}a.js"
                    on_demand_file_response = await session.request(method="GET", url=on_demand_file_url, headers=headers)
                    key_byte_indices_match = INDICES_REGEX.finditer(
                        str(on_demand_file_response.text))
                    for item in key_byte_indices_match:
                        key_byte_indices.append(item.group(2))

            if not key_byte_indices:
                raise Exception("Couldn't get KEY_BYTE indices")
            key_byte_indices = list(map(int, key_byte_indices))
            return key_byte_indices[0], key_byte_indices[1:]

        ClientTransaction.get_indices = get_indices

        # 2. Patch User.__init__ to handle missing legacy fields gracefully
        def patched_user_init(self_user, client, data):
            self_user._client = client
            legacy = data.get('legacy', {}) or {}

            self_user.id = data.get('rest_id')
            self_user.created_at = legacy.get('created_at', '')
            self_user.name = legacy.get('name', '')
            self_user.screen_name = legacy.get('screen_name', '')
            self_user.profile_image_url = legacy.get('profile_image_url_https', '')
            self_user.profile_banner_url = legacy.get('profile_banner_url')
            self_user.url = legacy.get('url')
            self_user.location = legacy.get('location', '')
            self_user.description = legacy.get('description', '')
            
            entities = legacy.get('entities', {}) or {}
            description_entities = entities.get('description', {}) or {}
            self_user.description_urls = description_entities.get('urls', [])
            
            url_entities = entities.get('url', {}) or {}
            self_user.urls = url_entities.get('urls', [])
            
            self_user.pinned_tweet_ids = legacy.get('pinned_tweet_ids_str', [])
            self_user.is_blue_verified = data.get('is_blue_verified', False)
            self_user.verified = legacy.get('verified', False)
            self_user.possibly_sensitive = legacy.get('possibly_sensitive', False)
            self_user.can_dm = legacy.get('can_dm', False)
            self_user.can_media_tag = legacy.get('can_media_tag', False)
            self_user.want_retweets = legacy.get('want_retweets', False)
            self_user.default_profile = legacy.get('default_profile', False)
            self_user.default_profile_image = legacy.get('default_profile_image', False)
            self_user.has_custom_timelines = legacy.get('has_custom_timelines', False)
            
            self_user.followers_count = legacy.get('followers_count', 0)
            self_user.fast_followers_count = legacy.get('fast_followers_count', 0)
            self_user.normal_followers_count = legacy.get('normal_followers_count', 0)
            self_user.following_count = legacy.get('friends_count', 0)
            self_user.favourites_count = legacy.get('favourites_count', 0)
            self_user.listed_count = legacy.get('listed_count', 0)
            self_user.media_count = legacy.get('media_count', 0)
            self_user.statuses_count = legacy.get('statuses_count', 0)
            self_user.is_translator = legacy.get('is_translator', False)
            self_user.translator_type = legacy.get('translator_type', '')
            self_user.withheld_in_countries = legacy.get('withheld_in_countries', [])
            self_user.protected = legacy.get('protected', False)

        User.__init__ = patched_user_init



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

            # Filter out tweets older than 1 day
            from datetime import datetime, timedelta, timezone
            tweet_dt = tweet.created_at_datetime
            compare_dt = datetime.now(timezone.utc) if tweet_dt.tzinfo else datetime.now()
            if tweet_dt < compare_dt - timedelta(days=MAX_TWEET_AGE_DAYS):
                return None

            # Skip if the account bio looks like an artist self-promoting
            # (we want buyers, not sellers)
            bio = getattr(user, "description", "") or ""
            artist_self_promo_signals = EXCLUDE_PATTERNS
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
        On proxy failure, retries with a different proxy (up to 2 retries).
        """
        if not self._logged_in:
            await self.login()

        max_retries = 2 if self.proxy_manager else 0
        last_error = None

        for attempt in range(1 + max_retries):
            try:
                print(f"  🔍 Searching: {query[:80]}...")
                tweets = await self.client.search_tweet(query, product="Latest", count=count)

                # Mark proxy as healthy on success
                if self.proxy_manager and self._current_proxy:
                    self.proxy_manager.mark_success(self._current_proxy)

                results = []
                for tweet in tweets:
                    extracted = self._extract_tweet(tweet)
                    if extracted:
                        results.append(extracted)

                print(f"  📥 Got {len(results)} quality tweets (filtered from {len(tweets)} raw)")
                return results

            except Exception as e:
                last_error = e

                # Only blame the proxy for connection-related errors
                is_proxy_error = isinstance(e, (
                    ConnectionError, TimeoutError, OSError
                ))
                # Also check for httpx-specific errors
                try:
                    import httpx
                    is_proxy_error = is_proxy_error or isinstance(e, (
                        httpx.ConnectError, httpx.ProxyError,
                        httpx.ConnectTimeout, httpx.ReadTimeout,
                    ))
                except ImportError:
                    pass

                # Also treat twikit Forbidden/NotFound (404/403) as proxy errors during search
                try:
                    from twikit.errors import Forbidden, NotFound
                    is_proxy_error = is_proxy_error or isinstance(e, (Forbidden, NotFound))
                except ImportError:
                    pass

                if is_proxy_error and self.proxy_manager and (self._current_proxy or attempt == 0):
                    if self._current_proxy:
                        self.proxy_manager.mark_failed(self._current_proxy)

                    if attempt < max_retries:
                        new_proxy = self.proxy_manager.get_proxy()
                        if new_proxy and new_proxy != self._current_proxy:
                            print(f"  🔄 Retrying with a different proxy (attempt {attempt + 2})...")
                            self._current_proxy = new_proxy
                            self.client = Client("en-US", proxy=self._current_proxy)
                            self._logged_in = False
                            await self.login()
                            continue
                        elif self._current_proxy is not None:
                            # Fallback to direct connection if the only proxy failed
                            print(f"  🔄 Retrying with direct connection (no proxy) (attempt {attempt + 2})...")
                            self._current_proxy = None
                            self.client = Client("en-US", proxy=None)
                            self._logged_in = False
                            await self.login()
                            continue
                        else:
                            print(f"  ❌ No alternative proxy or direct connection available")
                            raise
                    else:
                        raise
                else:
                    # Non-proxy error (twikit internal bug, etc) — don't retry
                    raise

        raise last_error

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
