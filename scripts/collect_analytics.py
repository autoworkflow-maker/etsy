import os
import json
import requests
from datetime import datetime, timedelta
from anthropic import Anthropic

client        = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
ETSY_TOKEN    = os.getenv("ETSY_ACCESS_TOKEN")
ETSY_SHOP_ID  = os.getenv("ETSY_SHOP_ID")


# ── Collect analytics ─────────────────────────────────────────

def get_shopify_orders(days_back=1):
    since   = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00Z")
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
    url     = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders.json?created_at_min={since}&status=any&limit=250"
    resp    = requests.get(url, headers=headers)
    orders  = resp.json().get("orders", [])

    revenue = sum(float(o["total_price"]) for o in orders)
    return {"orders": len(orders), "revenue": round(revenue, 2), "raw": orders}


def get_shopify_products():
    headers  = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
    url      = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json?limit=250&status=active"
    resp     = requests.get(url, headers=headers)
    return resp.json().get("products", [])


def get_product_sales_30d(product_id):
    since   = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00Z")
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
    url     = f"https://{SHOPIFY_STORE}/admin/api/2024-01/orders.json?status=any&created_at_min={since}&limit=250"
    orders  = requests.get(url, headers=headers).json().get("orders", [])

    count, revenue = 0, 0.0
    for order in orders:
        for item in order.get("line_items", []):
            if str(item.get("product_id")) == str(product_id):
                count   += 1
                revenue += float(item.get("price", 0))
    return count, round(revenue, 2)


# ── Smart sales manager ───────────────────────────────────────

def classify_and_update_products():
    products = get_shopify_products()
    actions  = []

    for product in products:
        pid        = product["id"]
        title      = product["title"]
        created_at = product.get("created_at", datetime.now().isoformat())
        variant    = product["variants"][0] if product.get("variants") else {}
        variant_id = variant.get("id")
        price      = float(variant.get("price", 9.00))
        days_old   = (datetime.now() - datetime.strptime(created_at[:10], "%Y-%m-%d")).days

        sales_30d, rev_30d = get_product_sales_30d(pid)
        sales_7d,  _       = get_product_sales_30d(pid)  # reuse with 7-day logic below

        # Classification
        if days_old < 7:
            cls = "NEW"
        elif sales_7d >= 5:
            cls = "BESTSELLER"
        elif sales_7d >= 2:
            cls = "GROWING"
        elif sales_30d == 0 and days_old > 14:
            cls = "DEAD"
        else:
            cls = "SLOW"

        # Decide action
        if cls == "BESTSELLER":
            new_price  = round(min(price * 1.2, 19.99), 2)
            new_status = "active"
            suffix     = " ⭐ Bestseller"
        elif cls == "GROWING":
            new_price  = price
            new_status = "active"
            suffix     = " 🔥 Popular"
        elif cls == "SLOW":
            new_price  = round(price * 0.80, 2)
            new_status = "active"
            suffix     = " — 20% Off"
        elif cls == "DEAD":
            new_price  = round(price * 0.50, 2)
            new_status = "archived" if days_old > 21 else "active"
            suffix     = " — 50% Off"
        else:  # NEW
            new_price  = price
            new_status = "active"
            suffix     = ""

        # Clean old suffixes
        clean_title = title
        for old in [" ⭐ Bestseller", " 🔥 Popular", " — 20% Off", " — 50% Off", " — New"]:
            clean_title = clean_title.replace(old, "")
        new_title = clean_title + suffix

        # Apply update
        if cls != "NEW":
            headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}
            payload = {"product": {
                "id": pid, "title": new_title, "status": new_status,
                "variants": [{"id": variant_id, "price": str(new_price)}]
            }}
            requests.put(f"https://{SHOPIFY_STORE}/admin/api/2024-01/products/{pid}.json",
                        headers=headers, json=payload)

            # Rewrite description for dead products
            if cls == "DEAD":
                prompt = f"Rewrite a Shopify product description for '{clean_title}'. It has low sales. Focus on value and urgency. Clean HTML only, 3 paragraphs, one CTA. No fake claims."
                resp   = client.messages.create(
                    model="claude-sonnet-4-6", max_tokens=400,
                    messages=[{"role": "user", "content": prompt}]
                )
                new_desc = resp.content[0].text.replace("```html","").replace("```","").strip()
                requests.put(f"https://{SHOPIFY_STORE}/admin/api/2024-01/products/{pid}.json",
                            headers=headers,
                            json={"product": {"id": pid, "body_html": new_desc}})

        actions.append({
            "product_id":     pid,
            "title":          clean_title,
            "days_old":       days_old,
            "sales_30d":      sales_30d,
            "revenue_30d":    rev_30d,
            "classification": cls,
            "new_price":      new_price,
            "new_status":     new_status
        })

        print(f"  {cls:12} | {clean_title[:40]} | ${new_price} | {days_old}d old | {sales_30d} sales")

    return actions


# ── Winner queue ──────────────────────────────────────────────

def score_winners(actions):
    winners = []
    for a in actions:
        if a["classification"] in ["BESTSELLER", "GROWING"]:
            winners.append({
                "keyword":    a["title"],
                "priority":   "high" if a["classification"] == "BESTSELLER" else "medium",
                "action":     "create_variants",
                "revenue_30d": a["revenue_30d"]
            })
        elif a["classification"] == "DEAD":
            winners.append({
                "keyword":    a["title"],
                "priority":   "low",
                "action":     "delist_if_no_change",
                "revenue_30d": 0
            })
    return winners


# ── Dashboard ─────────────────────────────────────────────────

def generate_dashboard(today_data, actions, winners):
    today    = datetime.now().strftime("%Y-%m-%d")
    cls_count = {}
    for a in actions:
        cls_count[a["classification"]] = cls_count.get(a["classification"], 0) + 1

    md = f"""# 📊 Digital Product Pipeline Dashboard
**Updated:** {today}

---

## Today's Revenue
| Metric | Value |
|--------|-------|
| Orders today | {today_data['orders']} |
| Revenue today | ${today_data['revenue']} |

---

## Product Health
| Status | Count |
|--------|-------|
| ⭐ Bestseller | {cls_count.get('BESTSELLER', 0)} |
| 🔥 Growing | {cls_count.get('GROWING', 0)} |
| 🆕 New | {cls_count.get('NEW', 0)} |
| 🐌 Slow | {cls_count.get('SLOW', 0)} |
| ❌ Dead/Archived | {cls_count.get('DEAD', 0)} |

---

## Winner Queue (for tomorrow's research)
"""
    for w in winners[:5]:
        md += f"- **{w['keyword'][:50]}** — {w['action']} ({w['priority']} priority)\n"

    md += f"\n---\n*Generated automatically by Pipeline Bot*\n"

    with open("data/DASHBOARD.md", "w") as f:
        f.write(md)

    print("  Dashboard saved to data/DASHBOARD.md")


# ── Main ──────────────────────────────────────────────────────

def run():
    print(f"Analytics started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print("\nPulling today's orders...")
    today_data = get_shopify_orders(days_back=1)
    print(f"  Orders: {today_data['orders']} | Revenue: ${today_data['revenue']}")

    print("\nRunning smart sales manager...")
    actions = classify_and_update_products()

    print("\nScoring winners...")
    winners = score_winners(actions)

    print("\nGenerating dashboard...")
    generate_dashboard(today_data, actions, winners)

    analytics = {
        "date":          datetime.now().strftime("%Y-%m-%d"),
        "today_orders":  today_data["orders"],
        "today_revenue": today_data["revenue"],
        "products":      actions
    }

    with open("data/analytics.json", "w") as f:
        json.dump(analytics, f, indent=2)

    with open("data/winner_queue.json", "w") as f:
        json.dump(winners, f, indent=2)

    print(f"\nDone — {len(actions)} products reviewed, {len(winners)} in winner queue")
    print(f"Revenue today: ${today_data['revenue']}")


if __name__ == "__main__":
    run()
