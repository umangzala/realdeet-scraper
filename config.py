# config.py — Realdeet Twitter Scraper Configuration

# ── Search Queries ──────────────────────────────────────────────────────────
# Each query targets a different angle of hiring intent.
# -is:retweet excludes retweets. lang:en limits to English.

SEARCH_QUERIES = [
    # AI image / art requirements
    '("looking for" OR "need a" OR "hiring" OR "seeking") ("AI artist" OR "AI art" OR "AI image") -is:retweet lang:en',

    # AI video requirements
    '("looking for" OR "need a" OR "hiring" OR "seeking") ("AI video" OR "AI video creator" OR "AI-generated video") -is:retweet lang:en',

    # Video editor requirements (broader)
    '("looking for" OR "need a" OR "hiring") ("video editor" OR "video creator" OR "motion graphics") -is:retweet lang:en',

    # Tool-specific requests (Midjourney, Sora, Runway, DALL-E)
    '("need" OR "want" OR "looking for") ("Midjourney" OR "DALL-E" OR "Sora" OR "Runway ML") ("artist" OR "creator" OR "editor") -is:retweet lang:en',

    # Commission-style requests from brands
    '("commission" OR "commissions open") ("AI art" OR "AI artist" OR "AI image") -is:retweet lang:en',

    # Softer signals — recommendation-seeking
    '("anyone know" OR "can anyone recommend" OR "DM me if you") ("AI artist" OR "AI video" OR "video editor") -is:retweet lang:en',
]

# ── Scraper Settings ─────────────────────────────────────────────────────────
TWEETS_PER_QUERY = 20          # tweets to fetch per query per run
SCRAPE_INTERVAL_MINUTES = 30   # how often the scheduler runs
REQUEST_DELAY_SECONDS = 5      # delay between queries (rate limit safety)
COOKIES_FILE = "cookies.json"  # persisted Twitter session cookies
MIN_FOLLOWER_COUNT = 20        # ignore accounts below this (bots/noise)

# ── Proxy Settings ───────────────────────────────────────────────────────────
PROXIES_FILE = "proxies.txt"            # optional: one proxy URL per line
PROXY_MAX_FAILURES = 3                  # disable proxy after N consecutive failures
PROXY_HEALTH_CHECK_TIMEOUT = 10         # seconds to wait for health check

# ── Classification Thresholds ────────────────────────────────────────────────
HIGH_URGENCY_KEYWORDS = ["asap", "urgent", "today", "immediately", "deadline", "by friday", "this week"]

# ── Categories ───────────────────────────────────────────────────────────────
CATEGORIES = ["ai_image", "ai_video", "video_edit", "other"]
