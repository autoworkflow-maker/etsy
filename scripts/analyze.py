import os
import json
from anthropic import Anthropic
from datetime import datetime

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SCORE_THRESHOLD = 25  # Products with total score >= 25 get made today


def score_trends(trends):
    """Send trends to Claude Haiku for fast, cheap scoring"""

    # Batch into groups of 10 to stay within token limits
    batches  = [trends[i:i+10] for i in range(0, len(trends), 10)]
    all_scored = []

    for i, batch in enumerate(batches):
        print(f"  Scoring batch {i+1}/{len(batches)}...")

        prompt = f"""You are a digital product market analyst for Etsy.

Score each product idea on four dimensions (0-10 each):
1. revenue_potential: avg price × realistic monthly sales volume
2. daily_utility: how often will a buyer re-use this? (planners > art)
3. competition_gap: how easy to differentiate? (low listings = better)
4. trend_momentum: is search volume rising right now?

Rules:
- competition 'low' = score competition_gap 8-10
- competition 'medium' = score competition_gap 5-7
- competition 'high' = score competition_gap 1-4
- reddit_signal=true adds +2 to trend_momentum
- trend_direction='rising' adds +2 to trend_momentum

Mark make_today: true for any product with total >= {SCORE_THRESHOLD}

Return ONLY a JSON array, no explanation, no markdown:
[{{"keyword":"...","scores":{{"revenue":8,"utility":9,"competition":6,"momentum":8}},"total":31,"make_today":true,"product_type":"PDF planner","suggested_price":4.99,"niche_angle":"be specific here e.g. ADHD weekly planner for remote workers"}}]

Today's trends to score:
{json.dumps(batch, indent=2)}
"""

        response = client.messages.create(
            model="claude-haiku-4-5",   # Fast + cheap for scoring
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            scored = json.loads(raw)
            all_scored.extend(scored)
        except json.JSONDecodeError as e:
            print(f"  JSON parse error in batch {i+1}: {e}")
            print(f"  Raw response: {raw[:200]}")

    return all_scored


def pick_todays_products(scored):
    """Filter to only products marked for creation today, sorted by score"""
    picks = [p for p in scored if p.get("make_today")]
    picks.sort(key=lambda x: x.get("total", 0), reverse=True)
    return picks[:5]  # Max 5 products per day to stay within API budget


def run():
    print(f"Analysis started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with open("data/trends.json", "r") as f:
        trends = json.load(f)

    print(f"Scoring {len(trends)} trends...")
    scored = score_trends(trends)

    os.makedirs("data", exist_ok=True)
    with open("data/scored.json", "w") as f:
        json.dump(scored, f, indent=2)

    picks = pick_todays_products(scored)

    with open("data/todays_picks.json", "w") as f:
        json.dump(picks, f, indent=2)

    print(f"\nToday's picks ({len(picks)} products to create):")
    for p in picks:
        print(f"  [{p.get('total', 0)}/40] {p['keyword']} — {p.get('product_type')} @ ${p.get('suggested_price')}")

    print(f"\nSaved to data/todays_picks.json")


if __name__ == "__main__":
    run()
