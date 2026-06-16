import os
import json
import time
import requests
from datetime import datetime

# Optional imports — install as needed
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

ETSY_API_KEY       = os.getenv("ETSY_API_KEY")
ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")
REDDIT_CLIENT_ID   = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET      = os.getenv("REDDIT_SECRET")

# ── Niche configuration — edit these to match your niche ──────
NICHE_KEYWORDS = [
    "adhd planner printable",
    "budget tracker pdf",
    "notion template",
    "ai prompt pack",
    "habit tracker printable",
    "productivity planner",
    "weekly planner printable",
    "social media caption pack",
    "resume template",
    "party printable"
]


def scrape_etsy_trends():
    """Pull trending search terms and listing data from Etsy API"""
    if not ETSY_API_KEY:
        print("No Etsy API key — skipping Etsy scrape")
        return []

    results = []
    headers = {"x-api-key": f"{ETSY_API_KEY}:{ETSY_SHARED_SECRET}"}

    for keyword in NICHE_KEYWORDS:
        try:
            url = f"https://openapi.etsy.com/v3/application/listings/active"
            params = {
                "keywords":    keyword,
                "limit":       10,
                "sort_on":     "score",
                "sort_order":  "desc"
            }
            response = requests.get(url, headers=headers, params=params)
            data     = response.json()

            listings = data.get("results", [])
            if listings:
                prices = [float(l.get("price", {}).get("amount", 0)) / 100
                          for l in listings if l.get("price")]
                avg_price = round(sum(prices) / len(prices), 2) if prices else 0

                results.append({
                    "keyword":         keyword,
                    "etsy_listings":   data.get("count", 0),
                    "avg_price_usd":   avg_price,
                    "source":          ["etsy"],
                    "score":           None
                })
            time.sleep(1)  # Respect rate limits

        except Exception as e:
            print(f"Etsy error for '{keyword}': {e}")

    return results


def scrape_google_trends():
    """Get rising search queries using pytrends"""
    if not PYTRENDS_AVAILABLE:
        print("pytrends not installed — skipping Google Trends")
        return []

    results = []
    try:
        pytrends = TrendReq(hl="en-US", tz=360)

        for keyword in NICHE_KEYWORDS[:5]:  # Limit to avoid rate limits
            try:
                pytrends.build_payload([keyword], timeframe="now 30-d")
                interest = pytrends.interest_over_time()

                if not interest.empty:
                    avg_interest = int(interest[keyword].mean())
                    trend        = "rising" if interest[keyword].iloc[-1] > interest[keyword].iloc[0] else "stable"

                    results.append({
                        "keyword":           keyword,
                        "monthly_searches":  avg_interest * 100,
                        "trend_direction":   trend,
                        "source":            ["google_trends"]
                    })
                time.sleep(10)  # Google Trends rate limit

            except Exception as e:
                print(f"Google Trends error for '{keyword}': {e}")

    except Exception as e:
        print(f"pytrends setup error: {e}")

    return results


def scrape_reddit():
    """Pull trending product discussions from relevant subreddits"""
    if not PRAW_AVAILABLE or not REDDIT_CLIENT_ID:
        print("Reddit not configured — skipping")
        return []

    results = []
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_SECRET,
            user_agent="DigitalProductPipeline/1.0"
        )

        subreddits = ["Etsy", "DigitalNomad", "Entrepreneur", "sidehustle"]

        for sub_name in subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for post in sub.hot(limit=10):
                    title_lower = post.title.lower()
                    for keyword in NICHE_KEYWORDS:
                        if keyword.split()[0] in title_lower:
                            results.append({
                                "keyword":  keyword,
                                "source":   ["reddit"],
                                "reddit_upvotes": post.score,
                                "reddit_post": post.title[:100]
                            })
                time.sleep(2)

            except Exception as e:
                print(f"Reddit error for r/{sub_name}: {e}")

    except Exception as e:
        print(f"Reddit setup error: {e}")

    return results


def merge_sources(etsy_data, google_data, reddit_data):
    """Combine all sources into unified trends list"""
    merged = {}

    for item in etsy_data:
        kw = item["keyword"]
        merged[kw] = item.copy()

    for item in google_data:
        kw = item["keyword"]
        if kw in merged:
            merged[kw]["monthly_searches"] = item.get("monthly_searches", 0)
            merged[kw]["trend_direction"]  = item.get("trend_direction", "stable")
            merged[kw]["source"].append("google_trends")
        else:
            merged[kw] = item.copy()

    for item in reddit_data:
        kw = item["keyword"]
        if kw in merged:
            merged[kw].setdefault("source", []).append("reddit")
            merged[kw]["reddit_signal"] = True
        else:
            merged[kw] = item.copy()

    # Fill defaults for any missing fields
    for kw, data in merged.items():
        data.setdefault("etsy_listings",   0)
        data.setdefault("avg_price_usd",   4.99)
        data.setdefault("monthly_searches", 0)
        data.setdefault("trend_direction", "stable")
        data.setdefault("competition",     "unknown")
        data.setdefault("reddit_signal",   False)
        data.setdefault("score",           None)

        # Classify competition
        listings = data["etsy_listings"]
        if listings < 500:
            data["competition"] = "low"
        elif listings < 2000:
            data["competition"] = "medium"
        else:
            data["competition"] = "high"

    return list(merged.values())


def run():
    print(f"Research started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print("Scraping Etsy...")
    etsy_data   = scrape_etsy_trends()
    print(f"  Found {len(etsy_data)} Etsy trends")

    print("Scraping Google Trends...")
    google_data = scrape_google_trends()
    print(f"  Found {len(google_data)} Google trends")

    print("Scraping Reddit...")
    reddit_data = scrape_reddit()
    print(f"  Found {len(reddit_data)} Reddit signals")

    print("Merging sources...")
    trends = merge_sources(etsy_data, google_data, reddit_data)

    os.makedirs("data", exist_ok=True)
    with open("data/trends.json", "w") as f:
        json.dump(trends, f, indent=2)

    print(f"Done — saved {len(trends)} trends to data/trends.json")


if __name__ == "__main__":
    run()
