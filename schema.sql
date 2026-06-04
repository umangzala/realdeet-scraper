-- schema.sql — Run this in Supabase SQL Editor to set up tables

-- ── Profiles (Twitter poster info) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    twitter_id      TEXT UNIQUE NOT NULL,
    handle          TEXT NOT NULL,
    display_name    TEXT,
    bio             TEXT,
    followers       INTEGER DEFAULT 0,
    following       INTEGER DEFAULT 0,
    tweet_count     INTEGER DEFAULT 0,
    account_created_at TEXT,
    website         TEXT,
    verified        BOOLEAN DEFAULT FALSE,
    profile_image_url TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Posts (captured tweets that are genuine requirements) ────────────────────
CREATE TABLE IF NOT EXISTS posts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tweet_id            TEXT UNIQUE NOT NULL,
    profile_id          UUID REFERENCES profiles(id) ON DELETE CASCADE,
    text                TEXT NOT NULL,
    posted_at           TEXT,
    url                 TEXT,

    -- Engagement
    likes               INTEGER DEFAULT 0,
    retweets            INTEGER DEFAULT 0,
    replies             INTEGER DEFAULT 0,

    -- Classification
    category            TEXT CHECK (category IN ('ai_image', 'ai_video', 'video_edit', 'other')),
    urgency             TEXT CHECK (urgency IN ('high', 'medium', 'low')) DEFAULT 'low',
    has_budget_signal   BOOLEAN DEFAULT FALSE,
    is_brand_or_business BOOLEAN DEFAULT FALSE,
    summary             TEXT,

    -- Lead status (for Realdeet BD team)
    status              TEXT CHECK (status IN ('new', 'contacted', 'converted', 'ignored')) DEFAULT 'new',
    notes               TEXT,
    assigned_to         TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_urgency ON posts(urgency);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_profile_id ON posts(profile_id);

-- ── Auto-update updated_at on profiles ───────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
