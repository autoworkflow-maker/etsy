# Digital Product Pipeline

Fully automated digital product creation and publishing system.
Built with Python, Claude AI, GitHub Actions.

## What it does daily (automatic)

1. **2:00 AM** — Research trending products (Etsy, Google Trends, Reddit)
2. **~2:05 AM** — AI scores every trend (Claude Haiku — fast + cheap)
3. **~2:10 AM** — Creates PDF guides + Pinterest images (Claude Sonnet)
4. **~2:20 AM** — Publishes to Etsy, Shopify, Blogger, Buffer social
5. **10:00 PM** — Collects analytics, updates product prices, generates dashboard

## Setup

### 1. Add GitHub Secrets (Settings → Secrets → Actions)

| Secret | Where to get it |
|--------|----------------|
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `ETSY_API_KEY` | developers.etsy.com |
| `ETSY_SHOP_ID` | Your Etsy shop URL |
| `ETSY_ACCESS_TOKEN` | Etsy OAuth flow |
| `REDDIT_CLIENT_ID` | reddit.com/prefs/apps |
| `REDDIT_SECRET` | reddit.com/prefs/apps |
| `SHOPIFY_STORE` | yourstore.myshopify.com |
| `SHOPIFY_TOKEN` | Shopify Admin API |
| `BLOGGER_BLOG_ID` | Blogger Settings |
| `BLOGGER_OAUTH_TOKEN` | Google OAuth |
| `BUFFER_TOKEN` | buffer.com/app/account |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary Dashboard |
| `CLOUDINARY_API_KEY` | Cloudinary Dashboard |
| `CLOUDINARY_API_SECRET` | Cloudinary Dashboard |

### 2. Edit your niche

Open `scripts/research.py` and update `NICHE_KEYWORDS` with your target products.

### 3. Test manually

Go to Actions tab → pick any workflow → click "Run workflow"

## Folder structure

```
.github/workflows/   — GitHub Actions (auto-run daily)
scripts/             — Python scripts (one per stage)
data/                — JSON files shared between stages
products/            — Generated product files (by date)
```

## Cost

~$8–15/month total. Break-even at 2-3 sales.
