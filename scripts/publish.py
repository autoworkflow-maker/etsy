import os
import json
import requests
from datetime import datetime

ETSY_REFRESH_TOKEN = os.getenv("ETSY_REFRESH_TOKEN")
ETSY_ACCESS_TOKEN  = os.getenv("ETSY_ACCESS_TOKEN")
ETSY_SHOP_ID       = os.getenv("ETSY_SHOP_ID")
SHOPIFY_STORE      = os.getenv("SHOPIFY_STORE")
SHOPIFY_TOKEN      = os.getenv("SHOPIFY_TOKEN")
BLOGGER_BLOG_ID    = os.getenv("BLOGGER_BLOG_ID")
BLOGGER_TOKEN      = os.getenv("BLOGGER_OAUTH_TOKEN")
BUFFER_TOKEN       = os.getenv("BUFFER_TOKEN")
ETSY_API_KEY = os.getenv("ETSY_API_KEY") or os.getenv("ETSY_KEYSTRING")
ETSY_SHARED_SECRET = os.getenv("ETSY_SHARED_SECRET")

# ── Etsy ──────────────────────────────────────────────────────
# ── Etsy ──────────────────────────────────────────────────────

def refresh_etsy_token():
    url = "https://api.etsy.com/v3/public/oauth/token"

    headers = {
        "x-api-key": f"{ETSY_API_KEY}:{ETSY_SHARED_SECRET}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        "grant_type": "refresh_token",
        "client_id": ETSY_API_KEY,
        "refresh_token": ETSY_REFRESH_TOKEN
    }

    response = requests.post(url, headers=headers, data=payload)
    result = response.json()

    if "access_token" in result:
        print("  Etsy token refreshed")
        return result["access_token"]

    print("  Etsy refresh error:", result)
    return ETSY_ACCESS_TOKEN

def publish_to_etsy(product):
    if not ETSY_ACCESS_TOKEN:
        print("  No Etsy token — skipping")
        return None

    print("  API Key loaded:", bool(ETSY_API_KEY))
    print("  Shared Secret loaded:", bool(ETSY_SHARED_SECRET))
    print("  Shop ID loaded:", bool(ETSY_SHOP_ID))

    if ETSY_API_KEY:
        print("  API Key length:", len(ETSY_API_KEY))

    if ETSY_SHARED_SECRET:
        print("  Secret length:", len(ETSY_SHARED_SECRET))

    headers = {
        "x-api-key": f"{ETSY_API_KEY}:{ETSY_SHARED_SECRET}",
        "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}"
    }

    headers = {
        "x-api-key": f"{ETSY_API_KEY}:{ETSY_SHARED_SECRET}",
        "Authorization": f"Bearer {ETSY_ACCESS_TOKEN}"
    }

    payload = {
        "title": product["etsy_title"][:140],
        "description": product["etsy_description"],
        "price": product.get("suggested_price", 9.00),
        "quantity": 999,
        "tags": product["etsy_tags"][:13],
        "taxonomy_id": 2078,
        "type": "download",
        "digital": True,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "is_supply": False
    }

    url = f"https://openapi.etsy.com/v3/application/shops/{ETSY_SHOP_ID}/listings"
    response = requests.post(url, headers=headers, data=payload)
    result = response.json()

    if "listing_id" in result:
        listing_id = result["listing_id"]
        print(f"  Etsy listing created: {listing_id}")

        if product.get("pdf_url"):
            print(f"  Note: attach PDF manually or via multipart upload to listing {listing_id}")

        return listing_id

    print(f"  Etsy error: {result}")
    return None

# ── Shopify ───────────────────────────────────────────────────

def publish_to_shopify(product):
    if not SHOPIFY_STORE:
        print("  No Shopify config — skipping")
        return None

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }

    description = f"""
{product['etsy_description']}
<hr>
<p><strong>Instant download:</strong> <a href="{product.get('pdf_url', '#')}">Click here to download your guide</a></p>
<p><small>Affiliate disclosure: this product may contain affiliate links.</small></p>
"""

    payload = {
        "product": {
            "title":      product["etsy_title"][:255],
            "body_html":  description,
            "vendor":     "AI Tools Daily",
            "product_type": "Digital Guide",
            "tags":       ", ".join(product["etsy_tags"]),
            "status":     "active",
            "variants": [{
                "price":             str(product.get("suggested_price", 9.00)),
                "compare_at_price":  "29.00",
                "inventory_management": None,
                "fulfillment_service":  "manual",
                "requires_shipping":    False,
                "taxable":              True
            }],
            "images": [{"src": product["pin_url"]}] if product.get("pin_url") else []
        }
    }

    url      = f"https://{SHOPIFY_STORE}/admin/api/2024-01/products.json"
    response = requests.post(url, headers=headers, json=payload)
    result   = response.json()

    if "product" in result:
        pid = result["product"]["id"]
        print(f"  Shopify product created: {pid}")
        return pid
    else:
        print(f"  Shopify error: {result}")
        return None


# ── Blogger ───────────────────────────────────────────────────

def publish_to_blogger(product):
    if not BLOGGER_TOKEN:
        print("  No Blogger token — skipping")
        return None

    headers = {
        "Authorization": f"Bearer {BLOGGER_TOKEN}",
        "Content-Type":  "application/json"
    }

    article_html = f"""
<h2>{product['etsy_title']}</h2>
<p>{product['etsy_description']}</p>
<hr>
<p><strong>Get this guide:</strong> <a href="#">Download for ${product.get('suggested_price', 9.00)}</a></p>
<p><small>Affiliate disclosure included.</small></p>
"""

    payload = {
        "kind":    "blogger#post",
        "title":   f"{product['etsy_title']} — Review {datetime.now().year}",
        "content": article_html,
        "labels":  product["etsy_tags"][:5]
    }

    url      = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/"
    response = requests.post(url, headers=headers, json=payload)
    result   = response.json()

    if "url" in result:
        print(f"  Blogger post: {result['url']}")
        return result["url"]
    else:
        print(f"  Blogger error: {result}")
        return None


# ── Buffer (social posts) ─────────────────────────────────────

def queue_social_post(product):
    if not BUFFER_TOKEN:
        print("  No Buffer token — skipping social post")
        return None

    headers = {
        "Authorization": f"Bearer {BUFFER_TOKEN}",
        "Content-Type":  "application/json"
    }

    # Get profile IDs first (run once and hardcode for speed)
    profiles_url = "https://api.bufferapp.com/1/profiles.json"
    profiles     = requests.get(profiles_url, headers=headers).json()

    if not profiles:
        print("  No Buffer profiles found")
        return None

    profile_ids = [p["id"] for p in profiles[:3]]  # Max 3 on free plan
    post_text   = product.get("social_post", f"New guide: {product['etsy_title']}")

    payload = {
        "text":        post_text,
        "profile_ids": profile_ids,
        "media":       {"link": product.get("pdf_url", ""), "photo": product.get("pin_url", "")}
    }

    url      = "https://api.bufferapp.com/1/updates/create.json"
    response = requests.post(url, headers=headers, json=payload)
    result   = response.json()

    if result.get("success"):
        print(f"  Buffer post queued for {len(profile_ids)} channels")
        return True
    else:
        print(f"  Buffer error: {result}")
        return None


# ── Main ──────────────────────────────────────────────────────

def run():
    print(f"Publishing started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with open("data/created_today.json", "r") as f:
        products = json.load(f)

    global ETSY_ACCESS_TOKEN
    ETSY_ACCESS_TOKEN = refresh_etsy_token()

    published = []

    for product in products:
        print(f"\nPublishing: {product['keyword']}")

        etsy_id    = publish_to_etsy(product)
        shopify_id = publish_to_shopify(product)
        blogger_url = publish_to_blogger(product)
        queue_social_post(product)

        published.append({
            "keyword":     product["keyword"],
            "etsy_id":     etsy_id,
            "shopify_id":  shopify_id,
            "blogger_url": blogger_url,
            "published_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    with open("data/published.json", "w") as f:
        json.dump(published, f, indent=2)

    print(f"\nPublished {len(published)} products across all platforms")


if __name__ == "__main__":
    run()
