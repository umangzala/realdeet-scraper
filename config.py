# config.py — Realdeet Twitter Scraper Configuration

# ── Search Queries ──────────────────────────────────────────────────────────
# Each query targets a different angle of hiring intent.
# -is:retweet excludes retweets. lang:en limits to English.

# SEARCH_QUERIES = [
#     # AI image / art requirements
#     '("looking for" OR "need a" OR "hiring" OR "seeking") ("AI artist" OR "AI art" OR "AI image") -is:retweet lang:en',

#     # AI video requirements
#     '("looking for" OR "need a" OR "hiring" OR "seeking") ("AI video" OR "AI video creator" OR "AI-generated video") -is:retweet lang:en',

#     # Video editor requirements (broader)
#     '("looking for" OR "need a" OR "hiring") ("video editor" OR "video creator" OR "motion graphics") -is:retweet lang:en',

#     # Tool-specific requests (Midjourney, Sora, Runway, DALL-E)
#     '("need" OR "want" OR "looking for") ("Midjourney" OR "DALL-E" OR "Sora" OR "Runway ML") ("artist" OR "creator" OR "editor") -is:retweet lang:en',

#     # Commission-style requests from brands
#     '("commission" OR "commissions open") ("AI art" OR "AI artist" OR "AI image") -is:retweet lang:en',

#     # Softer signals — recommendation-seeking
#     '("anyone know" OR "can anyone recommend" OR "DM me if you") ("AI artist" OR "AI video" OR "video editor") -is:retweet lang:en',
# ]

SEARCH_QUERIES = [

    # ── TIER 1: Strongest signals — explicit hiring from a company/team ──────

    # "We're hiring" with role context
    '("we\'re hiring" OR "we are hiring" OR "now hiring") ("video editor" OR "AI artist" OR "motion designer" OR "content creator") -is:retweet lang:en',

    # "Join our team" framing — almost always employer-side
    '("join our team" OR "join us" OR "open role" OR "open position") ("video editor" OR "AI artist" OR "creative" OR "designer") -is:retweet lang:en',

    # Job post with compensation signals
    '("paid role" OR "paid position" OR "full-time" OR "part-time" OR "contract role") ("video editor" OR "AI video" OR "AI artist" OR "motion graphics") -is:retweet lang:en',

    # Budget-explicit outsourcing from brands
    '("budget" OR "rate" OR "per video" OR "per month" OR "monthly retainer") ("video editor" OR "AI artist" OR "content creator") ("hiring" OR "looking for" OR "need") -is:retweet lang:en',


    # ── TIER 2: Strong signals — seeking with business context ───────────────

    # "Our brand/startup/agency needs"
    '("our brand" OR "our startup" OR "our agency" OR "our company" OR "our team") ("needs" OR "looking for" OR "hiring") ("video editor" OR "AI creator" OR "designer") -is:retweet lang:en',

    # DM-to-apply framing (employer asking candidates to DM them, not freelancers)
    '("DM us" OR "DM me your portfolio" OR "send your portfolio" OR "apply via DM") ("video editor" OR "AI artist" OR "creator") -is:retweet lang:en',

    # Tool-specific skill requirements (indicates a real project brief)
    '("looking for" OR "hiring") ("Midjourney" OR "Runway" OR "Sora" OR "CapCut" OR "Premiere Pro") ("for our" OR "for a brand" OR "for a client" OR "for a campaign") -is:retweet lang:en',

    # Ecom/brand-style ad creation requests
    '("looking for" OR "need") ("video ads" OR "ad creatives" OR "UGC" OR "product videos") ("brand" OR "ecommerce" OR "Shopify" OR "dropshipping") -is:retweet lang:en',

    # Social media / content manager hiring
    '("hiring" OR "looking for") ("social media manager" OR "content manager" OR "content strategist") ("AI" OR "video" OR "reels" OR "shorts") -is:retweet lang:en',


    # ── TIER 3: Moderate signals — recommendation-seeking from decision-makers ─

    # "Can anyone recommend" — often founders/managers, not jobseekers
    '("can anyone recommend" OR "anyone know a good" OR "looking to hire") ("video editor" OR "AI video creator" OR "motion designer") -"hire me" -"DM me" -is:retweet lang:en',

    # Referral-based hiring (businesses often use this)
    '("referrals welcome" OR "open to referrals" OR "know anyone who") ("video editor" OR "AI creator" OR "content creator") -is:retweet lang:en',
]


# ── NEGATIVE FILTERS to apply post-scrape (add to your filtering logic) ─────

EXCLUDE_PATTERNS = [
    # Freelancer self-promotion
    "DM me if you need",
    "hire me",
    "available for work",
    "open for commissions",
    "open for work",
    "my portfolio",
    "check out my work",
    "I'm a video editor",
    "I edit videos",
    "services starting at",

    # Platforms that attract jobseekers, not employers
    "Fiverr",
    "#FreelanceLife",
    "#HireMe",
    "#OpenForWork",
    "#EditorForHire",

    # Anti-AI debates / off-topic
    "AI art is theft",
    "AI art debate",
    "stolen art",
    "against AI",
]

# ── POST-SCRAPE BUSINESS SIGNAL SCORING ──────────────────────────────────────
# Boost score for posts that contain any of:
BUSINESS_SIGNALS = [
    "our team",
    "our brand",
    "our agency",
    "our startup",
    "full-time",
    "part-time",
    "monthly retainer",
    "per video",
    "budget:",
    "we're hiring",
    "now hiring",
    "join us",
    "paid role",
    "apply",
    "portfolio required",
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

# MAX_TWEET_AGE_DAYS 
MAX_TWEET_AGE_DAYS = 7 
