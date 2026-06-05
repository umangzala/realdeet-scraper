#!/bin/bash
# push_to_github.sh — Creates private GitHub repo and pushes all files
# Run once from inside the realdeet-scraper folder:
#   chmod +x push_to_github.sh && ./push_to_github.sh
set -e

USERNAME="umangzala"
REPO="realdeet-scraper"

echo ""
echo "🐙 Step 1/4 — Creating private GitHub repo..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d "{\"name\":\"$REPO\",\"description\":\"Twitter requirement scraper for Realdeet — collects AI artist and video creator hiring posts\",\"private\":true,\"auto_init\":false}")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "201" ]; then
  echo "✅ Repo created: https://github.com/$USERNAME/$REPO"
elif [ "$HTTP_CODE" = "422" ]; then
  echo "ℹ️  Repo already exists — continuing with push"
else
  echo "❌ Failed to create repo (HTTP $HTTP_CODE)"
  echo "$RESPONSE"
  exit 1
fi

echo ""
echo "🗂  Step 2/4 — Initialising git..."
cd "$(dirname "$0")"
git init
git add .

echo ""
echo "💾 Step 3/4 — Committing files..."
git commit -m "Initial commit: Realdeet Twitter scraper

Files:
- main.py          FastAPI app + APScheduler (scrapes every 30 min)
- twitter_client.py  twikit wrapper (no API key needed)
- classifier.py    GPT-4o-mini intent classifier
- database.py      Supabase client
- config.py        Search queries and settings
- schema.sql       Supabase table definitions
- requirements.txt
- .env.example
- .gitignore"

echo ""
echo "🚀 Step 4/4 — Pushing to GitHub..."
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "https://$USERNAME:$TOKEN@github.com/$USERNAME/$REPO.git"
git push -u origin main

echo ""
echo "✅ Done! Your repo is live:"
echo "   https://github.com/$USERNAME/$REPO"
echo ""
echo "⚠️  Security: revoke this token now that the push is done →"
echo "   https://github.com/settings/tokens"
